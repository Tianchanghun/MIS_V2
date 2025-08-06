#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERPia 배치 서비스
설정된 순서에 따라 ERPia API 모드들을 실행하는 서비스
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

from app.common.models import ErpiaBatchSettings, CompanyErpiaConfig, db, ErpiaOrderMaster, SalesAnalysisMaster
from app.services.erpia_client import ErpiaApiClient
from app.services.gift_classifier import GiftClassifier

logger = logging.getLogger(__name__)

class ErpiaBatchService:
    """ERPia 배치 실행 서비스"""
    
    def __init__(self, company_id: int):
        self.company_id = company_id
        self.erpia_client = ErpiaApiClient(company_id)
        self.gift_classifier = GiftClassifier(company_id)
        self.batch_steps = self._load_batch_steps()
        
    def _load_batch_steps(self) -> List[Dict]:
        """설정된 배치 실행 순서 로드"""
        try:
            batch_steps_setting = ErpiaBatchSettings.query.filter_by(
                company_id=self.company_id,
                setting_key='batch_steps'
            ).first()
            
            if batch_steps_setting and batch_steps_setting.setting_value:
                steps = json.loads(batch_steps_setting.setting_value)
                # 순서대로 정렬
                return sorted(steps, key=lambda x: x.get('order', 999))
            else:
                # 기본 실행 순서 (핵심 4개)
                return [
                    {'step': 'customers', 'order': 1, 'enabled': True},
                    {'step': 'stock', 'order': 2, 'enabled': True},
                    {'step': 'goods', 'order': 3, 'enabled': True},
                    {'step': 'sales', 'order': 4, 'enabled': True}
                ]
        except Exception as e:
            logger.error(f"배치 단계 설정 로드 실패: {e}")
            # 기본값 반환
            return [
                {'step': 'customers', 'order': 1, 'enabled': True},
                {'step': 'stock', 'order': 2, 'enabled': True},
                {'step': 'goods', 'order': 3, 'enabled': True},
                {'step': 'sales', 'order': 4, 'enabled': True}
            ]
    
    def collect_sales_data(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """설정된 순서에 따라 ERPia 데이터 수집 (4개월 수집)"""
        
        # 날짜 범위 설정 (4개월 이전부터)
        if not start_date or not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=120)).strftime('%Y%m%d')  # 4개월 이전
            logger.info(f"📅 자동 날짜 설정: {start_date}~{end_date} (4개월)")
        
        result = {
            'start_time': datetime.utcnow().isoformat(),
            'company_id': self.company_id,
            'admin_code': self.erpia_client.admin_code,  # ERPia 관리자 코드 (회사 식별용)
            'total_steps': 0,
            'completed_steps': 0,
            'failed_steps': 0,
            'step_results': {},
            'processed_orders': 0,
            'processed_products': 0,
            'processed_stock': 0,
            'gift_products': 0,
            'total_pages': 0,
            'saved_to_db': 0,  # DB 저장 건수 추가
            'updated_in_db': 0  # DB 업데이트 건수 추가
        }
        
        enabled_steps = [step for step in self.batch_steps if step.get('enabled', False)]
        result['total_steps'] = len(enabled_steps)
        
        # ERPia 회사 정보 로그
        company_info = self.erpia_client.get_current_company_info()
        logger.info(f"🏢 ERPia 연동 회사: {company_info['company_name']} (관리자코드: {company_info['admin_code']})")
        
        logger.info(f"🚀 배치 시작 - 회사 ID: {self.company_id}, 기간: {start_date}~{end_date}")
        logger.info(f"📋 실행 단계: {[step['step'] for step in enabled_steps]}")
        
        for step_config in enabled_steps:
            step_name = step_config['step']
            step_order = step_config['order']
            
            try:
                logger.info(f"⏳ 단계 {step_order}: {step_name} 실행 중...")
                step_result = self._execute_step(step_name, start_date, end_date)
                
                result['step_results'][step_name] = {
                    'status': 'SUCCESS',
                    'order': step_order,
                    'data_count': step_result.get('data_count', 0),
                    'pages': step_result.get('pages', 0),
                    'execution_time': step_result.get('execution_time', 0),
                    'saved_to_db': step_result.get('saved_to_db', 0),
                    'updated_in_db': step_result.get('updated_in_db', 0)
                }
                
                # 전체 결과에 누적
                if step_name == 'sales':
                    result['processed_orders'] = step_result.get('data_count', 0)
                    result['processed_products'] = step_result.get('product_count', 0)
                    result['gift_products'] = step_result.get('gift_count', 0)
                    result['saved_to_db'] += step_result.get('saved_to_db', 0)
                    result['updated_in_db'] += step_result.get('updated_in_db', 0)
                elif step_name == 'stock':
                    result['processed_stock'] = step_result.get('data_count', 0)
                
                result['total_pages'] += step_result.get('pages', 0)
                result['completed_steps'] += 1
                
                logger.info(f"✅ 단계 {step_order}: {step_name} 완료 ({step_result.get('data_count', 0)}건)")
                
                # API 호출 간격 준수
                time.sleep(self.erpia_client.call_interval)
                
            except Exception as e:
                logger.error(f"❌ 단계 {step_order}: {step_name} 실패 - {str(e)}")
                result['step_results'][step_name] = {
                    'status': 'FAILED',
                    'order': step_order,
                    'error': str(e)
                }
                result['failed_steps'] += 1
        
        result['end_time'] = datetime.utcnow().isoformat()
        result['success_rate'] = (result['completed_steps'] / result['total_steps']) * 100 if result['total_steps'] > 0 else 0
        
        logger.info(f"🏁 배치 완료 - 성공: {result['completed_steps']}/{result['total_steps']} (성공률: {result['success_rate']:.1f}%)")
        logger.info(f"💾 DB 저장: {result['saved_to_db']}건 신규, {result['updated_in_db']}건 업데이트")
        
        return result
    
    def _execute_step(self, step_name: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """개별 배치 단계 실행"""
        step_start_time = datetime.utcnow()
        
        if step_name == 'customers':
            return self._collect_customers(start_date, end_date)
        elif step_name == 'stock':
            return self._collect_stock()
        elif step_name == 'goods':
            return self._collect_goods()
        elif step_name == 'sales':
            return self._collect_sales_with_db_save(start_date, end_date)
        else:
            raise ValueError(f"알 수 없는 배치 단계: {step_name}")
    
    def _collect_customers(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """매장정보 수집 (mode=cust)"""
        data = self.erpia_client.fetch_customers(start_date, end_date)
        return {
            'data_count': len(data),
            'pages': 1,  # 실제 구현 시 페이지 수 계산
            'execution_time': 0
        }
    
    def _collect_stock(self) -> Dict[str, Any]:
        """재고 정보 수집 (mode=jegoAll)"""
        data = self.erpia_client.fetch_stock()
        return {
            'data_count': len(data),
            'pages': 1,
            'execution_time': 0
        }
    
    def _collect_goods(self) -> Dict[str, Any]:
        """상품 정보 수집 (mode=goods)"""
        data = self.erpia_client.fetch_goods()
        return {
            'data_count': len(data),
            'pages': 1,
            'execution_time': 0
        }
    
    def _collect_sales_with_db_save(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """매출 데이터 수집 (mode=jumun) + 사은품 분류 + DB 저장 (UPSERT)"""
        logger.info(f"💰 매출 데이터 수집 및 DB 저장 시작: {start_date}~{end_date}")
        
        # ERPia에서 데이터 수집
        sales_data = self.erpia_client.fetch_sales_data(start_date, end_date)
        
        # 사은품 자동 분류
        gift_count = 0
        product_count = 0
        saved_count = 0
        updated_count = 0
        
        try:
            for order in sales_data:
                # 주문 마스터 저장/업데이트 (Sl_No 기준 UPSERT)
                saved, updated = self._save_order_master(order)
                if saved:
                    saved_count += 1
                if updated:
                    updated_count += 1
                
                # 상품별 분석 데이터 저장
                for product in order.get('products', []):
                    if product.get('product_type') == 'GIFT':
                        gift_count += 1
                    else:
                        product_count += 1
                    
                    # 매출 분석 테이블에 저장
                    self._save_sales_analysis(order, product)
            
            # 커밋
            db.session.commit()
            logger.info(f"✅ 매출 데이터 DB 저장 완료: 신규 {saved_count}건, 업데이트 {updated_count}건")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ 매출 데이터 DB 저장 실패: {e}")
            raise e
        
        return {
            'data_count': len(sales_data),
            'product_count': product_count,
            'gift_count': gift_count,
            'pages': 1,  # 실제 구현 시 페이지 수 계산
            'execution_time': 0,
            'saved_to_db': saved_count,
            'updated_in_db': updated_count
        }
    
    def _save_order_master(self, order_data: Dict) -> tuple[bool, bool]:
        """주문 마스터 저장/업데이트 (Sl_No 기준 UPSERT)"""
        sl_no = order_data.get('sl_no')
        if not sl_no:
            logger.warning("⚠️ Sl_No가 없는 주문 데이터 건너뜀")
            return False, False
        
        # 기존 데이터 조회
        existing_order = ErpiaOrderMaster.query.filter_by(
            company_id=self.company_id,
            sl_no=sl_no
        ).first()
        
        if existing_order:
            # 업데이트
            self._update_order_master(existing_order, order_data)
            logger.debug(f"📝 주문 업데이트: {sl_no}")
            return False, True
        else:
            # 신규 저장
            new_order = self._create_order_master(order_data)
            db.session.add(new_order)
            logger.debug(f"💾 주문 신규 저장: {sl_no}")
            return True, False
    
    def _create_order_master(self, order_data: Dict) -> ErpiaOrderMaster:
        """새 주문 마스터 생성"""
        return ErpiaOrderMaster(
            company_id=self.company_id,
            site_key_code=order_data.get('site_key_code'),
            site_code=order_data.get('site_code'),
            site_id=order_data.get('site_id'),
            ger_code=order_data.get('ger_code'),
            sl_no=order_data.get('sl_no'),
            order_no=order_data.get('order_no'),
            j_date=self._parse_datetime(order_data.get('j_date')),
            j_time=order_data.get('j_time'),
            j_email=order_data.get('j_email'),
            j_id=order_data.get('j_id'),
            j_name=order_data.get('customer_name'),
            j_tel=order_data.get('j_tel'),
            j_hp=order_data.get('j_hp'),
            j_post=order_data.get('j_post'),
            j_addr=order_data.get('j_addr'),
            m_date=self._parse_datetime(order_data.get('order_date')),
            b_amt=order_data.get('delivery_amt', 0),
            dis_gong_amt=order_data.get('ds_gong_amt', 0),
            claim_yn=order_data.get('clam_yn'),
            site_ct_code=order_data.get('site_d_code'),
            created_at=datetime.utcnow()
        )
    
    def _update_order_master(self, existing_order: ErpiaOrderMaster, order_data: Dict):
        """기존 주문 마스터 업데이트"""
        existing_order.site_key_code = order_data.get('site_key_code')
        existing_order.site_code = order_data.get('site_code')
        existing_order.site_id = order_data.get('site_id')
        existing_order.ger_code = order_data.get('ger_code')
        existing_order.order_no = order_data.get('order_no')
        existing_order.j_date = self._parse_datetime(order_data.get('j_date'))
        existing_order.j_time = order_data.get('j_time')
        existing_order.j_email = order_data.get('j_email')
        existing_order.j_id = order_data.get('j_id')
        existing_order.j_name = order_data.get('customer_name')
        existing_order.j_tel = order_data.get('j_tel')
        existing_order.j_hp = order_data.get('j_hp')
        existing_order.j_post = order_data.get('j_post')
        existing_order.j_addr = order_data.get('j_addr')
        existing_order.m_date = self._parse_datetime(order_data.get('order_date'))
        existing_order.b_amt = order_data.get('delivery_amt', 0)
        existing_order.dis_gong_amt = order_data.get('ds_gong_amt', 0)
        existing_order.claim_yn = order_data.get('clam_yn')
        existing_order.site_ct_code = order_data.get('site_d_code')
    
    def _save_sales_analysis(self, order_data: Dict, product_data: Dict):
        """매출 분석 데이터 저장"""
        analysis_data = SalesAnalysisMaster(
            company_id=self.company_id,
            sales_no=order_data.get('sl_no'),
            sale_date=self._parse_date(order_data.get('order_date')),
            site_code=order_data.get('site_code'),
            ger_code=order_data.get('ger_code'),
            customer_name=order_data.get('customer_name'),
            product_code=product_data.get('product_code'),
            product_name=product_data.get('product_name'),
            product_type=product_data.get('product_type', 'PRODUCT'),
            brand_code=product_data.get('brand_code'),
            brand_name=product_data.get('brand_name'),
            quantity=product_data.get('quantity', 0),
            supply_price=product_data.get('supply_price', 0),
            sell_price=product_data.get('sell_price', 0),
            total_amount=(product_data.get('quantity', 0) * product_data.get('sell_price', 0)),
            delivery_amt=order_data.get('delivery_amt', 0),
            is_revenue=product_data.get('is_revenue', True),
            analysis_category=product_data.get('analysis_category'),
            gift_classification=product_data.get('gift_classification'),
            recipient_name=order_data.get('delivery_info', {}).get('recipient_name'),
            address=order_data.get('delivery_info', {}).get('address'),
            tracking_no=order_data.get('delivery_info', {}).get('tracking_no'),
            created_at=datetime.utcnow()
        )
        db.session.add(analysis_data)
    
    def _parse_datetime(self, date_str: str) -> datetime:
        """날짜 문자열을 datetime으로 변환"""
        if not date_str:
            return None
        try:
            if len(date_str) == 8:  # YYYYMMDD
                return datetime.strptime(date_str, '%Y%m%d')
            elif len(date_str) == 14:  # YYYYMMDDHHMMSS
                return datetime.strptime(date_str, '%Y%m%d%H%M%S')
            else:
                return datetime.fromisoformat(date_str)
        except:
            return None
    
    def _parse_date(self, date_str: str):
        """날짜 문자열을 date로 변환"""
        dt = self._parse_datetime(date_str)
        return dt.date() if dt else None
    
    def get_step_summary(self) -> Dict[str, Any]:
        """배치 단계 요약 정보"""
        enabled_steps = [step for step in self.batch_steps if step.get('enabled', False)]
        
        step_descriptions = {
            'customers': '매장정보 수집 (mode=cust)',
            'stock': '재고 정보 수집 (mode=jegoAll)',
            'goods': '상품 정보 수집 (mode=goods)',
            'sales': '매출 데이터 수집 (mode=jumun) + 사은품 분류 + DB 저장'
        }
        
        return {
            'total_steps': len(enabled_steps),
            'enabled_steps': [
                {
                    'step': step['step'],
                    'order': step['order'],
                    'description': step_descriptions.get(step['step'], step['step'])
                }
                for step in enabled_steps
            ]
        } 