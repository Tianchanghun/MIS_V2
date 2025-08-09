# 제품 관리 시스템 마이그레이션 진행 상황

## 📋 프로젝트 개요
- **목적**: 레거시 ASP.NET MVC 시스템에서 Flask 기반 제품 관리 시스템으로 마이그레이션
- **대상**: 제품 마스터, 제품 상세, 코드 체계, 자가코드 시스템
- **요구사항**: 100% 데이터 완전성, 16자리 자가코드 생성, 레거시 호환성

## 🎯 주요 성과

### ✅ 완료된 작업

#### 1. 레거시 코드 시스템 완전 마이그레이션
- **레거시 tbl_code 완전 복사**: 2,128개 코드 마이그레이션 완료
- **모든 필드 보존**: Seq, CodeSeq, ParentSeq, Depth, Sort, Code, CodeName, CodeInfo, InsUser, InsDate, UptUser, UptDate
- **1:1 매핑**: 레거시 Seq와 현재 시스템 seq 완전 일치

#### 2. 제품 마스터 데이터 마이그레이션
- **699개 제품 마스터** 마이그레이션 완료
- **legacy_seq 연결**: 레거시 DB와의 추적 가능한 연결
- **기본 정보**: 제품명, 가격(ProdTagAmt), 사용여부(UseYn), 생성정보

#### 3. 제품 상세 데이터 마이그레이션
- **1,183개 제품 상세** 마이그레이션 완료 (45개 매핑 실패)
- **16자리 자가코드**: StdDivProdCode 필드 보존
- **코드 구성 요소**: BrandCode, DivTypeCode, ProdGroupCode, ProdTypeCode, ProdCode, ProdType2Code, YearCode, ProdColorCode

#### 4. UI/UX 개선
- **모달 구조 개선**: 레거시와 동일한 2단계 구조 (기본 정보 → 제품 모델 등록)
- **직접 편집 기능**: 리스트에서 바로 편집 모달로 이동
- **검색/정렬/페이징**: 기본 기능 구현

### ⚠️ 진행 중/미완료 작업

#### 1. 년도 매핑 문제 (중요)
- **현재 상태**: 년도 필드가 NULL로 표시됨
- **원인 분석**: 
  - 레거시 ProdYear 값 ('18', '14', '16' 등)이 tbl_code의 개별 년도 코드와 매핑 필요
  - YR 코드 그룹에 1개 항목만 존재 (부모 그룹)
  - ProdYear 값들이 Code='12', '13', '14' 등의 개별 코드 그룹으로 저장됨
- **발견 사항**: 
  ```
  ProdYear '12' 발견: Seq 221, Code '12', CodeSeq 7, Name '2012'
  ProdYear '13' 발견: Seq 222, Code '13', CodeSeq 7, Name '2013'
  ProdYear '14' 발견: Seq 223, Code '14', CodeSeq 7, Name '2014'
  ```

#### 2. 모달 동작 문제
- **현재 상태**: `http://127.0.0.1:5000/product/` 모달이 정상 작동하지 않음
- **필요 작업**: 
  - 계층형 선택박스 (품목 → 타입) 구현
  - 편집 시 기존 값 pre-select
  - 16자리 자가코드 생성 로직 완성

#### 3. 추가 레거시 테이블 마이그레이션 (보류)
- **tbl_Product_CodeMatch**: Douzone 코드, ERPia 코드 (ProdCode 기준)
- **tbl_Product_CBM**: CBM 정보 (ProdCode 기준)

## 📊 마이그레이션 통계

### 데이터 현황
| 항목 | 레거시 DB | 현재 시스템 | 성공률 |
|------|-----------|-------------|--------|
| 코드 | 2,128개 | 2,128개 | 100% |
| 제품 마스터 | 699개 | 699개 | 100% |
| 제품 상세 | 1,228개 | 1,183개 | 96.3% |

### 코드 매핑 현황
| 코드 유형 | 매핑 성공률 | 비고 |
|-----------|-------------|------|
| 브랜드 (Brand) | 100% | 조이, 뉴나 등 |
| 품목 (ProdGroup) | 100% | 카시트, 유모차 등 |
| 타입 (ProdType) | 100% | 컨버터블 카시트 등 |
| 년도 (Year) | 0% | **해결 필요** |
| 색상 (Color) | - | 미확인 |

## 🔧 기술적 구현 내용

### 1. 데이터베이스 스키마
```sql
-- 제품 마스터
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    legacy_seq INTEGER UNIQUE,  -- 레거시 추적용
    company_id INTEGER,
    product_name VARCHAR(255),
    price DECIMAL(15,2),
    use_yn VARCHAR(1) DEFAULT 'Y',
    brand_code_seq INTEGER REFERENCES codes(seq),
    category_code_seq INTEGER REFERENCES codes(seq),
    type_code_seq INTEGER REFERENCES codes(seq),
    year_code_seq INTEGER REFERENCES codes(seq),
    -- ... 기타 필드
);

-- 제품 상세
CREATE TABLE product_details (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    legacy_seq INTEGER UNIQUE,  -- 레거시 DTL Seq
    std_div_prod_code VARCHAR(16),  -- 16자리 자가코드
    brand_code VARCHAR(10),
    div_type_code VARCHAR(10),
    prod_group_code VARCHAR(10),
    prod_type_code VARCHAR(10),
    prod_code VARCHAR(10),
    prod_type2_code VARCHAR(10),
    year_code VARCHAR(10),
    color_code VARCHAR(10),
    -- ... 기타 필드
);
```

### 2. 마이그레이션 스크립트
- **complete_legacy_code_migration.py**: 전체 코드 시스템 마이그레이션
- **simple_product_migration.py**: 제품 데이터 간단 마이그레이션
- **fix_yr_mapping_final.py**: 년도 매핑 수정 (진행 중)

### 3. API 엔드포인트
```python
# 제품 관리 API
GET  /product/api/list              # 제품 목록
GET  /product/api/get/<id>          # 제품 상세
POST /product/api/create            # 제품 생성
PUT  /product/api/update/<id>       # 제품 수정
GET  /product/api/codes/<type>      # 코드 목록
GET  /product/api/get-types-by-category/<seq>  # 계층형 코드
```

## 🚨 현재 해결 필요한 문제들

### 1. 년도 매핑 문제 (최우선)
```
문제: ProdYear '18' → 올바른 tbl_code.Seq 매핑 실패
해결 방향: Code='18', CodeName='2018' 형태의 개별 년도 코드 활용
```

### 2. 모달 동작 문제
```
문제: 계층형 선택박스, 편집 모드 pre-select 미구현
필요: JavaScript 로직 완성, API 연동 개선
```

### 3. 자가코드 생성 로직
```
구조: [브랜드2자리][구분1자리][품목그룹2자리][제품타입2자리][제품코드2자리][타입2-2자리][년도2자리][색상3자리] = 16자리
상태: 기본 구조 완성, 세부 로직 검증 필요
```

## 📋 다음 단계 작업 계획

### Phase 1: 년도 매핑 완성
1. **ProdYear 매핑 로직 수정**
   - Code='12','13','14' 등 개별 년도 코드 활용
   - Product.year_code_seq 필드 올바른 매핑
   - 매핑 검증 및 테스트

### Phase 2: 모달 기능 완성
1. **계층형 선택박스 구현**
   - 품목 선택 시 해당 타입만 표시
   - API 엔드포인트 개선
   - JavaScript 로직 완성

2. **편집 모드 개선**
   - 기존 값 pre-select
   - 16자리 자가코드 자동 생성
   - 유효성 검사 추가

### Phase 3: 추가 테이블 마이그레이션
1. **tbl_Product_CodeMatch 마이그레이션**
2. **tbl_Product_CBM 마이그레이션**
3. **전체 데이터 검증**

## 📁 관련 파일 목록

### 마이그레이션 스크립트
- `complete_legacy_code_migration.py` - 코드 시스템 완전 마이그레이션
- `simple_product_migration.py` - 제품 데이터 마이그레이션
- `fix_yr_mapping_final.py` - 년도 매핑 수정 (진행 중)
- `analyze_prodyear_structure.py` - 년도 구조 분석

### 애플리케이션 파일
- `app/product/routes.py` - 제품 관리 API
- `app/templates/product/index.html` - 제품 관리 UI
- `app/common/models.py` - 데이터베이스 모델

### 설정 파일
- `.env` - 레거시 DB 연결 정보
- `docker-compose.yml` - 개발 환경 설정

## 🔗 레거시 DB 연결 정보
```
LEGACY_DB_SERVER=210.109.96.74,2521
LEGACY_DB_NAME=db_mis
LEGACY_DB_USER=user_mis
LEGACY_DB_PASSWORD=user_mis!@12
```

## 📝 중요 참고사항

1. **레거시 Seq 보존**: 모든 마이그레이션에서 legacy_seq 필드로 원본 연결 유지
2. **16자리 자가코드**: 제품별 고유 식별자, 시리얼 번호 생성에 활용
3. **코드 체계**: 레거시 tbl_code의 계층 구조 완전 보존
4. **데이터 무결성**: 마이그레이션 시 원본 데이터 손상 없이 진행

---
**작성일**: 2024년 12월 19일  
**최종 업데이트**: 년도 매핑 문제 분석 완료, 모달 동작 문제 확인 