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
                    typeSelect.append(`<option value="${type.seq}" data-code="${type.code}">${type.code_name} (${type.code})</option>`);
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
        
            console.log('📝 상품 등록 모달 열기');
            
            // 🔧 모달 제목을 등록 모드로 변경
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
            
            console.log('📝 상품 수정 모달 열기 - ID:', productId);
            
            // 🔧 모달 제목을 수정 모드로 변경
            $('#productModalLabel').text('상품 수정');
            $('#isEditMode').val('true');
            $('#saveProductBtn').html('<i class="fas fa-save me-1"></i>수정');
            
            // 상품 정보 로드
            UIHelper.showLoading('상품 정보를 불러오는 중...');
            
            const response = await AjaxHelper.get(`/product/api/get/${productId}`);
            
            console.log('📥 API 응답:', response);
            
            if (response.success && response.product) {
                await this.populateForm(response.product, response.product_models);
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
        
        // 🔥 백엔드가 요구하는 필수 필드들
        formData.append('product_name', $('#product_name').val() || '');
        formData.append('price', $('#price').val() || '0');
        formData.append('description', $('#description').val() || '');
        
        // 🔥 백엔드가 기대하는 코드 필드들 (실제 DB 필드명 사용)
        formData.append('brand_code_seq', $('#brand_code_seq').val() || '');
        formData.append('prod_group_code_seq', $('#prod_group_code_seq').val() || '');  // 제품구분
        formData.append('prod_type_code_seq', $('#prod_type_code_seq').val() || '');    // 타입
        formData.append('year_code_seq', $('#year_code_seq').val() || '');
        
        // 사용여부 (use_yn)
        const useYn = $('#use_yn').val();
        formData.append('use_yn', useYn || 'Y');
        
        // 회사 정보
        formData.append('company_id', '1');
        
        // 🔥 제품 모델 데이터 수집 (새로운 필드들 포함)
        const productModels = [];
        $('.product-model-item').each(function(index) {
            const modelData = {
                // 기본 필드들
                color_code: $(this).find('.color-code').val(),
                name: $(this).find('.product-model-name').val() || $('#product_name').val(),
                std_code: $(this).find('.std-product-code').val(),
                
                // 🔥 코드 관리 필드들
                douzone_code: $(this).find('.douzone-code').val(),
                erpia_code: $(this).find('.erpia-code').val(),
                
                // 🔥 가격 관리 필드들
                official_cost: $(this).find('.official-cost').val(),
                consumer_price: $(this).find('.consumer-price').val(),
                operation_price: $(this).find('.operation-price').val(),
                
                // 🔥 추가 관리 필드들
                ans_value: $(this).find('.ans-value').val(),
                detail_brand_code_seq: $(this).find('.detail-brand-code').val(),
                color_detail_code_seq: $(this).find('.color-detail-code').val(),
                
                // 🔥 새로운 분류 체계 필드들
                product_division_code_seq: $(this).find('.product_division_code_seq').val(),
                product_group_code_seq: $(this).find('.product-group-code').val(),
                item_code_seq: $(this).find('.item-code').val(),
                item_detail_code_seq: $(this).find('.item-detail-code').val(),
                product_type_category_code_seq: $(this).find('.product-type-category-code').val(),
                
                // 기본값들
                additional_price: 0,
                stock_quantity: 0
            };
            
            // 필수 필드가 있는 경우만 추가
            if (modelData.color_code || modelData.std_code) {
                productModels.push(modelData);
            }
        });
        
        // 제품 모델 데이터를 JSON으로 변환하여 추가
        if (productModels.length > 0) {
            formData.append('product_models', JSON.stringify(productModels));
            console.log('📦 제품 모델 데이터:', productModels);
        } else {
            console.warn('⚠️ 제품 모델 데이터가 없습니다');
        }
        
        console.log('📦 폼 데이터 준비 완료');
        console.log('📋 전송 데이터:', {
            product_name: formData.get('product_name'),
            brand_code_seq: formData.get('brand_code_seq'),
            prod_group_code_seq: formData.get('prod_group_code_seq'),
            prod_type_code_seq: formData.get('prod_type_code_seq'),
            year_code_seq: formData.get('year_code_seq'),
            price: formData.get('price'),
            product_models_count: productModels.length
        });
        
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
     * 폼에 데이터 채우기 (강제 selected 적용 + 자사코드 파싱)
     */
    async populateForm(productData, productModels) {
        console.log('📝 상품 수정 폼 채우기:', productData);
        console.log('📦 상품 모델 데이터:', productModels);
        
        // 기본 필드들
        $('#productId').val(productData.id);
        $('#product_name').val(productData.product_name);
        $('#price').val(productData.price);
        $('#description').val(productData.description);
        
        // 🔥 자사코드 파싱을 통한 코드 정보 추출
        let parsedCodes = {};
        if (productModels && productModels.length > 0) {
            const firstModel = productModels[0];
            if (firstModel.std_div_prod_code && firstModel.std_div_prod_code.length >= 16) {
                const stdCode = firstModel.std_div_prod_code;
                parsedCodes = {
                    brand: stdCode.substring(0, 2),      // RY
                    divType: stdCode.substring(2, 3),    // 3
                    prodGroup: stdCode.substring(3, 5),  // GT (수정됨)
                    prodType: stdCode.substring(5, 7),   // TR
                    prod: stdCode.substring(7, 9),       // TJ
                    type2: stdCode.substring(9, 11),     // 00
                    year: stdCode.substring(11, 13),     // 25
                    color: stdCode.substring(13, 16)     // BLK
                };
                console.log('🔧 자사코드 파싱 결과:', stdCode, '→', parsedCodes);
            }
        }
        
        // 🔥 1단계: 회사 설정 (즉시)
        if (productData.company_id) {
            $('#company_id').val(productData.company_id).trigger('change');
            console.log('✅ 회사 설정:', productData.company_id);
        }
        
        // 🔥 2단계: 사용여부 설정 (즉시)
        const useYnValue = productData.is_active ? 'Y' : 'N';
        $('#use_yn').val(useYnValue).trigger('change');
        console.log('✅ 사용여부 설정:', useYnValue);
        
        // 🔥 3단계: 브랜드 코드 설정 (100ms 지연) - 파싱된 코드값 활용
        setTimeout(() => {
        if (productData.brand_code_seq) {
                this.setSelectValue('brand_code_seq', productData.brand_code_seq, '브랜드', parsedCodes.brand);
        }
        }, 100);
        
        // 🔥 4단계: 제품구분 설정 (200ms 지연) - 파싱된 코드값 활용
        setTimeout(() => {
        if (productData.category_code_seq) {
                this.setSelectValue('prod_group_code_seq', productData.category_code_seq, '제품구분', parsedCodes.prodGroup);
            }
        }, 200);
        
        // 🔥 5단계: 품목 설정 (300ms 지연) - 파싱된 코드값 활용
        setTimeout(() => {
            if (productData.category_code_seq) {
                this.setSelectValue('prod_code_seq', productData.category_code_seq, '품목', parsedCodes.prod);
            }
        }, 300);
        
        // 🔥 6단계: 타입 설정 (500ms 지연) - 품목 로드 후 파싱된 코드값 활용
        setTimeout(() => {
                if (productData.type_code_seq) {
                // 타입 옵션이 로드되었는지 확인
                const typeOptions = $('#prod_type_code_seq option');
                if (typeOptions.length <= 1) {
                    console.log('⚠️ 타입 옵션이 로드되지 않았음. 품목 기준으로 다시 로드 시도');
                    
                    if (productData.category_code_seq) {
                        // 품목 기준으로 타입 옵션 다시 로드
                        $.get(`/product/api/get-types-by-product-seq/${productData.category_code_seq}`)
                            .done((response) => {
                                if (response.success && response.types) {
                                    const typeSelect = $('#prod_type_code_seq');
                                    typeSelect.empty().append('<option value="">타입을 선택하세요</option>');
                                    
                                    response.types.forEach(type => {
                                        typeSelect.append(`<option value="${type.seq}" data-code="${type.code}">${type.code_name} (${type.code})</option>`);
                                    });
                                    
                                    console.log('✅ 타입 옵션 로드 완료:', response.types.length + '개');
                                }
                                
                                // 로드 후 다시 시도 (파싱된 코드값 활용)
                                setTimeout(() => {
                                    this.setSelectValue('prod_type_code_seq', productData.type_code_seq, '타입', parsedCodes.prodType);
                                }, 200);
                            });
                    }
                } else {
                    this.setSelectValue('prod_type_code_seq', productData.type_code_seq, '타입', parsedCodes.prodType);
                }
            }
        }, 500);
        
        // 🔥 7단계: 년식 설정 (400ms 지연) - 파싱된 코드값 활용
        setTimeout(() => {
        if (productData.year_code_seq) {
                this.setSelectValue('year_code_seq', productData.year_code_seq, '년식', parsedCodes.year);
            }
        }, 400);
        
        // 🔥 8단계: 상품 모델 정보 로드
        if (productModels) {
            setTimeout(() => {
                this.loadExistingProductModels(productData.id, productModels);
            }, 600);
        }
        
        console.log('✅ 폼 채우기 완료 (단계별 지연 적용)');
    }
    
    /**
     * Select 박스 값 설정 헬퍼 함수 (강화 버전 - 코드 기반 매칭 추가)
     */
    setSelectValue(selectId, value, label, codeValue = null) {
        const selectElement = $(`#${selectId}`);
        const stringValue = String(value);
        
        console.log(`🔧 ${label} 설정 시도:`, stringValue, codeValue ? `(코드: ${codeValue})` : '');
        
        // 옵션 존재 확인
        const options = selectElement.find('option');
        let targetOption = selectElement.find(`option[value="${stringValue}"]`);
        
        // 🔥 코드값으로도 매칭 시도
        if (targetOption.length === 0 && codeValue) {
            targetOption = selectElement.find(`option[data-code="${codeValue}"]`);
            if (targetOption.length > 0) {
                console.log(`✅ ${label} 코드값으로 매칭 성공:`, codeValue, '→', targetOption.val());
                stringValue = targetOption.val();
            }
        }
        
        console.log(`📋 ${label} 옵션 개수:`, options.length);
        console.log(`🎯 ${label} 대상 옵션:`, targetOption.length > 0 ? targetOption.text() : '없음');
        
        if (targetOption.length === 0) {
            console.error(`❌ ${label} 옵션에서 값을 찾을 수 없습니다:`, stringValue, codeValue ? `(코드: ${codeValue})` : '');
            return false;
        }
        
        // 값 설정 및 트리거
        selectElement.val(stringValue).trigger('change');
        
        // 재시도 메커니즘 (100ms 후)
        setTimeout(() => {
            if (selectElement.val() !== stringValue) {
                console.log(`⚠️ ${label} 재시도`);
                selectElement.val(stringValue);
                selectElement.find(`option[value="${stringValue}"]`).prop('selected', true);
                selectElement.trigger('change');
                } else {
                console.log(`✅ ${label} 설정 완료:`, stringValue);
            }
        }, 100);
        
        return true;
    }
    
    /**
     * 기존 상품 모델들 로딩 (색상 선택 포함)
     */
    loadExistingProductModels(productId, productModels) {
        console.log('📦 기존 상품 모델 로딩:', productModels.length + '개');
        
        const container = $('#productModelsContainer');
        container.empty();
        
        productModels.forEach((model, index) => {
            const modelHtml = this.createProductModelHTML(model, index);
            container.append(modelHtml);
            
            // 🔥 색상 선택 설정 (자사코드 기반)
            setTimeout(() => {
                const colorSelect = container.find(`.product-model-item:eq(${index}) .color-code`);
                
                // 자사코드에서 색상 코드 파싱
                if (model.std_div_prod_code && model.std_div_prod_code.length >= 16) {
                    const colorCode = model.std_div_prod_code.substring(13, 16); // 마지막 3자리
                    console.log(`🎨 모델 ${index} 색상 설정:`, model.color_code, `(자사코드: ${colorCode})`);
                    
                    // 1. color_code 값으로 직접 매칭
                    if (model.color_code) {
                        // data-code 속성으로 찾기
                        let colorOption = colorSelect.find(`option[data-code="${model.color_code}"]`);
                        if (colorOption.length === 0) {
                            // 파싱된 색상 코드로 찾기
                            colorOption = colorSelect.find(`option[data-code="${colorCode}"]`);
                        }
                        
                        if (colorOption.length > 0) {
                            colorSelect.val(colorOption.val()).trigger('change');
                            console.log(`✅ 모델 ${index} 색상 설정 완료:`, colorOption.text());
            } else {
                            console.warn(`⚠️ 모델 ${index} 색상 코드를 찾을 수 없음:`, model.color_code, colorCode);
                        }
                    }
                }
                
                // 2. 제품명 설정
                if (model.product_name) {
                    container.find(`.product-model-item:eq(${index}) .product-model-name`).val(model.product_name);
                }
                
                // 3. 자사코드 설정
                if (model.std_div_prod_code) {
                    container.find(`.product-model-item:eq(${index}) .std-product-code`).val(model.std_div_prod_code);
                }
                
            }, 200 + (index * 100)); // 순차적으로 100ms씩 지연
        });
        
        console.log('✅ 상품 모델 로딩 완료');
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
        
        // 🔥 브랜드 옵션 HTML 생성 (세부브랜드용)
        let brandOptionsHtml = '<option value="">브랜드를 선택하세요</option>';
        if (window.brandCodesData) {
            window.brandCodesData.forEach(brand => {
                const isSelected = model.detail_brand_code_seq && model.detail_brand_code_seq == brand.seq ? 'selected' : '';
                brandOptionsHtml += `<option value="${brand.seq}" ${isSelected}>${brand.code_name} (${brand.code})</option>`;
            });
        }
        
        // 🔥 새로운 분류 체계 옵션들 생성
        let productGroupOptionsHtml = '<option value="">제품군을 선택하세요</option>';
        if (window.productGroupCodesData) {
            window.productGroupCodesData.forEach(group => {
                const isSelected = model.category1_code_seq && model.category1_code_seq == group.seq ? 'selected' : '';
                productGroupOptionsHtml += `<option value="${group.seq}" ${isSelected}>${group.code_name}</option>`;
            });
        }
        
        let itemOptionsHtml = '<option value="">아이템을 선택하세요</option>';
        if (window.itemCodesData) {
            window.itemCodesData.forEach(item => {
                const isSelected = model.category3_code_seq && model.category3_code_seq == item.seq ? 'selected' : '';
                itemOptionsHtml += `<option value="${item.seq}" ${isSelected}>${item.code_name}</option>`;
            });
        }
        
        let itemDetailOptionsHtml = '<option value="">아이템상세를 선택하세요</option>';
        if (window.itemDetailCodesData) {
            window.itemDetailCodesData.forEach(detail => {
                const isSelected = model.category4_code_seq && model.category4_code_seq == detail.seq ? 'selected' : '';
                itemDetailOptionsHtml += `<option value="${detail.seq}" ${isSelected}>${detail.code_name}</option>`;
            });
        }
        
        let productTypeOptionsHtml = '<option value="">제품타입을 선택하세요</option>';
        if (window.productTypeCategoryCodesData) {
            window.productTypeCategoryCodesData.forEach(type => {
                const isSelected = model.category5_code_seq && model.category5_code_seq == type.seq ? 'selected' : '';
                productTypeOptionsHtml += `<option value="${type.seq}" ${isSelected}>${type.code_name}</option>`;
            });
        }
        
        // 🔥 ANS 옵션 생성 (1~30)
        let ansOptionsHtml = '<option value="">ANS를 선택하세요</option>';
        for (let i = 1; i <= 30; i++) {
            const isSelected = model.ans_value && model.ans_value == i ? 'selected' : '';
            ansOptionsHtml += `<option value="${i}" ${isSelected}>${i}</option>`;
        }
        
        // 🔥 색상별(상세) 옵션 HTML 생성 (새로 추가된 CLD 그룹)
        let colorDetailOptionsHtml = '<option value="">색상별(상세)를 선택하세요</option>';
        if (window.colorDetailCodesData) {
            window.colorDetailCodesData.forEach(colorDetail => {
                const isSelected = model.color_detail_code_seq && model.color_detail_code_seq == colorDetail.seq ? 'selected' : '';
                colorDetailOptionsHtml += `<option value="${colorDetail.seq}" ${isSelected}>${colorDetail.code_name} (${colorDetail.code})</option>`;
            });
        }
        
        // 🔥 세부브랜드(CL2) 옵션 HTML 생성
        let detailBrandOptionsHtml = '<option value="">세부브랜드를 선택하세요</option>';
        if (window.detailBrandCodesData) {
            window.detailBrandCodesData.forEach(detailBrand => {
                const isSelected = model.detail_brand_code_seq && model.detail_brand_code_seq == detailBrand.seq ? 'selected' : '';
                detailBrandOptionsHtml += `<option value="${detailBrand.seq}" ${isSelected}>${detailBrand.code_name} (${detailBrand.code})</option>`;
            });
        }
        
        // 🔥 제품구분(PD) 옵션 HTML 생성
        let productDivisionOptionsHtml = '<option value="">제품구분을 선택하세요</option>';
        if (window.productDivisionCodesData) {
            window.productDivisionCodesData.forEach(division => {
                const isSelected = model.product_division_code_seq && model.product_division_code_seq == division.seq ? 'selected' : '';
                productDivisionOptionsHtml += `<option value="${division.seq}" ${isSelected}>${division.code_name} (${division.code})</option>`;
            });
        }
        
        return `
            <div class="product-model-item border p-3 mb-3" data-index="${index}" data-model-id="${model.id}">
                <h6 class="text-primary mb-3">
                    <i class="fas fa-box me-1"></i>제품 모델 #${index + 1}
                    <small class="text-muted">(tbl_Product_DTL)</small>
                </h6>

                <!-- 기본 정보 -->
                <div class="row">
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">
                                <i class="fas fa-palette me-1"></i>색상 (CR) <span class="required">*</span>
                            </label>
                            <select class="form-select color-code" name="color_code[]" required>
                                ${colorOptionsHtml}
                            </select>
                            <small class="text-muted">CR 코드 그룹에서 관리</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">제품명 (색상별)</label>
                            <input type="text" class="form-control product-model-name" 
                                   name="product_model_name[]" 
                                   value="${model.product_name || ''}"
                                   placeholder="색상별 제품명 (선택사항)">
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">16자리 자사코드</label>
                            <div class="input-group">
                                <input type="text" class="form-control std-product-code" 
                                       name="std_product_code[]" 
                                       value="${model.std_div_prod_code || ''}"
                                       placeholder="자동생성됨" readonly>
                                <button type="button" class="btn btn-primary btn-generate-code" title="선택된 코드 기준으로 생성">
                                    <i class="fas fa-magic"></i> 자동생성
                                </button>
                            </div>
                            <small class="text-muted">tbl_Product_DTL - 16자리 레거시 형식</small>
                        </div>
                    </div>
                </div>
                
                <!-- 🔥 코드 관리 필드 -->
                <div class="row mt-3">
                    <div class="col-12">
                        <h6 class="text-secondary">
                            <i class="fas fa-code me-1"></i>코드 관리
                        </h6>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">더존코드 (20자)</label>
                            <input type="text" class="form-control douzone-code" 
                                   name="douzone_code[]" maxlength="20"
                                   value="${model.douzone_code || ''}"
                                   placeholder="더존 연동 코드">
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">ERPIA코드 (13자)</label>
                            <input type="text" class="form-control erpia-code" 
                                   name="erpia_code[]" maxlength="13"
                                   value="${model.erpia_code || ''}"
                                   placeholder="ERPIA 연동 코드">
                        </div>
                    </div>
                </div>
                
                <!-- 🔥 가격 관리 필드 -->
                <div class="row">
                    <div class="col-12">
                        <h6 class="text-secondary">
                            <i class="fas fa-won-sign me-1"></i>가격 관리
                        </h6>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">공식원가</label>
                            <div class="input-group">
                                <span class="input-group-text">₩</span>
                                <input type="number" class="form-control official-cost" 
                                       name="official_cost[]" min="0"
                                       value="${model.official_cost || 0}"
                                       placeholder="0">
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">소비자가</label>
                            <div class="input-group">
                                <span class="input-group-text">₩</span>
                                <input type="number" class="form-control consumer-price" 
                                       name="consumer_price[]" min="0"
                                       value="${model.consumer_price || 0}"
                                       placeholder="0">
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">운영가</label>
                            <div class="input-group">
                                <span class="input-group-text">₩</span>
                                <input type="number" class="form-control operation-price" 
                                       name="operation_price[]" min="0"
                                       value="${model.operation_price || 0}"
                                       placeholder="0">
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- 🔥 추가 관리 필드들 (ANS, 세부브랜드, 색상별) -->
                <div class="row">
                    <div class="col-12">
                        <h6 class="text-secondary">
                            <i class="fas fa-cogs me-1"></i>추가 관리
                        </h6>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">ANS</label>
                            <select class="form-select ans-value" name="ans_value[]">
                                ${ansOptionsHtml}
                            </select>
                            <small class="text-muted">1~30 값 선택</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">세부브랜드</label>
                            <select class="form-select detail-brand-code" name="detail_brand_code_seq[]">
                                ${detailBrandOptionsHtml}
                            </select>
                            <small class="text-muted">브랜드 코드 참조</small>
                        </div>
                    </div>
                </div>
                
                <!-- 🔥 새로운 분류 체계 -->
                <div class="row">
                    <div class="col-12">
                        <h6 class="text-secondary">
                            <i class="fas fa-sitemap me-1"></i>분류 관리 (Excel 기반)
                        </h6>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">제품군</label>
                            <select class="form-select product-group-code" name="product_group_code_seq[]">
                                ${productGroupOptionsHtml}
                            </select>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">아이템별</label>
                            <select class="form-select item-code" name="item_code_seq[]">
                                ${itemOptionsHtml}
                            </select>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">아이템상세</label>
                            <select class="form-select item-detail-code" name="item_detail_code_seq[]">
                                ${itemDetailOptionsHtml}
                            </select>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">제품구분</label>
                            <select class="form-select product_division_code_seq" name="product_division_code_seq[]">
                                ${productDivisionOptionsHtml}
                            </select>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">제품타입</label>
                            <select class="form-select product-type-category-code" name="product_type_category_code_seq[]">
                                ${productTypeOptionsHtml}
                            </select>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">🔥 색상별(상세)</label>
                            <select class="form-select color-detail-code" name="color_detail_code_seq[]">
                                ${colorDetailOptionsHtml}
                            </select>
                            <small class="text-muted">235개 세부 색상 선택 가능</small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <small class="text-info">
                            <i class="fas fa-info-circle me-1"></i>
                            Excel에서 가져온 분류 체계입니다.
                        </small>
                    </div>
                    <div class="col-md-3">
                        <button type="button" class="btn btn-outline-danger btn-sm btn-remove-model w-100">
                            <i class="fas fa-times me-1"></i>이 색상 모델 제거
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