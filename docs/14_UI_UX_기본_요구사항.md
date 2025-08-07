# UI/UX 기본 요구사항

## 개요
모든 페이지에 공통으로 적용되어야 하는 UI/UX 기본 요구사항을 정의합니다.

## 1. 테이블 정렬 기능
### 요구사항
- **모든 리스트 형태의 테이블 제목 행(헤더)에는 정렬 기능을 포함해야 합니다**
- 클릭 시 오름차순/내림차순 정렬이 가능해야 합니다
- 시각적으로 정렬 가능함을 나타내는 아이콘을 표시해야 합니다

### 구현 방법
```html
<th onclick="sortTable(0)">컬럼명 <i class="bi bi-arrow-down-up"></i></th>
```

```css
th {
    cursor: pointer;
    user-select: none;
}
th:hover {
    background-color: #e9ecef;
}
```

```javascript
function sortTable(columnIndex) {
    // 정렬 로직 구현
    // currentSort 상태 관리
    // 데이터 재렌더링
}
```

## 2. 실시간 검색 기능
### 요구사항
- **모든 페이지에는 검색 기능을 포함해야 합니다**
- 검색어 입력 시 실시간으로 필터링되어야 합니다 (keyup 이벤트)
- 글자만 입력해도 즉시 검색되어야 합니다 (별도 검색 버튼 불필요)
- 레거시 시스템 참조: https://mis.aone.co.kr/Member/UserAuthManager/

### 구현 방법
```html
<div class="input-group">
    <span class="input-group-text"><i class="bi bi-search"></i></span>
    <input type="text" class="form-control" id="searchInput" 
           placeholder="검색어를 입력하세요..." onkeyup="searchFunction()">
</div>
```

```javascript
function searchFunction() {
    const search = $('#searchInput').val().toLowerCase();
    const filtered = originalData.filter(item => 
        Object.values(item).some(value => 
            value.toString().toLowerCase().includes(search)
        )
    );
    renderTable(filtered);
}
```

## 3. 공통 UI 패턴
### 검색 영역
- 카드 형태로 구성
- 검색 입력창 + 초기화 버튼
- 아이콘 사용 (Bootstrap Icons)

### 테이블 영역
- 반응형 테이블 (`table-responsive`)
- 호버 효과 (`table-hover`)
- 스트라이프 패턴 (`table-striped`)
- 헤더 강조 (`table-light`)

### 모달 창
- 추가/수정 모달 분리 또는 통합
- 필수 입력 필드 표시 (`<span class="text-danger">*</span>`)
- 유효성 검사 및 오류 표시

## 4. 구현 우선순위
1. **필수 구현**: 모든 새로 개발되는 페이지
2. **점진적 적용**: 기존 페이지들에 순차적 적용
3. **일관성 유지**: 모든 페이지에서 동일한 패턴 사용

## 5. 참조 페이지
### 완료된 구현 예시
- `/admin/user_management` - 사용자 관리 (정렬 + 검색 완료)
- `/admin/department_management` - 부서 관리 (정렬 + 검색 완료)

### 적용 대상 페이지
- `/admin/code_management` - 코드 관리
- `/admin/menu_management` - 메뉴 관리
- `/admin/brand_management` - 브랜드 관리
- `/admin/permissions` - 권한 관리
- `/batch/` - 배치 관리
- `/gift/` - 사은품 관리
- `/customer/` - 고객 관리

## 6. 개발 가이드라인
### JavaScript 함수 네이밍
- 검색: `search{ModuleName}()` (예: `searchUsers()`, `searchDepartments()`)
- 정렬: `sortTable(columnIndex)`
- 초기화: `resetSearch()`

### CSS 클래스 네이밍
- 검색 입력: `#searchInput`
- 테이블: `#{moduleName}Table`
- 카운트 표시: `#{moduleName}Count`

### HTML 구조
```html
<!-- 검색 영역 -->
<div class="card mb-4">
    <div class="card-body">
        <!-- 검색 입력 -->
    </div>
</div>

<!-- 테이블 영역 -->
<div class="card">
    <div class="card-header">
        <h5>목록 <span id="count" class="badge bg-secondary">0</span></h5>
    </div>
    <div class="card-body">
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead class="table-light">
                    <!-- 정렬 가능한 헤더 -->
                </thead>
                <tbody>
                    <!-- 동적 데이터 -->
                </tbody>
            </table>
        </div>
    </div>
</div>
```

## 7. 품질 관리
- 모든 새 기능 개발 시 위 요구사항 준수 필수
- 코드 리뷰 시 UI/UX 기본 요구사항 체크
- 사용자 테스트 시 검색/정렬 기능 동작 확인 