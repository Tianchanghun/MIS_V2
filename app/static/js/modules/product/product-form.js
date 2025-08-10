/**
 * 상품 폼 관리 모듈
 * 상품 등록/수정 모달과 폼 처리
 */
const ProductForm = {
    // 모달 상태
    isEditMode: false,
    currentProductId: null,

    // 모달 표시
    showModal: function(productId = null) {
        this.isEditMode = productId !== null;
        this.currentProductId = productId;

        if (this.isEditMode) {
            this.loadProductData(productId);
        } else {
            this.resetForm();
        }

        $('#productModal').modal('show');
    },

    // 폼 초기화
    resetForm: function() {
        $('#productForm')[0].reset();
        $('#productModalLabel').text('상품 등록');
        $('#productId').val('');
        $('#isEditMode').val('false');
        
        // 동적 모델 행들 초기화
        this.resetModelRows();
        
        // 폼 활성화
        UIHelper.toggleForm('#productForm', false);
    },

    // 상품 데이터 로드
    loadProductData: function(productId) {
        $('#productModalLabel').text('상품 수정');
        $('#productId').val(productId);
        $('#isEditMode').val('true');
        
        UIHelper.toggleForm('#productForm', true);
        
        AjaxHelper.get(`/product/api/get/${productId}`)
            .done(function(response) {
                if (response.success) {
                    ProductForm.populateForm(response.product);
                } else {
                    UIHelper.showAlert('상품 정보를 불러올 수 없습니다.', 'error');
                    $('#productModal').modal('hide');
                }
            })
            .always(function() {
                UIHelper.toggleForm('#productForm', false);
            });
    },

    // 폼에 데이터 채우기
    populateForm: function(product) {
        // 기본 정보
        $('#company_id').val(product.company_id || '');
        $('#product_name').val(product.product_name || '');
        $('#description').val(product.description || '');
        $('#price').val(product.price || '');
        $('#use_yn').val(product.use_yn || 'Y');

        // 선택 필드들 (비동기로 설정)
        setTimeout(() => {
            $('#brand_code_seq').val(product.brand_code_seq || '');
            $('#prod_group_code_seq').val(product.prod_group_code_seq || '');
            $('#prod_code_seq').val(product.prod_code_seq || '');
            $('#prod_type_code_seq').val(product.prod_type_code_seq || '');
            $('#year_code_seq').val(product.year_code_seq || '');
        }, 100);

        // 제품 모델 데이터
        if (product.models && product.models.length > 0) {
            this.populateModelRows(product.models);
        }
    },

    // 모델 행들 채우기
    populateModelRows: function(models) {
        const container = $('#productModelsContainer');
        container.empty();

        models.forEach((model, index) => {
            const modelRow = this.createModelRow(index, model);
            container.append(modelRow);
        });
    },

    // 모델 행 생성
    createModelRow: function(index, data = {}) {
        return $(`
            <div class="product-model-item border p-3 mb-3" data-index="${index}">
                <div class="row">
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label for="color_code_${index}" class="form-label">색상 <span class="required">*</span></label>
                            <select id="color_code_${index}" class="form-control color-code" name="color_code[]" required>
                                <option value="">선택하세요</option>
                                ${this.buildColorOptions(data.color_code)}
                            </select>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label for="product_model_name_${index}" class="form-label">제품명</label>
                            <input type="text" id="product_model_name_${index}" class="form-control product-model-name" 
                                   name="product_model_name[]" value="${data.model_name || ''}" 
                                   placeholder="색상별 제품명 (선택사항)">
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="mb-3">
                            <label for="std_product_code_${index}" class="form-label">자사코드</label>
                            <input type="text" id="std_product_code_${index}" class="form-control std-product-code" 
                                   name="std_product_code[]" value="${data.std_code || ''}" 
                                   placeholder="자동생성됨" readonly>
                        </div>
                    </div>
                    <div class="col-md-1">
                        <div class="mb-3">
                            <label class="form-label">&nbsp;</label>
                            <button type="button" class="btn btn-danger btn-remove-model d-block">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `);
    },

    // 색상 옵션 빌드
    buildColorOptions: function(selectedValue = '') {
        // 실제로는 서버에서 가져온 색상 코드를 사용
        const colors = window.colorCodes || [];
        let options = '';
        
        colors.forEach(color => {
            const selected = color.code === selectedValue ? 'selected' : '';
            options += `<option value="${color.code}" ${selected}>${color.code_name} (${color.code})</option>`;
        });
        
        return options;
    },

    // 모델 행들 초기화
    resetModelRows: function() {
        const container = $('#productModelsContainer');
        container.empty();
        this.addModelRow(); // 기본 1개 행 추가
    },

    // 모델 행 추가
    addModelRow: function() {
        const container = $('#productModelsContainer');
        const index = container.children().length;
        const newRow = this.createModelRow(index);
        
        container.append(newRow);
        
        // 이벤트 핸들러 재설정
        this.setupModelRowEvents(newRow);
    },

    // 모델 행 이벤트 설정
    setupModelRowEvents: function($row) {
        // 삭제 버튼
        $row.find('.btn-remove-model').on('click', function() {
            if ($('#productModelsContainer').children().length > 1) {
                $row.remove();
                ProductForm.updateModelIndexes();
            } else {
                UIHelper.showAlert('최소 1개의 모델은 필요합니다.', 'warning');
            }
        });

        // 색상 변경 시 자사코드 자동생성
        $row.find('.color-code').on('change', function() {
            ProductForm.generateProductCode($row);
        });
    },

    // 모델 인덱스 업데이트
    updateModelIndexes: function() {
        $('#productModelsContainer').children().each(function(index) {
            $(this).attr('data-index', index);
            $(this).find('input, select').each(function() {
                const name = $(this).attr('name');
                if (name && name.includes('[')) {
                    // ID도 업데이트
                    const baseId = $(this).attr('id').replace(/_\d+$/, '');
                    $(this).attr('id', `${baseId}_${index}`);
                    
                    // Label for 속성도 업데이트
                    const $label = $(this).closest('.mb-3').find('label');
                    $label.attr('for', `${baseId}_${index}`);
                }
            });
        });
    },

    // 자사코드 자동생성
    generateProductCode: function($row) {
        const colorCode = $row.find('.color-code').val();
        const productName = $('#product_name').val();
        
        if (colorCode && productName) {
            // 간단한 코드 생성 로직 (실제로는 서버 API 호출)
            const generatedCode = `${productName.substring(0, 3)}_${colorCode}`.toUpperCase();
            $row.find('.std-product-code').val(generatedCode);
        }
    },

    // 폼 제출
    submitForm: function() {
        if (!this.validateForm()) {
            return;
        }

        const formData = new FormData($('#productForm')[0]);
        const url = this.isEditMode ? 
            `/product/api/update/${this.currentProductId}` : 
            '/product/api/create';

        UIHelper.setButtonLoading('#productSubmitBtn', true, '저장 중...');
        UIHelper.toggleForm('#productForm', true);

        AjaxHelper.upload(url, formData, {
            showLoading: false
        }).done(function(response) {
            if (response.success) {
                UIHelper.showAlert(response.message, 'success');
                $('#productModal').modal('hide');
                ProductList.refresh();
            }
        }).always(function() {
            UIHelper.setButtonLoading('#productSubmitBtn', false);
            UIHelper.toggleForm('#productForm', false);
        });
    },

    // 폼 검증
    validateForm: function() {
        // 필수 필드 검증
        const requiredFields = ['company_id', 'product_name', 'price'];
        let isValid = true;

        requiredFields.forEach(fieldName => {
            const $field = $(`#${fieldName}`);
            if (!$field.val().trim()) {
                $field.addClass('is-invalid');
                isValid = false;
            } else {
                $field.removeClass('is-invalid');
            }
        });

        // 모델 검증
        const hasValidModel = $('#productModelsContainer .color-code').filter(function() {
            return $(this).val() !== '';
        }).length > 0;

        if (!hasValidModel) {
            UIHelper.showAlert('최소 1개의 색상을 선택해야 합니다.', 'warning');
            isValid = false;
        }

        return isValid;
    },

    // 초기화
    init: function() {
        // 폼 제출 이벤트
        $('#productForm').on('submit', function(e) {
            e.preventDefault();
            ProductForm.submitForm();
        });

        // 모델 추가 버튼
        $('#addModelBtn').on('click', function() {
            ProductForm.addModelRow();
        });

        // 모달 숨김 시 초기화
        $('#productModal').on('hidden.bs.modal', function() {
            ProductForm.resetForm();
        });

        // 기본 모델 행 설정
        this.resetModelRows();
    }
};

// DOM 로드 완료 시 초기화
$(document).ready(function() {
    ProductForm.init();
}); 