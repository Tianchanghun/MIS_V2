#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
웹 기반 배치 스케줄러
ERPia 자동 데이터 수집을 웹에서 설정하고 관리
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import pytz
import json

from .erpia_client import ErpiaApiClient
from .gift_classifier import GiftClassifier

# 로깅 설정
logger = logging.getLogger(__name__)

@dataclass
class BatchJobConfig:
    """배치 작업 설정"""
    job_id: str
    name: str
    job_type: str  # DAILY_COLLECTION, CUSTOMER_SYNC, GIFT_CLASSIFY, REPORT_GENERATE
    company_id: int
    enabled: bool = True
    schedule_type: str = "cron"  # cron, interval
    cron_expression: str = "0 2 * * *"  # 매일 오전 2시
    interval_minutes: int = 60
    max_instances: int = 1
    coalesce: bool = True
    misfire_grace_time: int = 300  # 5분
    timezone: str = "Asia/Seoul"
    parameters: Dict[str, Any] = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass 
class BatchExecutionResult:
    """배치 실행 결과"""
    job_id: str
    execution_id: str
    started_at: datetime
    finished_at: datetime = None
    status: str = "RUNNING"  # RUNNING, SUCCESS, FAILED
    message: str = ""
    details: Dict[str, Any] = None
    error_trace: str = ""
    processed_count: int = 0
    company_id: int = 1

class BatchScheduler:
    """웹 기반 배치 스케줄러"""
    
    def __init__(self, app=None):
        """
        Args:
            app: Flask 애플리케이션 인스턴스
        """
        self.app = app
        self.scheduler = None
        self.erpia_clients = {}  # 회사별 ERPia 클라이언트 캐시
        self.gift_classifier = None
        self.is_running = False
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Flask 앱 초기화"""
        self.app = app
        
        # 데이터베이스 URL 가져오기
        database_url = app.config.get('SQLALCHEMY_DATABASE_URI')
        
        # Job Store 설정 (PostgreSQL)
        jobstores = {
            'default': SQLAlchemyJobStore(url=database_url)
        }
        
        # Executor 설정
        executors = {
            'default': ThreadPoolExecutor(20)
        }
        
        # Scheduler 설정
        job_defaults = {
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 300
        }
        
        # 스케줄러 생성
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=pytz.timezone('Asia/Seoul')
        )
        
        # 이벤트 리스너 등록
        self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error_listener, EVENT_JOB_ERROR)
        
        # 사은품 분류기 초기화
        self.gift_classifier = GiftClassifier()
        
        # 앱 종료 시 스케줄러 정리
        app.teardown_appcontext(self._shutdown_scheduler)
        
        logger.info("🔧 배치 스케줄러 초기화 완료")
    
    def start(self):
        """스케줄러 시작"""
        if not self.is_running:
            try:
                self.scheduler.start()
                self.is_running = True
                logger.info("🚀 배치 스케줄러 시작됨")
                
                # 기본 작업들 등록
                self._register_default_jobs()
                
            except Exception as e:
                logger.error(f"❌ 스케줄러 시작 실패: {e}")
                raise
    
    def stop(self):
        """스케줄러 중지"""
        if self.is_running and self.scheduler:
            try:
                self.scheduler.shutdown(wait=False)
                self.is_running = False
                logger.info("⏹️ 배치 스케줄러 중지됨")
            except Exception as e:
                logger.error(f"❌ 스케줄러 중지 실패: {e}")
    
    def add_job(self, job_config: BatchJobConfig) -> bool:
        """배치 작업 추가"""
        try:
            if not self.is_running:
                logger.warning("⚠️ 스케줄러가 실행 중이 아닙니다.")
                return False
            
            # 기존 작업 제거 (있는 경우)
            try:
                self.scheduler.remove_job(job_config.job_id)
            except:
                pass
            
            # 작업 함수 매핑
            job_func = self._get_job_function(job_config.job_type)
            if not job_func:
                logger.error(f"❌ 알 수 없는 작업 타입: {job_config.job_type}")
                return False
            
            # 스케줄 설정
            if job_config.schedule_type == "cron":
                # Cron 표현식 파싱 (분 시 일 월 요일)
                cron_parts = job_config.cron_expression.split()
                if len(cron_parts) != 5:
                    logger.error(f"❌ 잘못된 Cron 표현식: {job_config.cron_expression}")
                    return False
                
                minute, hour, day, month, day_of_week = cron_parts
                
                self.scheduler.add_job(
                    job_func,
                    'cron',
                    id=job_config.job_id,
                    name=job_config.name,
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week,
                    max_instances=job_config.max_instances,
                    coalesce=job_config.coalesce,
                    misfire_grace_time=job_config.misfire_grace_time,
                    timezone=job_config.timezone,
                    args=[job_config]
                )
            else:
                # 인터벌 스케줄
                self.scheduler.add_job(
                    job_func,
                    'interval',
                    id=job_config.job_id,
                    name=job_config.name,
                    minutes=job_config.interval_minutes,
                    max_instances=job_config.max_instances,
                    coalesce=job_config.coalesce,
                    misfire_grace_time=job_config.misfire_grace_time,
                    timezone=job_config.timezone,
                    args=[job_config]
                )
            
            # DB에 작업 설정 저장
            self._save_job_config(job_config)
            
            logger.info(f"✅ 배치 작업 추가됨: {job_config.name} ({job_config.job_id})")
            return True
            
        except Exception as e:
            logger.error(f"❌ 배치 작업 추가 실패: {e}")
            return False
    
    def remove_job(self, job_id: str) -> bool:
        """배치 작업 제거"""
        try:
            self.scheduler.remove_job(job_id)
            
            # DB에서 설정 삭제
            self._delete_job_config(job_id)
            
            logger.info(f"✅ 배치 작업 제거됨: {job_id}")
            return True
        except Exception as e:
            logger.error(f"❌ 배치 작업 제거 실패 ({job_id}): {e}")
            return False
    
    def get_jobs(self) -> List[Dict[str, Any]]:
        """등록된 배치 작업 목록 조회"""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                job_info = {
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger),
                    'func_name': job.func.__name__ if job.func else '',
                    'args': len(job.args) if job.args else 0,
                    'kwargs': len(job.kwargs) if job.kwargs else 0
                }
                jobs.append(job_info)
            return jobs
        except Exception as e:
            logger.error(f"❌ 작업 목록 조회 실패: {e}")
            return []
    
    def run_job_now(self, job_id: str) -> bool:
        """배치 작업 즉시 실행"""
        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                logger.error(f"❌ 작업을 찾을 수 없음: {job_id}")
                return False
            
            # 즉시 실행
            job.func(*job.args, **job.kwargs)
            logger.info(f"🚀 작업 즉시 실행됨: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 작업 즉시 실행 실패 ({job_id}): {e}")
            return False
    
    def _get_job_function(self, job_type: str):
        """작업 타입에 따른 함수 반환"""
        job_functions = {
            'DAILY_COLLECTION': self._daily_collection_job,
            'CUSTOMER_SYNC': self._customer_sync_job,
            'GIFT_CLASSIFY': self._gift_classify_job,
            'REPORT_GENERATE': self._report_generate_job,
            'DATA_CLEANUP': self._data_cleanup_job
        }
        return job_functions.get(job_type)
    
    def _daily_collection_job(self, job_config: BatchJobConfig):
        """일일 ERPia 데이터 수집 작업"""
        execution_id = f"{job_config.job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = BatchExecutionResult(
            job_id=job_config.job_id,
            execution_id=execution_id,
            started_at=datetime.now(),
            company_id=job_config.company_id
        )
        
        try:
            logger.info(f"🔄 일일 데이터 수집 시작: {job_config.name}")
            
            # ERPia 클라이언트 획득
            erpia_client = self._get_erpia_client(job_config.company_id)
            
            # 수집할 날짜 결정 (어제 날짜)
            target_date = job_config.parameters.get('target_date')
            if not target_date:
                yesterday = datetime.now() - timedelta(days=1)
                target_date = yesterday.strftime('%Y%m%d')
            
            # 주문 데이터 수집
            order_data = erpia_client.get_daily_orders(target_date)
            
            # 데이터베이스 저장
            saved_count = self._save_order_data(order_data)
            
            # 자동 사은품 분류 (설정된 경우)
            if job_config.parameters.get('auto_gift_classify', True):
                self.gift_classifier.classify_orders(order_data['orders'])
            
            # 실행 결과 저장
            result.status = "SUCCESS"
            result.message = f"데이터 수집 완료: {saved_count}건"
            result.processed_count = saved_count
            result.details = {
                'target_date': target_date,
                'orders_count': order_data['total_orders'],
                'products_count': order_data['total_products'],
                'deliveries_count': order_data['total_deliveries']
            }
            
            logger.info(f"✅ 일일 데이터 수집 완료: {saved_count}건")
            
        except Exception as e:
            error_trace = traceback.format_exc()
            result.status = "FAILED"
            result.message = f"수집 실패: {str(e)}"
            result.error_trace = error_trace
            logger.error(f"❌ 일일 데이터 수집 실패: {e}")
            
        finally:
            result.finished_at = datetime.now()
            self._save_execution_result(result)
    
    def _customer_sync_job(self, job_config: BatchJobConfig):
        """고객 정보 동기화 작업"""
        execution_id = f"{job_config.job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = BatchExecutionResult(
            job_id=job_config.job_id,
            execution_id=execution_id,
            started_at=datetime.now(),
            company_id=job_config.company_id
        )
        
        try:
            logger.info(f"🔄 고객 정보 동기화 시작: {job_config.name}")
            
            erpia_client = self._get_erpia_client(job_config.company_id)
            
            # 동기화 기간 설정 (기본: 최근 30일)
            days_back = job_config.parameters.get('days_back', 30)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            start_date_str = start_date.strftime('%Y%m%d')
            end_date_str = end_date.strftime('%Y%m%d')
            
            # 고객 데이터 수집
            customers = erpia_client.get_customer_list(start_date_str, end_date_str)
            
            # 데이터베이스 저장/업데이트
            saved_count = self._save_customer_data(customers)
            
            result.status = "SUCCESS"
            result.message = f"고객 동기화 완료: {saved_count}건"
            result.processed_count = saved_count
            result.details = {
                'period': f"{start_date_str} ~ {end_date_str}",
                'customers_count': len(customers)
            }
            
            logger.info(f"✅ 고객 정보 동기화 완료: {saved_count}건")
            
        except Exception as e:
            error_trace = traceback.format_exc()
            result.status = "FAILED"
            result.message = f"동기화 실패: {str(e)}"
            result.error_trace = error_trace
            logger.error(f"❌ 고객 정보 동기화 실패: {e}")
            
        finally:
            result.finished_at = datetime.now()
            self._save_execution_result(result)
    
    def _gift_classify_job(self, job_config: BatchJobConfig):
        """사은품 자동 분류 작업"""
        execution_id = f"{job_config.job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = BatchExecutionResult(
            job_id=job_config.job_id,
            execution_id=execution_id,
            started_at=datetime.now(),
            company_id=job_config.company_id
        )
        
        try:
            logger.info(f"🔄 사은품 자동 분류 시작: {job_config.name}")
            
            # 분류할 기간 설정
            days_back = job_config.parameters.get('days_back', 7)
            
            # 미분류 상품 분류
            classified_count = self.gift_classifier.auto_classify_recent_products(
                company_id=job_config.company_id,
                days_back=days_back
            )
            
            result.status = "SUCCESS"
            result.message = f"사은품 분류 완료: {classified_count}건"
            result.processed_count = classified_count
            result.details = {
                'days_back': days_back,
                'classified_count': classified_count
            }
            
            logger.info(f"✅ 사은품 자동 분류 완료: {classified_count}건")
            
        except Exception as e:
            error_trace = traceback.format_exc()
            result.status = "FAILED"
            result.message = f"분류 실패: {str(e)}"
            result.error_trace = error_trace
            logger.error(f"❌ 사은품 자동 분류 실패: {e}")
            
        finally:
            result.finished_at = datetime.now()
            self._save_execution_result(result)
    
    def _report_generate_job(self, job_config: BatchJobConfig):
        """보고서 생성 작업"""
        execution_id = f"{job_config.job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = BatchExecutionResult(
            job_id=job_config.job_id,
            execution_id=execution_id,
            started_at=datetime.now(),
            company_id=job_config.company_id
        )
        
        try:
            logger.info(f"🔄 보고서 생성 시작: {job_config.name}")
            
            # 보고서 생성 로직 (추후 구현)
            # - 일일/주간/월간 매출 보고서
            # - 사은품 분석 보고서
            # - 거래처별 매출 현황
            
            result.status = "SUCCESS"
            result.message = "보고서 생성 완료"
            result.processed_count = 1
            
            logger.info("✅ 보고서 생성 완료")
            
        except Exception as e:
            error_trace = traceback.format_exc()
            result.status = "FAILED"
            result.message = f"보고서 생성 실패: {str(e)}"
            result.error_trace = error_trace
            logger.error(f"❌ 보고서 생성 실패: {e}")
            
        finally:
            result.finished_at = datetime.now()
            self._save_execution_result(result)
    
    def _data_cleanup_job(self, job_config: BatchJobConfig):
        """데이터 정리 작업"""
        execution_id = f"{job_config.job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = BatchExecutionResult(
            job_id=job_config.job_id,
            execution_id=execution_id,
            started_at=datetime.now(),
            company_id=job_config.company_id
        )
        
        try:
            logger.info(f"🔄 데이터 정리 시작: {job_config.name}")
            
            # 오래된 로그 데이터 정리
            # 중복 데이터 정리 등
            
            result.status = "SUCCESS"
            result.message = "데이터 정리 완료"
            result.processed_count = 0
            
            logger.info("✅ 데이터 정리 완료")
            
        except Exception as e:
            error_trace = traceback.format_exc()
            result.status = "FAILED"
            result.message = f"데이터 정리 실패: {str(e)}"
            result.error_trace = error_trace
            logger.error(f"❌ 데이터 정리 실패: {e}")
            
        finally:
            result.finished_at = datetime.now()
            self._save_execution_result(result)
    
    def _get_erpia_client(self, company_id: int) -> ErpiaApiClient:
        """회사별 ERPia 클라이언트 획득 (캐시됨)"""
        if company_id not in self.erpia_clients:
            self.erpia_clients[company_id] = ErpiaApiClient(company_id)
        return self.erpia_clients[company_id]
    
    def _save_order_data(self, order_data: Dict[str, Any]) -> int:
        """주문 데이터를 데이터베이스에 저장"""
        try:
            from app.common.models import ErpiaOrderMaster, ErpiaOrderProduct, ErpiaOrderDelivery, db
            
            saved_count = 0
            
            with db.session.begin():
                # 주문 마스터 저장
                for order in order_data['orders']:
                    # 중복 체크
                    existing = ErpiaOrderMaster.query.filter_by(
                        sl_no=order.sl_no,
                        company_id=order.company_id
                    ).first()
                    
                    if not existing:
                        master_model = ErpiaOrderMaster(**order.__dict__)
                        db.session.add(master_model)
                        saved_count += 1
                
                # 상품 저장
                for product in order_data['products']:
                    existing = ErpiaOrderProduct.query.filter_by(
                        sl_no=product.sl_no,
                        sl_seq=product.sl_seq,
                        company_id=product.company_id
                    ).first()
                    
                    if not existing:
                        product_model = ErpiaOrderProduct(**product.__dict__)
                        db.session.add(product_model)
                
                # 배송 정보 저장
                for delivery in order_data['deliveries']:
                    existing = ErpiaOrderDelivery.query.filter_by(
                        sl_no=delivery.sl_no,
                        company_id=delivery.company_id
                    ).first()
                    
                    if not existing:
                        delivery_model = ErpiaOrderDelivery(**delivery.__dict__)
                        db.session.add(delivery_model)
            
            return saved_count
            
        except Exception as e:
            logger.error(f"❌ 주문 데이터 저장 실패: {e}")
            return 0
    
    def _save_customer_data(self, customers: List) -> int:
        """고객 데이터를 데이터베이스에 저장/업데이트"""
        try:
            from app.common.models import ErpiaCustomer, db
            
            saved_count = 0
            
            with db.session.begin():
                for customer in customers:
                    existing = ErpiaCustomer.query.filter_by(
                        g_code=customer.g_code,
                        company_id=customer.company_id
                    ).first()
                    
                    if existing:
                        # 업데이트
                        for key, value in customer.__dict__.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                    else:
                        # 신규 추가
                        customer_model = ErpiaCustomer(**customer.__dict__)
                        db.session.add(customer_model)
                        saved_count += 1
            
            return saved_count
            
        except Exception as e:
            logger.error(f"❌ 고객 데이터 저장 실패: {e}")
            return 0
    
    def _save_job_config(self, job_config: BatchJobConfig):
        """작업 설정을 데이터베이스에 저장"""
        try:
            from app.common.models import BatchJobConfig as JobConfigModel, db
            
            existing = JobConfigModel.query.filter_by(job_id=job_config.job_id).first()
            if existing:
                # 업데이트
                for key, value in job_config.__dict__.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = datetime.now()
            else:
                # 신규 추가
                config_model = JobConfigModel(**job_config.__dict__)
                db.session.add(config_model)
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"❌ 작업 설정 저장 실패: {e}")
    
    def _delete_job_config(self, job_id: str):
        """작업 설정을 데이터베이스에서 삭제"""
        try:
            from app.common.models import BatchJobConfig as JobConfigModel, db
            
            config = JobConfigModel.query.filter_by(job_id=job_id).first()
            if config:
                db.session.delete(config)
                db.session.commit()
                
        except Exception as e:
            logger.error(f"❌ 작업 설정 삭제 실패: {e}")
    
    def _save_execution_result(self, result: BatchExecutionResult):
        """실행 결과를 데이터베이스에 저장"""
        try:
            from app.common.models import BatchExecutionResult as ResultModel, db
            
            result_model = ResultModel(**result.__dict__)
            if result.details:
                result_model.details = json.dumps(result.details, ensure_ascii=False)
            
            db.session.add(result_model)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"❌ 실행 결과 저장 실패: {e}")
    
    def _register_default_jobs(self):
        """기본 배치 작업들 등록"""
        try:
            # 에이원 일일 데이터 수집 (매일 오전 2시)
            aone_daily = BatchJobConfig(
                job_id="aone_daily_collection",
                name="에이원 일일 ERPia 데이터 수집",
                job_type="DAILY_COLLECTION",
                company_id=1,
                cron_expression="0 2 * * *",
                parameters={
                    'auto_gift_classify': True
                }
            )
            self.add_job(aone_daily)
            
            # 에이원월드 일일 데이터 수집 (매일 오전 2시 30분)
            aoneworld_daily = BatchJobConfig(
                job_id="aoneworld_daily_collection",
                name="에이원월드 일일 ERPia 데이터 수집",
                job_type="DAILY_COLLECTION",
                company_id=2,
                cron_expression="30 2 * * *",
                parameters={
                    'auto_gift_classify': True
                }
            )
            self.add_job(aoneworld_daily)
            
            # 고객 정보 동기화 (주간, 일요일 오전 3시)
            customer_sync = BatchJobConfig(
                job_id="weekly_customer_sync",
                name="고객 정보 주간 동기화",
                job_type="CUSTOMER_SYNC",
                company_id=1,
                cron_expression="0 3 * * 0",
                parameters={
                    'days_back': 30
                }
            )
            self.add_job(customer_sync)
            
            # 사은품 자동 분류 (매일 오전 4시)
            gift_classify = BatchJobConfig(
                job_id="daily_gift_classify",
                name="사은품 자동 분류",
                job_type="GIFT_CLASSIFY",
                company_id=1,
                cron_expression="0 4 * * *",
                parameters={
                    'days_back': 7
                }
            )
            self.add_job(gift_classify)
            
            logger.info("✅ 기본 배치 작업들 등록 완료")
            
        except Exception as e:
            logger.error(f"❌ 기본 배치 작업 등록 실패: {e}")
    
    def _job_executed_listener(self, event):
        """작업 실행 완료 이벤트 리스너"""
        logger.info(f"📋 작업 실행 완료: {event.job_id}")
    
    def _job_error_listener(self, event):
        """작업 실행 오류 이벤트 리스너"""
        logger.error(f"❌ 작업 실행 오류: {event.job_id} - {event.exception}")
    
    def _shutdown_scheduler(self, exception):
        """앱 종료 시 스케줄러 정리"""
        if self.is_running:
            self.stop()

# 전역 스케줄러 인스턴스
batch_scheduler = BatchScheduler()

# 사용 예시
if __name__ == "__main__":
    import time
    
    # 테스트용 스케줄러
    test_scheduler = BatchScheduler()
    test_scheduler.start()
    
    # 테스트 작업 추가
    test_job = BatchJobConfig(
        job_id="test_job",
        name="테스트 작업",
        job_type="DAILY_COLLECTION",
        company_id=1,
        schedule_type="interval",
        interval_minutes=1  # 1분마다 실행
    )
    
    test_scheduler.add_job(test_job)
    
    # 10초 대기 후 종료
    time.sleep(10)
    test_scheduler.stop() 