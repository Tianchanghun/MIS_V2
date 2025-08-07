# 거래처 관리 - 분류정보 드롭다운 확장 요구사항

## 📋 **기존 분류정보 (레거시 시스템)**

### 1. CST (Customer) 코드 그룹 구조
```
CST (거래처 분류)
├── DIS (유통)
│   ├── 직영
│   ├── 대리점 
│   ├── 온라인
│   └── 기타
├── CH (채널)
│   ├── 온라인
│   ├── 오프라인
│   └── 혼합
├── SL (매출)
│   ├── 소매
│   ├── 도매
│   └── 직판
└── TY (형태)
    ├── 매장
    ├── 창고
    └── 사무소
```

## 🆕 **추가 분류정보 (이미지 기반)**

### 2. 브랜드존
- **코드**: `BZ` (Brand Zone)
- **옵션**:
  - 뉴나
  - 리안/조이
  - 조이/뉴나
  - 리안/조이/뉴나
  - 리안/뉴나
  - 뉴나/조이
  - 공통구매

### 3. 뉴나 브랜드 조닝
- **코드**: `NZ` (Nuna Zoning)
- **옵션**:
  - 벽면
  - 아일랜드

### 4. 지역
- **코드**: `RG` (Region)
- **옵션**:
  - 서울특별시
  - 대구광역시
  - 충청남도
  - 경기도
  - 대전광역시
  - 경상북도
  - 부산광역시
  - 제주도
  - 강원도
  - 인천광역시
  - 충청북도
  - 전라북도
  - 울산광역시
  - 경상남도
  - 광주광역시
  - 세종특별자치시
  - 공통
  - 이서현/박소연
  - 전라남도
  - 바터
  - 제주특별자치도

### 5. 가결산 구분값
- **코드**: `FG` (Financial Group)
- **옵션**:
  - 오프라인_전문매장
  - 온라인_기타매장  
  - 오프라인_특판
  - 오프라인_제휴
  - 오프라인_할인
  - 온라인_승합
  - 기타_기타매장
  - 전시회_자사매장
  - 온라인 자사매장
  - 전시회_대행업체
  - 시스템코드
  - 온라인_본조직
  - 그룹사_그룹사
  - 온라인_스마트
  - -
  - 박기영
  - 바터신행건
  - 특판

## 🔧 **구현 계획**

### 1단계: 코드 시스템 확장
```python
# 새로운 코드 그룹 추가
code_groups = [
    {'code': 'BZ', 'name': '브랜드존', 'sort': 1},
    {'code': 'NZ', 'name': '뉴나 브랜드 조닝', 'sort': 2}, 
    {'code': 'RG', 'name': '지역', 'sort': 3},
    {'code': 'FG', 'name': '가결산 구분값', 'sort': 4}
]
```

### 2단계: ErpiaCustomer 모델 확장
```python
class ErpiaCustomer(db.Model):
    # 기존 필드들...
    
    # 추가 분류 필드
    brand_zone = db.Column(db.String(50))        # 브랜드존
    nuna_zoning = db.Column(db.String(50))       # 뉴나 브랜드 조닝  
    region = db.Column(db.String(50))            # 지역
    financial_group = db.Column(db.String(50))   # 가결산 구분값
```

### 3단계: 모달 UI 확장
```html
<!-- 분류정보 탭 -->
<div class="tab-pane fade" id="nav-category">
    <div class="row">
        <!-- 기존 분류 -->
        <div class="col-md-6">
            <label for="distribution_type">유통</label>
            <select id="distribution_type" class="form-control">
                <!-- CST > DIS 하위 코드들 -->
            </select>
        </div>
        
        <!-- 새로운 분류들 -->
        <div class="col-md-6">
            <label for="brand_zone">브랜드존</label>
            <select id="brand_zone" class="form-control">
                <!-- BZ 하위 코드들 -->
            </select>
        </div>
        
        <div class="col-md-6">
            <label for="nuna_zoning">뉴나 브랜드 조닝</label>
            <select id="nuna_zoning" class="form-control">
                <!-- NZ 하위 코드들 -->
            </select>
        </div>
        
        <div class="col-md-6">
            <label for="region">지역</label>
            <select id="region" class="form-control">
                <!-- RG 하위 코드들 -->
            </select>
        </div>
        
        <div class="col-md-6">
            <label for="financial_group">가결산 구분값</label>
            <select id="financial_group" class="form-control">
                <!-- FG 하위 코드들 -->
            </select>
        </div>
    </div>
</div>
```

### 4단계: API 확장
```python
@admin_bp.route('/api/shop/classifications')
def get_shop_classifications():
    """거래처 분류정보 조회 API"""
    try:
        classifications = {}
        
        # 기존 분류 (CST 그룹)
        cst_group = Code.query.filter_by(code='CST', depth=0).first()
        if cst_group:
            # 유통, 채널, 매출, 형태
            for sub_code in ['DIS', 'CH', 'SL', 'TY']:
                sub_group = Code.query.filter_by(
                    code_seq=cst_group.seq, 
                    code=sub_code, 
                    depth=1
                ).first()
                if sub_group:
                    classifications[sub_code.lower()] = Code.get_codes_by_parent_seq(sub_group.seq)
        
        # 새로운 분류들
        for code in ['BZ', 'NZ', 'RG', 'FG']:
            group = Code.query.filter_by(code=code, depth=0).first()
            if group:
                classifications[code.lower()] = Code.get_codes_by_parent_seq(group.seq)
        
        return jsonify({
            'success': True,
            'data': classifications
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })
```

## 📝 **데이터베이스 스크립트**

### 코드 테이블 데이터 삽입
```sql
-- 브랜드존 그룹 추가
INSERT INTO tbl_code (code_seq, parent_seq, depth, sort, code, code_name) VALUES 
(NULL, NULL, 0, 5, 'BZ', '브랜드존');

-- 뉴나 브랜드 조닝 그룹 추가  
INSERT INTO tbl_code (code_seq, parent_seq, depth, sort, code, code_name) VALUES
(NULL, NULL, 0, 6, 'NZ', '뉴나 브랜드 조닝');

-- 지역 그룹 추가
INSERT INTO tbl_code (code_seq, parent_seq, depth, sort, code, code_name) VALUES
(NULL, NULL, 0, 7, 'RG', '지역');

-- 가결산 구분값 그룹 추가
INSERT INTO tbl_code (code_seq, parent_seq, depth, sort, code, code_name) VALUES
(NULL, NULL, 0, 8, 'FG', '가결산 구분값');
```

## ✅ **완성 후 기대효과**

1. **완벽한 거래처 분류**: 8개 분류 체계로 세밀한 거래처 관리
2. **레거시 호환성**: 기존 CST 체계 + 새로운 분류 추가
3. **사용자 편의성**: 드롭다운으로 직관적인 선택
4. **데이터 일관성**: 코드 관리 시스템 활용으로 표준화
5. **확장 가능성**: 추후 분류 추가/수정 용이

---
**작성일**: 2025-01-07  
**작성자**: MIS v2 개발팀  
**상태**: 요구사항 정리 완료 