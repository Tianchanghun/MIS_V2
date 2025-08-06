#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERPia API 클라이언트
- docs 기반 완전 구현
- 멀티테넌트 지원 (회사별 설정)
- EUC-KR → UTF-8 변환
- 30건 페이징 제한
- 3초 호출 간격
"""

import requests
import xml.etree.ElementTree as ET
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ErpiaApiClient:
    """
    ERPia API 클라이언트 (회사별 설정 지원)
    
    @docs/06_ERPia_API_완전_가이드.md 기반 구현
    """
    
    def __init__(self, company_id: int):
        """
        Args:
            company_id: 회사 ID (1=에이원, 2=에이원월드)
        """
        self.company_id = company_id
        self.base_url = "http://www.erpia.net/xml/xml.asp"
        self._load_settings()
    
    def _load_settings(self):
        """회사별 ERPia 설정 로드"""
        try:
            from app.common.models import CompanyErpiaConfig, ErpiaBatchSettings
            
            # ERPia 연동 설정
            config = CompanyErpiaConfig.query.filter_by(company_id=self.company_id).first()
            if config:
                self.admin_code = config.admin_code
                self.password = config.password
                self.api_url = config.api_url
                self.is_active = config.is_active
            else:
                # 기본값 (에이원 설정)
                self.admin_code = 'aone'
                self.password = 'ka22fslfod1vid'
                self.api_url = 'http://www.erpia.net/xml/xml.asp'
                self.is_active = True
            
            # 배치 설정
            settings = {}
            for setting in ErpiaBatchSettings.query.filter_by(company_id=self.company_id).all():
                settings[setting.setting_key] = setting.setting_value
            
            self.call_interval = int(settings.get('call_interval', '3'))
            self.page_size = int(settings.get('page_size', '30'))
            self.retry_count = int(settings.get('retry_count', '3'))
            self.timeout = 30
            
        except Exception as e:
            logger.error(f"ERPia 설정 로드 실패: {e}")
            # 기본값 설정
            self.admin_code = 'aone'
            self.password = 'ka22fslfod1vid'
            self.api_url = 'http://www.erpia.net/xml/xml.asp'
            self.is_active = True
            self.call_interval = 3
            self.page_size = 30
            self.retry_count = 3
            self.timeout = 30
    
    def test_connection(self) -> Dict[str, Any]:
        """ERPia 연결 테스트"""
        try:
            # 오늘 날짜로 간단한 고객 정보 조회 테스트
            today = datetime.now().strftime('%Y%m%d')
            params = {
                'mode': 'cust',
                'admin_code': self.admin_code,
                'pwd': self.password,
                'sDate': today,
                'eDate': today,
                'onePageCnt': 1,
                'page': 1
            }
            
            response = requests.get(self.api_url, params=params, timeout=self.timeout)
            response.encoding = 'euc-kr'
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            info_nodes = root.findall('info')
            
            return {
                'success': True,
                'message': f'연결 성공! ERPia API 정상 응답 확인',
                'data_count': len(info_nodes)
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'연결 실패: {str(e)}'
            }
    
    def fetch_sales_data(self, start_date: str, end_date: str) -> List[Dict]:
        """매출 데이터 수집 (mode=jumun) - 핵심 API"""
        logger.info(f"💰 ERPia 매출 데이터 수집 시작: {start_date}~{end_date}")
        
        all_orders = []
        page = 1
        
        while True:
            if page > 1:
                time.sleep(self.call_interval)
            
            params = {
                'mode': 'jumun',
                'admin_code': self.admin_code,
                'pwd': self.password,
                'sDate': start_date,
                'eDate': end_date,
                'page': page,
                'datetype': 'm',
                'onePageCnt': self.page_size
            }
            
            try:
                response = requests.get(self.api_url, params=params, timeout=self.timeout)
                response.encoding = 'euc-kr'
                response.raise_for_status()
                
                root = ET.fromstring(response.text)
                info_nodes = root.findall('info')
                
                if not info_nodes:
                    break
                
                for info in info_nodes:
                    order_data = self._parse_order_data(info)
                    all_orders.append(order_data)
                
                page += 1
                
            except Exception as e:
                logger.error(f"❌ 매출 데이터 수집 실패 (페이지 {page}): {e}")
                break
        
        logger.info(f"✅ ERPia 매출 데이터 수집 완료: {len(all_orders)}건")
        return all_orders
    
    def _parse_order_data(self, info_node) -> Dict:
        """주문 데이터 파싱 및 사은품 분류 - 이미지 XML 구조 기반"""
        order = {
            # 기본 주문 정보
            'site_key_code': self._get_text(info_node, 'Site_Key_Code'),  # 마케팅 코드
            'site_code': self._get_text(info_node, 'Site_Code'),          # 사이트 코드
            'site_id': self._get_text(info_node, 'Site_Id'),              # 마켓 아이디
            'ger_code': self._get_text(info_node, 'GerCode'),             # 매입 거래처 코드
            'sl_no': self._get_text(info_node, 'Sl_No'),                  # 전표번호
            'order_no': self._get_text(info_node, 'orderNo'),             # 주문번호
            
            # 주문자 정보
            'j_date': self._get_text(info_node, 'Jdate'),                 # 주문일
            'j_time': self._get_text(info_node, 'Jtime'),                 # 주문 시간
            'j_email': self._get_text(info_node, 'Jemail'),               # 주문자 이메일
            'j_id': self._get_text(info_node, 'Jid'),                     # 주문자 마켓 아이디
            'customer_name': self._get_text(info_node, 'Jname'),          # 주문자 이름
            'j_tel': self._get_text(info_node, 'Jtel'),                   # 주문자 전화번호
            'j_hp': self._get_text(info_node, 'Jhp'),                     # 주문자 핸드폰
            'j_post': self._get_text(info_node, 'Jpost'),                 # 주문자 우편번호
            'j_addr': self._get_text(info_node, 'Jaddr'),                 # 주문자 주소
            
            # 매출 정보
            'order_date': self._get_text(info_node, 'mDate'),             # 매출일
            'delivery_amt': self._safe_int(self._get_text(info_node, 'bAmt')), # 배송비 등록
            'ds_gong_amt': self._safe_int(self._get_text(info_node, 'dsGongAmt')), # 매출할인 공급가 등록
            'clam_yn': self._get_text(info_node, 'clamYN'),               # 클레임여부(추정,취소,반품)
            'site_d_code': self._get_text(info_node, 'siteDCode'),        # 사이트 전담코드
            'ger_check': self._get_text(info_node, 'gerCheck'),           # 이점여부(=가격점검여부)
            
            # ERPia 수집 정보
            'admin_code': self.admin_code,                                # ERPia 관리자 코드 (회사 식별용)
            
            'products': [],
            'delivery_info': {},
            'company_id': self.company_id
        }
        
        # 상품 정보 파싱 (사은품 분류 포함)
        for goods in info_node.findall('GoodsInfo'):
            product = self._parse_product_data_jumun(goods)
            order['products'].append(product)
        
        # 배송 정보 파싱
        delivery_node = info_node.find('BealInfo')
        if delivery_node is not None:
            order['delivery_info'] = {
                'b_type': self._get_text(delivery_node, 'Btype'),         # 선택불구분
                'recipient_name': self._get_text(delivery_node, 'Bname'), # 수령자 이름
                'b_tel': self._get_text(delivery_node, 'Btel'),           # 수령자 전화번호
                'phone': self._get_text(delivery_node, 'Bhp'),            # 수령자 핸드폰
                'b_post': self._get_text(delivery_node, 'Bpost'),         # 수령자 우편번호
                'address': self._get_text(delivery_node, 'Baddr'),        # 수령자 주소
                'b_bigo': self._get_text(delivery_node, 'Bbigo'),         # 배송정보설치
                'tag_code': self._get_text(delivery_node, 'TagCode'),     # 택배사코드
                'tracking_no': self._get_text(delivery_node, 'songNo')    # 운송장번호
            }
        
        return order
    
    def _parse_product_data_jumun(self, goods_node) -> Dict:
        """주문 상품 데이터 파싱 및 사은품 자동 분류 - mode=jumun용"""
        gong_amt = self._safe_int(self._get_text(goods_node, 'gongAmt'))
        pan_amt = self._safe_int(self._get_text(goods_node, 'panAmt'))
        product_name = self._get_text(goods_node, 'Gname')
        
        product = {
            # 기본 상품 정보
            'subul_kind': self._get_text(goods_node, 'subul_kind'),       # 수불코드
            'sl_seq': self._get_text(goods_node, 'Sl_Seq'),               # 전표순번
            'order_seq': self._get_text(goods_node, 'orderSeq'),          # 주문순번
            
            # 마켓 상품 정보
            'product_code': self._get_text(goods_node, 'Gcode'),          # 마켓 상품코드
            'product_name': product_name,                                 # 마켓 주문 상품명
            'g_stand': self._get_text(goods_node, 'Gstand'),              # 마켓 주문 규격
            'quantity': self._safe_int(self._get_text(goods_node, 'Gqty')), # 수량
            'supply_price': gong_amt,                                     # 공급단가
            'sell_price': pan_amt,                                        # 판매단가
            'changgo_code': self._get_text(goods_node, 'Changgo_Code'),   # 창고코드
            
            # ERPia 연계 상품 정보
            'grv_code': self._get_text(goods_node, 'GrvCode'),            # 자체코드(=자체상품코드)
            'ger_code': self._get_text(goods_node, 'GerCode'),            # ERPia 상품코드
            'ger_name': self._get_text(goods_node, 'GerName'),            # ERPia 상품명
            'ger_stand': self._get_text(goods_node, 'GerStand'),          # ERPia 규격
            'brand_code': self._get_text(goods_node, 'brandCode'),        # ERPia 브랜드 코드
            'brand_name': self._get_text(goods_node, 'brandName'),        # ERPia 브랜드 명칭
            
            # 가격 정보
            'open_amt': self._safe_int(self._get_text(goods_node, 'openAmt')), # 시장가
            'guidance_amt': self._safe_int(self._get_text(goods_node, 'guidanceAmt')) # 지도가
        }
        
        # 사은품 자동 분류 로직 적용
        classification = self._classify_product_type(gong_amt, pan_amt, product_name)
        product.update(classification)
        
        return product
    
    def _parse_product_data(self, goods_node) -> Dict:
        """기존 상품 데이터 파싱 (호환성 유지)"""
        return self._parse_product_data_jumun(goods_node)
    
    def _classify_product_type(self, gong_amt: int, pan_amt: int, product_name: str) -> Dict:
        """상품 유형 분류 (일반상품 vs 사은품)"""
        
        # 0원 상품은 사은품으로 분류
        if gong_amt == 0 and pan_amt == 0:
            return {
                'product_type': 'GIFT',
                'is_revenue': False,
                'analysis_category': '사은품',
                'gift_classification': 'AUTO_ZERO_PRICE'
            }
        
        # 키워드 기반 분류
        gift_keywords = ['사은품', '증정품', '무료', '샘플', '체험', '선물']
        for keyword in gift_keywords:
            if keyword in product_name:
                return {
                    'product_type': 'GIFT',
                    'is_revenue': False,
                    'analysis_category': '사은품',
                    'gift_classification': f'AUTO_KEYWORD_{keyword}'
                }
        
        # 일반상품으로 분류
        return {
            'product_type': 'PRODUCT',
            'is_revenue': True,
            'analysis_category': '매출상품',
            'gift_classification': None
        }
    
    def fetch_customers(self, start_date: str, end_date: str) -> List[Dict]:
        """매장정보 수집 (mode=cust) - 이미지 XML 구조 기반"""
        logger.info(f"🏪 매장정보 수집 시작: {start_date}~{end_date}")
        
        all_data = []
        page = 1
        
        while True:
            if page > 1:
                time.sleep(self.call_interval)
            
            params = {
                'mode': 'cust',
                'admin_code': self.admin_code,
                'pwd': self.password,
                'sDate': start_date,
                'eDate': end_date,
                'onePageCnt': self.page_size,
                'page': page
            }
            
            try:
                response = requests.get(self.api_url, params=params, timeout=self.timeout)
                response.encoding = 'euc-kr'
                response.raise_for_status()
                
                root = ET.fromstring(response.text)
                info_nodes = root.findall('info')
                
                if not info_nodes:
                    break
                
                for info in info_nodes:
                    customer_data = {
                        # 기본 정보
                        'customer_code': self._get_text(info, 'G_code'),      # ERPia 거래처 코드
                        'customer_name': self._get_text(info, 'G_name'),      # 거래처명
                        'ceo': self._get_text(info, 'G_Ceo'),                 # 대표자
                        'business_number': self._get_text(info, 'G_Sano'),    # 사업자번호
                        'business_type': self._get_text(info, 'G_up'),        # 업태
                        'business_item': self._get_text(info, 'G_Jong'),      # 종목
                        
                        # 연락처 정보
                        'phone': self._get_text(info, 'G_tel'),               # 전화
                        'fax': self._get_text(info, 'G_Fax'),                 # 팩스
                        
                        # 담당자 정보
                        'our_manager': self._get_text(info, 'G_Damdang'),     # (우리회사의) 거래처 담당
                        'customer_manager': self._get_text(info, 'G_Gdamdang'), # (상대회사) 거래처의 담당자
                        'customer_manager_tel': self._get_text(info, 'G_GDamdangTel'), # 거래처 담당자 연락처
                        
                        # 주소 정보
                        'location': self._get_text(info, 'G_Location'),       # 위물도시선물
                        'zip_code1': self._get_text(info, 'G_Post1'),         # 우편번호
                        'address1': self._get_text(info, 'G_Juso1'),          # 주소
                        'zip_code2': self._get_text(info, 'G_Post2'),         # 사업거치선 우편번호
                        'address2': self._get_text(info, 'G_Juso2'),          # 사업거치선 주소
                        
                        # 관리 정보
                        'remarks': self._get_text(info, 'G_Remk'),            # 비고
                        'program_usage': self._get_text(info, 'G_Program_Sayong'), # SCM 사용여부
                        'input_user': self._get_text(info, 'In_user'),        # 등록자
                        'edit_date': self._get_text(info, 'editDate'),        # 최종수정일
                        'status': self._get_text(info, 'stts'),               # 상태 (0:사용, 9:미사용)
                        'online_code': self._get_text(info, 'G_OnCode'),      # 자체거래처코드
                        
                        # 세금 관련 담당자
                        'tax_manager': self._get_text(info, 'Tax_GDamdang'),  # 사업거치선 담당자 이름
                        'tax_manager_tel': self._get_text(info, 'Tax_GDamdangTel'), # 사업거치선 담당자 연락처
                        'tax_email': self._get_text(info, 'Tax_Email'),       # 사업거치선 담당자 이메일
                        
                        # 연계 정보
                        'link_code_acct': self._get_text(info, 'linkCodeAcct'), # 회계 연계코드
                        'jo_type': self._get_text(info, 'G_JoType'),          # 거래(업종)구분
                        
                        # 매입 단가 정보
                        'dan_ga_gu': self._get_text(info, 'G_DanGa_Gu'),      # 매입단가
                        'discount_yul': self._get_text(info, 'G_Discount_Yul'), # 매입단가 할인율등록
                        'discount_or_up': self._get_text(info, 'G_Discount_Or_Up'), # 할인율등록구분
                        'use_recent_danga_yn': self._get_text(info, 'Use_Recent_DanGa_YN'), # 최근판단단가 우선적용률
                        
                        # 매입 단가 정보 (J 버전)
                        'dan_ga_gu_j': self._get_text(info, 'G_DanGa_GuJ'),   # 매입단가
                        'discount_yul_j': self._get_text(info, 'G_Discount_YulJ'), # 매입단가 할인율등록
                        'discount_or_up_j': self._get_text(info, 'G_Discount_Or_UpJ'), # 할인율등록구분
                        'use_recent_danga_yn_j': self._get_text(info, 'Use_Recent_DanGa_YNJ'), # 최근판단단가 우선적용률
                        
                        # 계좌 정보
                        'account': self._get_text(info, 'G_Account'),         # 계좌번호
                        'bank_name': self._get_text(info, 'G_BankName'),      # 은행명
                        'bank_holder': self._get_text(info, 'G_BankHolder'),  # 예금주
                        
                        # 배송 정보
                        'tag_code': self._get_text(info, 'G_TagCode'),        # 택배사코드
                        'tag_cust_code': self._get_text(info, 'G_TagCustCode'), # 택배 연계코드
                        'direct_shipping_type': self._get_text(info, 'G_DirectShippingType'), # 직배송업체구분
                        
                        # 추가 메모
                        'memo': self._get_text(info, 'G_Memo'),               # 메모
                        
                        # ERPia 수집 정보
                        'admin_code': self.admin_code,                        # ERPia 관리자 코드 (회사 식별용)
                        'company_id': self.company_id
                    }
                    all_data.append(customer_data)
                
                page += 1
                
            except Exception as e:
                logger.error(f"❌ 매장정보 수집 실패 (페이지 {page}): {e}")
                break
        
        logger.info(f"✅ 매장정보 수집 완료: {len(all_data)}건")
        return all_data
    
    def fetch_stock(self) -> List[Dict]:
        """재고 정보 수집 (mode=jegoAll) - 레거시 방식"""
        logger.info("📦 재고 정보 수집 시작 (레거시 호환)")
        
        params = {
            'mode': 'jegoAll',  # 레거시와 동일한 모드
            'admin_code': self.admin_code,
            'pwd': self.password
        }
        
        try:
            response = requests.get(self.api_url, params=params, timeout=self.timeout)
            response.encoding = 'euc-kr'
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            info_nodes = root.findall('info')
            
            result_data = []
            for info in info_nodes:
                stock_data = {
                    'online_code': self._get_text(info, 'G_OnCode'),
                    'goods_code': self._get_text(info, 'G_Code'),
                    'goods_name': self._get_text(info, 'G_Name'),
                    'goods_standard': self._get_text(info, 'G_Stand'),
                    'stock_qty': self._get_text(info, 'jego'),
                    'admin_code': self.admin_code,                        # ERPia 관리자 코드 (회사 식별용)
                    'company_id': self.company_id
                }
                result_data.append(stock_data)
            
            logger.info(f"✅ 재고 정보 수집 완료: {len(result_data)}건")
            return result_data
            
        except Exception as e:
            logger.error(f"❌ 재고 정보 수집 실패: {e}")
            return []

    def fetch_goods(self) -> List[Dict]:
        """상품 정보 수집 (mode=goods) - 이미지 XML 구조 기반"""
        logger.info("📦 상품 정보 수집 시작")
        
        all_data = []
        page = 1
        
        while True:
            if page > 1:
                time.sleep(self.call_interval)
            
            params = {
                'mode': 'goods',
                'admin_code': self.admin_code,
                'pwd': self.password,
                'onePageCnt': self.page_size,
                'page': page
            }
            
            try:
                response = requests.get(self.api_url, params=params, timeout=self.timeout)
                response.encoding = 'euc-kr'
                response.raise_for_status()
                
                root = ET.fromstring(response.text)
                info_nodes = root.findall('info')
                
                if not info_nodes:
                    break
                
                for info in info_nodes:
                    goods_data = {
                        # 기본 상품 정보
                        'online_code': self._get_text(info, 'G_OnCode'),  # 자체물상품코드
                        'goods_code': self._get_text(info, 'G_Code'),    # ERPia 상품코드
                        'goods_name': self._get_text(info, 'G_Name'),    # ERPia 상품명
                        'goods_standard': self._get_text(info, 'G_Stand'), # ERPia 규격
                        'alias_name': self._get_text(info, 'aliasName'), # 상품별칭
                        
                        # 제조 정보
                        'origin': self._get_text(info, 'origin'),        # 원산지
                        'making': self._get_text(info, 'making'),        # 제조사
                        'brand': self._get_text(info, 'brand'),          # 브랜드
                        
                        # 관리 정보
                        'date': self._get_text(info, 'date'),            # 최종수정일
                        'damdang': self._get_text(info, 'damdang'),      # 담당자
                        
                        # URL 정보
                        'url': self._get_text(info, 'url'),              # 상품상세 URL
                        'img_url': self._get_text(info, 'imgUrl'),       # 웹당 상품 이미지 url
                        'img_url_big': self._get_text(info, 'imgUrlBig'), # 웹당 상품 큰 이미지 url
                        
                        # 가격 정보
                        'inter_amt': self._safe_int(self._get_text(info, 'interAmt')), # 인터넷 판매단가
                        'do_amt': self._safe_int(self._get_text(info, 'doAmt')),       # 도매 판매단가
                        'so_amt': self._safe_int(self._get_text(info, 'soAmt')),       # 소매 단가
                        'user_amt': self._safe_int(self._get_text(info, 'userAmt')),   # 권장 소비자가
                        'ip_amt': self._safe_int(self._get_text(info, 'ipAmt')),       # 매입 단가
                        
                        # 상태 정보
                        'tax_free': self._get_text(info, 'taxfree'),     # 비과세
                        'state': self._get_text(info, 'state'),          # 상품상태
                        'jb_yn': self._get_text(info, 'jbYN'),           # 직배송여부
                        
                        # 추가 정보 (이미지에서 확인된 기타 필드들)
                        'link_code_acct': self._get_text(info, 'linkCodeAcct'),    # 회계 연계코드
                        'link_code_wms': self._get_text(info, 'linkCodeWms'),      # 물류 연계코드
                        'link_code_tmp': self._get_text(info, 'linkCodeTmp'),      # 기타 연계코드
                        'unit_kind': self._get_text(info, 'Unit_Kind'),            # 단위구분
                        'unit': self._get_text(info, 'Unit'),                      # 단위
                        'unit_val': self._safe_int(self._get_text(info, 'Unit_Val')), # 단위환산
                        'remk1': self._get_text(info, 'remk1'),                    # 비고1
                        'box_in_qty': self._safe_int(self._get_text(info, 'boxInQty')), # 1박스당 수량
                        'bun_ryu': self._get_text(info, 'bunRyu'),                 # 분류 (= 업태 부가세 구분)
                        'location': self._get_text(info, 'location'),              # 로케이션(창고-위치정보)
                        'changgo_code': self._get_text(info, 'Changgo_Code'),      # 매출 창고코드
                        'bar_code': self._get_text(info, 'barCode'),               # 바코드
                        'bs_sale_yn': self._get_text(info, 'BS_Sale_YN'),          # 단독배송여부
                        'concrete_yn': self._get_text(info, 'concrete_YN'),        # 유무형 구분
                        'deposit_gubun': self._get_text(info, 'Deposit_GUBUN'),    # 무형상품분류
                        'tag_print_yn': self._get_text(info, 'tagPrintYN'),        # 택배출력여부
                        'g_width': self._safe_int(self._get_text(info, 'G_Width')),    # 가로(폭)
                        'g_vertical': self._safe_int(self._get_text(info, 'G_Vertical')), # 세로(장)
                        'g_height': self._safe_int(self._get_text(info, 'G_Height')),  # 높이(고)
                        'g_opt_no_name': self._get_text(info, 'G_optNo_name'),     # 색상명
                        'g_color_name': self._get_text(info, 'G_color_name'),      # 옵션명
                        'j_beasong_yn': self._get_text(info, 'J_BeasongsYN'),      # 직배송여부
                        
                        # ERPia 수집 정보
                        'admin_code': self.admin_code,                        # ERPia 관리자 코드 (회사 식별용)
                        'company_id': self.company_id
                    }
                    all_data.append(goods_data)
                
                page += 1
                
            except Exception as e:
                logger.error(f"❌ 상품 정보 수집 실패 (페이지 {page}): {e}")
                break
        
        logger.info(f"✅ 상품 정보 수집 완료: {len(all_data)}건")
        return all_data
    
    def _get_text(self, node, tag: str, default: str = '') -> str:
        """XML 노드에서 텍스트 안전하게 추출"""
        try:
            element = node.find(tag)
            return element.text if element is not None and element.text else default
        except:
            return default
    
    def _safe_int(self, value: str) -> int:
        """문자열을 안전하게 정수로 변환"""
        try:
            return int(value) if value else 0
        except (ValueError, TypeError):
            return 0
    
    @staticmethod
    def get_company_by_admin_code(admin_code: str) -> Dict[str, Any]:
        """ERPia 관리자 코드로 회사 정보 조회"""
        try:
            from app.common.models import CompanyErpiaConfig, Company
            
            config = CompanyErpiaConfig.query.filter_by(admin_code=admin_code).first()
            if config:
                company = Company.query.get(config.company_id)
                return {
                    'company_id': config.company_id,
                    'company_name': company.company_name if company else 'Unknown',
                    'admin_code': admin_code,
                    'found': True
                }
            else:
                return {
                    'company_id': None,
                    'company_name': 'Unknown',
                    'admin_code': admin_code,
                    'found': False
                }
        except Exception as e:
            logger.error(f"관리자 코드로 회사 조회 실패: {e}")
            return {
                'company_id': None,
                'company_name': 'Error',
                'admin_code': admin_code,
                'found': False
            }
    
    def get_current_company_info(self) -> Dict[str, Any]:
        """현재 ERPia 클라이언트의 회사 정보 반환"""
        return self.get_company_by_admin_code(self.admin_code) 