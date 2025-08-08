#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
대량 매장 정보 동기화 스크립트
2001년 01월 01일부터 현재까지 주단위로 ERPia에서 매장 정보를 가져옵니다.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Flask 앱 컨텍스트 설정
from app import create_app
from app.common.models import db, ErpiaCustomer, CompanyErpiaConfig, Code
from app.services.erpia_client import ErpiaApiClient

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bulk_customer_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BulkCustomerSync:
    def __init__(self, company_id=1):
        """
        대량 매장 정보 동기화 클래스
        
        Args:
            company_id (int): 회사 ID (1=에이원, 2=에이원월드)
        """
        self.company_id = company_id
        self.app = create_app()
        self.erpia_client = None
        self.classification_mapping = {}
        
        # 통계
        self.total_weeks = 0
        self.total_inserted = 0
        self.total_updated = 0
        self.total_errors = 0
        self.current_week = 0
        
    def init_erpia_client(self):
        """ERPia 클라이언트 초기화"""
        try:
            with self.app.app_context():
                config = CompanyErpiaConfig.query.filter_by(company_id=self.company_id).first()
                if not config:
                    raise Exception(f"회사 ID {self.company_id}의 ERPia 설정이 없습니다.")
                
                if not config.is_active:
                    raise Exception(f"회사 ID {self.company_id}의 ERPia 연동이 비활성화되어 있습니다.")
                
                self.erpia_client = ErpiaApiClient(company_id=self.company_id)
                logger.info(f"✅ ERPia 클라이언트 초기화 완료 (회사 ID: {self.company_id})")
                
        except Exception as e:
            logger.error(f"❌ ERPia 클라이언트 초기화 실패: {e}")
            raise
    
    def init_classification_mapping(self):
        """분류 코드 매핑 초기화"""
        try:
            with self.app.app_context():
                cst_group = Code.query.filter_by(code='CST', depth=0).first()
                if cst_group:
                    classification_groups = Code.query.filter_by(
                        parent_seq=cst_group.seq, 
                        depth=1
                    ).all()
                    
                    for group in classification_groups:
                        group_codes = Code.query.filter_by(
                            parent_seq=group.seq,
                            depth=2
                        ).all()
                        
                        group_key = group.code.lower()
                        self.classification_mapping[group_key] = {}
                        for code in group_codes:
                            self.classification_mapping[group_key][code.code] = code.code_name
                    
                    logger.info(f"📋 분류 매핑 준비 완료: {list(self.classification_mapping.keys())}")
                else:
                    logger.warning("⚠️ CST 분류 그룹을 찾을 수 없습니다.")
                    
        except Exception as e:
            logger.error(f"❌ 분류 매핑 초기화 실패: {e}")
            self.classification_mapping = {}
    
    def calculate_date_ranges(self, start_date, end_date):
        """주단위 날짜 범위 계산"""
        date_ranges = []
        current_date = start_date
        
        while current_date <= end_date:
            week_end = min(current_date + timedelta(days=6), end_date)
            date_ranges.append((current_date, week_end))
            current_date = week_end + timedelta(days=1)
        
        return date_ranges
    
    def sync_customers_for_period(self, start_date, end_date):
        """특정 기간의 매장 정보 동기화"""
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')
        
        logger.info(f"📅 매장 정보 수집: {start_str} ~ {end_str}")
        
        try:
            with self.app.app_context():
                # ERPia에서 데이터 가져오기
                customers_data = self.erpia_client.fetch_customers(start_str, end_str)
                
                if not customers_data:
                    logger.warning(f"⚠️ 해당 기간에 데이터가 없습니다: {start_str} ~ {end_str}")
                    return 0, 0, 0
                
                inserted_count = 0
                updated_count = 0
                error_count = 0
                
                logger.info(f"📊 수집된 매장 데이터: {len(customers_data)}개")
                
                for customer_data in customers_data:
                    try:
                        customer_code = customer_data.get('customer_code', '').strip()
                        if not customer_code:
                            error_count += 1
                            continue
                        
                        # 시스템 필드 제외
                        system_fields = {'seq', 'ins_user', 'ins_date', 'upt_user', 'upt_date', 'company_id'}
                        customer_data_filtered = {k: v for k, v in customer_data.items() 
                                                if hasattr(ErpiaCustomer, k) and k not in system_fields}
                        
                        # 기존 데이터 확인
                        existing_customer = ErpiaCustomer.query.filter_by(
                            customer_code=customer_code,
                            company_id=self.company_id
                        ).first()
                        
                        if existing_customer:
                            # 업데이트
                            for key, value in customer_data_filtered.items():
                                setattr(existing_customer, key, value)
                            existing_customer.upt_user = 'bulk_sync'
                            existing_customer.upt_date = datetime.utcnow()
                            updated_count += 1
                        else:
                            # 신규 추가
                            new_customer = ErpiaCustomer(
                                company_id=self.company_id,
                                ins_user='bulk_sync',
                                ins_date=datetime.utcnow(),
                                upt_user='bulk_sync',
                                upt_date=datetime.utcnow(),
                                **customer_data_filtered
                            )
                            db.session.add(new_customer)
                            inserted_count += 1
                    
                    except Exception as e:
                        logger.error(f"❌ 매장 데이터 처리 실패 ({customer_code}): {e}")
                        error_count += 1
                        continue
                
                # 커밋
                db.session.commit()
                logger.info(f"✅ 완료: 신규 {inserted_count}개, 업데이트 {updated_count}개, 오류 {error_count}개")
                
                return inserted_count, updated_count, error_count
                
        except Exception as e:
            logger.error(f"❌ 기간별 동기화 실패 ({start_str} ~ {end_str}): {e}")
            with self.app.app_context():
                db.session.rollback()
            raise
    
    def run_bulk_sync(self, start_year=2001, end_date=None):
        """대량 동기화 실행"""
        if end_date is None:
            end_date = datetime.now().date()
        
        start_date = datetime(start_year, 1, 1).date()
        
        logger.info(f"🚀 대량 매장 정보 동기화 시작")
        logger.info(f"📅 기간: {start_date} ~ {end_date}")
        logger.info(f"🏢 대상 회사: {self.company_id} ({'에이원' if self.company_id == 1 else '에이원월드'})")
        
        try:
            # 초기화
            self.init_erpia_client()
            self.init_classification_mapping()
            
            # 주단위 날짜 범위 계산
            date_ranges = self.calculate_date_ranges(start_date, end_date)
            self.total_weeks = len(date_ranges)
            
            logger.info(f"📊 총 {self.total_weeks}주간의 데이터를 처리합니다")
            
            # 주단위로 처리
            for week_start, week_end in date_ranges:
                self.current_week += 1
                
                try:
                    # 진행률 표시
                    progress = (self.current_week / self.total_weeks) * 100
                    logger.info(f"📈 진행률: {self.current_week}/{self.total_weeks} ({progress:.1f}%)")
                    
                    # 매장 정보 동기화
                    inserted, updated, errors = self.sync_customers_for_period(week_start, week_end)
                    
                    # 통계 업데이트
                    self.total_inserted += inserted
                    self.total_updated += updated
                    self.total_errors += errors
                    
                    # 진행 상황 로그
                    if (self.current_week % 10 == 0) or (self.current_week == self.total_weeks):
                        logger.info(f"📊 누적 통계: 신규 {self.total_inserted}개, 업데이트 {self.total_updated}개, 오류 {self.total_errors}개")
                    
                    # 과부하 방지를 위한 잠시 대기 (ERPia 서버 보호)
                    import time
                    time.sleep(3.0)  # 3초 대기
                    
                except Exception as e:
                    logger.error(f"❌ 주간 처리 실패 ({week_start} ~ {week_end}): {e}")
                    self.total_errors += 1
                    continue
            
            # 최종 결과
            logger.info(f"🎉 대량 동기화 완료!")
            logger.info(f"📊 최종 통계:")
            logger.info(f"   - 처리된 주간: {self.total_weeks}주")
            logger.info(f"   - 신규 추가: {self.total_inserted}개")
            logger.info(f"   - 업데이트: {self.total_updated}개")
            logger.info(f"   - 오류: {self.total_errors}개")
            logger.info(f"   - 총 처리: {self.total_inserted + self.total_updated}개")
            
            return {
                'success': True,
                'total_weeks': self.total_weeks,
                'inserted': self.total_inserted,
                'updated': self.total_updated,
                'errors': self.total_errors,
                'total_processed': self.total_inserted + self.total_updated
            }
            
        except Exception as e:
            logger.error(f"❌ 대량 동기화 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'inserted': self.total_inserted,
                'updated': self.total_updated,
                'errors': self.total_errors
            }

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='대량 매장 정보 동기화')
    parser.add_argument('--company-id', type=int, default=1, choices=[1, 2],
                      help='회사 ID (1=에이원, 2=에이원월드)')
    parser.add_argument('--start-year', type=int, default=2001,
                      help='시작 연도 (기본값: 2001)')
    parser.add_argument('--end-date', type=str, default=None,
                      help='종료 날짜 (YYYY-MM-DD 형식, 기본값: 오늘)')
    
    args = parser.parse_args()
    
    # 종료 날짜 파싱
    end_date = None
    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        except ValueError:
            logger.error("❌ 종료 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용하세요.")
            return
    
    # 동기화 실행
    sync = BulkCustomerSync(company_id=args.company_id)
    result = sync.run_bulk_sync(start_year=args.start_year, end_date=end_date)
    
    if result['success']:
        logger.info("✅ 대량 동기화가 성공적으로 완료되었습니다.")
    else:
        logger.error(f"❌ 대량 동기화 실패: {result.get('error', '알 수 없는 오류')}")

if __name__ == "__main__":
    main() 