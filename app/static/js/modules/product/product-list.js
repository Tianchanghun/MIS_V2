/**
 * 상품 목록 관리 모듈
 * 상품 목록 조회, 필터링, 정렬, 페이징 기능 제공
 */

class ProductListManager {
    constructor() {
        this.products = [];
        this.filteredProducts = [];
        this.currentPage = 1;
        this.currentPerPage = 50;
        this.currentView = 'table';
        this.currentSort = {
            column: 'created_at',
            direction: 'desc'
        };
        
        this.init();
    }
    
    /**
     * 초기화
     */
    init() {
        console.log('🔧 ProductListManager.init() 시작');
        
        // 필수 DOM 요소 존재 확인
        const requiredElements = [
            '#productTableBody',
            '#searchInput', 
            '#productCount',
            '#loadingSpinner',
            '#emptyState'
        ];
        
        let missingElements = [];
        requiredElements.forEach(selector => {
            if ($(selector).length === 0) {
                missingElements.push(selector);
            } else {
                console.log(`✅ DOM 요소 존재: ${selector}`);
            }
        });
        
        if (missingElements.length > 0) {
            console.error('❌ 필수 DOM 요소가 없습니다:', missingElements);
            alert('페이지 요소가 완전히 로드되지 않았습니다. 새로고침해주세요.');
            return;
        }
        
        this.bindEvents();
        this.loadProducts();
        console.log('✅ 상품 목록 관리자 초기화 완료');
    }
    
    /**
     * 이벤트 바인딩
     */
    bindEvents() {
        // 실시간 검색 입력 이벤트 (debounce 시간 단축)
        $('#searchInput').on('input keyup', this.debounce(() => {
            console.log('🔍 실시간 검색 시작:', $('#searchInput').val());
            this.searchProducts();
        }, 200)); // 300ms에서 200ms로 단축
        
        // PRD 품목 필터 변경 시 타입 코드 동적 로드
        $('#productCodeFilter').on('change', () => {
            const selectedPrdSeq = $('#productCodeFilter').val();
            console.log('📦 PRD 품목 선택:', selectedPrdSeq);
            this.loadTypeCodesByProduct(selectedPrdSeq);
            this.searchProducts();
        });
        
        // 필터 변경 이벤트 (기존 + PRD/타입 추가)
        $('#brandFilter, #categoryFilter, #statusFilter, #typeFilter, #yearFilter').on('change', () => {
            console.log('🔧 필터 변경됨');
            this.searchProducts();
        });
        
        // 고급 필터 이벤트 (색상 코드 CR 연동)
        $('#colorFilter, #divTypeFilter').on('change', () => {
            console.log('🎨 고급 필터 변경됨');
            this.searchProducts();
        });
        
        // 자사코드 실시간 검색
        $('#stdCodeFilter').on('input keyup', this.debounce(() => {
            console.log('🏷️ 자사코드 검색:', $('#stdCodeFilter').val());
            this.searchProducts();
        }, 200));
        
        // 정렬 변경
        $('#sortSelect').on('change', () => {
            this.changeSorting();
        });
        
        // 페이지당 표시 개수 변경
        $('[onchange="changePerPage(this.value)"]').on('change', (e) => {
            this.changePerPage($(e.target).val());
        });
        
        // Enter 키 즉시 검색
        $('#searchInput').on('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.searchProducts();
            }
        });
    }
    
    /**
     * 상품 데이터 로드
     */
    async loadProducts() {
        try {
            console.log('📥 상품 로드 시작');
            console.log('📍 현재 페이지:', this.currentPage);
            console.log('📍 페이지당 개수:', this.currentPerPage);
            console.log('📍 정렬:', this.currentSort);
            
            UIHelper.showLoading('상품 목록을 불러오는 중...');
            
            const response = await AjaxHelper.get('/product/api/list', {
                page: this.currentPage,
                per_page: this.currentPerPage,
                sort_by: this.currentSort.column,
                sort_direction: this.currentSort.direction
            });
            
            console.log('📊 API 응답 전체:', response);
            console.log('📊 응답 성공 여부:', response.success);
            console.log('📊 응답 데이터:', response.data);
            console.log('📊 데이터 타입:', typeof response.data);
            console.log('📊 데이터 길이:', response.data ? response.data.length : 'null');
            
            if (response.success) {
                this.products = response.data || [];
                this.filteredProducts = [...this.products];
                console.log('📦 상품 데이터 로드됨:', this.products.length + '개');
                console.log('📦 첫 번째 상품:', this.products[0]);
                
                this.renderProducts();
                this.updateCounters();
                this.updatePagination(response.pagination || {});
                console.log('✅ 상품 목록 렌더링 완료');
            } else {
                console.error('❌ API 응답 실패:', response.message);
                UIHelper.showAlert('상품 목록을 불러오는데 실패했습니다: ' + response.message, 'error');
            }
        } catch (error) {
            console.error('❌ 상품 로드 실패:', error);
            console.error('❌ 오류 상세:', error.stack);
            UIHelper.showAlert('상품 목록을 불러오는데 실패했습니다', 'error');
        } finally {
            console.log('🔄 로딩 숨김 처리');
            UIHelper.hideLoading();
        }
    }
    
    /**
     * 상품 렌더링
     */
    renderProducts() {
        try {
            console.log('🎨 상품 렌더링 시작:', this.filteredProducts.length + '개');
            
            if (this.currentView === 'table') {
                this.renderTableView();
        } else {
            this.renderCardView();
            }
            this.updateCounters();
            
            // 렌더링 완료 후 로딩 확실히 숨기기
            setTimeout(() => {
                UIHelper.hideLoading();
            }, 100);
            
            console.log('✅ 상품 렌더링 완료');
        } catch (error) {
            console.error('❌ 상품 렌더링 오류:', error);
            UIHelper.hideLoading();
        }
    }
    
    /**
     * 테이블 뷰 렌더링
     */
    renderTableView() {
        console.log('🎨 테이블 뷰 렌더링 시작');
        const tbody = $('#productTableBody');
        console.log('📍 테이블 body 요소:', tbody.length);
        tbody.empty();
        
        console.log('📊 렌더링할 상품 수:', this.filteredProducts ? this.filteredProducts.length : 'null');
        
        if (!this.filteredProducts || this.filteredProducts.length === 0) {
            console.log('📭 상품이 없어서 빈 상태 표시');
            tbody.html(`
                <tr>
                    <td colspan="11" class="text-center py-4">
                        <i class="fas fa-inbox fa-2x text-muted mb-2"></i>
                        <p class="text-muted mb-0">등록된 상품이 없습니다</p>
                    </td>
                </tr>
            `);
            return;
        }
        
        console.log('📝 상품 행 생성 시작');
        this.filteredProducts.forEach((product, index) => {
            console.log(`📄 ${index + 1}번째 상품 렌더링:`, product.product_name);
            const row = this.createTableRow(product, index);
            tbody.append(row);
        });
        console.log('✅ 테이블 뷰 렌더링 완료');
    }
    
    /**
     * 테이블 행 생성
     */
    createTableRow(product, index) {
        console.log('🔧 테이블 행 생성:', product.product_name);
        
        const globalIndex = ((this.currentPage - 1) * this.currentPerPage) + index + 1;
        
        // 가격 포맷팅 (안전하게)
        let priceDisplay = '미정';
        if (product.price && product.price > 0) {
            priceDisplay = parseInt(product.price).toLocaleString() + '원';
        }
        
        // 날짜 포맷팅 (안전하게)
        let dateDisplay = '-';
        if (product.created_at) {
            try {
                const date = new Date(product.created_at);
                dateDisplay = date.toLocaleDateString('ko-KR');
            } catch (e) {
                dateDisplay = '-';
            }
        }
        
        const rowHtml = `
            <tr onclick="editProduct(${product.id})" style="cursor: pointer;">
                <td class="text-center">${globalIndex}</td>
                <td>
                    <span class="badge company-badge-${product.company_id} text-white">
                        ${product.company_id === 1 ? '에이원' : '에이원월드'}
                    </span>
                </td>
                <td>${product.brand_name || '미지정'}</td>
                <td>
                    <div>
                        <strong>${product.product_name}</strong>
                        ${product.product_code ? `<br><small class="text-muted">${product.product_code}</small>` : ''}
                    </div>
                </td>
                <td>${product.category_name || '미지정'}</td>
                <td>${product.type_name || '-'}</td>
                <td>${product.year_code_name || '-'}</td>
                <td class="price-display">${priceDisplay}</td>
                <td>
                    <span class="badge ${product.is_active ? 'bg-success' : 'bg-secondary'}">
                        ${product.is_active ? '활성' : '비활성'}
                    </span>
                </td>
                <td class="text-center">
                    <small class="text-muted">${dateDisplay}</small>
                </td>
                <td class="text-center">
                    <div class="btn-group btn-group-sm" role="group">
                        <button type="button" class="btn btn-outline-primary btn-sm" 
                                onclick="event.stopPropagation(); editProduct(${product.id})" 
                                title="수정">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button type="button" class="btn btn-outline-danger btn-sm" 
                                onclick="event.stopPropagation(); deleteProduct(${product.id})" 
                                title="삭제">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
        
        console.log('✅ 테이블 행 생성 완료:', globalIndex);
        return rowHtml;
    }
    
    /**
     * 카드 뷰 렌더링
     */
    renderCardView() {
        const cardContainer = $('#cardView');
        cardContainer.empty();
        
        if (!this.filteredProducts || this.filteredProducts.length === 0) {
            cardContainer.html(`
                <div class="col-12 text-center py-5">
                    <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
                    <h5 class="text-muted">등록된 상품이 없습니다</h5>
                    <p class="text-muted">상품을 등록하거나 검색 조건을 변경해 보세요.</p>
                </div>
            `);
            return;
        }

        this.filteredProducts.forEach(product => {
            const card = this.createProductCard(product);
            cardContainer.append(card);
        });
    }
    
    /**
     * 상품 카드 생성
     */
    createProductCard(product) {
        return `
            <div class="col-lg-4 col-md-6 mb-3">
                <div class="card product-card h-100" onclick="editProduct(${product.id})">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span class="badge company-badge-${product.company_id} text-white">
                            ${product.company_id === 1 ? '에이원' : '에이원월드'}
                        </span>
                        <span class="badge ${product.is_active ? 'bg-success' : 'bg-secondary'}">
                            ${product.is_active ? '활성' : '비활성'}
                        </span>
                    </div>
                    <div class="card-body">
                        <h6 class="card-title">${product.product_name}</h6>
                        ${product.product_code ? `<p class="card-text"><small class="text-muted">코드: ${product.product_code}</small></p>` : ''}
                        <p class="card-text">
                            <strong>브랜드:</strong> ${product.brand_name || '미지정'}<br>
                            <strong>품목:</strong> ${product.category_name || '미지정'}<br>
                            <strong>타입:</strong> ${product.type_name || '-'}<br>
                            <strong>년도:</strong> ${product.year_code_name || '-'}<br>
                            <strong>가격:</strong> <span class="price-display">${product.price ? this.formatPrice(product.price) + '원' : '미정'}</span>
                        </p>
                            </div>
                    <div class="card-footer">
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted">${this.formatDate(product.created_at)}</small>
                            <div class="btn-group btn-group-sm" role="group">
                                <button type="button" class="btn btn-outline-primary btn-sm" 
                                        onclick="event.stopPropagation(); editProduct(${product.id})" 
                                        title="수정">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button type="button" class="btn btn-outline-danger btn-sm" 
                                        onclick="event.stopPropagation(); deleteProduct(${product.id})" 
                                        title="삭제">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * 상품 검색 및 필터링
     */
    searchProducts() {
        const filters = this.getFilterValues();
        
        this.filteredProducts = this.products.filter(product => {
            return this.applyFilters(product, filters);
        });
        
        this.currentPage = 1; // 필터링 시 첫 페이지로
        this.renderProducts();
    }
    
    /**
     * 필터 값 가져오기
     */
    getFilterValues() {
        return {
            searchTerm: $('#searchInput').val().toLowerCase(),
            brandFilter: $('#brandFilter').val(),
            categoryFilter: $('#categoryFilter').val(),
            productCodeFilter: $('#productCodeFilter').val(),  // PRD 품목 필터
            typeFilter: $('#typeFilter').val(),
            colorFilter: $('#colorFilter').val(),               // CR 색상 필터
            yearFilter: $('#yearFilter').val(),
            statusFilter: $('#statusFilter').val(),
            stdCodeFilter: $('#stdCodeFilter').val().toLowerCase()  // 자사코드 검색
        };
    }
    
    /**
     * 필터 적용
     */
    applyFilters(product, filters) {
        // 통합 검색어 필터 (상품명, 코드, 브랜드명, 설명 등)
        const searchMatch = !filters.searchTerm || 
            (product.product_name && product.product_name.toLowerCase().includes(filters.searchTerm)) ||
            (product.product_code && product.product_code.toLowerCase().includes(filters.searchTerm)) ||
            (product.brand_name && product.brand_name.toLowerCase().includes(filters.searchTerm)) ||
            (product.category_name && product.category_name.toLowerCase().includes(filters.searchTerm)) ||
            (product.type_name && product.type_name.toLowerCase().includes(filters.searchTerm)) ||
            (product.description && product.description.toLowerCase().includes(filters.searchTerm));
        
        // 브랜드 필터
        const brandMatch = !filters.brandFilter || product.brand_code_seq == filters.brandFilter;
        
        // 품목 (카테고리) 필터
        const categoryMatch = !filters.categoryFilter || product.category_code_seq == filters.categoryFilter;
        
        // PRD 품목 필터 (새로 추가)
        const productCodeMatch = !filters.productCodeFilter || product.category_code_seq == filters.productCodeFilter;
        
        // 타입 필터
        const typeMatch = !filters.typeFilter || product.type_code_seq == filters.typeFilter;
        
        // 색상 필터 (CR)
        const colorMatch = !filters.colorFilter || product.color_code_seq == filters.colorFilter;
        
        // 년도 필터
        const yearMatch = !filters.yearFilter || product.year_code_seq == filters.yearFilter;
        
        // 상태 필터
        const statusMatch = !filters.statusFilter || 
            (filters.statusFilter === 'true' && product.is_active) ||
            (filters.statusFilter === 'false' && !product.is_active);
        
        // 자사코드 필터
        const stdCodeMatch = !filters.stdCodeFilter || 
            (product.std_div_prod_code && product.std_div_prod_code.toLowerCase().includes(filters.stdCodeFilter));
        
        return searchMatch && brandMatch && (categoryMatch || productCodeMatch) && 
               typeMatch && colorMatch && yearMatch && statusMatch && stdCodeMatch;
    }
    
    /**
     * 뷰 전환
     */
    switchView(viewType) {
        this.currentView = viewType;
        
        if (viewType === 'table') {
            $('#tableView').show();
            $('#cardView').hide();
            $('#tableViewBtn').addClass('active');
            $('#cardViewBtn').removeClass('active');
        } else {
            $('#tableView').hide();
            $('#cardView').show();
            $('#tableViewBtn').removeClass('active');
            $('#cardViewBtn').addClass('active');
        }
        
        this.renderProducts();
    }
    
    /**
     * 정렬 변경
     */
    changeSorting() {
        const sortValue = $('#sortSelect').val();
        const [column, direction] = sortValue.split('-');
        
        this.currentSort.column = column;
        this.currentSort.direction = direction;
        
        this.loadProducts();
    }
    
    /**
     * 페이지당 표시 개수 변경
     */
    changePerPage(perPage) {
        this.currentPerPage = parseInt(perPage);
        this.currentPage = 1;
        this.loadProducts();
    }
    
    /**
     * 필터 초기화
     */
    resetFilters() {
        // 모든 필터 초기화
        $('#searchInput, #brandFilter, #categoryFilter, #statusFilter, #typeFilter, #yearFilter, #colorFilter, #divTypeFilter, #productCodeFilter, #stdCodeFilter').val('');
        
        // 고급 필터 접기
        $('#advancedFilters').collapse('hide');
        
        // 필터링 재실행
        this.filteredProducts = [...this.products];
        this.renderProducts();
    }
    
    /**
     * 카운터 업데이트
     */
    updateCounters() {
        $('#productCount').text(this.filteredProducts.length);
        
        const start = (this.currentPage - 1) * this.currentPerPage + 1;
        const end = Math.min(this.currentPage * this.currentPerPage, this.filteredProducts.length);
        const total = this.filteredProducts.length;
        
        $('#recordInfo').text(`${start}-${end} / ${total}개 표시`);
    }
    
    /**
     * 페이지네이션 업데이트
     */
    updatePagination(paginationData) {
        const container = $('#pagination');
        if (!paginationData) return;
        
        container.empty();
        
        // 이전 버튼
        if (paginationData.has_prev) {
            container.append(`
                <li class="page-item">
                    <a class="page-link" href="#" onclick="goToPage(${paginationData.page - 1}); return false;">이전</a>
                </li>
            `);
        }
        
        // 페이지 번호들
        const startPage = Math.max(1, paginationData.page - 2);
        const endPage = Math.min(paginationData.pages, paginationData.page + 2);
        
        if (startPage > 1) {
            container.append(`<li class="page-item"><a class="page-link" href="#" onclick="goToPage(1); return false;">1</a></li>`);
            if (startPage > 2) {
                container.append(`<li class="page-item disabled"><span class="page-link">...</span></li>`);
            }
        }
        
        for (let i = startPage; i <= endPage; i++) {
            const isActive = i === paginationData.page ? 'active' : '';
            container.append(`
                <li class="page-item ${isActive}">
                    <a class="page-link" href="#" onclick="goToPage(${i}); return false;">${i}</a>
                </li>
            `);
        }
        
        if (endPage < paginationData.pages) {
            if (endPage < paginationData.pages - 1) {
                container.append(`<li class="page-item disabled"><span class="page-link">...</span></li>`);
            }
            container.append(`<li class="page-item"><a class="page-link" href="#" onclick="goToPage(${paginationData.pages}); return false;">${paginationData.pages}</a></li>`);
        }
        
        // 다음 버튼
        if (paginationData.has_next) {
            container.append(`
                <li class="page-item">
                    <a class="page-link" href="#" onclick="goToPage(${paginationData.page + 1}); return false;">다음</a>
                </li>
            `);
        }
        
        // 페이지 정보 업데이트
        const start = ((paginationData.page - 1) * paginationData.per_page) + 1;
        const end = Math.min(paginationData.page * paginationData.per_page, paginationData.total);
        $('#recordInfo').text(`${start}-${end} / ${paginationData.total}개 표시`);
        
        console.log('📖 페이지네이션 업데이트:', paginationData);
    }
    
    /**
     * 페이지 이동
     */
    goToPage(page) {
        this.currentPage = page;
        this.loadProducts();
    }
    
    /**
     * 가격 포맷팅
     */
    formatPrice(price) {
        if (!price && price !== 0) return '-';
        return parseInt(price).toLocaleString();
    }
    
    /**
     * 날짜 포맷팅
     */
    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString('ko-KR');
    }
    
    /**
     * 디바운스 함수
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func.apply(this, args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * PRD 품목 선택에 따른 타입 코드 동적 로드
     */
    async loadTypeCodesByProduct(productSeq) {
        try {
            if (!productSeq) {
                // 품목이 선택되지 않으면 타입 코드 초기화
                $('#typeFilter').html('<option value="">전체</option>');
                return;
            }
            
            console.log('🔗 타입 코드 로드 시작:', productSeq);
            
            const response = await AjaxHelper.get('/admin/api/codes/children', {
                parent_seq: productSeq
            });
            
            if (response.success) {
                const typeFilterSelect = $('#typeFilter');
                typeFilterSelect.html('<option value="">전체</option>');
                
                response.data.forEach(typeCode => {
                    typeFilterSelect.append(
                        `<option value="${typeCode.seq}">${typeCode.code_name} (${typeCode.code})</option>`
                    );
                });
                
                console.log('✅ 타입 코드 로드 완료:', response.data.length + '개');
            } else {
                console.warn('⚠️ 타입 코드 로드 실패:', response.message);
            }
        } catch (error) {
            console.error('❌ 타입 코드 로드 에러:', error);
        }
    }
}

// 레거시 호환을 위한 전역 함수들
function loadProducts() { 
    if (window.productListManager) productListManager.loadProducts(); 
}
function searchProducts() { 
    if (window.productListManager) productListManager.searchProducts(); 
}
function switchView(viewType) { 
    if (window.productListManager) productListManager.switchView(viewType); 
}
function changeSorting() { 
    if (window.productListManager) productListManager.changeSorting(); 
}
function changePerPage(perPage) { 
    if (window.productListManager) productListManager.changePerPage(perPage); 
}
function resetFilters() { 
    if (window.productListManager) productListManager.resetFilters(); 
}
function goToPage(page) { 
    if (window.productListManager) productListManager.goToPage(page); 
} 