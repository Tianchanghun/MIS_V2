#!/usr/bin/env python3
"""
ERPia API 클라이언트 - 설정 기반 동적 구성
- 데이터베이스 설정값 사용
- 웹에서 설정 변경 가능
- 기본값 자동 적용
"""

import requests
import xml.etree.ElementTree as ET
import time
from typing import List, Dict, Optional, Union
from datetime import datetime
import chardet
import logging
from models.erpia_settings import ErpiaSettings

class ErpiaApiClient:
    """ERPia API 완전 구현 클라이언트 - 설정 기반"""
    
    def __init__(self):
        self.base_url = "http://www.erpia.net/xml/xml.asp"
        self.admin_code = "aone"
        self.password = "ka22fslfod1vid"
        
        # 데이터베이스 설정값 사용 (기본값 자동 적용)
        self.page_size = ErpiaSettings.get_page_size()  # 기본값: 30
        self.call_interval = ErpiaSettings.get_call_interval()  # 기본값: 3초
        self.timeout = ErpiaSettings.get_timeout()  # 기본값: 30초
        self.retry_count = ErpiaSettings.get_retry_count()  # 기본값: 3회
        
        self.last_call_time = 0
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # 설정값 로그 출력
        self.logger.info(f"🔧 ERPia API 설정 - 페이지크기: {self.page_size}, 호출간격: {self.call_interval}초, 타임아웃: {self.timeout}초")
    
    def reload_settings(self):
        """설정값 다시 로드 (웹에서 설정 변경 후 호출)"""
        old_page_size = self.page_size
        old_interval = self.call_interval
        
        self.page_size = ErpiaSettings.get_page_size()
        self.call_interval = ErpiaSettings.get_call_interval()
        self.timeout = ErpiaSettings.get_timeout()
        self.retry_count = ErpiaSettings.get_retry_count()
        
        self.logger.info(f"🔄 설정 다시 로드됨 - 페이지크기: {old_page_size}→{self.page_size}, 호출간격: {old_interval}→{self.call_interval}초")
    
    def _safe_call(self, url: str, params: Dict) -> Optional[ET.Element]:
        """안전한 API 호출 (설정 기반 간격, EUC-KR 처리, 재시도)"""
        # 설정된 간격 보장
        current_time = time.time()
        elapsed = current_time - self.last_call_time
        if elapsed < self.call_interval:
            wait_time = self.call_interval - elapsed
            self.logger.info(f"⏱️ {wait_time:.1f}초 대기 중... (설정값: {self.call_interval}초)")
            time.sleep(wait_time)
        
        # 재시도 로직
        for attempt in range(self.retry_count):
            try:
                self.logger.info(f"🔄 API 호출 (시도 {attempt + 1}/{self.retry_count}): {url}")
                response = requests.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                # 인코딩 감지 및 변환
                detected = chardet.detect(response.content)
                encoding = detected.get('encoding', 'euc-kr')
                
                if encoding.lower() in ['euc-kr', 'cp949']:
                    xml_content = response.content.decode('euc-kr').encode('utf-8')
                else:
                    xml_content = response.content
                
                # XML 파싱
                root = ET.fromstring(xml_content)
                self.last_call_time = time.time()
                
                self.logger.info(f"✅ API 호출 성공 (인코딩: {encoding})")
                return root
                
            except requests.RequestException as e:
                self.logger.warning(f"⚠️ API 요청 실패 (시도 {attempt + 1}/{self.retry_count}): {e}")
                if attempt < self.retry_count - 1:
                    time.sleep(1)  # 재시도 전 1초 대기
                else:
                    self.logger.error(f"❌ API 요청 최종 실패: {e}")
                    return None
            except ET.ParseError as e:
                self.logger.error(f"❌ XML 파싱 실패: {e}")
                return None
            except Exception as e:
                self.logger.error(f"❌ 알 수 없는 오류: {e}")
                return None
        
        return None
    
    def get_market_codes(self) -> List[Dict[str, str]]:
        """마켓코드 조회 (mode=mk)"""
        params = {'mode': 'mk'}
        root = self._safe_call(self.base_url, params)
        
        if root is None:
            return []
        
        markets = []
        for info in root.findall('.//info'):
            market = {
                'code': self._get_element_text(info, 'code'),
                'name': self._get_element_text(info, 'name')
            }
            markets.append(market)
        
        return markets
    
    def get_site_codes(self) -> List[Dict[str, str]]:
        """사이트코드 조회 (mode=sitecode)"""
        params = {
            'mode': 'sitecode',
            'admin_code': self.admin_code
        }
        root = self._safe_call(self.base_url, params)
        
        if root is None:
            return []
        
        sites = []
        for info in root.findall('.//info'):
            site = {
                'site_code': self._get_element_text(info, 'SiteCode'),
                'site_name': self._get_element_text(info, 'SiteName'),
                'market_code': self._get_element_text(info, 'MarketCode'),
                'market_name': self._get_element_text(info, 'MarketName'),
                'market_id': self._get_element_text(info, 'MarketId'),
                'status': self._get_element_text(info, 'Stts')
            }
            sites.append(site)
        
        return sites
    
    def get_delivery_companies(self) -> List[Dict[str, Union[str, List]]]:
        """택배사코드 조회 (mode=tagcom)"""
        params = {'mode': 'tagcom'}
        root = self._safe_call(self.base_url, params)
        
        if root is None:
            return []
        
        companies = []
        for info in root.findall('.//info'):
            # 기본 정보
            company = {
                'code': self._get_element_text(info, 'code'),
                'name': self._get_element_text(info, 'name'),
                'details': []
            }
            
            # 상세 정보 (detail/Row)
            detail = info.find('detail')
            if detail is not None:
                for row in detail.findall('Row'):
                    detail_info = {
                        't_code': self._get_element_text(row, 'T_Code'),
                        't_name': self._get_element_text(row, 'T_Name')
                    }
                    company['details'].append(detail_info)
            
            companies.append(company)
        
        return companies
    
    def get_warehouse_codes(self) -> List[Dict[str, str]]:
        """창고코드 조회 (mode=ChanggoCode)"""
        params = {
            'mode': 'ChanggoCode',
            'admin_code': self.admin_code
        }
        root = self._safe_call(self.base_url, params)
        
        if root is None:
            return []
        
        warehouses = []
        for info in root.findall('.//info'):
            warehouse = {
                'code': self._get_element_text(info, 'code'),
                'name': self._get_element_text(info, 'name')
            }
            warehouses.append(warehouse)
        
        return warehouses
    
    def get_brand_codes(self, status: str = None, brand_code: str = None) -> List[Dict[str, str]]:
        """브랜드코드 조회 (mode=brand)"""
        params = {
            'mode': 'brand',
            'admin_code': self.admin_code
        }
        
        if status:
            params['stts'] = status
        if brand_code:
            params['code'] = brand_code
        
        root = self._safe_call(self.base_url, params)
        
        if root is None:
            return []
        
        brands = []
        for info in root.findall('.//info'):
            brand = {
                'code': self._get_element_text(info, 'code'),
                'name': self._get_element_text(info, 'name'),
                'maker': self._get_element_text(info, 'maker'),
                'status': self._get_element_text(info, 'Stts')
            }
            brands.append(brand)
        
        return brands
    
    def get_products(self, start_date: str = None, end_date: str = None, 
                    product_codes: List[str] = None) -> List[Dict[str, str]]:
        """상품 정보 조회 (mode=goods)"""
        params = {
            'mode': 'goods',
            'admin_code': self.admin_code,
            'pwd': self.password
        }
        
        if start_date:
            params['sdate'] = start_date
        if end_date:
            params['edate'] = end_date
        if product_codes:
            # vXml 형태로 상품코드 전달 (최대 10개)
            vxml_parts = [f"<row><c>{code}</c></row>" for code in product_codes[:10]]
            params['vXml'] = ''.join(vxml_parts)
        
        root = self._safe_call(self.base_url, params)
        
        if root is None:
            return []
        
        products = []
        for info in root.findall('.//info'):
            product = {
                'g_on_code': self._get_element_text(info, 'G_OnCode'),
                'g_code': self._get_element_text(info, 'G_Code'),
                'g_name': self._get_element_text(info, 'G_Name'),
                'g_stand': self._get_element_text(info, 'G_Stand'),
                'alias_name': self._get_element_text(info, 'aliasName'),
                'origin': self._get_element_text(info, 'origin'),
                'making': self._get_element_text(info, 'making'),
                'brand': self._get_element_text(info, 'brand'),
                'date': self._get_element_text(info, 'date'),
                'damdang': self._get_element_text(info, 'damdang'),
                'url': self._get_element_text(info, 'url'),
                'img_url': self._get_element_text(info, 'imgUrl'),
                'img_url_big': self._get_element_text(info, 'imgUrlBig'),
                'inter_amt': self._get_element_text(info, 'interAmt'),
                'do_amt': self._get_element_text(info, 'doAmt'),
                'so_amt': self._get_element_text(info, 'soAmt'),
                'user_amt': self._get_element_text(info, 'userAmt'),
                'ip_amt': self._get_element_text(info, 'ipAmt'),
                'taxfree': self._get_element_text(info, 'taxfree'),
                'state': self._get_element_text(info, 'state'),
                'jb_yn': self._get_element_text(info, 'jbYN'),
                'bar_code': self._get_element_text(info, 'barCode'),
                'width': self._get_element_text(info, 'G_Width'),
                'vertical': self._get_element_text(info, 'G_Vertical'),
                'height': self._get_element_text(info, 'G_Height'),
                'option_name': self._get_element_text(info, 'G_optNo_name'),
                'color_name': self._get_element_text(info, 'G_color_name'),
                'direct_shipping': self._get_element_text(info, 'J_BeasongYN')
            }
            products.append(product)
        
        return products
    
    def get_customers_paginated(self, start_date: str, end_date: str = None) -> List[Dict[str, str]]:
        """거래처 정보 조회 (mode=cust) - 설정 기반 페이징 자동 처리"""
        all_customers = []
        page = 1
        
        while True:
            self.logger.info(f"📄 거래처 조회 - 페이지 {page} (페이지당 {self.page_size}건)")
            
            params = {
                'mode': 'cust',
                'admin_code': self.admin_code,
                'pwd': self.password,
                'sdate': start_date,
                'onePageCnt': self.page_size,  # 설정값 사용
                'page': page
            }
            
            if end_date:
                params['edate'] = end_date
            
            root = self._safe_call(self.base_url, params)
            
            if root is None:
                break
            
            # 페이징 정보 확인
            select_cnt = int(self._get_element_text(root, 'SelecCnt') or '0')
            tot_page = int(self._get_element_text(root, 'TotPage') or '0')
            
            self.logger.info(f"📊 조회 결과: {select_cnt}건, 총 {tot_page}페이지")
            
            # 고객 정보 파싱
            customers = []
            for info in root.findall('.//info'):
                customer = {
                    'g_code': self._get_element_text(info, 'G_code'),
                    'g_name': self._get_element_text(info, 'G_name'),
                    'g_damdang': self._get_element_text(info, 'G_Damdang'),
                    'g_ceo': self._get_element_text(info, 'G_Ceo'),
                    'g_sano': self._get_element_text(info, 'G_Sano'),
                    'g_up': self._get_element_text(info, 'G_up'),
                    'g_jong': self._get_element_text(info, 'G_Jong'),
                    'g_tel': self._get_element_text(info, 'G_tel'),
                    'g_fax': self._get_element_text(info, 'G_Fax'),
                    'g_g_damdang': self._get_element_text(info, 'G_GDamdang'),
                    'g_g_damdang_tel': self._get_element_text(info, 'G_GDamdangTel'),
                    'g_location': self._get_element_text(info, 'G_Location'),
                    'g_post1': self._get_element_text(info, 'G_Post1'),
                    'g_juso1': self._get_element_text(info, 'G_Juso1'),
                    'g_post2': self._get_element_text(info, 'G_Post2'),
                    'g_juso2': self._get_element_text(info, 'G_Juso2'),
                    'g_remk': self._get_element_text(info, 'G_Remk'),
                    'g_program_sayong': self._get_element_text(info, 'G_Program_Sayong'),
                    'in_user': self._get_element_text(info, 'In_user'),
                    'edit_date': self._get_element_text(info, 'editDate'),
                    'stts': self._get_element_text(info, 'stts'),
                    'g_on_code': self._get_element_text(info, 'G_OnCode'),
                    # 추가 상세 필드들
                    'tax_g_damdang': self._get_element_text(info, 'Tax_GDamdang'),
                    'tax_g_damdang_tel': self._get_element_text(info, 'Tax_GDamdangTel'),
                    'tax_email': self._get_element_text(info, 'Tax_Email'),
                    'link_code_acct': self._get_element_text(info, 'linkCodeAcct'),
                    'g_io_type': self._get_element_text(info, 'G_ioType'),
                    'g_dan_ga_gu': self._get_element_text(info, 'G_DanGa_Gu'),
                    'g_discount_yul': self._get_element_text(info, 'G_Discount_Yul'),
                    'g_discount_or_up': self._get_element_text(info, 'G_Discount_Or_Up'),
                    'g_account': self._get_element_text(info, 'G_Account'),
                    'g_bank_name': self._get_element_text(info, 'G_BankName'),
                    'g_bank_holder': self._get_element_text(info, 'G_BankHolder'),
                    'g_tag_code': self._get_element_text(info, 'G_TagCode'),
                    'g_tag_cust_code': self._get_element_text(info, 'G_TagCustCode'),
                    'g_direct_shipping_type': self._get_element_text(info, 'G_DirectShippingType'),
                    'g_memo': self._get_element_text(info, 'G_Memo')
                }
                customers.append(customer)
            
            all_customers.extend(customers)
            
            # 더 이상 페이지가 없으면 종료
            if page >= tot_page or len(customers) == 0:
                break
            
            page += 1
        
        self.logger.info(f"✅ 거래처 조회 완료: 총 {len(all_customers)}건")
        return all_customers
    
    def get_sales_paginated(self, start_date: str, end_date: str = None) -> List[Dict[str, str]]:
        """매출 정보 조회 (mode=sales) - 설정 기반 페이징"""
        all_sales = []
        page = 1
        
        while True:
            self.logger.info(f"💹 매출 조회 - 페이지 {page} (페이지당 {self.page_size}건)")
            
            params = {
                'mode': 'sales',
                'admin_code': self.admin_code,
                'pwd': self.password,
                'sdate': start_date,
                'onePageCnt': self.page_size,  # 설정값 사용
                'page': page
            }
            
            if end_date:
                params['edate'] = end_date
            
            root = self._safe_call(self.base_url, params)
            
            if root is None:
                break
            
            # 페이징 정보 확인
            select_cnt = int(self._get_element_text(root, 'SelecCnt') or '0')
            tot_page = int(self._get_element_text(root, 'TotPage') or '0')
            
            self.logger.info(f"📊 매출 조회 결과: {select_cnt}건, 총 {tot_page}페이지")
            
            # 매출 정보 파싱
            sales = []
            for info in root.findall('.//info'):
                sale = {
                    'order_no': self._get_element_text(info, 'orderNo'),
                    'order_date': self._get_element_text(info, 'orderDate'),
                    'customer_code': self._get_element_text(info, 'custCode'),
                    'customer_name': self._get_element_text(info, 'custName'),
                    'product_code': self._get_element_text(info, 'productCode'),
                    'product_name': self._get_element_text(info, 'productName'),
                    'quantity': self._get_element_text(info, 'quantity'),
                    'unit_price': self._get_element_text(info, 'unitPrice'),
                    'total_amount': self._get_element_text(info, 'totalAmount'),
                    'status': self._get_element_text(info, 'status')
                }
                sales.append(sale)
            
            all_sales.extend(sales)
            
            # 더 이상 페이지가 없으면 종료
            if page >= tot_page or len(sales) == 0:
                break
            
            page += 1
        
        self.logger.info(f"✅ 매출 조회 완료: 총 {len(all_sales)}건")
        return all_sales
    
    def _get_element_text(self, parent: ET.Element, tag_name: str) -> str:
        """XML 엘리먼트에서 안전하게 텍스트 추출"""
        element = parent.find(tag_name)
        return element.text if element is not None and element.text else ''

# 사용 예시
if __name__ == "__main__":
    print("🚀 ERPia API 설정 기반 클라이언트 테스트 시작")
    
    # 기본 설정값 초기화 (최초 실행시)
    ErpiaSettings.initialize_default_settings()
    
    client = ErpiaApiClient()
    
    # 현재 설정값 출력
    print(f"📊 현재 설정 - 페이지크기: {client.page_size}, 호출간격: {client.call_interval}초")
    
    # 1. 마켓코드 조회
    print("\n📋 마켓코드 조회 중...")
    markets = client.get_market_codes()
    print(f"✅ 마켓코드 {len(markets)}건 조회됨")
    for market in markets[:3]:
        print(f"   - {market['code']}: {market['name']}")
    
    print("\n🎉 ERPia API 설정 기반 테스트 완료!") 