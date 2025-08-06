# ERPia API 레거시 시스템 분석 보고서

## 📋 개요

본 문서는 기존 `@mis.aone.co.kr` 레거시 시스템에서 ERPia API를 어떻게 활용하여 **매출(주문)**, **거래처(고객)**, **상품** 정보를 수집하는지 분석한 결과입니다.

---

## 🎯 핵심 API 모드 분석

### 1. **매출(주문) 데이터 수집** - `mode=jumun`

#### **API 호출 방법**
```csharp
// 레거시 코드 분석 결과
string URLString = string.Format(
    "http://www.erpia.net/xml/xml.asp?mode=jumun&admin_code=aone&pwd=ka22fslfod1vid&sDate={0}&eDate={1}&page={2}&datetype=m", 
    sDate, eDate, iPage
);

using (var wc = new WebClient())
{
    xmlStr = wc.DownloadString(URLString);
}
```

#### **주요 파라미터**
- `mode=jumun`: 주문/매출 데이터 모드
- `admin_code=aone`: 관리자 코드 (에이원)
- `pwd=ka22fslfod1vid`: 인증 비밀번호
- `sDate`: 시작일자 (yyyyMMdd 형식)
- `eDate`: 종료일자 (yyyyMMdd 형식)
- `page`: 페이지 번호 (1부터 시작)
- `datetype=m`: 날짜 타입 (주문일 기준)

#### **XML 응답 구조 (실제 확인)**
```xml
<root>
    <info>
        <!-- 기본 주문 정보 -->
        <Site_Key_Code>마케팅 코드</Site_Key_Code>
        <Site_Code>사이트 코드</Site_Code>
        <Site_Id>마켓 아이디</Site_Id>
        <GerCode>매입 거래처 코드</GerCode>
        <Sl_No>전표번호</Sl_No>
        <orderNo>주문번호</orderNo>
        
        <!-- 주문자 정보 -->
        <Jdate>주문일</Jdate>
        <Jtime>주문 시간</Jtime>
        <Jemail>주문자 이메일</Jemail>
        <Jid>주문자 마켓 아이디</Jid>
        <Jname>주문자 이름</Jname>
        <Jtel>주문자 전화번호</Jtel>
        <Jhp>주문자 핸드폰</Jhp>
        <Jpost>주문자 우편번호</Jpost>
        <Jaddr>주문자 주소</Jaddr>
        
        <!-- 매출 정보 -->
        <mDate>매출일</mDate>
        <bAmt>배송비 등록</bAmt>
        <dsGongAmt>매출할인 공급가 등록</dsGongAmt>
        <clamYN>클레임여부(추정,취소,반품)</clamYN>
        <siteDCode>사이트 전담코드</siteDCode>
        <gerCheck>이점여부(=가격점검여부)</gerCheck>
        
        <!-- 상품 정보 (복수) -->
        <GoodsInfo>
            <!-- 기본 상품 정보 -->
            <subul_kind>수불코드</subul_kind>
            <Sl_Seq>전표순번</Sl_Seq>
            <orderSeq>주문순번</orderSeq>
            
            <!-- 마켓 상품 정보 -->
            <Gcode>마켓 상품코드</Gcode>
            <Gname>마켓 주문 상품명</Gname>
            <Gstand>마켓 주문 규격</Gstand>
            <Gqty>수량</Gqty>
            <gongAmt>공급단가</gongAmt>
            <panAmt>판매단가</panAmt>
            <Changgo_Code>창고코드</Changgo_Code>
            
            <!-- ERPia 연계 상품 정보 -->
            <GrvCode>자체코드(=자체상품코드)</GrvCode>
            <GerCode>ERPia 상품코드</GerCode>
            <GerName>ERPia 상품명</GerName>
            <GerStand>ERPia 규격</GerStand>
            <brandCode>ERPia 브랜드 코드</brandCode>
            <brandName>ERPia 브랜드 명칭</brandName>
            
            <!-- 가격 정보 -->
            <openAmt>시장가</openAmt>
            <guidanceAmt>지도가</guidanceAmt>
        </GoodsInfo>
        
        <!-- 배송 정보 -->
        <BealInfo>
            <Btype>선택불구분</Btype>
            <Bname>수령자 이름</Bname>
            <Btel>수령자 전화번호</Btel>
            <Bhp>수령자 핸드폰</Bhp>
            <Bpost>수령자 우편번호</Bpost>
            <Baddr>수령자 주소</Baddr>
            <Bbigo>배송정보설치</Bbigo>
            <TagCode>택배사코드</TagCode>
            <songNo>운송장번호</songNo>
        </BealInfo>
    </info>
</root>
```

#### **데이터 처리 로직**
1. **중복 체크**: `Sl_No`로 기존 데이터 존재 여부 확인
2. **배송 정보 저장**: `tbl_Erpia_Order_Delivery` 테이블
3. **주문 마스터 저장**: `tbl_Erpia_Order_Mst` 테이블
4. **상품 상세 저장**: `tbl_Erpia_Order_Product` 테이블

---

### 2. **거래처(매장) 정보 수집** - `mode=cust`

#### **API 호출 방법**
```csharp
// 레거시 코드 분석 결과
var URLString = "http://www.erpia.net/xml/xml.asp?mode=cust&admin_code=aone&pwd=ka22fslfod1vid&sDate=" + 
                DateTime.Now.ToString("yyyyMMdd") + "&eDate=" + DateTime.Now.ToString("yyyyMMdd") + 
                "&onePageCnt=10&page=" + idx;

XmlDocument xml = new XmlDocument();
xml.Load(URLString);
```

#### **주요 파라미터**
- `mode=cust`: 매장(거래처) 정보 모드
- `admin_code=aone`: 관리자 코드
- `pwd=ka22fslfod1vid`: 인증 비밀번호
- `sDate`: 시작일자
- `eDate`: 종료일자
- `onePageCnt=10`: 페이지당 데이터 건수 (레거시에서는 10건씩)
- `page`: 페이지 번호

#### **XML 응답 구조 (실제 확인)**
```xml
<root>
    <!-- 조회 정보 -->
    <SelectCnt>조회된 거래처 수</SelectCnt>
    <TotPage>총 페이지 수</TotPage>
    
    <info>
        <!-- 기본 정보 -->
        <G_code>ERPia 거래처 코드(=거래처코드)</G_code>
        <G_name>거래처명</G_name>
        <G_Ceo>대표자</G_Ceo>
        <G_Sano>사업자번호</G_Sano>
        <G_up>업태</G_up>
        <G_Jong>종목</G_Jong>
        
        <!-- 연락처 정보 -->
        <G_tel>전화</G_tel>
        <G_Fax>팩스</G_Fax>
        
        <!-- 담당자 정보 -->
        <G_Damdang>(우리회사의) 거래처 담당</G_Damdang>
        <G_Gdamdang>(상대회사) 거래처의 담당자</G_Gdamdang>
        <G_GDamdangTel>거래처 담당자 연락처</G_GDamdangTel>
        
        <!-- 주소 정보 -->
        <G_Location>위물도시선물</G_Location>
        <G_Post1>우편번호</G_Post1>
        <G_Juso1>주소</G_Juso1>
        <G_Post2>사업거치선 우편번호</G_Post2>
        <G_Juso2>사업거치선 주소</G_Juso2>
        
        <!-- 관리 정보 -->
        <G_Remk>비고</G_Remk>
        <G_Program_Sayong>SCM 사용여부</G_Program_Sayong>
        <In_user>등록자</In_user>
        <editDate>최종수정일</editDate>
        <stts>상태 (0:사용, 9:미사용)</stts>
        <G_OnCode>자체거래처코드</G_OnCode>
        
        <!-- 세금 관련 담당자 -->
        <Tax_GDamdang>사업거치선 담당자 이름</Tax_GDamdang>
        <Tax_GDamdangTel>사업거치선 담당자 연락처</Tax_GDamdangTel>
        <Tax_Email>사업거치선 담당자 이메일</Tax_Email>
        
        <!-- 연계 정보 -->
        <linkCodeAcct>회계 연계코드</linkCodeAcct>
        <G_JoType>거래(업종)구분</G_JoType>
        
        <!-- 매입 단가 정보 -->
        <G_DanGa_Gu>매입단가</G_DanGa_Gu>
        <G_Discount_Yul>매입단가 할인율등록</G_Discount_Yul>
        <G_Discount_Or_Up>할인율등록구분</G_Discount_Or_Up>
        <Use_Recent_DanGa_YN>최근판단단가 우선적용률</Use_Recent_DanGa_YN>
        
        <!-- 매입 단가 정보 (J 버전) -->
        <G_DanGa_GuJ>매입단가</G_DanGa_GuJ>
        <G_Discount_YulJ>매입단가 할인율등록</G_Discount_YulJ>
        <G_Discount_Or_UpJ>할인율등록구분</G_Discount_Or_UpJ>
        <Use_Recent_DanGa_YNJ>최근판단단가 우선적용률</Use_Recent_DanGa_YNJ>
        
        <!-- 계좌 정보 -->
        <G_Account>계좌번호</G_Account>
        <G_BankName>은행명</G_BankName>
        <G_BankHolder>예금주</G_BankHolder>
        
        <!-- 배송 정보 -->
        <G_TagCode>택배사코드</G_TagCode>
        <G_TagCustCode>택배 연계코드</G_TagCustCode>
        <G_DirectShippingType>직배송업체구분</G_DirectShippingType>
        
        <!-- 추가 메모 -->
        <G_Memo>메모</G_Memo>
    </info>
</root>
```

#### **데이터 저장**
- `tbl_Erpia_Customer` 테이블에 저장
- Naver API를 이용한 주소 검증 로직 포함

---

### 3. **상품 정보 수집** - `mode=jegoAll` (재고 전체)

#### **API 호출 방법**
```csharp
// 레거시 코드 분석 결과 (StockController.cs)
string URLString = "http://www.erpia.net/xml/xml.asp?mode=jegoAll&admin_code=aone&pwd=ka22fslfod1vid";

string xmlStr;
using (var wc = new WebClient())
{
    xmlStr = wc.DownloadString(URLString);
}
```

#### **주요 파라미터**
- `mode=jegoAll`: 재고 전체 조회 모드
- `admin_code=aone`: 관리자 코드
- `pwd=ka22fslfod1vid`: 인증 비밀번호

#### **XML 응답 구조**
```xml
<root>
    <info>
        <G_OnCode>온라인코드</G_OnCode>
        <G_Code>상품코드</G_Code>
        <G_Name>상품명</G_Name>
        <G_Stand>상품규격</G_Stand>
        <jego>재고수량</jego>
    </info>
</root>
```

### **4. 상품 정보 수집** - `mode=goods` (확장 구현)

#### **API 호출 방법**
```python
# 현재 구현 방식
params = {
    'mode': 'goods',
    'admin_code': 'aone',
    'pwd': 'ka22fslfod1vid',
    'onePageCnt': 30,
    'page': 1
}
```

#### **주요 파라미터**
- `mode=goods`: 상품 상세 정보 모드
- `admin_code=aone`: 관리자 코드
- `pwd=ka22fslfod1vid`: 인증 비밀번호
- `onePageCnt=30`: 페이지당 데이터 건수
- `page`: 페이지 번호

#### **XML 응답 구조 (실제 확인)**
```xml
<root>
    <info>
        <!-- 기본 정보 -->
        <G_OnCode>자체물상품코드(=자체코드)</G_OnCode>
        <G_Code>ERPia 상품코드</G_Code>
        <G_Name>ERPia 상품명</G_Name>
        <G_Stand>ERPia 규격</G_Stand>
        <aliasName>상품별칭</aliasName>
        
        <!-- 제조/브랜드 정보 -->
        <origin>원산지</origin>
        <making>제조사</making>
        <brand>브랜드</brand>
        
        <!-- 관리 정보 -->
        <date>최종수정일</date>
        <damdang>담당자</damdang>
        
        <!-- URL 정보 -->
        <url>상품상세 URL</url>
        <imgUrl>웹당 상품 이미지 url</imgUrl>
        <imgUrlBig>웹당 상품 큰 이미지 url</imgUrlBig>
        
        <!-- 가격 정보 -->
        <interAmt>인터넷 판매단가</interAmt>
        <doAmt>도매 판매단가</doAmt>
        <soAmt>소매 단가</soAmt>
        <userAmt>권장 소비자가</userAmt>
        <ipAmt>매입 단가</ipAmt>
        
        <!-- 상태 정보 -->
        <taxfree>비과세</taxfree>
        <state>상품상태</state>
        <jbYN>직배송여부</jbYN>
        
        <!-- 연계코드 -->
        <linkCodeAcct>회계 연계코드</linkCodeAcct>
        <linkCodeWms>물류 연계코드</linkCodeWms>
        <linkCodeTmp>기타 연계코드</linkCodeTmp>
        
        <!-- 단위 정보 -->
        <Unit_Kind>단위구분</Unit_Kind>
        <Unit>단위</Unit>
        <Unit_Val>단위환산</Unit_Val>
        
        <!-- 기타 정보 -->
        <remk1>비고</remk1>
        <boxInQty>1박스당 수량</boxInQty>
        <bunRyu>분류 (= 업태 부가세 구분)</bunRyu>
        <location>로케이션(창고-위치정보)</location>
        <Changgo_Code>매출 창고코드</Changgo_Code>
        <barCode>바코드</barCode>
        <BS_Sale_YN>단독배송여부</BS_Sale_YN>
        <concrete_YN>유무형 구분</concrete_YN>
        <Deposit_GUBUN>무형상품분류</Deposit_GUBUN>
        <tagPrintYN>택배출력여부</tagPrintYN>
        <G_Width>가로(폭)</G_Width>
        <G_Vertical>세로(장)</G_Vertical>
        <G_Height>높이(고)</G_Height>
        <G_optNo_name>색상명</G_optNo_name>
        <G_color_name>옵션명</G_color_name>
        <J_BeasongsYN>직배송여부</J_BeasongsYN>
    </info>
</root>
```

#### **데이터 처리**
- **페이징**: 30건씩 처리 (ERPia 최대 제한)
- **저장**: 상품 마스터 테이블에 저장
- **특징**: 재고 정보(`mode=jegoAll`)보다 훨씬 상세한 정보 제공

---

## 🔄 레거시 시스템의 배치 처리 패턴

### 1. **실행 순서**
```csharp
public void GetOrderXmlData()
{
    // 1단계: 매장정보 동기화 먼저 실행
    this.ErpiaCustSync();
    
    // 2단계: 주문 정보 수집
    // 날짜별 반복 처리...
}
```

### 2. **ERPia 관리자 코드 추적**
수집되는 모든 데이터에는 `admin_code` 필드가 포함되어 어느 회사에서 수집한 데이터인지 추적 가능:

**회사별 관리자 코드:**
- **에이원**: `admin_code=aone`
- **에이원월드**: `admin_code=[별도 제공 예정]`

**추적 필드:**
- `admin_code`: ERPia 관리자 코드 (회사 식별용)
- `company_id`: 내부 회사 ID
- `collected_at`: 수집 시간

**활용 예시:**
```python
# 특정 관리자 코드로 수집된 데이터 조회
aone_customers = fetch_customers_by_admin_code('aone')
aone_world_sales = fetch_sales_by_admin_code('aone_world')

# 회사 정보 확인
company_info = ErpiaApiClient.get_company_by_admin_code('aone')
print(f"회사: {company_info['company_name']}")
```

### 3. **페이징 처리**
```csharp
int iPage = 1;
while (true)
{
    // API 호출
    string URLString = string.Format("...", sDate, iPage);
    
    // XML 파싱
    XmlNodeList xnList = xml.SelectNodes("/root/info");
    
    // 데이터가 없으면 종료
    if (xnList.Count == 0)
    {
        break;
    }
    
    // 다음 페이지로
    iPage++;
}
```

### 3. **중복 방지**
```csharp
// 주문번호로 중복 체크
string sSlNo = xn["Sl_No"].InnerText;
int rowCnt = db.tbl_Erpia_Order_Mst.Where(a => a.Sl_No == sSlNo).Count();
if (rowCnt > 0)
{
    continue; // 이미 존재하면 건너뜀
}
```

---

## 📊 현재 구현과의 차이점 분석

### 1. **API 모드 매핑**
| 레거시 시스템 | 현재 구현 | 용도 |
|-------------|-----------|-----|
| `mode=jumun` | `mode=jumun` | 매출/주문 데이터 ✅ |
| `mode=cust` | `mode=cust` | 고객 정보 ✅ |
| `mode=jegoAll` | `mode=goods` | 상품 정보 ⚠️ |

### 2. **페이징 설정**
- **레거시**: `onePageCnt=10` (10건씩)
- **현재**: `onePageCnt=30` (30건씩) - ERPia 최대 제한

### 3. **데이터 구조**
- **레거시**: 별도 테이블 (`tbl_Erpia_*`)
- **현재**: 통합 분석 테이블 + 회사별 분리

---

## 🚨 주의사항 및 제약사항

### 1. **API 호출 제한**
- **호출 간격**: 레거시에서는 별도 제한 없음
- **현재 구현**: 3초 간격 (안정성 향상)

### 2. **인코딩**
- ERPia API는 **EUC-KR** 인코딩 사용
- 한글 데이터 처리 시 인코딩 변환 필수

### 3. **인증 정보**
- `admin_code=aone`
- `pwd=ka22fslfod1vid`
- 에이원 전용 계정 (에이원월드는 별도 계정 필요)

### 4. **데이터 신뢰성**
```csharp
// 레거시의 데이터 검증 로직
if (xn["BeaInfo"] == null && item["subul_kind"].InnerText == "221")
{
    saveYn = false; // 배송정보 없는 특정 수불종류는 제외
    break;
}
```

---

## 🎯 권장사항

### 1. **API 모드 통일**
- `mode=goods` 대신 `
```
레거시 시스템 분석 결과, ERPia API의 핵심 4개 모드로 분리 구현했습니다:

1. **`mode=cust`** - 매장정보 (완벽 호환 ✅)
2. **`mode=jegoAll`** - 재고 정보 (레거시 호환 ✅) 
3. **`mode=goods`** - 상품 정보 (확장 구현 ✅)
4. **`mode=jumun`** - 매출/주문 데이터 (완벽 호환 ✅)

현재 구현된 시스템은 레거시의 `mode=jegoAll` (재고)는 그대로 유지하면서, 추가로 `mode=goods` (상품 상세)를 지원하여 더 풍부한 상품 정보를 수집할 수 있습니다. 성능 최적화 (30건 페이징, 3초 간격)와 안정성 (재시도, 오류 처리)이 개선되었습니다.

### **🔄 최종 실행 순서**
```
1단계: 매장정보 수집 (mode=cust)
   ↓ 3초 대기
2단계: 재고 정보 수집 (mode=jegoAll) - 레거시 호환
   ↓ 3초 대기
3단계: 상품 정보 수집 (mode=goods) - 상세 정보
   ↓ 3초 대기
4단계: 매출 데이터 수집 (mode=jumun) + 사은품 분류
```