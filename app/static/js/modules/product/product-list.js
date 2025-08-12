/**
 * 캐시 버스팅: v1754977360
 * 수정 시간: 2025-08-12 14:42:40
 * 브라우저 캐시 무력화를 위한 버전 표시
 */

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
        this.currentSearch = '';  // 🔥 검색어 초기화 추가
        this.currentSort = {
            column: 'created_at',
            direction: 'desc'
        };
        this.retryCount = 0; // 🔥 재시도 횟수 추가
        this.maxRetries = 3;  // 🔥 최대 재시도 횟수
        
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
            '#productCount',
            '#loadingSpinner',
            '#emptyState'
        ];
        
        // 옵션 DOM 요소들 (있으면 좋지만 없어도 됨)
        const optionalElements = [
            '#searchName', 
            '#searchProduct',
            '#searchType'
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
            this.safeAlert('페이지 요소가 완전히 로드되지 않았습니다. 새로고침해주세요.', 'warning');
            // 필수 요소가 없어도 계속 진행 (일부 기능은 동작할 수 있음)
        }
        
        // 이벤트 바인딩 (검색 버튼 방식으로 변경)
        try {
            this.bindEvents();
            console.log('✅ 이벤트 바인딩 완료');
        } catch (error) {
            console.error('❌ 이벤트 바인딩 실패:', error);
        }
        
        // 상품 목록 로드 (지연 실행으로 안전하게)
        setTimeout(() => {
            console.log('🚀 상품 목록 로드 시작 (지연 실행)');
            this.loadProducts().catch(error => {
                console.error('❌ 초기 상품 로드 실패:', error);
                // 빈 상태 표시
                this.showEmptyState('상품 데이터를 불러올 수 없습니다.');
            });
        }, 100);
        
        console.log('✅ ProductListManager 초기화 완료');
    }
    
    /**
     * 이벤트 바인딩 (검색 버튼 방식으로 변경)
     */
    bindEvents() {
        // 검색 폼 제출 이벤트
        $('#searchForm').on('submit', (e) => {
            e.preventDefault();
            console.log('🔍 검색 버튼 클릭');
            this.searchProducts();
        });
        
        // 품목 선택 시 타입 목록 동적 로드
        $('#searchProduct').on('change', () => {
            this.loadProductTypes();
        });
        
        // 정렬 변경
        $('#sortSelect').on('change', () => {
            this.changeSorting();
        });
        
        // 페이지당 표시 개수 변경
        $('[onchange="changePerPage(this.value)"]').on('change', (e) => {
            this.changePerPage($(e.target).val());
        });
        
        console.log('✅ 이벤트 바인딩 완료');
    }
    
    /**
     * 상품 목록 로드
     */
    async loadProducts() {
        try {
            console.log('📦 상품 목록 로드 시작');
            UIHelper.showLoading();
            
            // API 파라미터 준비 - 새로운 검색 필드 지원
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.currentPerPage,
                sort_by: this.currentSort.column,
                sort_direction: this.currentSort.direction,
                _: Date.now()
            });
            
            // 새로운 검색 파라미터들
            const searchName = $('#searchName').val() || '';
            const searchProduct = $('#searchProduct').val() || '';
            const searchType = $('#searchType').val() || '';
            const showInactive = $('#showInactive').is(':checked');
            
            if (searchName) params.append('search_name', searchName);
            if (searchProduct) params.append('search_product', searchProduct);
            if (searchType) params.append('search_type', searchType);
            if (showInactive) params.append('show_inactive', 'true');
            
            const response = await AjaxHelper.get(`/product/api/list?${params}`);
            
            if (response.success) {
                this.allProducts = response.data || [];
                this.filteredProducts = [...this.allProducts];
                this.currentPagination = response.pagination;
                
                // 통계 정보 업데이트
                if (response.stats) {
                    this.updateStats(response.stats);
                }
                
                this.displayProducts();
                this.updatePagination();
                this.retryCount = 0; // 🔥 성공 시 재시도 횟수 리셋
                
                console.log(`✅ 상품 목록 로드 완료: ${this.allProducts.length}개`);
            } else {
                throw new Error(response.message || '상품 목록을 불러오는 중 오류가 발생했습니다.');
            }
            
        } catch (error) {
            console.error('❌ 상품 목록 로드 실패:', error);
            
            // 🔥 재시도 로직
            if (this.retryCount < this.maxRetries) {
                this.retryCount++;
                console.log(`🔄 재시도 중... (${this.retryCount}/${this.maxRetries})`);
                
                // 지연 시간을 점점 늘려가며 재시도
                const delay = this.retryCount * 1000;
                setTimeout(() => {
                    this.loadProducts();
                }, delay);
                return;
            }
            
            // 🔥 최대 재시도 횟수 초과 시
            this.safeAlert('상품 목록을 불러올 수 없습니다. 페이지를 새로고침해주세요.', 'error');
            this.showEmptyState();
        } finally {
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
        console.log('🔍 검색 실행');
        this.currentPage = 1; // 페이지 초기화
        this.loadProducts();
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
     * 필터 초기화 (통합검색만)
     */
    resetFilters() {
        // 통합검색 초기화
        $('#searchInput').val('');
        
        // 필터링 재실행
        this.filteredProducts = [...this.products];
        this.renderProducts();
        
        console.log('🔄 검색 필터 초기화 완료');
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
     * 빈 상태 표시
     */
    showEmptyState(message = '등록된 상품이 없습니다') {
        try {
            console.log('📭 빈 상태 표시:', message);
            
            // 테이블 내용 비우기
            const tableBody = $('#productTableBody');
            if (tableBody.length > 0) {
                tableBody.empty();
            }
            
            // 카드 뷰 비우기
            const cardView = $('#cardView');
            if (cardView.length > 0) {
                cardView.empty();
            }
            
            // 빈 상태 요소 표시
            const emptyState = $('#emptyState');
            if (emptyState.length > 0) {
                emptyState.find('h5').text(message);
                emptyState.show();
            }
            
            // 테이블/카드 뷰 숨기기
            $('#tableView').hide();
            $('#cardView').hide();
            
            // 카운터 초기화
            this.updateCounters();
            
        } catch (error) {
            console.error('❌ 빈 상태 표시 실패:', error);
        }
    }

    /**
     * 통계 정보 업데이트
     */
    updateStats(stats) {
        if ($('#productCount').length) {
            $('#productCount').text(stats.total_products || 0);
        }
        if ($('#stdCodeCount').length) {
            $('#stdCodeCount').text(stats.std_code_products || 0);
        }
    }
    
    /**
     * 상품 목록 표시
     */
    displayProducts() {
        if (this.currentView === 'table') {
            this.renderProducts();
        } else {
            this.renderCardView();
        }
    }
    
    /**
     * 안전한 알림 표시
     */
    safeAlert(message, type = 'info') {
        try {
            if (typeof UIHelper !== 'undefined' && UIHelper.showAlert) {
                UIHelper.showAlert(message, type);
            } else {
                alert(message);
            }
        } catch (error) {
            console.error('Alert 표시 실패:', error);
            alert(message);
        }
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

    /**
     * 품목에 따른 타입 목록 로드
     */
    async loadProductTypes() {
        const productSeq = $('#searchProduct').val();
        const typeSelect = $('#searchType');
        
        // 초기화
        typeSelect.html('<option value="">전체 타입</option>');
        
        if (!productSeq) {
            return;
        }
        
        try {
            const response = await $.ajax({
                url: `/product/api/get-types-by-product-seq/${productSeq}`,
                method: 'GET'
            });
            
            if (response.success && response.data) {
                response.data.forEach(type => {
                    typeSelect.append(`<option value="${type.seq}">${type.code_name}</option>`);
                });
            }
        } catch (error) {
            console.error('타입 목록 로드 실패:', error);
        }
    }
}

// 즉시 실행 함수로 안전한 초기화
(function() {
    'use strict';
    
    // 전역 변수 초기화
    window.productListManager = null;
    
    // 안전한 알림 표시 함수
    function safeAlert(message, type = 'error') {
        try {
            if (typeof UIHelper !== 'undefined' && UIHelper.showAlert) {
                UIHelper.showAlert(message, type);
            } else {
                alert(message);
            }
        } catch (error) {
            console.error('알림 표시 실패:', error);
            alert(message);
        }
    }
    
    // DOM 로드 완료 시 초기화
    function initializeProductListManager() {
        try {
            console.log('🚀 ProductListManager 초기화 시작');
            
            // 필수 라이브러리 확인
            if (typeof $ === 'undefined') {
                console.error('❌ jQuery가 없습니다');
                safeAlert('jQuery 라이브러리가 로드되지 않았습니다. 페이지를 새로고침해주세요.');
                return false;
            }
            
            if (typeof UIHelper === 'undefined') {
                console.error('❌ UIHelper가 없습니다');
                safeAlert('UI 헬퍼가 로드되지 않았습니다. 페이지를 새로고침해주세요.');
                return false;
            }
            
            if (typeof AjaxHelper === 'undefined') {
                console.error('❌ AjaxHelper가 없습니다');
                safeAlert('AJAX 헬퍼가 로드되지 않았습니다. 페이지를 새로고침해주세요.');
                return false;
            }
            
            // ProductListManager 초기화
            window.productListManager = new ProductListManager();
            console.log('✅ ProductListManager 초기화 완료');
            return true;
            
        } catch (error) {
            console.error('❌ ProductListManager 초기화 실패:', error);
            safeAlert('상품 목록 관리자 초기화에 실패했습니다: ' + error.message);
            return false;
        }
    }
    
    // DOM 준비 시 초기화
    $(document).ready(function() {
        setTimeout(initializeProductListManager, 100);
    });
    
})();

// 레거시 호환을 위한 전역 함수들
function loadProducts() { 
    if (window.productListManager) productListManager.loadProducts(); 
}
function searchProducts() { 
    if (window.productListManager) productListManager.searchProducts(); 
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