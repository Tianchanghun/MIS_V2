/**
 * 상품 목록 관리 모듈
 * DataTables와 표준 라이브러리를 활용한 상품 목록 처리
 */
const ProductList = {
    // 전역 변수
    dataTable: null,
    currentFilters: {},

    // 초기화
    init: function() {
        console.log('🚀 상품 목록 모듈 초기화');
        this.initDataTable();
        this.setupEventHandlers();
        this.setupFilters();
    },

    // DataTables 초기화
    initDataTable: function() {
        if ($.fn.DataTable.isDataTable('#productTable')) {
            $('#productTable').DataTable().destroy();
        }

        this.dataTable = DataTableConfig.productTable('#productTable', {
            serverSide: true,
            ajax: {
                url: '/product/api/list',
                type: 'GET',
                data: function(d) {
                    // 기본 DataTables 파라미터를 Flask 형식으로 변환
                    return {
                        page: Math.floor(d.start / d.length) + 1,
                        per_page: d.length,
                        sort_by: d.columns[d.order[0].column].data,
                        sort_direction: d.order[0].dir,
                        search_term: d.search.value,
                        // 추가 필터
                        company_filter: $('#companyFilter').val() || '',
                        brand_filter: $('#brandFilter').val() || '',
                        category_filter: $('#categoryFilter').val() || '',
                        status_filter: $('#statusFilter').val() || '',
                        type_filter: $('#typeFilter').val() || '',
                        year_filter: $('#yearFilter').val() || ''
                    };
                },
                dataSrc: function(json) {
                    // Flask 응답을 DataTables 형식으로 변환
                    return {
                        draw: json.draw || 1,
                        recordsTotal: json.pagination?.total || 0,
                        recordsFiltered: json.pagination?.total || 0,
                        data: json.products || []
                    };
                }
            },
            drawCallback: function() {
                // 테이블 그려진 후 툴팁 및 카운터 업데이트
                $('[data-bs-toggle="tooltip"]').tooltip();
                ProductList.updateCounters();
            }
        });
    },

    // 이벤트 핸들러 설정
    setupEventHandlers: function() {
        // 새 상품 등록 버튼
        $('#addProductBtn').on('click', function() {
            ProductForm.showModal();
        });

        // 새로고침 버튼
        $('#refreshBtn').on('click', function() {
            ProductList.refresh();
        });

        // 엑셀 다운로드 버튼
        $('#excelDownloadBtn').on('click', function() {
            ProductList.downloadExcel();
        });

        // 페이지 크기 변경
        $('#perPageSelect').on('change', function() {
            const newPageLength = parseInt($(this).val());
            ProductList.dataTable.page.len(newPageLength).draw();
        });

        // 뷰 모드 변경
        $('input[name="viewMode"]').on('change', function() {
            ProductList.toggleViewMode($(this).val());
        });
    },

    // 필터 설정
    setupFilters: function() {
        // 검색 입력 (디바운싱)
        let searchTimeout;
        $('#searchInput').on('keyup', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                ProductList.dataTable.search($(this).val()).draw();
            }, 300);
        });

        // 선택 필터들
        const filterSelectors = [
            '#companyFilter', '#brandFilter', '#categoryFilter', 
            '#statusFilter', '#typeFilter', '#yearFilter'
        ];

        filterSelectors.forEach(selector => {
            $(selector).on('change', function() {
                ProductList.dataTable.ajax.reload();
            });
        });

        // 필터 초기화 버튼
        $('#resetFiltersBtn').on('click', function() {
            ProductList.resetFilters();
        });
    },

    // 필터 초기화
    resetFilters: function() {
        $('#searchInput').val('');
        $('#companyFilter, #brandFilter, #categoryFilter, #statusFilter, #typeFilter, #yearFilter').val('');
        this.dataTable.search('').ajax.reload();
        UIHelper.showAlert('필터가 초기화되었습니다.', 'info');
    },

    // 테이블 새로고침
    refresh: function() {
        UIHelper.showAlert('데이터를 새로고침합니다.', 'info');
        this.dataTable.ajax.reload(null, false); // 페이지 유지
    },

    // 뷰 모드 토글
    toggleViewMode: function(mode) {
        if (mode === 'table') {
            $('#tableView').show();
            $('#cardView').hide();
        } else {
            $('#tableView').hide();
            $('#cardView').show();
            this.renderCardView();
        }
    },

    // 카드 뷰 렌더링
    renderCardView: function() {
        const data = this.dataTable.data().toArray();
        const container = $('#productCards');
        
        if (data.length === 0) {
            container.html(`
                <div class="col-12 text-center py-5">
                    <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
                    <h5 class="text-muted">등록된 상품이 없습니다</h5>
                </div>
            `);
            return;
        }

        let html = '';
        data.forEach(product => {
            html += this.buildProductCard(product);
        });
        
        container.html(html);
        $('[data-bs-toggle="tooltip"]').tooltip();
    },

    // 상품 카드 빌드
    buildProductCard: function(product) {
        const statusClass = product.is_active ? 'success' : 'secondary';
        const statusText = product.is_active ? '활성' : '비활성';
        const companyBadge = product.company_id === 1 ? 'bg-primary' : 'bg-success';
        
        return `
            <div class="col-lg-4 col-md-6 mb-4">
                <div class="card h-100 shadow-sm product-card" onclick="editProduct(${product.id})" style="cursor: pointer;">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span class="badge ${companyBadge}">${product.company_name}</span>
                        <span class="badge bg-${statusClass}">${statusText}</span>
                    </div>
                    <div class="card-body">
                        <h6 class="card-title">${product.product_name}</h6>
                        ${product.product_code ? `<p class="text-muted small mb-2">${product.product_code}</p>` : ''}
                        <div class="row text-center">
                            <div class="col-6">
                                <small class="text-muted">브랜드</small>
                                <div class="fw-bold">${product.brand_name || '-'}</div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">가격</small>
                                <div class="fw-bold text-primary">
                                    ${product.price ? new Intl.NumberFormat('ko-KR').format(product.price) + '원' : '-'}
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="card-footer d-flex justify-content-between" onclick="event.stopPropagation();">
                        <button class="btn btn-sm btn-outline-primary" onclick="editProduct(${product.id})" 
                                data-bs-toggle="tooltip" title="수정">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-info" onclick="viewProduct(${product.id})" 
                                data-bs-toggle="tooltip" title="상세보기">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteProduct(${product.id})" 
                                data-bs-toggle="tooltip" title="삭제">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    },

    // 카운터 업데이트
    updateCounters: function() {
        const info = this.dataTable.page.info();
        $('#productCount').text(info.recordsTotal);
        $('#tableCount').text(info.recordsFiltered);
    },

    // 엑셀 다운로드
    downloadExcel: function() {
        UIHelper.setButtonLoading('#excelDownloadBtn', true, '다운로드 중...');
        
        AjaxHelper.get('/product/api/export/excel', this.currentFilters, {
            showLoading: false
        }).done(function(response) {
            if (response.success) {
                // 파일 다운로드 처리
                window.location.href = response.download_url;
                UIHelper.showAlert('엑셀 파일 다운로드가 시작됩니다.', 'success');
            }
        }).always(function() {
            UIHelper.setButtonLoading('#excelDownloadBtn', false);
        });
    }
};

// 전역 함수들 (기존 코드와 호환성 유지)
function editProduct(productId) {
    ProductForm.showModal(productId);
}

function viewProduct(productId) {
    ProductDetail.showModal(productId);
}

function deleteProduct(productId) {
    UIHelper.showConfirm(
        '상품 삭제',
        '정말로 이 상품을 삭제하시겠습니까?',
        function(confirmed) {
            if (confirmed) {
                ProductList.deleteProductById(productId);
            }
        }
    );
}

// 상품 삭제 처리
ProductList.deleteProductById = function(productId) {
    AjaxHelper.delete(`/product/api/delete/${productId}`)
        .done(function(response) {
            if (response.success) {
                UIHelper.showAlert('상품이 삭제되었습니다.', 'success');
                ProductList.refresh();
            }
        });
};

// DOM 로드 완료 시 초기화
$(document).ready(function() {
    ProductList.init();
}); 