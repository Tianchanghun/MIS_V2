#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사은품 자동 분류 엔진
0원 상품과 키워드 기반으로 사은품을 자동 분류하여 매출 정확도 향상
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import json

# 로깅 설정
logger = logging.getLogger(__name__)

@dataclass
class GiftClassificationRule:
    """사은품 분류 규칙"""
    rule_id: str
    name: str
    rule_type: str  # ZERO_PRICE, KEYWORD, PATTERN, MASTER_BASED
    enabled: bool = True
    priority: int = 1  # 낮을수록 높은 우선순위
    
    # 키워드 규칙
    keywords: List[str] = None
    
    # 패턴 규칙 (정규식)
    pattern: str = ""
    
    # 가격 범위 규칙
    min_price: int = 0
    max_price: int = 0
    
    # 브랜드/거래처 제외 규칙
    exclude_brands: List[str] = None
    exclude_customers: List[str] = None
    
    # 분류 설정
    classification_reason: str = ""
    confidence_score: float = 1.0
    
    # 시스템 정보
    company_id: int = 1
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.exclude_brands is None:
            self.exclude_brands = []
        if self.exclude_customers is None:
            self.exclude_customers = []
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class GiftClassificationResult:
    """사은품 분류 결과"""
    product_id: str
    sl_no: str
    sl_seq: int
    original_type: str
    classified_type: str  # PRODUCT, GIFT
    classification_reason: str
    confidence_score: float
    rule_applied: str
    revenue_impact: int
    is_revenue: bool
    gift_type: str  # ZERO_PRICE, KEYWORD_BASED, PATTERN_BASED, MASTER_BASED
    classified_at: datetime
    company_id: int

@dataclass
class GiftStatistics:
    """사은품 통계"""
    total_products: int
    gift_products: int
    revenue_products: int
    zero_price_gifts: int
    keyword_gifts: int
    pattern_gifts: int
    master_gifts: int
    total_revenue_impact: int
    accuracy_rate: float
    classification_date: datetime
    company_id: int

class GiftClassifier:
    """사은품 자동 분류 엔진"""
    
    def __init__(self, company_id: int = 1):
        """
        Args:
            company_id: 회사 ID (1=에이원, 2=에이원월드)
        """
        self.company_id = company_id
        self.classification_rules = []
        self.load_classification_rules()
        
    def load_classification_rules(self):
        """분류 규칙 로드"""
        try:
            # 기본 규칙들 생성
            self.classification_rules = self._create_default_rules()
            
            # DB에서 사용자 정의 규칙 로드
            custom_rules = self._load_custom_rules()
            self.classification_rules.extend(custom_rules)
            
            # 우선순위별 정렬
            self.classification_rules.sort(key=lambda x: x.priority)
            
            logger.info(f"🔧 사은품 분류 규칙 로드 완료: {len(self.classification_rules)}개")
            
        except Exception as e:
            logger.error(f"❌ 분류 규칙 로드 실패: {e}")
            self.classification_rules = self._create_default_rules()
    
    def _create_default_rules(self) -> List[GiftClassificationRule]:
        """기본 분류 규칙 생성"""
        default_rules = [
            # 1. 0원 상품 규칙 (최고 우선순위)
            GiftClassificationRule(
                rule_id="zero_price_rule",
                name="0원 상품 자동 분류",
                rule_type="ZERO_PRICE",
                priority=1,
                max_price=0,
                classification_reason="공급가 0원 (자동분류)",
                confidence_score=1.0,
                company_id=self.company_id
            ),
            
            # 2. 사은품 키워드 규칙
            GiftClassificationRule(
                rule_id="gift_keyword_rule",
                name="사은품 키워드 매칭",
                rule_type="KEYWORD",
                priority=2,
                keywords=[
                    "사은품", "증정품", "무료", "샘플", "체험", "증정", "무료배송",
                    "서비스", "덤", "추가", "보너스", "이벤트", "프로모션",
                    "테스터", "시연", "체험용", "샘플용", "견본", "증정용"
                ],
                classification_reason="사은품 키워드 매칭",
                confidence_score=0.9,
                company_id=self.company_id
            ),
            
            # 3. 특정 브랜드 제외 규칙
            GiftClassificationRule(
                rule_id="exclude_main_brands",
                name="주요 브랜드 제외",
                rule_type="KEYWORD",
                priority=3,
                exclude_brands=["조이", "아이조이", "브라이텍스", "맥시코시"],
                classification_reason="주요 브랜드 제외",
                confidence_score=0.8,
                company_id=self.company_id
            ),
            
            # 4. 소액 상품 의심 규칙
            GiftClassificationRule(
                rule_id="low_price_rule",
                name="소액 상품 사은품 의심",
                rule_type="ZERO_PRICE",
                priority=4,
                min_price=1,
                max_price=1000,
                keywords=["사은품", "증정", "무료"],
                classification_reason="소액 + 키워드 매칭",
                confidence_score=0.7,
                company_id=self.company_id
            )
        ]
        
        return default_rules
    
    def _load_custom_rules(self):
        """사용자 정의 분류 규칙 로드"""
        try:
            # Flask 앱 컨텍스트 확인
            from flask import has_app_context, current_app
            
            if not has_app_context():
                print("⚠️ Flask 앱 컨텍스트 없음 - 기본 규칙 사용")
                return self._create_default_rules()
            
            # 사용자 정의 규칙 로드 시도
            return self._create_default_rules()
            
        except Exception as e:
            print(f"⚠️ 사용자 정의 규칙 로드 실패: {e}")
            # Flask 앱 컨텍스트가 없는 경우 기본 규칙 사용
            return self._create_default_rules()
        
        # DB 연결 실패 시 기본 규칙 사용  
        print("⚠️ Flask 앱 컨텍스트 없음 - 기본 규칙 사용")
        return self._create_default_rules()
    
    def classify_product(self, product_data: Dict[str, Any]) -> GiftClassificationResult:
        """단일 상품 사은품 분류"""
        try:
            # 상품 정보 추출
            g_name = product_data.get('g_name', '')
            gong_amt = product_data.get('gong_amt', 0)
            pan_amt = product_data.get('pan_amt', 0)
            brand_name = product_data.get('brand_name', '')
            g_erp_name = product_data.get('g_erp_name', '')
            sl_no = product_data.get('sl_no', '')
            sl_seq = product_data.get('sl_seq', 0)
            
            # 각 규칙에 대해 검사
            for rule in self.classification_rules:
                if not rule.enabled:
                    continue
                
                classification = self._apply_rule(rule, product_data)
                if classification:
                    logger.debug(f"🎁 사은품 분류: {g_name} -> {classification.classification_reason}")
                    return classification
            
            # 모든 규칙에 해당하지 않으면 일반 상품으로 분류
            return GiftClassificationResult(
                product_id=f"{sl_no}_{sl_seq}",
                sl_no=sl_no,
                sl_seq=sl_seq,
                original_type="PRODUCT",
                classified_type="PRODUCT",
                classification_reason="일반 매출 상품",
                confidence_score=1.0,
                rule_applied="default",
                revenue_impact=gong_amt,
                is_revenue=True,
                gift_type="",
                classified_at=datetime.now(),
                company_id=self.company_id
            )
            
        except Exception as e:
            logger.error(f"❌ 상품 분류 실패: {e}")
            # 실패 시 일반 상품으로 처리
            return GiftClassificationResult(
                product_id=f"{sl_no}_{sl_seq}",
                sl_no=sl_no,
                sl_seq=sl_seq,
                original_type="PRODUCT",
                classified_type="PRODUCT",
                classification_reason="분류 실패 - 일반 상품으로 처리",
                confidence_score=0.0,
                rule_applied="error",
                revenue_impact=product_data.get('gong_amt', 0),
                is_revenue=True,
                gift_type="",
                classified_at=datetime.now(),
                company_id=self.company_id
            )
    
    def _apply_rule(self, rule: GiftClassificationRule, product_data: Dict[str, Any]) -> Optional[GiftClassificationResult]:
        """규칙 적용"""
        try:
            g_name = product_data.get('g_name', '')
            gong_amt = product_data.get('gong_amt', 0)
            pan_amt = product_data.get('pan_amt', 0)
            brand_name = product_data.get('brand_name', '')
            sl_no = product_data.get('sl_no', '')
            sl_seq = product_data.get('sl_seq', 0)
            
            # 브랜드 제외 확인
            if rule.exclude_brands and brand_name:
                for exclude_brand in rule.exclude_brands:
                    if exclude_brand.lower() in brand_name.lower():
                        return None
            
            # 규칙 타입별 처리
            if rule.rule_type == "ZERO_PRICE":
                # 0원 상품 규칙
                if gong_amt == 0 and pan_amt == 0:
                    return self._create_gift_result(rule, product_data, "ZERO_PRICE")
                
                # 가격 범위 확인 (소액 상품)
                if rule.min_price <= gong_amt <= rule.max_price:
                    # 키워드도 함께 확인하는 경우
                    if rule.keywords:
                        if self._check_keywords(g_name, rule.keywords):
                            return self._create_gift_result(rule, product_data, "ZERO_PRICE")
                    else:
                        return self._create_gift_result(rule, product_data, "ZERO_PRICE")
            
            elif rule.rule_type == "KEYWORD":
                # 키워드 규칙
                if self._check_keywords(g_name, rule.keywords):
                    return self._create_gift_result(rule, product_data, "KEYWORD_BASED")
            
            elif rule.rule_type == "PATTERN":
                # 패턴 규칙 (정규식)
                if rule.pattern and re.search(rule.pattern, g_name, re.IGNORECASE):
                    return self._create_gift_result(rule, product_data, "PATTERN_BASED")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 규칙 적용 실패 ({rule.rule_id}): {e}")
            return None
    
    def _check_keywords(self, text: str, keywords: List[str]) -> bool:
        """키워드 매칭 확인"""
        if not text or not keywords:
            return False
        
        text_lower = text.lower()
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return True
        return False
    
    def _create_gift_result(self, rule: GiftClassificationRule, product_data: Dict[str, Any], gift_type: str) -> GiftClassificationResult:
        """사은품 분류 결과 생성"""
        sl_no = product_data.get('sl_no', '')
        sl_seq = product_data.get('sl_seq', 0)
        gong_amt = product_data.get('gong_amt', 0)
        
        return GiftClassificationResult(
            product_id=f"{sl_no}_{sl_seq}",
            sl_no=sl_no,
            sl_seq=sl_seq,
            original_type="PRODUCT",
            classified_type="GIFT",
            classification_reason=rule.classification_reason,
            confidence_score=rule.confidence_score,
            rule_applied=rule.rule_id,
            revenue_impact=0,  # 사은품은 매출 영향 0
            is_revenue=False,
            gift_type=gift_type,
            classified_at=datetime.now(),
            company_id=self.company_id
        )
    
    def classify_orders(self, orders: List[Dict[str, Any]]) -> List[GiftClassificationResult]:
        """여러 주문의 상품들을 일괄 분류"""
        results = []
        
        try:
            logger.info(f"🔄 주문 상품 일괄 분류 시작: {len(orders)}건")
            
            total_products = 0
            classified_gifts = 0
            
            for order in orders:
                products = order.get('products', [])
                
                for product in products:
                    result = self.classify_product(product.__dict__ if hasattr(product, '__dict__') else product)
                    results.append(result)
                    total_products += 1
                    
                    if result.classified_type == "GIFT":
                        classified_gifts += 1
            
            logger.info(f"✅ 상품 분류 완료: 전체 {total_products}건, 사은품 {classified_gifts}건")
            
            # 분류 결과 저장
            self._save_classification_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 주문 상품 일괄 분류 실패: {e}")
            return results
    
    def auto_classify_recent_products(self, company_id: int, days_back: int = 7) -> int:
        """최근 상품들의 자동 분류"""
        try:
            logger.info(f"🔄 최근 {days_back}일간 상품 자동 분류 시작")
            
            from app.common.models import ErpiaOrderProduct, db
            
            # 최근 상품 조회
            since_date = datetime.now() - timedelta(days=days_back)
            
            products = ErpiaOrderProduct.query.filter(
                ErpiaOrderProduct.company_id == company_id,
                ErpiaOrderProduct.created_at >= since_date,
                # 아직 분류되지 않은 상품들
                ErpiaOrderProduct.product_type.is_(None)
            ).all()
            
            classified_count = 0
            results = []
            
            for product in products:
                # 상품 데이터 준비
                product_data = {
                    'sl_no': product.sl_no,
                    'sl_seq': product.sl_seq,
                    'g_name': product.g_name,
                    'gong_amt': product.gong_amt,
                    'pan_amt': product.pan_amt,
                    'brand_name': product.brand_name,
                    'g_erp_name': product.g_erp_name
                }
                
                # 분류 실행
                result = self.classify_product(product_data)
                results.append(result)
                
                # DB 업데이트
                product.product_type = result.classified_type
                product.is_revenue = result.is_revenue
                product.gift_type = result.gift_type
                product.classification_reason = result.classification_reason
                product.revenue_impact = result.revenue_impact
                
                if result.classified_type == "GIFT":
                    classified_count += 1
            
            # 변경사항 저장
            db.session.commit()
            
            # 분류 결과 로그 저장
            self._save_classification_results(results)
            
            logger.info(f"✅ 자동 분류 완료: {len(products)}건 중 {classified_count}건 사은품 분류")
            return classified_count
            
        except Exception as e:
            logger.error(f"❌ 자동 분류 실패: {e}")
            return 0
    
    def get_classification_statistics(self, start_date: str, end_date: str) -> GiftStatistics:
        """분류 통계 조회"""
        try:
            from app.common.models import ErpiaOrderProduct
            
            # 기간 내 상품 조회
            products = ErpiaOrderProduct.query.filter(
                ErpiaOrderProduct.company_id == self.company_id,
                ErpiaOrderProduct.created_at >= datetime.strptime(start_date, '%Y-%m-%d'),
                ErpiaOrderProduct.created_at <= datetime.strptime(end_date, '%Y-%m-%d')
            ).all()
            
            total_products = len(products)
            gift_products = sum(1 for p in products if p.product_type == "GIFT")
            revenue_products = total_products - gift_products
            
            # 사은품 타입별 통계
            zero_price_gifts = sum(1 for p in products if p.gift_type == "ZERO_PRICE")
            keyword_gifts = sum(1 for p in products if p.gift_type == "KEYWORD_BASED")
            pattern_gifts = sum(1 for p in products if p.gift_type == "PATTERN_BASED")
            master_gifts = sum(1 for p in products if p.gift_type == "MASTER_BASED")
            
            # 매출 영향 계산
            total_revenue_impact = sum(p.revenue_impact or 0 for p in products)
            
            # 정확도 계산 (임시로 분류된 상품 비율로 계산)
            accuracy_rate = (gift_products + revenue_products) / total_products if total_products > 0 else 0
            
            return GiftStatistics(
                total_products=total_products,
                gift_products=gift_products,
                revenue_products=revenue_products,
                zero_price_gifts=zero_price_gifts,
                keyword_gifts=keyword_gifts,
                pattern_gifts=pattern_gifts,
                master_gifts=master_gifts,
                total_revenue_impact=total_revenue_impact,
                accuracy_rate=accuracy_rate,
                classification_date=datetime.now(),
                company_id=self.company_id
            )
            
        except Exception as e:
            logger.error(f"❌ 분류 통계 조회 실패: {e}")
            return GiftStatistics(
                total_products=0,
                gift_products=0,
                revenue_products=0,
                zero_price_gifts=0,
                keyword_gifts=0,
                pattern_gifts=0,
                master_gifts=0,
                total_revenue_impact=0,
                accuracy_rate=0.0,
                classification_date=datetime.now(),
                company_id=self.company_id
            )
    
    def add_classification_rule(self, rule: GiftClassificationRule) -> bool:
        """분류 규칙 추가"""
        try:
            from app.common.models import GiftClassificationRule as RuleModel, db
            
            # DB에 저장
            rule_model = RuleModel(
                rule_id=rule.rule_id,
                name=rule.name,
                rule_type=rule.rule_type,
                enabled=rule.enabled,
                priority=rule.priority,
                keywords=json.dumps(rule.keywords, ensure_ascii=False) if rule.keywords else None,
                pattern=rule.pattern,
                min_price=rule.min_price,
                max_price=rule.max_price,
                exclude_brands=json.dumps(rule.exclude_brands, ensure_ascii=False) if rule.exclude_brands else None,
                exclude_customers=json.dumps(rule.exclude_customers, ensure_ascii=False) if rule.exclude_customers else None,
                classification_reason=rule.classification_reason,
                confidence_score=rule.confidence_score,
                company_id=rule.company_id,
                created_at=rule.created_at,
                updated_at=rule.updated_at
            )
            
            db.session.add(rule_model)
            db.session.commit()
            
            # 메모리 규칙 목록 업데이트
            self.classification_rules.append(rule)
            self.classification_rules.sort(key=lambda x: x.priority)
            
            logger.info(f"✅ 분류 규칙 추가됨: {rule.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 분류 규칙 추가 실패: {e}")
            return False
    
    def _save_classification_results(self, results: List[GiftClassificationResult]):
        """분류 결과 저장"""
        try:
            from app.common.models import GiftClassificationLog, db
            
            for result in results:
                log = GiftClassificationLog(
                    product_id=result.product_id,
                    sl_no=result.sl_no,
                    sl_seq=result.sl_seq,
                    original_type=result.original_type,
                    classified_type=result.classified_type,
                    classification_reason=result.classification_reason,
                    confidence_score=result.confidence_score,
                    rule_applied=result.rule_applied,
                    revenue_impact=result.revenue_impact,
                    is_revenue=result.is_revenue,
                    gift_type=result.gift_type,
                    classified_at=result.classified_at,
                    company_id=result.company_id
                )
                db.session.add(log)
            
            db.session.commit()
            logger.debug(f"📝 분류 결과 로그 저장: {len(results)}건")
            
        except Exception as e:
            logger.error(f"❌ 분류 결과 저장 실패: {e}")
    
    def test_classification_rules(self, test_products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """분류 규칙 테스트"""
        try:
            logger.info(f"🔍 분류 규칙 테스트 시작: {len(test_products)}건")
            
            results = []
            rule_stats = defaultdict(int)
            
            for product in test_products:
                result = self.classify_product(product)
                results.append(result)
                rule_stats[result.rule_applied] += 1
            
            # 통계 계산
            total_count = len(results)
            gift_count = sum(1 for r in results if r.classified_type == "GIFT")
            product_count = total_count - gift_count
            
            test_result = {
                'total_products': total_count,
                'gift_products': gift_count,
                'revenue_products': product_count,
                'gift_ratio': gift_count / total_count if total_count > 0 else 0,
                'rule_statistics': dict(rule_stats),
                'results': results,
                'tested_at': datetime.now()
            }
            
            logger.info(f"✅ 규칙 테스트 완료: 사은품 {gift_count}/{total_count}건 ({gift_count/total_count*100:.1f}%)")
            return test_result
            
        except Exception as e:
            logger.error(f"❌ 분류 규칙 테스트 실패: {e}")
            return {
                'total_products': 0,
                'gift_products': 0,
                'revenue_products': 0,
                'gift_ratio': 0,
                'rule_statistics': {},
                'results': [],
                'tested_at': datetime.now()
            }

# 사용 예시
if __name__ == "__main__":
    # 사은품 분류기 테스트
    classifier = GiftClassifier(company_id=1)
    
    # 테스트 상품들
    test_products = [
        {
            'sl_no': 'TEST001',
            'sl_seq': 1,
            'g_name': '조이 카시트 (본품)',
            'gong_amt': 150000,
            'pan_amt': 180000,
            'brand_name': '조이'
        },
        {
            'sl_no': 'TEST001',
            'sl_seq': 2,
            'g_name': '유모차 커버 사은품',
            'gong_amt': 0,
            'pan_amt': 0,
            'brand_name': '기타'
        },
        {
            'sl_no': 'TEST002',
            'sl_seq': 1,
            'g_name': '워터 증정품',
            'gong_amt': 500,
            'pan_amt': 1000,
            'brand_name': '기타'
        }
    ]
    
    # 분류 테스트
    test_result = classifier.test_classification_rules(test_products)
    print(f"테스트 결과: {test_result}")
    
    # 통계 조회
    stats = classifier.get_classification_statistics('2024-01-01', '2024-12-31')
    print(f"분류 통계: {stats}") 