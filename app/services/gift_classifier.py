#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사은품 자동 분류 엔진
- 회사별 분류 규칙 지원
- 매출분석 시스템 연동
- 지능형 분류 로직
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class GiftClassifier:
    """
    사은품 자동 분류 엔진 (회사별 설정 지원)
    
    @docs/06_ERPia_API_완전_가이드.md의 사은품 처리 로직 구현
    """
    
    def __init__(self, company_id: int):
        """
        Args:
            company_id: 회사 ID (1=에이원, 2=에이원월드)
        """
        self.company_id = company_id
        self._load_classification_rules()
    
    def _load_classification_rules(self):
        """회사별 분류 규칙 로드"""
        try:
            from app.common.models import ErpiaBatchSettings
            
            # 자동 분류 활성화 여부
            auto_classify_setting = ErpiaBatchSettings.query.filter_by(
                company_id=self.company_id,
                setting_key='auto_gift_classify'
            ).first()
            
            self.auto_classify_enabled = (
                auto_classify_setting.setting_value.lower() == 'true' 
                if auto_classify_setting else True
            )
            
            # 기본 분류 규칙
            self.classification_rules = self._create_default_rules()
            
            logger.info(f"🎁 사은품 분류 규칙 로드 완료 (회사: {self.company_id}, 자동분류: {self.auto_classify_enabled})")
            
        except Exception as e:
            logger.warning(f"⚠️ 분류 규칙 로드 실패, 기본값 사용: {e}")
            self.auto_classify_enabled = True
            self.classification_rules = self._create_default_rules()
    
    def _create_default_rules(self) -> Dict[str, Any]:
        """기본 분류 규칙 생성"""
        return {
            'zero_price_rules': {
                'enabled': True,
                'priority': 1,
                'description': '공급가 0원 AND 판매가 0원인 상품을 사은품으로 분류'
            },
            'keyword_rules': {
                'enabled': True,
                'priority': 2,
                'keywords': ['사은품', '증정품', '무료', '샘플', '체험', '덤', '서비스'],
                'description': '상품명에 특정 키워드가 포함된 상품을 사은품으로 분류'
            },
            'brand_rules': {
                'enabled': True,
                'priority': 3,
                'brand_codes': ['GIFT', 'SAMPLE', 'FREE'],
                'description': '특정 브랜드 코드의 상품을 사은품으로 분류'
            },
            'amount_threshold_rules': {
                'enabled': False,  # 기본적으로 비활성화
                'priority': 4,
                'max_amount': 1000,  # 1000원 이하
                'description': '특정 금액 이하의 상품을 사은품으로 분류'
            }
        }
    
    def classify_product(self, gong_amt: int, pan_amt: int, product_name: str, 
                        product_code: str = '', brand_code: str = '') -> Dict[str, Any]:
        """
        상품 분류 실행
        
        Args:
            gong_amt: 공급가
            pan_amt: 판매가
            product_name: 상품명
            product_code: 상품 코드
            brand_code: 브랜드 코드
            
        Returns:
            분류 결과
        """
        if not self.auto_classify_enabled:
            # 자동 분류 비활성화 시 모든 상품을 일반상품으로 처리
            return self._create_product_result(gong_amt, pan_amt, '자동분류 비활성화')
        
        result = {
            'original_gong_amt': gong_amt,
            'original_pan_amt': pan_amt,
            'product_name': product_name,
            'product_code': product_code,
            'brand_code': brand_code,
            'classification_reasons': [],
            'classification_priority': 999,
            'classified_at': datetime.utcnow().isoformat()
        }
        
        # 우선순위 순으로 분류 규칙 적용
        
        # 1. 0원 상품 체크 (최우선)
        if self.classification_rules['zero_price_rules']['enabled']:
            if gong_amt == 0 and pan_amt == 0:
                result.update(self._create_gift_result(
                    'ZERO_PRICE',
                    '공급가 0원 AND 판매가 0원',
                    1
                ))
                result['classification_reasons'].append('공급가 0원')
                return result
        
        # 2. 상품명 키워드 기반 분류
        if self.classification_rules['keyword_rules']['enabled']:
            keywords = self.classification_rules['keyword_rules']['keywords']
            product_name_lower = product_name.lower()
            
            for keyword in keywords:
                if keyword in product_name_lower:
                    result.update(self._create_gift_result(
                        'NAME_KEYWORD',
                        f'상품명 키워드: {keyword}',
                        2
                    ))
                    result['classification_reasons'].append(f'상품명 키워드: {keyword}')
                    return result
        
        # 3. 브랜드 코드 기반 분류
        if self.classification_rules['brand_rules']['enabled'] and brand_code:
            brand_codes = self.classification_rules['brand_rules']['brand_codes']
            
            for target_brand in brand_codes:
                if brand_code.upper().startswith(target_brand):
                    result.update(self._create_gift_result(
                        'BRAND_CODE',
                        f'브랜드 코드: {brand_code}',
                        3
                    ))
                    result['classification_reasons'].append(f'브랜드 코드: {target_brand}')
                    return result
        
        # 4. 금액 임계값 기반 분류 (선택적)
        if self.classification_rules['amount_threshold_rules']['enabled']:
            max_amount = self.classification_rules['amount_threshold_rules']['max_amount']
            if gong_amt > 0 and gong_amt <= max_amount:
                result.update(self._create_gift_result(
                    'AMOUNT_THRESHOLD',
                    f'금액 임계값: {gong_amt}원 ≤ {max_amount}원',
                    4
                ))
                result['classification_reasons'].append(f'금액 임계값 이하: {gong_amt}원')
                return result
        
        # 5. 일반상품으로 분류
        result.update(self._create_product_result(gong_amt, pan_amt, '일반상품'))
        result['classification_reasons'].append('일반상품')
        
        return result
    
    def _create_gift_result(self, gift_type: str, reason: str, priority: int) -> Dict[str, Any]:
        """사은품 분류 결과 생성"""
        return {
            'product_type': 'GIFT',
            'is_revenue': False,
            'analysis_category': '사은품',
            'revenue_impact': 0,
            'gift_type': gift_type,
            'include_in_quantity': True,    # 수량 집계에는 포함
            'include_in_revenue': False,    # 매출 집계에서 제외
            'classification_reason': reason,
            'classification_priority': priority
        }
    
    def _create_product_result(self, gong_amt: int, pan_amt: int, reason: str) -> Dict[str, Any]:
        """일반상품 분류 결과 생성"""
        return {
            'product_type': 'PRODUCT',
            'is_revenue': True,
            'analysis_category': '매출상품',
            'revenue_impact': gong_amt,
            'gift_type': None,
            'include_in_quantity': True,
            'include_in_revenue': True,
            'classification_reason': reason,
            'classification_priority': 999
        }
    
    def batch_classify_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        상품 목록 일괄 분류
        
        Args:
            products: 상품 정보 리스트
            
        Returns:
            분류된 상품 정보 리스트
        """
        classified_products = []
        
        for product in products:
            try:
                classification = self.classify_product(
                    gong_amt=product.get('supply_price', 0),
                    pan_amt=product.get('sell_price', 0),
                    product_name=product.get('product_name', ''),
                    product_code=product.get('product_code', ''),
                    brand_code=product.get('brand_code', '')
                )
                
                # 원본 상품 정보에 분류 결과 병합
                classified_product = product.copy()
                classified_product.update(classification)
                classified_products.append(classified_product)
                
            except Exception as e:
                logger.error(f"❌ 상품 분류 오류: {e}")
                logger.error(f"   문제 상품: {product}")
                
                # 오류 시 일반상품으로 처리
                error_product = product.copy()
                error_product.update(self._create_product_result(
                    product.get('supply_price', 0),
                    product.get('sell_price', 0),
                    f'분류 오류: {str(e)}'
                ))
                classified_products.append(error_product)
        
        return classified_products
    
    def get_gift_summary_by_order(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        주문별 사은품 요약 정보 생성
        
        Args:
            products: 분류된 상품 목록
            
        Returns:
            사은품 요약 정보
        """
        total_products = len(products)
        gift_products = [p for p in products if p.get('product_type') == 'GIFT']
        revenue_products = [p for p in products if p.get('product_type') == 'PRODUCT']
        
        # 사은품 유형별 통계
        gift_types = {}
        for gift in gift_products:
            gift_type = gift.get('gift_type', 'UNKNOWN')
            if gift_type not in gift_types:
                gift_types[gift_type] = {'count': 0, 'products': []}
            gift_types[gift_type]['count'] += 1
            gift_types[gift_type]['products'].append(gift.get('product_name', ''))
        
        return {
            'total_product_count': total_products,
            'gift_product_count': len(gift_products),
            'revenue_product_count': len(revenue_products),
            'gift_ratio': len(gift_products) / total_products if total_products > 0 else 0,
            'total_revenue': sum(p.get('revenue_impact', 0) for p in revenue_products),
            'gift_types': gift_types,
            'gift_products': [p.get('product_name', '') for p in gift_products],
            'classification_summary': {
                'auto_classified': len([p for p in gift_products if p.get('classification_priority', 999) < 999]),
                'manual_review_needed': len([p for p in products if p.get('classification_reason', '').startswith('분류 오류')])
            }
        }
    
    def generate_classification_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        분류 성과 리포트 생성
        
        Args:
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
            
        Returns:
            분류 리포트
        """
        try:
            from app.common.models import SalesAnalysisMaster
            from sqlalchemy import func, and_
            from datetime import datetime
            
            start_date_obj = datetime.strptime(start_date, '%Y%m%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y%m%d').date()
            
            # 기본 쿼리
            base_query = SalesAnalysisMaster.query.filter(
                and_(
                    SalesAnalysisMaster.company_id == self.company_id,
                    SalesAnalysisMaster.sale_date >= start_date_obj,
                    SalesAnalysisMaster.sale_date <= end_date_obj
                )
            )
            
            # 전체 통계
            total_count = base_query.count()
            
            # 사은품 분류별 통계
            gift_stats = base_query.filter(
                SalesAnalysisMaster.product_type == 'GIFT'
            ).with_entities(
                SalesAnalysisMaster.gift_classification,
                func.count(SalesAnalysisMaster.id).label('count')
            ).group_by(
                SalesAnalysisMaster.gift_classification
            ).all()
            
            # 사은품 부착률 (주문 기준)
            total_orders = base_query.with_entities(
                func.count(func.distinct(SalesAnalysisMaster.sales_no))
            ).scalar()
            
            orders_with_gifts = base_query.filter(
                SalesAnalysisMaster.product_type == 'GIFT'
            ).with_entities(
                func.count(func.distinct(SalesAnalysisMaster.sales_no))
            ).scalar()
            
            gift_attachment_rate = (orders_with_gifts / total_orders * 100) if total_orders > 0 else 0
            
            report = {
                'period': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'company_id': self.company_id
                },
                'summary': {
                    'total_products': total_count,
                    'total_orders': total_orders,
                    'orders_with_gifts': orders_with_gifts,
                    'gift_attachment_rate': round(gift_attachment_rate, 2)
                },
                'classification_breakdown': {
                    stat.gift_classification or 'UNKNOWN': stat.count
                    for stat in gift_stats
                },
                'classification_rules': {
                    'auto_classify_enabled': self.auto_classify_enabled,
                    'active_rules': [
                        rule_name for rule_name, rule_config in self.classification_rules.items()
                        if rule_config.get('enabled', False)
                    ]
                },
                'generated_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"📊 사은품 분류 리포트 생성 완료: {total_count}건 분석")
            return report
            
        except Exception as e:
            logger.error(f"❌ 분류 리포트 생성 실패: {e}")
            raise

# 전역 분류기 인스턴스 (회사별 캐시)
_classifiers = {}

def get_gift_classifier(company_id: int) -> GiftClassifier:
    """
    회사별 사은품 분류기 인스턴스 반환 (캐시 지원)
    
    Args:
        company_id: 회사 ID
        
    Returns:
        GiftClassifier 인스턴스
    """
    if company_id not in _classifiers:
        _classifiers[company_id] = GiftClassifier(company_id)
    return _classifiers[company_id]

def refresh_classifier_cache(company_id: int = None):
    """
    분류기 캐시 새로고침
    
    Args:
        company_id: 특정 회사 ID (None이면 전체 캐시 초기화)
    """
    global _classifiers
    
    if company_id is None:
        _classifiers.clear()
        logger.info("🔄 모든 사은품 분류기 캐시 초기화")
    else:
        if company_id in _classifiers:
            del _classifiers[company_id]
            logger.info(f"🔄 회사 {company_id} 사은품 분류기 캐시 초기화")

# 레거시 호환성을 위한 함수들
def classify_product_type(gong_amt: int, pan_amt: int, product_name: str, company_id: int = 1) -> Dict[str, Any]:
    """
    레거시 호환성을 위한 상품 분류 함수
    
    Args:
        gong_amt: 공급가
        pan_amt: 판매가
        product_name: 상품명
        company_id: 회사 ID
        
    Returns:
        분류 결과
    """
    classifier = get_gift_classifier(company_id)
    return classifier.classify_product(gong_amt, pan_amt, product_name) 