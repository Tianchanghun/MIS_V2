/**
 * 상품 관리 모듈
 * 상품 등록, 수정, 삭제, 조회 기능 제공
 */

class ProductManager {
    constructor() {
        this.currentProductId = null;
        this.isEditMode = false;
        this.init();
    }
    
    /**
     * 초기화
     */
    init() {
        this.bindEvents();
        console.log('✅ 상품 관리자 초기화 완료');
    }
    
    /**
     * 이벤트 바인딩
     */
    bindEvents() {
        // 상품 등록 버튼
        $('#addProductBtn, button[onclick="addProduct()"]').off('click').on('click', () => {
            this.showAddModal();
        });
        
        // 상품 폼 제출
        $('#productForm').off('submit').on('submit', (e) => {
            e.preventDefault();
            this.saveProduct();
        });
        
        // 모달 닫기 시 폼 리셋
        $('#productModal').on('hidden.bs.modal', () => {
            this.resetForm();
        });
        
        // 계층형 코드 선택 이벤트
        this.bindHierarchicalEvents();
        
        // 엑셀 관련 버튼
        $('#downloadTemplateBtn, button[onclick="downloadTemplate()"]').off('click').on('click', () => {
            this.downloadTemplate();
        });
        
        $('#uploadExcelBtn, button[onclick="uploadExcel()"]').off('click').on('click', () => {
            this.uploadExcel();
        });
        
        $('#downloadExcelBtn, button[onclick="downloadExcel()"]').off('click').on('click', () => {
            this.downloadExcel();
        });
        
        // ERPia 동기화
        $('#syncERPiaBtn, button[onclick="syncERPia()"]').off('click').on('click', () => {
            this.syncERPia();
        });
    }
    
    /**
     * 계층형 코드 선택 이벤트 바인딩
     */
    bindHierarchicalEvents() {
        // 품목 선택 시 하위 타입 로드
        $('#prod_code_seq').off('change').on('change', async (e) => {
            const productSeq = $(e.target).val();
            console.log('🔗 품목 선택:', productSeq);
            
            // 타입 드롭다운 초기화
            $('#prod_type_code_seq').html('<option value="">선택하세요</option>');
            
            if (productSeq) {
                await this.loadTypesByProductSeq(productSeq);
            }
        });
    }
    
    /**
     * 품목 선택 시 하위 타입 로드
     */
    async loadTypesByProductSeq(productSeq) {
        try {
            console.log('🔄 타입 로딩 시작 - 품목 SEQ:', productSeq);
            
            const response = await AjaxHelper.get(`/product/api/get-types-by-product-seq/${productSeq}`);
            
            if (response.success && response.types) {
                const typeSelect = $('#prod_type_code_seq');
                typeSelect.empty();
                typeSelect.append('<option value="">타입 선택</option>');
                
                response.types.forEach(type => {
                    typeSelect.append(`<option value="${type.seq}">${type.code_name}</option>`);
                });
                
                console.log(`✅ ${response.types.length}개 타입 로드 완료`);
            } else {
                console.warn('⚠️ 타입 데이터 없음 또는 API 오류');
                const typeSelect = $('#prod_type_code_seq');
                typeSelect.empty();
                typeSelect.append('<option value="">타입 없음</option>');
            }
        } catch (error) {
            console.error('❌ 타입 로드 실패:', error);
            UIHelper.showAlert('타입 정보를 불러오는데 실패했습니다.');
        }
    }
    
    /**
     * 상품 등록 모달 표시
     */
    async showAddModal() {
        try {
            this.isEditMode = false;
            this.currentProductId = null;
            
            $('#productModalLabel').text('상품 등록');
            $('#isEditMode').val('false');
            $('#saveProductBtn').html('<i class="fas fa-save me-1"></i>저장');
            
            // 폼 초기화
            this.resetForm();
            
            // 코드 데이터 로드
            console.log('🔄 상품 등록 모달 - 코드 데이터 로드 시작');
            UIHelper.showLoading('코드 정보를 불러오는 중...');
            
            await this.loadInitialCodeData();
            
            // 모달 표시
            $('#productModal').modal('show');
            
            console.log('✅ 상품 등록 모달 표시 완료');
            
        } catch (error) {
            console.error('❌ 상품 등록 모달 오류:', error);
            UIHelper.showAlert('모달을 여는 중 오류가 발생했습니다', 'error');
        } finally {
            UIHelper.hideLoading();
        }
    }
    
    /**
     * 상품 수정 모달 표시 (viewProduct 기능 통합)
     */
    async viewProduct(productId) {
        // viewProduct 호출 시 바로 수정 모달로 이동
        await this.showEditModal(productId);
    }
    
    /**
     * 상품 수정 모달 표시
     */
    async showEditModal(productId) {
        try {
            this.isEditMode = true;
            this.currentProductId = productId;
            
            // 상품 정보 로드
            UIHelper.showLoading('상품 정보를 불러오는 중...');
            
            const response = await AjaxHelper.get(`/product/api/get/${productId}`);
            
            console.log('📥 API 응답:', response); // 디버깅용
            
            if (response.success && response.product) {
                await this.populateForm(response.product); // 'data' → 'product' 로 변경
                $('#productModal').modal('show');
                console.log('✅ 상품 수정 모달 표시 완료');
            } else {
                console.error('❌ API 응답 오류:', response);
                UIHelper.showAlert('상품 정보를 불러오는데 실패했습니다: ' + (response.message || '알 수 없는 오류'), 'error');
            }
        } catch (error) {
            console.error('❌ 상품 수정 모달 오류:', error);
            UIHelper.showAlert('상품 정보를 불러오는데 실패했습니다', 'error');
        } finally {
            UIHelper.hideLoading();
        }
    }
    
    /**
     * 상품 삭제
     */
    async deleteProduct(productId) {
        const confirmed = await UIHelper.showConfirm(
            '상품 삭제',
            '정말로 이 상품을 삭제하시겠습니까?<br><small class="text-muted">이 작업은 되돌릴 수 없습니다.</small>'
        );
        
        if (!confirmed) return;
        
        try {
            UIHelper.showLoading('상품을 삭제하는 중...');
            
            const response = await AjaxHelper.delete(`/product/api/delete/${productId}`);
            
            if (response.success) {
                UIHelper.showAlert('상품이 성공적으로 삭제되었습니다', 'success');
                
                // 목록 새로고침
                if (window.productListManager) {
                    productListManager.loadProducts();
                }
            } else {
                UIHelper.showAlert('상품 삭제에 실패했습니다: ' + response.message, 'error');
            }
        } catch (error) {
            console.error('상품 삭제 오류:', error);
            UIHelper.showAlert('상품 삭제 중 오류가 발생했습니다', 'error');
        } finally {
            UIHelper.hideLoading();
        }
    }
    
    /**
     * 상품 저장 (등록/수정)
     */
    async saveProduct() {
        try {
            // 폼 유효성 검사
            if (!this.validateForm()) {
                return;
            }
            
            const formData = this.getFormData();
            const url = this.isEditMode ? `/product/api/update/${this.currentProductId}` : '/product/api/create';
            const method = this.isEditMode ? 'PUT' : 'POST';
            
            UIHelper.showLoading(this.isEditMode ? '상품을 수정하는 중...' : '상품을 등록하는 중...');
            
            const response = await AjaxHelper.post(url, formData);
            
            if (response.success) {
                UIHelper.showAlert(
                    this.isEditMode ? '상품이 성공적으로 수정되었습니다' : '상품이 성공적으로 등록되었습니다', 
                    'success'
                );
                
                $('#productModal').modal('hide');
                
                // 목록 새로고침
                if (window.productListManager) {
                    productListManager.loadProducts();
                }
            } else {
                UIHelper.showAlert('상품 저장에 실패했습니다: ' + response.message, 'error');
            }
        } catch (error) {
            console.error('상품 저장 오류:', error);
            UIHelper.showAlert('상품 저장 중 오류가 발생했습니다', 'error');
        } finally {
            UIHelper.hideLoading();
        }
    }
    
    /**
     * 폼 데이터 가져오기
     */
    getFormData() {
        const formData = new FormData();
        
        // 기본 필드들 (실제 API 필드명에 맞춤)
        const fields = [
            'product_name',
            'price', 
            'description',
            'company_id'
        ];
        
        // 기본 필드 추가
        fields.forEach(field => {
            const value = $(`#${field}`).val();
            if (value !== null && value !== '') {
                formData.append(field, value);
            }
        });
        
        // 사용여부 (use_yn -> is_active 변환)
        const useYn = $('#use_yn').val();
        formData.append('is_active', useYn === 'Y');
        
        // 코드 관련 필드들 (실제 DB 필드명 사용)
        const codeFields = {
            'brand_code_seq': $('#brand_code_seq').val(),
            'category_code_seq': $('#prod_group_code_seq').val(),  // 제품구분
            'product_code_seq': $('#prod_code_seq').val(),         // 품목
            'type_code_seq': $('#prod_type_code_seq').val(),       // 타입
            'year_code_seq': $('#year_code_seq').val()             // 년식
        };
        
        // 코드 필드 추가
        Object.keys(codeFields).forEach(field => {
            const value = codeFields[field];
            if (value && value !== '') {
                formData.append(field, value);
            }
        });
        
        // 회사 정보 (현재 세션 기반)
        if (!formData.has('company_id')) {
            formData.append('company_id', '1'); // 기본값, 실제로는 세션에서 가져와야 함
        }
        
        console.log('📦 폼 데이터 준비 완료');
        return formData;
    }
    
    /**
     * 폼 유효성 검사
     */
    validateForm() {
        const productName = $('#product_name').val().trim();
        
        if (!productName) {
            UIHelper.showAlert('상품명을 입력해주세요', 'warning');
            $('#product_name').focus();
            return false;
        }
        
        if (productName.length < 2) {
            UIHelper.showAlert('상품명은 2글자 이상 입력해주세요', 'warning');
            $('#product_name').focus();
            return false;
        }
        
        const price = $('#price').val();
        if (price && price < 0) {
            UIHelper.showAlert('가격은 0 이상이어야 합니다', 'warning');
            $('#price').focus();
            return false;
        }
        
        return true;
    }
    
    /**
     * 폼에 데이터 채우기
     */
    async populateForm(productData) {
        // 모달 제목 변경
        $('#productModalLabel').text('상품 수정');
        $('#isEditMode').val('edit');
        $('#saveProductBtn').html('<i class="fas fa-edit me-1"></i>수정');
        
        // 기본 필드들
        $('#productId').val(productData.id);
        $('#product_name').val(productData.product_name);
        $('#price').val(productData.price);
        $('#description').val(productData.description);
        
        // 회사 정보
        if (productData.company_id) $('#company_id').val(productData.company_id);
        
        // 사용여부 (is_active -> use_yn 변환)
        $('#use_yn').val(productData.is_active ? 'Y' : 'N');
        
        // 브랜드 선택 (정렬 순서대로 로드 후 selected)
        if (productData.brand_code_seq) {
            $('#brand_code_seq').val(productData.brand_code_seq);
            console.log('✅ 브랜드 selected:', productData.brand_code_seq);
        }
        
        // 품목 선택 (PRD 그룹에서 로드 후 selected)
        if (productData.category_code_seq) {
            $('#prod_group_code_seq').val(productData.category_code_seq);
            console.log('✅ 품목(PRD) selected:', productData.category_code_seq);
            
            // 품목 선택 후 하위 타입 로드
            try {
                await this.loadTypesByProductSeq(productData.category_code_seq);
                
                // 타입 선택
                if (productData.type_code_seq) {
                    $('#prod_type_code_seq').val(productData.type_code_seq);
                    console.log('✅ 타입 selected:', productData.type_code_seq);
                }
            } catch (error) {
                console.error('❌ 타입 로드 실패:', error);
            }
        }
        
        // 년도 선택
        if (productData.year_code_seq) {
            $('#year_code_seq').val(productData.year_code_seq);
            console.log('✅ 년도 selected:', productData.year_code_seq);
        }
        
        // 색상 선택 (CRD 그룹에서 로드 후 selected)
        if (productData.color_code_seq) {
            $('#color_code_seq').val(productData.color_code_seq);
            console.log('✅ 색상(CRD) selected:', productData.color_code_seq);
        }
        
        // 기존 자사코드들 로드
        await this.loadExistingStdCodes(productData.id);
    }
    
    /**
     * 기존 자사코드들 로드 및 표시
     */
    async loadExistingStdCodes(productId) {
        try {
            console.log('🔄 기존 자사코드 로드 시작 - 상품 ID:', productId);
            
            const response = await AjaxHelper.get(`/product/api/get-product-models/${productId}`);
            
            if (response.success && response.models) {
                const container = $('#existingProductModels');
                container.empty();
                
                if (response.models.length > 0) {
                    container.append('<h6 class="mt-3 mb-2">등록된 자사코드</h6>');
                    
                    response.models.forEach(model => {
                        const modelHtml = `
                            <div class="alert alert-info d-flex justify-content-between align-items-center mb-2">
                                <div>
                                    <strong>${model.std_div_prod_code}</strong>
                                    ${model.product_name ? `- ${model.product_name}` : ''}
                                </div>
                                <button type="button" class="btn btn-sm btn-outline-danger" 
                                        onclick="productManager.removeStdCode(${model.id})">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        `;
                        container.append(modelHtml);
                    });
                    
                    console.log(`✅ ${response.models.length}개 자사코드 표시 완료`);
                } else {
                    container.append('<p class="text-muted mt-3">등록된 자사코드가 없습니다.</p>');
                }
            } else {
                console.warn('⚠️ 자사코드 데이터 없음');
                $('#existingProductModels').html('<p class="text-muted mt-3">자사코드 정보를 불러올 수 없습니다.</p>');
            }
        } catch (error) {
            console.error('❌ 자사코드 로드 실패:', error);
            $('#existingProductModels').html('<p class="text-danger mt-3">자사코드 로드 중 오류가 발생했습니다.</p>');
        }
    }
    
    /**
     * 자사코드 삭제
     */
    async removeStdCode(modelId) {
        if (!confirm('이 자사코드를 삭제하시겠습니까?')) {
            return;
        }
        
        try {
            const response = await AjaxHelper.delete(`/product/api/product-model/${modelId}`);
            
            if (response.success) {
                console.log('✅ 자사코드 삭제 완료');
                // 목록 새로고침
                await this.loadExistingStdCodes(this.currentProductId);
            } else {
                UIHelper.showAlert('자사코드 삭제에 실패했습니다: ' + (response.message || '알 수 없는 오류'));
            }
        } catch (error) {
            console.error('❌ 자사코드 삭제 실패:', error);
            UIHelper.showAlert('자사코드 삭제 중 오류가 발생했습니다.');
        }
    }
    
    /**
     * 폼 리셋
     */
    resetForm() {
        $('#productForm')[0].reset();
        $('#productId').val('');
        this.currentProductId = null;
        this.isEditMode = false;
        
        // 유효성 검사 스타일 제거
        $('#productForm').removeClass('was-validated');
        $('.is-invalid').removeClass('is-invalid');
    }
    
    /**
     * 템플릿 다운로드
     */
    downloadTemplate() {
        try {
            const url = '/product/api/download-template';
            window.location.href = url;
            UIHelper.showAlert('템플릿 다운로드가 시작됩니다', 'info');
        } catch (error) {
            console.error('템플릿 다운로드 오류:', error);
            UIHelper.showAlert('템플릿 다운로드 중 오류가 발생했습니다', 'error');
        }
    }
    
    /**
     * 엑셀 업로드
     */
    uploadExcel() {
        // TODO: 엑셀 업로드 기능 구현
        UIHelper.showAlert('엑셀 업로드 기능을 구현 중입니다', 'info');
    }
    
    /**
     * 엑셀 다운로드
     */
    downloadExcel() {
        try {
            const url = '/product/api/download-excel';
            window.location.href = url;
            UIHelper.showAlert('엑셀 다운로드가 시작됩니다', 'info');
        } catch (error) {
            console.error('엑셀 다운로드 오류:', error);
            UIHelper.showAlert('엑셀 다운로드 중 오류가 발생했습니다', 'error');
        }
    }
    
    /**
     * ERPia 동기화
     */
    async syncERPia() {
        const confirmed = await UIHelper.showConfirm(
            'ERPia 동기화',
            'ERPia와 동기화하시겠습니까?<br><small class="text-muted">시간이 다소 걸릴 수 있습니다.</small>'
        );
        
        if (!confirmed) return;
        
        try {
            UIHelper.showLoading('ERPia와 동기화하는 중...');
            
            // TODO: ERPia 동기화 API 구현
            const response = await AjaxHelper.post('/product/api/sync-erpia');
            
            if (response.success) {
                UIHelper.showAlert('ERPia 동기화가 완료되었습니다', 'success');
                
                // 목록 새로고침
                if (window.productListManager) {
                    productListManager.loadProducts();
                }
            } else {
                UIHelper.showAlert('ERPia 동기화에 실패했습니다: ' + response.message, 'error');
            }
        } catch (error) {
            console.error('ERPia 동기화 오류:', error);
            UIHelper.showAlert('ERPia 동기화 기능을 구현 중입니다', 'info');
        } finally {
            UIHelper.hideLoading();
        }
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
     * 초기 코드 데이터 로드 (PRD, CR 등)
     */
    async loadInitialCodeData() {
        try {
            // PRD 품목 코드 로드
            const prdResponse = await AjaxHelper.get('/admin/api/codes/group/PRD');
            if (prdResponse.success) {
                const prdSelect = $('#prod_code_seq');
                prdSelect.html('<option value="">품목을 선택하세요</option>');
                
                prdResponse.data.forEach(code => {
                    prdSelect.append(`<option value="${code.seq}" data-code="${code.code}">${code.code_name} (${code.code})</option>`);
                });
                console.log('✅ PRD 품목 코드 로드 완료:', prdResponse.data.length + '개');
            }
            
            // CR 색상 코드 로드
            const crResponse = await AjaxHelper.get('/admin/api/codes/group/CR');
            if (crResponse.success) {
                const colorSelects = $('.color-code');
                colorSelects.each(function() {
                    const $this = $(this);
                    $this.html('<option value="">색상을 선택하세요</option>');
                    
                    crResponse.data.forEach(code => {
                        $this.append(`<option value="${code.seq}" data-code="${code.code}">${code.code_name} (${code.code})</option>`);
                    });
                });
                console.log('✅ CR 색상 코드 로드 완료:', crResponse.data.length + '개');
            }
            
        } catch (error) {
            console.error('❌ 초기 코드 데이터 로드 실패:', error);
            throw error;
        }
    }
}

// 전역 변수로 인스턴스 노출
let productManager;

// DOM 준비 시 초기화 - 의존성 확인
$(document).ready(function() {
    // 필수 라이브러리 로드 확인
    if (typeof $ === 'undefined') {
        console.error('❌ jQuery가 로드되지 않았습니다');
        return;
    }
    
    if (typeof UIHelper === 'undefined') {
        console.error('❌ UIHelper가 로드되지 않았습니다');
        return;
    }
    
    if (typeof AjaxHelper === 'undefined') {
        console.error('❌ AjaxHelper가 로드되지 않았습니다');
        return;
    }
    
    console.log('🚀 상품 관리자 초기화 시작');
    productManager = new ProductManager();
});

// 레거시 호환을 위한 전역 함수들
function addProduct() { 
    if (window.productManager) {
        productManager.showAddModal(); 
    } else {
        console.error('❌ ProductManager가 초기화되지 않았습니다');
        // 긴급 초기화 시도
        setTimeout(() => {
            if (window.productManager) {
                productManager.showAddModal();
            } else {
                alert('상품 관리자가 아직 로드 중입니다. 잠시 후 다시 시도해주세요.');
            }
        }, 1000);
    }
}

function editProduct(productId) { 
    if (window.productManager) {
        productManager.showEditModal(productId); 
    } else {
        console.error('❌ ProductManager가 초기화되지 않았습니다');
        // 긴급 초기화 시도
        setTimeout(() => {
            if (window.productManager) {
                productManager.showEditModal(productId);
            } else {
                alert('상품 관리자가 아직 로드 중입니다. 잠시 후 다시 시도해주세요.');
            }
        }, 1000);
    }
}

function viewProduct(productId) { 
    if (window.productManager) {
        productManager.viewProduct(productId); 
    } else {
        console.error('❌ ProductManager가 초기화되지 않았습니다');
        editProduct(productId); // fallback
    }
}

function deleteProduct(productId) { 
    if (window.productManager) {
        productManager.deleteProduct(productId); 
    } else {
        console.error('❌ ProductManager가 초기화되지 않았습니다');
        if (confirm('정말로 이 상품을 삭제하시겠습니까?')) {
            window.location.reload(); // 임시 fallback
        }
    }
}

function downloadTemplate() { 
    if (window.productManager) {
        productManager.downloadTemplate(); 
    } else {
        window.open('/product/api/download-template', '_blank');
    }
}

function uploadExcel() { 
    if (window.productManager) {
        productManager.uploadExcel(); 
    } else {
        alert('엑셀 업로드 기능을 준비 중입니다.');
    }
}

function downloadExcel() { 
    if (window.productManager) {
        productManager.downloadExcel(); 
    } else {
        window.open('/product/api/download-excel', '_blank');
    }
}

function syncERPia() { 
    if (window.productManager) {
        productManager.syncERPia(); 
    } else {
        alert('ERPia 동기화 기능을 준비 중입니다.');
    }
} 