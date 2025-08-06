#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERPia API 클라이언트 (완전한 필드 지원 + 안정성 강화)
레거시 시스템의 모든 ERPia 필드를 포함하여 구현
"""

import requests
import xml.etree.ElementTree as ET
import time
import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from urllib.parse import urlencode

# 로깅 설정
logger = logging.getLogger(__name__)

@dataclass
class ErpiaOrderMaster:
    """ERPia 주문 마스터 데이터"""
    # 기본 정보
    site_key_code: str = ""
    site_code: str = ""
    site_id: str = ""
    ger_code: str = ""
    sl_no: str = ""
    order_no: str = ""
    
    # 주문자 정보
    j_date: str = ""
    j_time: str = ""
    j_email: str = ""
    j_id: str = ""
    j_name: str = ""
    j_tel: str = ""
    j_hp: str = ""
    j_post: str = ""
    j_addr: str = ""
    
    # 분석된 주소 정보 (Naver API 기반)
    a_addr: str = ""
    a_sido: str = ""
    a_sigungu: str = ""
    
    # 금액 정보
    m_date: str = ""
    b_amt: int = 0
    dis_gong_amt: int = 0
    
    # 상태 정보
    claim_yn: str = ""
    site_ct_code: str = ""

@dataclass
class ErpiaOrderProduct:
    """ERPia 주문 상품 데이터"""
    # 기본 정보
    subul_kind: str = ""
    sl_no: str = ""
    sl_seq: int = 0
    order_seq: str = ""
    
    # 상품 정보
    g_code: str = ""
    g_name: str = ""
    g_stand: str = ""
    g_qty: int = 0
    
    # 가격 정보
    gong_amt: int = 0
    pan_amt: int = 0
    open_amt: int = 0
    guidance_amt: int = 0
    
    # 창고/브랜드 정보
    chang_go_code: str = ""
    g_my_code: str = ""
    g_erp_code: str = ""
    g_erp_name: str = ""
    g_erp_stand: str = ""
    brand_code: str = ""
    brand_name: str = ""
    
    # 사은품 분류 정보 (신규 추가)
    product_type: str = "PRODUCT"  # PRODUCT, GIFT
    is_revenue: bool = True
    gift_type: str = ""  # ZERO_PRICE, KEYWORD_BASED, MASTER_BASED
    classification_reason: str = ""
    revenue_impact: int = 0
    
    # 시스템 정보
    upt_date: datetime = None
    company_id: int = 1

@dataclass
class ErpiaOrderDelivery:
    """ERPia 주문 배송 데이터"""
    sl_no: str = ""
    b_type: str = ""
    b_name: str = ""
    b_tel: str = ""
    b_hp: str = ""
    b_post: str = ""
    b_addr: str = ""
    b_bigo: str = ""
    tag_code: str = ""
    song_no: str = ""
    company_id: int = 1

@dataclass
class ErpiaCustomer:
    """ERPia 고객 데이터"""
    g_code: str = ""
    g_name: str = ""
    g_damdang: str = ""
    g_ceo: str = ""
    g_sano: str = ""
    g_up: str = ""
    g_jong: str = ""
    g_tel: str = ""
    g_fax: str = ""
    g_g_damdang: str = ""
    g_g_damdang_tel: str = ""
    g_location: str = ""
    g_post1: str = ""
    g_juso1: str = ""
    g_post2: str = ""
    g_juso2: str = ""
    g_remk: str = ""
    g_program_sayong: str = ""
    in_user: str = ""
    edit_date: str = ""
    stts: str = ""
    g_on_code: str = ""
    company_id: int = 1

@dataclass
class BatchSettings:
    """배치 설정 (웹에서 관리)"""
    schedule_time: str = "02:00"
    call_interval: int = 3
    page_size: int = 30
    retry_count: int = 3
    timeout: int = 30
    auto_gift_classify: bool = True
    gift_keywords: List[str] = None

    def __post_init__(self):
        if self.gift_keywords is None:
            self.gift_keywords = ["사은품", "증정품", "무료", "샘플", "체험"]

class ErpiaApiClient:
    """ERPia API 클라이언트 (안정성 강화 버전)"""
    
    def __init__(self, admin_code: str = "aone", password: str = "ka22fslfod1vid"):
        self.base_url = "http://www.erpia.net/xml/xml.asp"
        self.admin_code = admin_code
        self.password = password
        
        # 안정성 설정 (사용자 요구사항 반영)
        self.max_page_size = 30  # 페이지당 최대 30건
        self.request_delay = 3   # 3초 대기
        self.retry_count = 3     # 재시도 횟수
        self.timeout = 30        # 타임아웃 30초
        
        # 요청 통계
        self.total_requests = 0
        self.failed_requests = 0
        
        logger.info(f"ERPia 클라이언트 초기화 완료 - 페이지크기: {self.max_page_size}, 대기시간: {self.request_delay}초")
    
    def _safe_request(self, params: Dict[str, Any], retry_count: int = None) -> Optional[ET.Element]:
        """안전한 HTTP 요청 (재시도 로직 포함)"""
        if retry_count is None:
            retry_count = self.retry_count
        
        for attempt in range(retry_count + 1):
            try:
                # 안전성을 위한 요청 간격 준수
                if self.total_requests > 0:
                    logger.debug(f"API 호출 간격 대기: {self.request_delay}초")
                    time.sleep(self.request_delay)
                
                self.total_requests += 1
                
                # HTTP 요청
                response = requests.get(
                    self.base_url,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # EUC-KR → UTF-8 변환 (사용자 요구사항)
                try:
                    # 먼저 EUC-KR로 시도
                    response.encoding = 'euc-kr'
                    xml_content = response.text
                    
                    # UTF-8로 다시 인코딩
                    xml_content = xml_content.encode('utf-8', errors='ignore').decode('utf-8')
                    
                    logger.debug(f"XML 인코딩 변환 완료: EUC-KR → UTF-8")
                    
                except UnicodeDecodeError:
                    # EUC-KR 실패 시 UTF-8로 직접 시도
                    response.encoding = 'utf-8'
                    xml_content = response.text
                    logger.warning("EUC-KR 변환 실패, UTF-8로 처리")
                
                # XML 파싱
                root = ET.fromstring(xml_content)
                
                logger.info(f"API 호출 성공: {params.get('mode', 'unknown')} (시도 {attempt + 1}/{retry_count + 1})")
                return root
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"API 호출 실패 (시도 {attempt + 1}/{retry_count + 1}): {e}")
                if attempt == retry_count:
                    self.failed_requests += 1
                    logger.error(f"API 호출 최종 실패: {e}")
                    return None
                
                # 재시도 전 대기 (지수 백오프)
                wait_time = min(30, (2 ** attempt) * self.request_delay)
                logger.info(f"재시도 전 대기: {wait_time}초")
                time.sleep(wait_time)
                
            except ET.ParseError as e:
                logger.error(f"XML 파싱 오류: {e}")
                self.failed_requests += 1
                return None
        
        return None
    
    def fetch_sales_data(self, start_date: str, end_date: str, 
                        page_size: int = None, max_pages: int = 1000) -> List[Dict[str, Any]]:
        """매출 데이터 조회 (안정성 강화)"""
        if page_size is None:
            page_size = self.max_page_size
        
        # 페이지 크기 제한 (사용자 요구사항: 30건 이하)
        page_size = min(page_size, self.max_page_size)
        
        all_orders = []
        page = 1
        
        logger.info(f"매출 데이터 수집 시작: {start_date} ~ {end_date}, 페이지크기: {page_size}")
        
        while page <= max_pages:
            logger.info(f"페이지 {page} 수집 중...")
            
            params = {
                'mode': 'jumun',
                'admin_code': self.admin_code,
                'pwd': self.password,
                'sDate': start_date,
                'eDate': end_date,
                'page': page,
                'datetype': 'm',
                'onePageCnt': page_size
            }
            
            root = self._safe_request(params)
            if root is None:
                logger.error(f"페이지 {page} 수집 실패 - 중단")
                break
            
            # 주문 정보 파싱
            info_nodes = root.findall('info')
            if not info_nodes:
                logger.info(f"페이지 {page}에서 데이터 없음 - 수집 완료")
                break
            
            page_orders = []
            for info in info_nodes:
                try:
                    order_data = self._parse_order_with_all_fields(info)
                    page_orders.append(order_data)
                except Exception as e:
                    logger.warning(f"주문 데이터 파싱 오류: {e}")
                    continue
            
            all_orders.extend(page_orders)
            logger.info(f"페이지 {page}: {len(page_orders)}건 수집 (누적: {len(all_orders)}건)")
            
            page += 1
        
        logger.info(f"매출 데이터 수집 완료: 총 {len(all_orders)}건, 요청: {self.total_requests}회, 실패: {self.failed_requests}회")
        return all_orders
    
    def _parse_order_with_all_fields(self, info_node) -> Dict[str, Any]:
        """주문 데이터 파싱 (모든 필드 포함)"""
        
        # 기본 주문 정보
        order = {
            'sl_no': self._get_text_safe(info_node, 'Sl_No'),
            'site_code': self._get_text_safe(info_node, 'Site_Code'),
            'site_key_code': self._get_text_safe(info_node, 'Site_Key_Code'),
            'ger_code': self._get_text_safe(info_node, 'GerCode'),
            'order_no': self._get_text_safe(info_node, 'Order_No'),
            
            # 주문자 정보
            'j_date': self._get_text_safe(info_node, 'jDate'),
            'j_time': self._get_text_safe(info_node, 'jTime'),
            'j_email': self._get_text_safe(info_node, 'jEmail'),
            'j_id': self._get_text_safe(info_node, 'jId'),
            'j_name': self._get_text_safe(info_node, 'Jname'),
            'j_tel': self._get_text_safe(info_node, 'jTel'),
            'j_hp': self._get_text_safe(info_node, 'jHp'),
            'j_post': self._get_text_safe(info_node, 'jPost'),
            'j_addr': self._get_text_safe(info_node, 'jAddr'),
            
            # 분석된 주소
            'a_addr': self._get_text_safe(info_node, 'aAddr'),
            'a_sido': self._get_text_safe(info_node, 'aSido'),
            'a_sigungu': self._get_text_safe(info_node, 'aSigungu'),
            
            # 금액 정보
            'm_date': self._get_text_safe(info_node, 'mDate'),
            'b_amt': self._get_int_safe(info_node, 'bAmt'),
            'dis_gong_amt': self._get_int_safe(info_node, 'disGongAmt'),
            
            # 상태 정보
            'claim_yn': self._get_text_safe(info_node, 'claimYn'),
            'site_ct_code': self._get_text_safe(info_node, 'siteCtCode'),
            
            # 상품 정보
            'products': [],
            
            # 배송 정보
            'delivery_info': {},
            
            # 메타 정보
            'collected_at': datetime.now().isoformat(),
            'encoding_converted': True  # EUC-KR → UTF-8 변환 완료 표시
        }
        
        # 상품 정보 파싱 (모든 필드 포함)
        for goods in info_node.findall('GoodsInfo'):
            product = self._parse_product_with_all_fields(goods)
            order['products'].append(product)
        
        # 배송 정보 파싱 (모든 필드 포함)
        delivery_node = info_node.find('BeaInfo')
        if delivery_node is not None:
            order['delivery_info'] = {
                'recipient_name': self._get_text_safe(delivery_node, 'Bname'),
                'recipient_tel': self._get_text_safe(delivery_node, 'Btel'),
                'recipient_hp': self._get_text_safe(delivery_node, 'Bhp'),
                'recipient_post': self._get_text_safe(delivery_node, 'Bpost'),
                'recipient_addr': self._get_text_safe(delivery_node, 'Baddr'),
                'tracking_no': self._get_text_safe(delivery_node, 'songNo'),
                'shipping_company': self._get_text_safe(delivery_node, 'taebaeCode'),
                'delivery_memo': self._get_text_safe(delivery_node, 'deliveryMemo')
            }
        
        return order
    
    def _parse_product_with_all_fields(self, goods_node) -> Dict[str, Any]:
        """상품 정보 파싱 (모든 필드 포함)"""
        
        gong_amt = self._get_int_safe(goods_node, 'gongAmt')
        pan_amt = self._get_int_safe(goods_node, 'panAmt')
        product_name = self._get_text_safe(goods_node, 'Gname')
        
        product = {
            # 기본 상품 정보
            'product_code': self._get_text_safe(goods_node, 'Gcode'),
            'product_name': product_name,
            'quantity': self._get_int_safe(goods_node, 'Gqty'),
            'supply_price': gong_amt,
            'sell_price': pan_amt,
            
            # 추가 상품 정보
            'subul_kind': self._get_text_safe(goods_node, 'subul_kind'),
            'brand_code': self._get_text_safe(goods_node, 'brandCode'),
            'brand_name': self._get_text_safe(goods_node, 'brandName'),
            'category_code': self._get_text_safe(goods_node, 'categoryCode'),
            'category_name': self._get_text_safe(goods_node, 'categoryName'),
            'unit': self._get_text_safe(goods_node, 'unit'),
            'weight': self._get_text_safe(goods_node, 'weight'),
            'volume': self._get_text_safe(goods_node, 'volume'),
            
            # 옵션 정보
            'option1': self._get_text_safe(goods_node, 'option1'),
            'option2': self._get_text_safe(goods_node, 'option2'),
            'option3': self._get_text_safe(goods_node, 'option3'),
            
            # 사은품 분류 (0원 상품 자동 분류)
            'is_gift': (gong_amt == 0 and pan_amt == 0),
            'gift_classification_reason': '0원 상품' if (gong_amt == 0 and pan_amt == 0) else None,
            
            # 메타 정보
            'parsed_at': datetime.now().isoformat()
        }
        
        return product
    
    def _get_text_safe(self, node, tag_name: str, default: str = '') -> str:
        """XML 노드에서 텍스트 안전하게 추출 (UTF-8 보장)"""
        try:
            element = node.find(tag_name)
            if element is not None and element.text:
                # UTF-8 인코딩 보장
                text = element.text.strip()
                # 제어 문자 제거
                text = re.sub(r'[\r\n\t]', '', text)
                return text
            return default
        except Exception as e:
            logger.warning(f"텍스트 추출 오류 ({tag_name}): {e}")
            return default
    
    def _get_int_safe(self, node, tag_name: str, default: int = 0) -> int:
        """XML 노드에서 정수 안전하게 추출"""
        try:
            text = self._get_text_safe(node, tag_name)
            if text:
                # 숫자가 아닌 문자 제거
                text = re.sub(r'[^\d-]', '', text)
                return int(text) if text else default
            return default
        except (ValueError, TypeError) as e:
            logger.warning(f"정수 변환 오류 ({tag_name}): {e}")
            return default
    
    def get_statistics(self) -> Dict[str, Any]:
        """API 호출 통계 반환"""
        return {
            'total_requests': self.total_requests,
            'failed_requests': self.failed_requests,
            'success_rate': (self.total_requests - self.failed_requests) / max(1, self.total_requests) * 100,
            'settings': {
                'max_page_size': self.max_page_size,
                'request_delay': self.request_delay,
                'retry_count': self.retry_count,
                'timeout': self.timeout
            }
        }

# 사용 예시
if __name__ == "__main__":
    # ERPia API 클라이언트 테스트
    client = ErpiaApiClient(admin_code="aone", password="ka22fslfod1vid")
    
    # 연결 테스트
    test_result = client.fetch_sales_data(start_date="20230101", end_date="20230131")
    print(f"연결 테스트: {test_result}")
    
    # 오늘 주문 데이터 수집
    today = datetime.now().strftime('%Y%m%d')
    orders = client.fetch_sales_data(start_date=today, end_date=today)
    print(f"주문 수집: {len(orders)}건") 