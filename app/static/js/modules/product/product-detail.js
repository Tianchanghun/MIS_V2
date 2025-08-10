/**
 * 상품 상세보기 모듈
 * 상품 정보 조회 및 상세 정보 표시
 */
const ProductDetail = {
    // 모달 표시
    showModal: function(productId) {
        if (!productId) {
            UIHelper.showAlert('상품 ID가 없습니다.', 'warning');
            return;
        }

        $('#productDetailModal').modal('show');
        this.loadProductDetail(productId);
    },

    // 상품 상세 정보 로드
    loadProductDetail: function(productId) {
        const modalBody = $('#productDetailModalBody');
        
        // 로딩 상태 표시
        modalBody.html(`
            <div class="text-center py-5">
                <div class="spinner-border text-primary mb-3" role="status"></div>
                <div>상품 정보를 불러오는 중...</div>
            </div>
        `);

        AjaxHelper.get(`/product/api/get/${productId}`, {}, {
            showLoading: false
        }).done(function(response) {
            if (response.success) {
                ProductDetail.renderProductDetail(response.product);
            } else {
                modalBody.html(`
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        상품 정보를 불러올 수 없습니다.
                    </div>
                `);
            }
        }).fail(function() {
            modalBody.html(`
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    오류가 발생했습니다.
                </div>
            `);
        });
    },

    // 상품 상세 정보 렌더링
    renderProductDetail: function(product) {
        const modalBody = $('#productDetailModalBody');
        
        const html = `
            <div class="row">
                <div class="col-md-6">
                    <h6 class="fw-bold text-primary mb-3">
                        <i class="fas fa-info-circle me-2"></i>기본 정보
                    </h6>
                    <table class="table table-sm table-borderless">
                        <tr>
                            <td class="fw-bold text-muted" style="width: 30%;">상품명:</td>
                            <td>${product.product_name || '-'}</td>
                        </tr>
                        <tr>
                            <td class="fw-bold text-muted">상품코드:</td>
                            <td>${product.product_code || '-'}</td>
                        </tr>
                        <tr>
                            <td class="fw-bold text-muted">회사:</td>
                            <td>
                                <span class="badge ${product.company_id === 1 ? 'bg-primary' : 'bg-success'}">
                                    ${product.company_id === 1 ? '에이원' : '에이원월드'}
                                </span>
                            </td>
                        </tr>
                        <tr>
                            <td class="fw-bold text-muted">브랜드:</td>
                            <td>${product.brand_name || '미지정'}</td>
                        </tr>
                        <tr>
                            <td class="fw-bold text-muted">가격:</td>
                            <td class="fw-bold text-primary">
                                ${product.price ? this.formatPrice(product.price) + '원' : '미정'}
                            </td>
                        </tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6 class="fw-bold text-success mb-3">
                        <i class="fas fa-tags me-2"></i>분류 정보
                    </h6>
                    <table class="table table-sm table-borderless">
                        <tr>
                            <td class="fw-bold text-muted" style="width: 30%;">품목:</td>
                            <td>${product.category_name || '미지정'}</td>
                        </tr>
                        <tr>
                            <td class="fw-bold text-muted">타입:</td>
                            <td>${product.type_name || '미지정'}</td>
                        </tr>
                        <tr>
                            <td class="fw-bold text-muted">년도:</td>
                            <td>${product.year_code_name || '-'}</td>
                        </tr>
                        <tr>
                            <td class="fw-bold text-muted">상태:</td>
                            <td>
                                <span class="badge ${product.is_active ? 'bg-success' : 'bg-secondary'}">
                                    ${product.is_active ? '활성' : '비활성'}
                                </span>
                            </td>
                        </tr>
                        <tr>
                            <td class="fw-bold text-muted">등록일:</td>
                            <td>${this.formatDate(product.created_at)}</td>
                        </tr>
                    </table>
                </div>
            </div>

            ${product.description ? `
                <div class="mt-4">
                    <h6 class="fw-bold text-info mb-3">
                        <i class="fas fa-file-text me-2"></i>상품 설명
                    </h6>
                    <div class="card">
                        <div class="card-body">
                            <p class="mb-0">${product.description}</p>
                        </div>
                    </div>
                </div>
            ` : ''}

            ${product.models && product.models.length > 0 ? `
                <div class="mt-4">
                    <h6 class="fw-bold text-warning mb-3">
                        <i class="fas fa-palette me-2"></i>색상별 모델 (${product.models.length}개)
                    </h6>
                    <div class="row">
                        ${product.models.map(model => this.buildModelCard(model)).join('')}
                    </div>
                </div>
            ` : ''}

            <div class="mt-4 pt-3 border-top">
                <div class="row text-center">
                    <div class="col-md-4">
                        <small class="text-muted">등록자</small>
                        <div class="fw-bold">${product.created_by || '-'}</div>
                    </div>
                    <div class="col-md-4">
                        <small class="text-muted">등록일</small>
                        <div class="fw-bold">${this.formatDate(product.created_at)}</div>
                    </div>
                    <div class="col-md-4">
                        <small class="text-muted">수정일</small>
                        <div class="fw-bold">${this.formatDate(product.updated_at)}</div>
                    </div>
                </div>
            </div>

            <div class="mt-4 text-center">
                <button type="button" class="btn btn-primary me-2" onclick="editProduct(${product.id})">
                    <i class="fas fa-edit me-2"></i>수정
                </button>
                <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">
                    <i class="fas fa-times me-2"></i>닫기
                </button>
            </div>
        `;

        modalBody.html(html);
    },

    // 모델 카드 빌드
    buildModelCard: function(model) {
        return `
            <div class="col-md-6 col-lg-4 mb-3">
                <div class="card border-start border-primary border-3">
                    <div class="card-body p-3">
                        <div class="d-flex align-items-center mb-2">
                            <div class="color-indicator me-2" 
                                 style="width: 20px; height: 20px; border-radius: 50%; background-color: ${this.getColorValue(model.color_code)}; border: 1px solid #ddd;">
                            </div>
                            <strong>${model.color_name || model.color_code}</strong>
                        </div>
                        ${model.model_name ? `<div class="small text-muted mb-1">모델명: ${model.model_name}</div>` : ''}
                        ${model.std_code ? `<div class="small text-muted">자사코드: <code>${model.std_code}</code></div>` : ''}
                    </div>
                </div>
            </div>
        `;
    },

    // 색상 값 가져오기 (간단한 매핑)
    getColorValue: function(colorCode) {
        const colorMap = {
            'RED': '#dc3545',
            'BLUE': '#0d6efd',
            'GREEN': '#198754',
            'YELLOW': '#ffc107',
            'BLACK': '#212529',
            'WHITE': '#f8f9fa',
            'GRAY': '#6c757d'
        };
        
        return colorMap[colorCode] || '#6c757d';
    },

    // 가격 포맷
    formatPrice: function(price) {
        return new Intl.NumberFormat('ko-KR').format(price);
    },

    // 날짜 포맷
    formatDate: function(dateString) {
        if (!dateString) return '-';
        
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('ko-KR', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (e) {
            return dateString;
        }
    },

    // 초기화
    init: function() {
        // 모달이 없으면 생성
        if (!$('#productDetailModal').length) {
            this.createModal();
        }
    },

    // 모달 생성
    createModal: function() {
        const modal = $(`
            <div class="modal fade" id="productDetailModal" tabindex="-1" aria-labelledby="productDetailModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="productDetailModalLabel">
                                <i class="fas fa-eye me-2"></i>상품 상세보기
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body" id="productDetailModalBody">
                            <!-- 동적 내용 -->
                        </div>
                    </div>
                </div>
            </div>
        `);
        
        $('body').append(modal);
    }
};

// DOM 로드 완료 시 초기화
$(document).ready(function() {
    ProductDetail.init();
}); 