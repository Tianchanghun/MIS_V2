 # ERPia API XML 요청 가이드

## 📋 **문서 개요**

**작성일**: 2025-08-05  
**기반**: ERPia API V3.7 (2021.07.01) - 에이원 전용  
**목적**: ERPia 시스템으로부터 XML 형태로 데이터를 요청하는 방법 가이드  
**레거시 분석**: `ErpiaRelationController.cs` 기반 실제 사용 패턴

---

## 🔑 **인증 정보**

### **기본 접속 정보**
```plaintext
🌐 ERPia 서버: http://www.erpia.net/
🛠️ XML API 엔드포인트: http://www.erpia.net/xml/xml.asp
👤 관리자 코드(admin_code): aone
🔐 비밀번호(pwd): ka22fslfod1vid
```

### **보안 주의사항**
- ⚠️ 모든 요청은 HTTP 기반 (HTTPS 아님)
- 🔐 인증 정보가 URL 파라미터로 전송됨
- 📝 접근 권한은 에이원(aone) 계정으로 제한

---

## 🛠️ **API 엔드포인트 구조**

### **기본 URL 형식**
```
http://www.erpia.net/xml/xml.asp?[파라미터들]
```

### **공통 필수 파라미터**
| 파라미터 | 값 | 설명 |
|---------|----|----|
| `admin_code` | `aone` | 관리자 코드 (고정값) |
| `pwd` | `ka22fslfod1vid` | 비밀번호 (일부 API에서 필요) |
| `mode` | 변수 | 요청 모드 (API 유형) |

---

## 📊 **지원되는 API 모드**

### 1. **고객 정보 조회 (mode=cust)**

#### **요청 URL 예시**
```
http://www.erpia.net/xml/xml.asp?mode=cust&admin_code=aone&pwd=ka22fslfod1vid&sDate=20190101&eDate=20201231&onePageCnt=10&page=1
```

#### **파라미터 상세**
| 파라미터 | 필수 | 타입 | 설명 | 예시 |
|---------|------|------|------|------|
| `mode` | ✅ | string | 고정값: "cust" | cust |
| `admin_code` | ✅ | string | 관리자 코드 | aone |
| `pwd` | ✅ | string | 비밀번호 | ka22fslfod1vid |
| `sDate` | ✅ | string | 시작일 (YYYYMMDD) | 20190101 |
| `eDate` | ✅ | string | 종료일 (YYYYMMDD) | 20201231 |
| `onePageCnt` | ❌ | int | 한 페이지당 레코드 수 | 10 |
| `page` | ❌ | int | 페이지 번호 (1부터 시작) | 1 |

#### **응답 XML 구조**
```xml
<root>
    <info>
        <G_code>고객코드</G_code>
        <G_name>고객명</G_name>
        <G_Damdang>담당자</G_Damdang>
        <G_Ceo>대표자</G_Ceo>
        <G_Sano>사업자번호</G_Sano>
        <G_up>업태</G_up>
        <G_Jong>종목</G_Jong>
        <G_tel>전화번호</G_tel>
        <G_Fax>팩스번호</G_Fax>
        <G_GDamdang>담당자명</G_GDamdang>
        <G_GDamdangTel>담당자전화</G_GDamdangTel>
        <G_Location>위치</G_Location>
        <G_Post1>우편번호1</G_Post1>
        <G_Juso1>주소1</G_Juso1>
        <G_Post2>우편번호2</G_Post2>
        <G_Juso2>주소2</G_Juso2>
        <G_Remk>비고</G_Remk>
        <G_Program_Sayong>프로그램사용</G_Program_Sayong>
        <In_user>입력자</In_user>
        <editDate>수정일</editDate>
        <stts>상태</stts>
        <G_OnCode>온라인코드</G_OnCode>
    </info>
    <!-- 추가 고객 정보... -->
</root>
```

### 2. **사이트 코드 조회 (mode=sitecode)**

#### **요청 URL 예시**
```
http://www.erpia.net/xml/xml.asp?mode=sitecode&admin_code=aone
```

#### **파라미터 상세**
| 파라미터 | 필수 | 타입 | 설명 | 예시 |
|---------|------|------|------|------|
| `mode` | ✅ | string | 고정값: "sitecode" | sitecode |
| `admin_code` | ✅ | string | 관리자 코드 | aone |

#### **응답 XML 구조**
```xml
<root>
    <info>
        <SiteCode>사이트코드</SiteCode>
        <SiteName>사이트명</SiteName>
        <MarketCode>마켓코드</MarketCode>
        <MarketName>마켓명</MarketName>
        <MarketId>마켓ID</MarketId>
        <Stts>상태</Stts>
    </info>
    <!-- 추가 사이트 정보... -->
</root>
```

---

## 💻 **C# 구현 예시**

### **고객 정보 조회 구현**
```csharp
using System;
using System.Xml;

public class ErpiaApiClient
{
    private const string BASE_URL = "http://www.erpia.net/xml/xml.asp";
    private const string ADMIN_CODE = "aone";
    private const string PASSWORD = "ka22fslfod1vid";
    
    /// <summary>
    /// 고객 정보 조회
    /// </summary>
    /// <param name="startDate">시작일 (YYYYMMDD)</param>
    /// <param name="endDate">종료일 (YYYYMMDD)</param>
    /// <param name="pageSize">페이지당 레코드 수</param>
    /// <param name="pageNumber">페이지 번호</param>
    /// <returns>XML 문서</returns>
    public XmlDocument GetCustomerList(string startDate, string endDate, int pageSize = 10, int pageNumber = 1)
    {
        try
        {
            string url = $"{BASE_URL}?mode=cust&admin_code={ADMIN_CODE}&pwd={PASSWORD}" +
                        $"&sDate={startDate}&eDate={endDate}&onePageCnt={pageSize}&page={pageNumber}";
            
            XmlDocument xml = new XmlDocument();
            xml.Load(url);
            
            return xml;
        }
        catch (Exception ex)
        {
            throw new Exception($"ERPia API 고객 정보 조회 실패: {ex.Message}");
        }
    }
    
    /// <summary>
    /// 사이트 코드 조회
    /// </summary>
    /// <returns>XML 문서</returns>
    public XmlDocument GetSiteCodeList()
    {
        try
        {
            string url = $"{BASE_URL}?mode=sitecode&admin_code={ADMIN_CODE}";
            
            XmlDocument xml = new XmlDocument();
            xml.Load(url);
            
            return xml;
        }
        catch (Exception ex)
        {
            throw new Exception($"ERPia API 사이트 코드 조회 실패: {ex.Message}");
        }
    }
}
```

### **고객 정보 파싱 예시**
```csharp
/// <summary>
/// XML에서 고객 정보 파싱
/// </summary>
/// <param name="xml">ERPia에서 받은 XML 문서</param>
/// <returns>고객 정보 리스트</returns>
public List<Customer> ParseCustomerXml(XmlDocument xml)
{
    var customers = new List<Customer>();
    
    XmlNodeList customerNodes = xml.SelectNodes("/root/info");
    
    foreach (XmlNode node in customerNodes)
    {
        var customer = new Customer
        {
            Code = GetNodeValue(node, "G_code"),
            Name = GetNodeValue(node, "G_name"),
            Manager = GetNodeValue(node, "G_Damdang"),
            CEO = GetNodeValue(node, "G_Ceo"),
            BusinessNumber = GetNodeValue(node, "G_Sano"),
            BusinessType = GetNodeValue(node, "G_up"),
            BusinessItem = GetNodeValue(node, "G_Jong"),
            Phone = GetNodeValue(node, "G_tel"),
            Fax = GetNodeValue(node, "G_Fax"),
            ManagerName = GetNodeValue(node, "G_GDamdang"),
            ManagerPhone = GetNodeValue(node, "G_GDamdangTel"),
            Location = GetNodeValue(node, "G_Location"),
            PostCode1 = GetNodeValue(node, "G_Post1"),
            Address1 = GetNodeValue(node, "G_Juso1"),
            PostCode2 = GetNodeValue(node, "G_Post2"),
            Address2 = GetNodeValue(node, "G_Juso2"),
            Remarks = GetNodeValue(node, "G_Remk"),
            ProgramUsage = GetNodeValue(node, "G_Program_Sayong"),
            InputUser = GetNodeValue(node, "In_user"),
            EditDate = GetNodeValue(node, "editDate"),
            Status = GetNodeValue(node, "stts"),
            OnlineCode = GetNodeValue(node, "G_OnCode")?.Replace("\r\n", "")
        };
        
        customers.Add(customer);
    }
    
    return customers;
}

/// <summary>
/// XML 노드에서 안전하게 값 추출
/// </summary>
/// <param name="node">XML 노드</param>
/// <param name="nodeName">노드명</param>
/// <returns>노드 값 (없으면 빈 문자열)</returns>
private string GetNodeValue(XmlNode node, string nodeName)
{
    return node[nodeName]?.InnerText ?? string.Empty;
}
```

---

## 🐍 **Python 구현 예시**

### **requests + xml.etree.ElementTree 사용**
```python
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime

class ErpiaApiClient:
    """ERPia API 클라이언트"""
    
    def __init__(self):
        self.base_url = "http://www.erpia.net/xml/xml.asp"
        self.admin_code = "aone"
        self.password = "ka22fslfod1vid"
    
    def get_customer_list(self, start_date: str, end_date: str, 
                         page_size: int = 10, page_number: int = 1) -> Optional[ET.Element]:
        """
        고객 정보 조회
        
        Args:
            start_date: 시작일 (YYYYMMDD 형식)
            end_date: 종료일 (YYYYMMDD 형식)
            page_size: 페이지당 레코드 수
            page_number: 페이지 번호 (1부터 시작)
            
        Returns:
            XML 루트 엘리먼트 또는 None
        """
        try:
            params = {
                'mode': 'cust',
                'admin_code': self.admin_code,
                'pwd': self.password,
                'sDate': start_date,
                'eDate': end_date,
                'onePageCnt': page_size,
                'page': page_number
            }
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            # XML 파싱
            root = ET.fromstring(response.content)
            return root
            
        except requests.RequestException as e:
            print(f"❌ ERPia API 요청 실패: {e}")
            return None
        except ET.ParseError as e:
            print(f"❌ XML 파싱 실패: {e}")
            return None
    
    def get_site_code_list(self) -> Optional[ET.Element]:
        """
        사이트 코드 조회
        
        Returns:
            XML 루트 엘리먼트 또는 None
        """
        try:
            params = {
                'mode': 'sitecode',
                'admin_code': self.admin_code
            }
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            # XML 파싱
            root = ET.fromstring(response.content)
            return root
            
        except requests.RequestException as e:
            print(f"❌ ERPia API 요청 실패: {e}")
            return None
        except ET.ParseError as e:
            print(f"❌ XML 파싱 실패: {e}")
            return None
    
    def parse_customer_xml(self, xml_root: ET.Element) -> List[Dict[str, str]]:
        """
        고객 정보 XML 파싱
        
        Args:
            xml_root: XML 루트 엘리먼트
            
        Returns:
            고객 정보 딕셔너리 리스트
        """
        customers = []
        
        for info in xml_root.findall('.//info'):
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
                'g_on_code': self._get_element_text(info, 'G_OnCode').replace('\r\n', '') if self._get_element_text(info, 'G_OnCode') else ''
            }
            customers.append(customer)
        
        return customers
    
    def parse_site_code_xml(self, xml_root: ET.Element) -> List[Dict[str, str]]:
        """
        사이트 코드 XML 파싱
        
        Args:
            xml_root: XML 루트 엘리먼트
            
        Returns:
            사이트 코드 딕셔너리 리스트
        """
        site_codes = []
        
        for info in xml_root.findall('.//info'):
            site_code = {
                'site_code': self._get_element_text(info, 'SiteCode'),
                'site_name': self._get_element_text(info, 'SiteName'),
                'market_code': self._get_element_text(info, 'MarketCode'),
                'market_name': self._get_element_text(info, 'MarketName'),
                'market_id': self._get_element_text(info, 'MarketId'),
                'stts': self._get_element_text(info, 'Stts')
            }
            site_codes.append(site_code)
        
        return site_codes
    
    def _get_element_text(self, parent: ET.Element, tag_name: str) -> str:
        """
        XML 엘리먼트에서 안전하게 텍스트 추출
        
        Args:
            parent: 부모 엘리먼트
            tag_name: 태그명
            
        Returns:
            텍스트 값 (없으면 빈 문자열)
        """
        element = parent.find(tag_name)
        return element.text if element is not None and element.text else ''

# 사용 예시
if __name__ == "__main__":
    # ERPia API 클라이언트 초기화
    api_client = ErpiaApiClient()
    
    # 고객 정보 조회 (2019년 전체)
    print("🔄 고객 정보 조회 중...")
    xml_root = api_client.get_customer_list("20190101", "20191231", page_size=50, page_number=1)
    
    if xml_root is not None:
        customers = api_client.parse_customer_xml(xml_root)
        print(f"✅ {len(customers)}건의 고객 정보를 성공적으로 조회했습니다.")
        
        # 첫 번째 고객 정보 출력 예시
        if customers:
            first_customer = customers[0]
            print(f"📋 첫 번째 고객: {first_customer['g_name']} ({first_customer['g_code']})")
    
    # 사이트 코드 조회
    print("\n🔄 사이트 코드 조회 중...")
    xml_root = api_client.get_site_code_list()
    
    if xml_root is not None:
        site_codes = api_client.parse_site_code_xml(xml_root)
        print(f"✅ {len(site_codes)}건의 사이트 코드를 성공적으로 조회했습니다.")
```

---

## 🔄 **페이징 처리 방법**

### **전체 데이터 조회 패턴**
```python
def get_all_customers(self, start_date: str, end_date: str, page_size: int = 10) -> List[Dict[str, str]]:
    """
    모든 고객 정보 조회 (페이징 자동 처리)
    
    Args:
        start_date: 시작일 (YYYYMMDD)
        end_date: 종료일 (YYYYMMDD)
        page_size: 페이지당 레코드 수
        
    Returns:
        전체 고객 정보 리스트
    """
    all_customers = []
    page_number = 1
    
    while True:
        print(f"📄 페이지 {page_number} 조회 중...")
        
        xml_root = self.get_customer_list(start_date, end_date, page_size, page_number)
        if xml_root is None:
            print(f"❌ 페이지 {page_number} 조회 실패")
            break
        
        customers = self.parse_customer_xml(xml_root)
        
        # 더 이상 데이터가 없으면 종료
        if not customers:
            print(f"✅ 페이지 {page_number}에서 데이터 없음. 조회 완료.")
            break
        
        all_customers.extend(customers)
        print(f"📋 페이지 {page_number}: {len(customers)}건 조회됨 (누적: {len(all_customers)}건)")
        
        page_number += 1
        
        # 무한루프 방지 (최대 1000페이지)
        if page_number > 1000:
            print("⚠️ 최대 페이지 수 도달. 조회 중단.")
            break
    
    return all_customers
```

---

## ⚠️ **주의사항 및 제한사항**

### **1. 보안 관련**
- 🔓 **HTTP 통신**: HTTPS가 아닌 HTTP 사용으로 보안에 취약
- 🔑 **URL 파라미터 인증**: 인증 정보가 URL에 노출됨
- 📝 **로그 주의**: 웹 서버 로그에 인증 정보가 기록될 수 있음

### **2. 성능 관련**
- ⏱️ **응답 시간**: 대용량 데이터 조회 시 응답이 느릴 수 있음
- 📊 **페이지 크기**: `onePageCnt`는 적절히 조절 (권장: 10-50)
- 🔄 **재시도 로직**: 네트워크 오류에 대비한 재시도 구현 필요

### **3. 데이터 관련**
- 📅 **날짜 형식**: YYYYMMDD 형식 엄격히 준수
- 🔤 **문자 인코딩**: UTF-8 또는 EUC-KR 확인 필요
- 🧹 **데이터 정리**: `\r\n` 등 제어 문자 처리 필요

### **4. API 제한사항**
- 🚫 **동시 접속**: 과도한 동시 요청 시 차단 가능
- 📊 **데이터 범위**: 특정 기간으로 제한됨
- 🔄 **업데이트 주기**: 실시간이 아닌 배치 업데이트

---

## 🧪 **테스트 방법**

### **1. 브라우저 테스트**
다음 URL을 브라우저에서 직접 테스트:
```
http://www.erpia.net/xml/xml.asp?mode=sitecode&admin_code=aone
```

### **2. curl 테스트**
```bash
# 사이트 코드 조회
curl "http://www.erpia.net/xml/xml.asp?mode=sitecode&admin_code=aone"

# 고객 정보 조회 (1페이지)
curl "http://www.erpia.net/xml/xml.asp?mode=cust&admin_code=aone&pwd=ka22fslfod1vid&sDate=20190101&eDate=20191231&onePageCnt=5&page=1"
```

### **3. Python 간단 테스트**
```python
import requests

# 간단한 연결 테스트
url = "http://www.erpia.net/xml/xml.asp?mode=sitecode&admin_code=aone"
response = requests.get(url)
print(f"상태 코드: {response.status_code}")
print(f"응답 길이: {len(response.text)}")
print(f"응답 내용 (일부): {response.text[:200]}...")
```

---

## 📝 **추가 API 모드 추정**

### **가능한 다른 모드들** (추정)
레거시 코드에서는 `cust`와 `sitecode`만 확인되었지만, 일반적인 ERPia API에서 제공할 수 있는 모드들:

| 모드 | 설명 | 추정 파라미터 |
|------|------|---------------|
| `order` | 주문 정보 | mode=order&admin_code=aone&pwd=... |
| `product` | 상품 정보 | mode=product&admin_code=aone&pwd=... |
| `stock` | 재고 정보 | mode=stock&admin_code=aone&pwd=... |
| `sales` | 매출 정보 | mode=sales&admin_code=aone&pwd=... |

⚠️ **주의**: 위 모드들은 추정이므로 실제 테스트를 통해 확인 필요

---

## 🎯 **MIS v2 프로젝트 적용 방안**

### **1. Flask 서비스로 구현**
```python
# services/erpia_service.py
from flask import current_app
import logging

class ErpiaService:
    """ERPia API 서비스"""
    
    def __init__(self):
        self.api_client = ErpiaApiClient()
        self.logger = logging.getLogger(__name__)
    
    def sync_customers(self, start_date: str, end_date: str) -> bool:
        """
        ERPia에서 고객 정보 동기화
        
        Args:
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
            
        Returns:
            성공 여부
        """
        try:
            customers = self.api_client.get_all_customers(start_date, end_date)
            
            # PostgreSQL에 저장
            from models.customer import Customer
            success_count = 0
            
            for customer_data in customers:
                customer = Customer.create_from_erpia(customer_data)
                if customer:
                    success_count += 1
            
            self.logger.info(f"✅ ERPia 고객 동기화 완료: {success_count}건")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ERPia 고객 동기화 실패: {e}")
            return False
```

### **2. 스케줄러 작업으로 등록**
```python
# tasks/erpia_sync.py
from celery import Celery
from datetime import datetime, timedelta

@celery.task
def sync_erpia_customers():
    """ERPia 고객 정보 동기화 작업"""
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
    
    erpia_service = ErpiaService()
    result = erpia_service.sync_customers(start_date, end_date)
    
    return {
        'success': result,
        'start_date': start_date,
        'end_date': end_date,
        'timestamp': datetime.now().isoformat()
    }
```

---

## 📚 **참고 자료**

### **레거시 코드 위치**
- `mis.aone.co.kr/Controllers/ErpiaRelationController.cs`
- `mis.aone.co.kr/Models/tbl_Erpia_Customer.cs`
- `mis.aone.co.kr/Models/tbl_Erpia_SiteCode.cs`

### **관련 테이블**
- `tbl_Erpia_Customer`: ERPia 고객 정보
- `tbl_Erpia_SiteCode`: ERPia 사이트 코드
- `tbl_Erpia_Customer_Slave_Input`: ERPia 고객 부가 정보

### **외부 연동**
- Naver API: 주소 → 좌표 변환
- Google Maps API: 지오코딩 (주석 처리됨)

---

**📝 문서 버전**: v1.0  
**📝 마지막 업데이트**: 2025-08-05  
**📝 검토자**: MIS v2 개발팀  
**📝 승인**: 기획팀 