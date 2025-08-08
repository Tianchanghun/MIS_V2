# 레거시 상품 정보 엑셀 추출 스크립트

## 📋 개요

레거시 MIS 시스템(mis.aone.co.kr)의 MS-SQL 데이터베이스에서 모든 상품 정보를 엑셀 파일로 추출하는 스크립트입니다.

## 🎯 추출 데이터

### 📊 **상품 목록 시트**
- 상품 마스터 정보 (tbl_Product + 관련 코드)
- 회사명, 브랜드명, 품목명, 타입명 등 코드 매핑된 정보

### 📝 **상품 상세 시트** 
- 상품 상세 정보 (tbl_Product_DTL)
- 색상, 타입 등 세부 구분 정보

### 🏷️ **코드 정보 시트**
- 상품 관련 코드 테이블 정보
- 회사, 브랜드, 품목, 타입 등의 코드 체계

### 📈 **통계 정보 시트**
- 총 상품 수, 사용/미사용 현황
- 회사별/브랜드별 통계

## 🚀 실행 방법

### 기본 실행
```bash
cd C:\mis_v2
python scripts/export_legacy_products.py
```

### 파일명 지정 실행
```bash
python scripts/export_legacy_products.py --output "상품목록_2025년8월.xlsx"
```

## ⚙️ 데이터베이스 연결 설정

스크립트 실행 전에 레거시 MS-SQL 데이터베이스 연결 정보를 확인해야 합니다.

### 🔧 **연결 정보 수정**

`scripts/export_legacy_products.py` 파일의 `connect_to_legacy_db()` 함수에서 연결 정보를 수정:

```python
# Windows 인증 방식 (기본)
connection_string = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost\\SQLEXPRESS;"  # 실제 서버 주소로 변경
    "DATABASE=db_mis;"
    "Trusted_Connection=yes;"
)

# 사용자명/비밀번호 방식
connection_string = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=실제서버주소;"
    "DATABASE=db_mis;"
    "UID=사용자명;"
    "PWD=비밀번호;"
)
```

### 🔍 **일반적인 연결 설정들**

| 설정 | 설명 | 예시 |
|------|------|------|
| SERVER | SQL Server 주소 | `localhost\\SQLEXPRESS`, `192.168.1.100` |
| DATABASE | 데이터베이스명 | `db_mis` |
| 인증방식 | Windows 또는 SQL 인증 | `Trusted_Connection=yes` 또는 `UID/PWD` |

## 📊 추출되는 상품 정보 구조

### **상품 마스터 (tbl_Product)**
```
- 상품번호 (Seq)
- 회사코드/회사명 (Company)
- 브랜드코드/브랜드명 (Brand) 
- 품목코드/품목명 (ProdGroup)
- 타입코드/타입명 (ProdType)
- 제품년도 (ProdYear)
- 상품명 (ProdName)
- 상품가격 (ProdTagAmt)
- 매뉴얼경로 (ProdManual)
- 상품정보 (ProdInfo)
- FAQ연동 (FaqYn)
- 노출여부 (ShowYn)
- 사용여부 (UseYn)
- 등록일/등록자 (InsDate/InsUser)
- 수정일/수정자 (UptDate/UptUser)
```

### **상품 상세 (tbl_Product_DTL)**
```
- 상세번호 (Seq)
- 상품번호 (ProdSeq)
- 상품구분코드 (ProdDivCode)
- 상세명 (ProdDtlName)
- 사용여부 (UseYn)
- 등록정보 (InsDate/InsUser)
```

## 📝 출력 예시

### 성공적인 실행 결과
```
🚀 레거시 상품 정보 추출 시작
📁 출력 파일: legacy_products.xlsx
✅ 레거시 MS-SQL 데이터베이스 연결 성공
🔍 상품 정보 조회 시작...
📊 총 1,234개 상품 정보 조회 완료
📊 총 5,678개 상품 상세 정보 조회 완료
📊 총 89개 코드 정보 조회 완료
💾 엑셀 파일 저장 중: legacy_products.xlsx
✅ 엑셀 파일 저장 완료: legacy_products.xlsx

📊 상품 정보 요약:
   - 총 상품 수: 1,234개
   - 사용 중인 상품: 1,100개
   - 미사용 상품: 134개
   - 회사 수: 2개
   - 브랜드 수: 15개

📋 회사별 상품 수:
   - 에이원: 800개
   - 에이원월드: 434개

✅ 상품 정보 추출이 성공적으로 완료되었습니다.
📂 파일 위치: C:\mis_v2\legacy_products.xlsx
```

## 🔧 문제 해결

### 데이터베이스 연결 오류
```
❌ 레거시 DB 연결 실패: [Microsoft][ODBC Driver 17 for SQL Server]...
```
**해결 방법:**
1. SQL Server가 실행 중인지 확인
2. 연결 정보 (서버 주소, 데이터베이스명) 확인
3. 방화벽 설정 확인
4. SQL Server 인증 모드 확인

### ODBC 드라이버 오류
```
❌ [Microsoft][ODBC Driver Manager] 데이터 원본 이름을 찾을 수 없습니다
```
**해결 방법:**
1. SQL Server ODBC 드라이버 설치 확인
2. 드라이버 버전 확인 (17, 18 등)
3. 연결 문자열의 DRIVER 부분 수정

### 권한 오류
```
❌ 로그인이 데이터베이스 'db_mis'에 액세스할 수 없습니다
```
**해결 방법:**
1. 데이터베이스 접근 권한 확인
2. 사용자 계정의 SQL Server 권한 확인
3. 관리자 권한으로 실행

## 📂 출력 파일 구성

생성되는 엑셀 파일에는 다음 시트들이 포함됩니다:

| 시트명 | 내용 | 설명 |
|--------|------|------|
| **상품목록** | 상품 마스터 정보 | 메인 상품 데이터 |
| **상품상세** | 상품 상세 정보 | 색상, 타입 등 세부 정보 |
| **코드정보** | 관련 코드 테이블 | 회사, 브랜드 등 코드 체계 |
| **통계정보** | 추출 통계 | 요약 정보 및 통계 |

## 💡 활용 방안

### 1. **MIS v2 상품 마이그레이션**
- 추출된 데이터를 기반으로 새 시스템 상품 등록
- 코드 체계 매핑 및 변환

### 2. **데이터 분석**
- 회사별/브랜드별 상품 현황 분석
- 사용/미사용 상품 정리

### 3. **백업 및 아카이빙**
- 레거시 시스템 데이터 백업
- 히스토리 데이터 보관

## ⚠️ 주의사항

1. **대용량 데이터**: 상품 수가 많으면 처리 시간이 오래 걸릴 수 있습니다
2. **네트워크 연결**: 원격 DB 연결 시 네트워크 상태 확인 필요
3. **권한 관리**: 프로덕션 DB 접근 시 읽기 전용 권한 사용 권장
4. **데이터 무결성**: 추출 중 DB 변경 시 일관성 문제 가능

## 📞 지원

문제 발생 시 다음 로그 파일을 확인하세요:
- **로그 파일**: `legacy_product_export.log`
- **위치**: 스크립트 실행 디렉토리 