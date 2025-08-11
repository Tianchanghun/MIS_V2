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
                await this.populateForm(response.product, response.product_models); // product_models도 전달
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
     * 폼에 데이터 채우기 (강제 selected 적용)
     */
    async populateForm(productData, productModels) {
        console.log('🔧 상품 수정 폼 데이터 채우기 시작:', productData);
        
        // 모달 제목 변경
        $('#productModalLabel').text('상품 수정');
        $('#isEditMode').val('edit');
        $('#saveProductBtn').html('<i class="fas fa-edit me-1"></i>수정');
        
        // 기본 필드들
        $('#productId').val(productData.id);
        $('#product_name').val(productData.product_name);
        $('#price').val(productData.price);
        $('#description').val(productData.description);
        
        // 회사 정보 강제 selected
        if (productData.company_id) {
            $('#company_id').val(productData.company_id).trigger('change');
            console.log('✅ 회사 강제 selected:', productData.company_id);
        }
        
        // 사용여부 (is_active -> use_yn 변환)
        const useYnValue = productData.is_active ? 'Y' : 'N';
        $('#use_yn').val(useYnValue).trigger('change');
        console.log('✅ 사용여부 강제 selected:', useYnValue);
        
        // 🔥 브랜드 코드 강제 selected
        if (productData.brand_code_seq) {
            setTimeout(() => {
                const brandValue = String(productData.brand_code_seq); // 문자열로 변환
                console.log('🔧 브랜드 설정 시도:', brandValue, typeof brandValue);
                
                // 옵션 존재 확인
                const brandSelect = $('#brand_code_seq');
                const brandOptions = brandSelect.find('option');
                console.log('📋 브랜드 셀렉트박스:', brandSelect.length > 0 ? '존재' : '없음');
                console.log('📋 브랜드 옵션 개수:', brandOptions.length);
                console.log('📋 브랜드 옵션들:', brandOptions.map(function() { return $(this).val() + ':' + $(this).text(); }).get());
                
                if (brandOptions.length <= 1) {
                    console.error('❌ 브랜드 옵션이 로드되지 않았습니다! 기본 옵션만 존재');
                    return;
                }
                
                // 해당 값이 옵션에 있는지 확인
                const targetOption = brandSelect.find(`option[value="${brandValue}"]`);
                console.log('🎯 찾는 브랜드 옵션:', targetOption.length > 0 ? targetOption.text() : '없음');
                
                if (targetOption.length === 0) {
                    console.error('❌ 브랜드 옵션에서 값을 찾을 수 없습니다:', brandValue);
                    return;
                }
                
                brandSelect.val(brandValue).trigger('change');
                console.log('🔥 브랜드 코드 강제 적용:', brandValue);
                
                // 강제 확인
                const currentVal = brandSelect.val();
                if (currentVal != brandValue) {
                    console.warn('⚠️ 브랜드 재시도. 기대값:', brandValue, '현재값:', currentVal);
                    targetOption.prop('selected', true);
                    brandSelect.trigger('change');
                    console.log('✅ 브랜드 옵션 강제 선택:', targetOption.text());
                } else {
                    console.log('✅ 브랜드 선택 성공:', currentVal);
                }
            }, 300); // 시간을 늘려서 DOM 로딩 완료 대기
        }
        
        // 🔥 제품구분 코드 강제 selected
        if (productData.category_code_seq) {
            setTimeout(() => {
                const categoryValue = String(productData.category_code_seq);
                console.log('🔧 제품구분 설정 시도:', categoryValue, typeof categoryValue);
                
                // 옵션 존재 확인
                const categorySelect = $('#prod_group_code_seq');
                const categoryOptions = categorySelect.find('option');
                console.log('📋 제품구분 셀렉트박스:', categorySelect.length > 0 ? '존재' : '없음');
                console.log('📋 제품구분 옵션 개수:', categoryOptions.length);
                console.log('📋 제품구분 옵션들:', categoryOptions.map(function() { return $(this).val() + ':' + $(this).text(); }).get());
                
                if (categoryOptions.length <= 1) {
                    console.error('❌ 제품구분 옵션이 로드되지 않았습니다! 기본 옵션만 존재');
                    return;
                }
                
                // 해당 값이 옵션에 있는지 확인
                const targetOption = categorySelect.find(`option[value="${categoryValue}"]`);
                console.log('🎯 찾는 제품구분 옵션:', targetOption.length > 0 ? targetOption.text() : '없음');
                
                if (targetOption.length === 0) {
                    console.error('❌ 제품구분 옵션에서 값을 찾을 수 없습니다:', categoryValue);
                    return;
                }
                
                categorySelect.val(categoryValue).trigger('change');
                console.log('🔥 제품구분 코드 강제 적용:', categoryValue);
                
                // 강제 확인
                const currentVal = categorySelect.val();
                if (currentVal != categoryValue) {
                    console.warn('⚠️ 제품구분 재시도. 기대값:', categoryValue, '현재값:', currentVal);
                    targetOption.prop('selected', true);
                    categorySelect.trigger('change');
                    console.log('✅ 제품구분 옵션 강제 선택:', targetOption.text());
                } else {
                    console.log('✅ 제품구분 선택 성공:', currentVal);
                }
            }, 350);
        }
        
        // 🔥 품목(PRD) 코드 강제 selected
        if (productData.category_code_seq) {
            setTimeout(() => {
                const prdValue = String(productData.category_code_seq);
                console.log('🔧 품목(PRD) 설정 시도:', prdValue, typeof prdValue);
                
                // 옵션 존재 확인
                const prdSelect = $('#prod_code_seq');
                const prdOptions = prdSelect.find('option');
                console.log('📋 품목 셀렉트박스:', prdSelect.length > 0 ? '존재' : '없음');
                console.log('📋 품목 옵션 개수:', prdOptions.length);
                console.log('📋 품목 옵션들:', prdOptions.map(function() { return $(this).val() + ':' + $(this).text(); }).get());
                
                if (prdOptions.length <= 1) {
                    console.error('❌ 품목 옵션이 로드되지 않았습니다! 기본 옵션만 존재');
                    return;
                }
                
                // 해당 값이 옵션에 있는지 확인
                const targetOption = prdSelect.find(`option[value="${prdValue}"]`);
                console.log('🎯 찾는 품목 옵션:', targetOption.length > 0 ? targetOption.text() : '없음');
                
                if (targetOption.length === 0) {
                    console.error('❌ 품목 옵션에서 값을 찾을 수 없습니다:', prdValue);
                    return;
                }
                
                prdSelect.val(prdValue).trigger('change');
                console.log('🔥 품목(PRD) 코드 강제 적용:', prdValue);
                
                // 강제 확인
                const currentVal = prdSelect.val();
                if (currentVal != prdValue) {
                    console.warn('⚠️ 품목 재시도. 기대값:', prdValue, '현재값:', currentVal);
                    targetOption.prop('selected', true);
                    prdSelect.trigger('change');
                    console.log('✅ 품목 옵션 강제 선택:', targetOption.text());
                } else {
                    console.log('✅ 품목 선택 성공:', currentVal);
                }
            }, 400);
            
            // 품목 선택 후 하위 타입 로드 및 강제 선택
            try {
                await this.loadTypesByProductSeq(productData.category_code_seq);
                
                // 🔥 타입 코드 강제 selected (타입 로드 완료 후)
                if (productData.type_code_seq) {
                    setTimeout(() => {
                        const typeValue = String(productData.type_code_seq);
                        console.log('🔧 타입 설정 시도:', typeValue, typeof typeValue);
                        
                        // 옵션 존재 확인
                        const typeSelect = $('#prod_type_code_seq');
                        const typeOptions = typeSelect.find('option');
                        console.log('📋 타입 셀렉트박스:', typeSelect.length > 0 ? '존재' : '없음');
                        console.log('📋 타입 옵션 개수:', typeOptions.length);
                        console.log('📋 타입 옵션들:', typeOptions.map(function() { return $(this).val() + ':' + $(this).text(); }).get());
                        
                        if (typeOptions.length <= 1) {
                            console.error('❌ 타입 옵션이 로드되지 않았습니다! 기본 옵션만 존재');
                            return;
                        }
                        
                        // 해당 값이 옵션에 있는지 확인
                        const targetOption = typeSelect.find(`option[value="${typeValue}"]`);
                        console.log('🎯 찾는 타입 옵션:', targetOption.length > 0 ? targetOption.text() : '없음');
                        
                        if (targetOption.length === 0) {
                            console.error('❌ 타입 옵션에서 값을 찾을 수 없습니다:', typeValue);
                            return;
                        }
                        
                        typeSelect.val(typeValue).trigger('change');
                        console.log('🔥 타입 코드 강제 적용:', typeValue);
                        
                        // 강제 확인
                        const currentVal = typeSelect.val();
                        if (currentVal != typeValue) {
                            console.warn('⚠️ 타입 재시도. 기대값:', typeValue, '현재값:', currentVal);
                            targetOption.prop('selected', true);
                            typeSelect.trigger('change');
                            console.log('✅ 타입 옵션 강제 선택:', targetOption.text());
                        } else {
                            console.log('✅ 타입 선택 성공:', currentVal);
                        }
                    }, 600);
                }
            } catch (error) {
                console.error('❌ 타입 로드 실패:', error);
            }
        }
        
        // 🔥 년식 코드 강제 selected
        if (productData.year_code_seq) {
            setTimeout(() => {
                const yearValue = String(productData.year_code_seq);
                console.log('🔧 년식 설정 시도:', yearValue, typeof yearValue);
                
                // 옵션 존재 확인
                const yearSelect = $('#year_code_seq');
                const yearOptions = yearSelect.find('option');
                console.log('📋 년식 셀렉트박스:', yearSelect.length > 0 ? '존재' : '없음');
                console.log('📋 년식 옵션 개수:', yearOptions.length);
                console.log('📋 년식 옵션들:', yearOptions.map(function() { return $(this).val() + ':' + $(this).text(); }).get());
                
                if (yearOptions.length <= 1) {
                    console.error('❌ 년식 옵션이 로드되지 않았습니다! 기본 옵션만 존재');
                    return;
                }
                
                // 해당 값이 옵션에 있는지 확인
                const targetOption = yearSelect.find(`option[value="${yearValue}"]`);
                console.log('🎯 찾는 년식 옵션:', targetOption.length > 0 ? targetOption.text() : '없음');
                
                if (targetOption.length === 0) {
                    console.error('❌ 년식 옵션에서 값을 찾을 수 없습니다:', yearValue);
                    return;
                }
                
                yearSelect.val(yearValue).trigger('change');
                console.log('🔥 년식 코드 강제 적용:', yearValue);
                
                // 강제 확인
                const currentVal = yearSelect.val();
                if (currentVal != yearValue) {
                    console.warn('⚠️ 년식 재시도. 기대값:', yearValue, '현재값:', currentVal);
                    targetOption.prop('selected', true);
                    yearSelect.trigger('change');
                    console.log('✅ 년식 옵션 강제 선택:', targetOption.text());
                } else {
                    console.log('✅ 년식 선택 성공:', currentVal);
                }
            }, 500);
        }
        
        // 기존 자사코드들 로드 (tbl_Product_DTL 연동)
        await this.loadExistingProductModels(productData.id, productModels);
        
        console.log('✅ 상품 수정 폼 데이터 채우기 완료');
    }
    
    /**
     * 기존 상품 모델들 로드 (tbl_Product_DTL) - 강제 selected 적용
     */
    async loadExistingProductModels(productId, productModels) {
        try {
            console.log('🔧 기존 상품 모델 로드 시작:', productModels);
            
            if (!productModels || productModels.length === 0) {
                console.log('📭 상품 모델이 없습니다.');
                return;
            }
            
            // 상품 모델 컨테이너 초기화
            const container = $('#productModelsContainer');
            container.empty();
            
            // 각 상품 모델을 HTML로 렌더링
            productModels.forEach((model, index) => {
                const modelHtml = this.createProductModelHTML(model, index);
                container.append(modelHtml);
                
                // 🔥 각 모델의 색상 강제 선택 (DOM 추가 후)
                setTimeout(() => {
                    const modelContainer = container.find(`.product-model-item[data-index="${index}"]`);
                    const colorSelect = modelContainer.find('.color-code');
                    
                    if (model.color_code_info && model.color_code_info.seq) {
                        console.log(`🎨 모델 ${index} 색상 강제 적용:`, model.color_code_info.seq, model.color_code_info.code_name);
                        
                        // 방법 1: 직접 값 설정
                        colorSelect.val(model.color_code_info.seq);
                        
                        // 방법 2: 옵션 강제 선택
                        colorSelect.find('option').each(function() {
                            if ($(this).val() == model.color_code_info.seq) {
                                $(this).prop('selected', true);
                                console.log('✅ 색상 옵션 강제 선택됨:', $(this).text());
                            } else {
                                $(this).prop('selected', false);
                            }
                        });
                        
                        // 방법 3: change 이벤트 트리거
                        colorSelect.trigger('change');
                        
                        // 확인
                        setTimeout(() => {
                            const selectedValue = colorSelect.val();
                            if (selectedValue == model.color_code_info.seq) {
                                console.log('🎯 색상 선택 성공:', selectedValue);
                            } else {
                                console.error('❌ 색상 선택 실패. 기대값:', model.color_code_info.seq, '실제값:', selectedValue);
                            }
                        }, 100);
                    }
                }, 200 * (index + 1)); // 각 모델마다 시간차 적용
            });
            
            console.log(`✅ ${productModels.length}개 상품 모델 로드 완료`);
            
        } catch (error) {
            console.error('❌ 상품 모델 로드 실패:', error);
        }
    }
    
    /**
     * 상품 모델 HTML 생성 (색상 selected 상태 적용)
     */
    createProductModelHTML(model, index) {
        // 색상 옵션 HTML 생성 (selected 상태 포함)
        let colorOptionsHtml = '<option value="">색상을 선택하세요</option>';
        
        // HTML에서 color_codes를 가져와서 사용
        if (window.colorCodesData) {
            window.colorCodesData.forEach(color => {
                const isSelected = model.color_code_info && model.color_code_info.seq == color.seq ? 'selected' : '';
                colorOptionsHtml += `<option value="${color.seq}" data-code="${color.code}" ${isSelected}>${color.code_name} (${color.code})</option>`;
            });
        }
        
        return `
            <div class="product-model-item border p-3 mb-3" data-index="${index}" data-model-id="${model.id}">
                <div class="row">
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">
                                <i class="fas fa-palette me-1"></i>색상 (CR) <span class="required">*</span>
                            </label>
                            <select class="form-select color-code" name="color_code[]" required>
                                ${colorOptionsHtml}
                            </select>
                            <small class="text-muted">현재: ${model.color_code_info ? model.color_code_info.code_name : model.color_code}</small>
                        </div>
                    </div>
                    
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">제품명 (색상별)</label>
                            <input type="text" class="form-control product-model-name" 
                                   name="product_model_name[]" 
                                   value="${model.product_name || ''}"
                                   placeholder="색상별 제품명">
                        </div>
                    </div>
                    
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">16자리 자사코드</label>
                            <div class="input-group">
                                <input type="text" class="form-control std-product-code" 
                                       name="std_product_code[]" 
                                       value="${model.std_div_prod_code || ''}"
                                       readonly>
                                <button type="button" class="btn btn-primary btn-generate-code" title="선택된 코드 기준으로 생성">
                                    <i class="fas fa-magic"></i> 자동생성
                                </button>
                            </div>
                            <small class="text-muted">tbl_Product_DTL 연동</small>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6">
                        <small class="text-info">
                            <strong>코드 구성:</strong> 
                            ${model.brand_code}+${model.div_type_code}+${model.prod_group_code}+${model.prod_type_code}+${model.prod_code}+${model.prod_type2_code}+${model.year_code}+${model.color_code}
                        </small>
                    </div>
                    <div class="col-md-4">
                        <small class="text-muted">상태: ${model.status}, 사용: ${model.use_yn}</small>
                    </div>
                    <div class="col-md-2">
                        <button type="button" class="btn btn-outline-danger btn-sm btn-remove-model w-100">
                            <i class="fas fa-times me-1"></i>제거
                        </button>
                    </div>
                </div>
            </div>
        `;
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
     * 초기 코드 데이터 로드 (PRD, CR 등) - 안전한 방식으로 수정
     */
    async loadInitialCodeData() {
        try {
            console.log('🔄 초기 코드 데이터 로드 시작');
            
            // 이미 HTML에서 로드된 데이터가 있는지 확인
            const prdSelect = $('#prod_code_seq');
            const colorSelects = $('.color-code');
            
            // PRD 품목 코드가 이미 있는지 확인
            if (prdSelect.find('option').length <= 1) {
                console.log('⚠️ PRD 품목 코드가 비어있음 - 서버에서 로드된 데이터 사용');
                // 필요시 여기에 추가 로직
            } else {
                console.log('✅ PRD 품목 코드 이미 로드됨:', prdSelect.find('option').length - 1 + '개');
            }
            
            // CR 색상 코드가 이미 있는지 확인
            if (colorSelects.length > 0 && colorSelects.first().find('option').length <= 1) {
                console.log('⚠️ CR 색상 코드가 비어있음 - 서버에서 로드된 데이터 사용');
                // 필요시 여기에 추가 로직
            } else {
                console.log('✅ CR 색상 코드 이미 로드됨');
            }
            
            console.log('✅ 초기 코드 데이터 로드 완료');
            
        } catch (error) {
            console.error('❌ 초기 코드 데이터 로드 실패:', error);
            // 에러가 발생해도 모달은 열리도록 함
            console.log('🔄 에러 무시하고 모달 열기 계속 진행');
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