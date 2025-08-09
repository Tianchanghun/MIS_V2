# 제품 관리 시스템 다음 단계 작업 계획

## 🚨 긴급 해결 필요 (Priority 1)

### 1. 년도 매핑 문제 해결
**문제**: ProdYear 값이 올바르게 매핑되지 않아 년도 필드가 NULL로 표시

**분석 결과**:
```
ProdYear '12' → Code='12', Seq=221, Name='2012'
ProdYear '13' → Code='13', Seq=222, Name='2013'  
ProdYear '14' → Code='14', Seq=223, Name='2014'
ProdYear '18' → Code='18', Seq=???, Name='2018'
```

**해결 방안**:
1. **개별 년도 코드 매핑**: ProdYear 값을 Code 필드로 매핑하여 해당 Seq 찾기
2. **매핑 스크립트 수정**: `fix_yr_mapping_final.py` 로직 변경
3. **검증**: 699개 제품의 년도 매핑 완료 확인

**예상 작업 시간**: 2-3시간

### 2. 모달 동작 문제 해결
**문제**: `http://127.0.0.1:5000/product/` 모달이 정상 작동하지 않음

**구체적 문제점**:
- 계층형 선택박스 (품목 선택 → 해당 타입만 표시) 미작동
- 편집 모드에서 기존 값이 pre-select되지 않음
- 16자리 자가코드 생성 로직 불완전

**해결 방안**:
1. **JavaScript 디버깅**: 브라우저 콘솔 에러 확인
2. **API 응답 확인**: `/product/api/get-types-by-category/<seq>` 정상 동작 검증
3. **모달 초기화 로직**: 편집 모드 시 기존 데이터 로딩 확인

**예상 작업 시간**: 3-4시간

## 📋 중요 작업 (Priority 2)

### 3. 자가코드 생성 로직 완성
**현재 상태**: 기본 구조는 있으나 세부 검증 필요

**16자리 구조**:
```
[브랜드 2자리][구분 1자리][품목그룹 2자리][제품타입 2자리][제품코드 2자리][타입2 2자리][년도 2자리][색상 3자리]
```

**필요 작업**:
1. **코드 생성 규칙 검증**: 레거시 시스템과 동일한 로직 확인
2. **중복 코드 방지**: 기존 자가코드와 충돌 방지
3. **자동 증가 로직**: 같은 조합에서 순번 증가

### 4. 추가 레거시 테이블 마이그레이션
**대상 테이블**:
- `tbl_Product_CodeMatch`: Douzone 코드, ERPia 코드
- `tbl_Product_CBM`: CBM 정보

**연결 방식**: ProdCode (또는 StdDivProdCode) 기준

**예상 작업 시간**: 4-5시간

## 🔧 개선 작업 (Priority 3)

### 5. UI/UX 개선
**개선 항목**:
- 검색 기능 고도화 (자가코드, 제품명, 브랜드별)
- 정렬 기능 완성 (년도, 브랜드, 제품명 등)
- 페이징 개선 (대용량 데이터 처리)
- 반응형 디자인 적용

### 6. 데이터 검증 및 정리
**검증 항목**:
- 45개 매핑 실패 제품 상세 분석
- 중복 데이터 확인 및 정리
- 누락된 필드 데이터 보완

### 7. 성능 최적화
**개선 영역**:
- 대용량 제품 목록 로딩 성능
- 코드 검색 API 성능
- 데이터베이스 인덱스 최적화

## 📝 상세 작업 스펙

### 년도 매핑 수정 스크립트 (fix_year_mapping_correct.py)
```python
# 수정해야 할 로직
# 기존: Code='YR' 그룹에서 CodeSeq로 매핑 시도
# 수정: ProdYear 값을 직접 Code 필드로 사용하여 Seq 찾기

def fix_year_mapping_correct():
    # 1. ProdYear별 Code 매핑 테이블 생성
    prod_year_mapping = {}
    for prod_year in ['09', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25']:
        # SELECT Seq FROM tbl_code WHERE Code = prod_year
        
    # 2. Product.year_code_seq 업데이트
    # UPDATE products SET year_code_seq = mapped_seq WHERE legacy_seq IN (...)
```

### 모달 JavaScript 수정
```javascript
// 계층형 선택박스 개선
function updateTypesForCategory(categorySeq) {
    // API 호출: /product/api/get-types-by-category/${categorySeq}
    // 타입 선택박스 업데이트
    // 기존 선택값 유지 (편집 모드)
}

// 편집 모드 초기화
function initializeEditMode(productData) {
    // 모든 선택박스에 기존 값 설정
    // 계층형 관계 고려하여 순차적으로 초기화
}
```

## 🧪 테스트 계획

### 1. 년도 매핑 테스트
- [ ] 전체 699개 제품의 년도 매핑 완료 확인
- [ ] 샘플 제품들의 년도 표시 정상 확인
- [ ] API 응답에서 year_code_name 정상 출력 확인

### 2. 모달 기능 테스트  
- [ ] 신규 등록: 품목 선택 → 타입 필터링 동작
- [ ] 편집 모드: 기존 값들이 정확히 pre-select됨
- [ ] 자가코드 생성: 16자리 코드 정상 생성
- [ ] 저장 기능: 입력 데이터 정상 저장

### 3. 전체 시스템 테스트
- [ ] 제품 목록 표시: 모든 필드 정상 표시
- [ ] 검색 기능: 다양한 조건으로 검색 가능
- [ ] 정렬 기능: 각 컬럼별 정렬 동작
- [ ] 페이징: 대용량 데이터에서 성능 확인

## 📚 참고 문서

### 레거시 시스템 분석 결과
- **ProdYear 구조**: 2자리 년도 (09, 10, 11, ..., 25)
- **Code 매핑**: ProdYear '18' → Code='18', Name='2018'
- **자가코드 예시**: `JI1CS01ST182BK` (16자리)

### API 엔드포인트 명세
```
GET  /product/api/codes/years          # 년도 코드 목록
GET  /product/api/get-types-by-category/<seq>  # 품목별 타입 목록  
POST /product/api/create               # 제품 등록
PUT  /product/api/update/<id>          # 제품 수정
```

## ⚠️ 주의사항

1. **데이터 백업**: 수정 전 반드시 현재 상태 백업
2. **레거시 연결**: 작업 중 레거시 DB 연결 끊어지지 않도록 주의
3. **점진적 적용**: 한 번에 모든 변경사항 적용하지 말고 단계별 검증
4. **사용자 테스트**: 기능 완성 후 실제 사용 시나리오로 테스트

---
**작성일**: 2024년 12월 19일  
**예상 완료**: 2024년 12월 20일 (년도 매핑 + 모달 기능) 