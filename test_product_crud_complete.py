#!/usr/bin/env python3
"""
상품 관리 CRUD 전체 테스트
- 타입2 저장 확인
- 16자리 자사코드 생성
- 상품 등록/수정/삭제/조회
- 페이징 기능
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"

class ProductCRUDTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name, success, message="", data=None):
        """테스트 결과 로깅"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
    
    def test_1_page_load(self):
        """1. 상품 관리 페이지 로드 테스트"""
        try:
            response = self.session.get(f"{BASE_URL}/product/")
            if response.status_code == 200:
                self.log_test("페이지 로드", True, f"상태코드: {response.status_code}")
                return True
            else:
                self.log_test("페이지 로드", False, f"상태코드: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("페이지 로드", False, f"오류: {str(e)}")
            return False
    
    def test_2_get_codes(self):
        """2. 코드 정보 조회 테스트"""
        try:
            response = self.session.get(f"{BASE_URL}/product/api/get-codes")
            if response.status_code == 200:
                data = response.json()
                brands_count = len(data.get('brands', []))
                colors_count = len(data.get('colors', []))
                self.log_test("코드 조회", True, f"브랜드: {brands_count}개, 색상: {colors_count}개")
                return data
            else:
                self.log_test("코드 조회", False, f"상태코드: {response.status_code}")
                return None
        except Exception as e:
            self.log_test("코드 조회", False, f"오류: {str(e)}")
            return None
    
    def test_3_generate_std_code(self):
        """3. 자사코드 생성 테스트 (타입2 포함)"""
        try:
            # 자사코드 생성 API 호출 (타입2 포함)
            payload = {
                'brandSeq': 1,      # 브랜드
                'prodGroupSeq': 1,  # 제품구분  
                'prodCodeSeq': 1,   # 품목
                'prodTypeSeq': 1,   # 타입
                'yearSeq': 1,       # 년도
                'colorSeq': 1,      # 색상
                'type2Seq': 1       # 🔥 타입2 추가
            }
            
            response = self.session.post(f"{BASE_URL}/product/api/generate-code", json=payload)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    generated_code = data.get('generated_code')
                    components = data.get('components', {})
                    type2_value = components.get('type2', '00')
                    
                    self.log_test("자사코드 생성", True, 
                                f"코드: {generated_code} (16자리: {len(generated_code) == 16}), 타입2: {type2_value}")
                    return generated_code
                else:
                    self.log_test("자사코드 생성", False, data.get('message'))
            else:
                self.log_test("자사코드 생성", False, f"상태코드: {response.status_code}")
        except Exception as e:
            self.log_test("자사코드 생성", False, f"오류: {str(e)}")
        return None
    
    def test_4_create_product(self, std_code):
        """4. 상품 등록 테스트"""
        try:
            # 제품 모델 데이터 (타입2 포함)
            product_models = [{
                'name': f'테스트상품_{int(time.time())}',
                'std_code': std_code,
                'color_code': 'BLK',
                'prod_type2_code_seq': 1,  # 🔥 타입2 seq 포함
                'douzone_code': 'TEST001',
                'erpia_code': 'TEST002',
                'official_cost': 10000,
                'consumer_price': 15000,
                'operation_price': 12000,
                'ans_value': 15,
                'additional_price': 0,
                'stock_quantity': 100
            }]
            
            payload = {
                'product_name': f'테스트상품_{int(time.time())}',
                'company_id': 1,
                'brand_code_seq': 1,
                'prod_group_code_seq': 1,
                'prod_type_code_seq': 1,
                'year_code_seq': 1,
                'price': 15000,
                'description': '타입2 테스트용 상품',
                'use_yn': 'Y',
                'product_models': json.dumps(product_models)
            }
            
            response = self.session.post(f"{BASE_URL}/product/api/create", data=payload)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    product_id = data.get('product', {}).get('id')
                    self.log_test("상품 등록", True, f"상품 ID: {product_id}")
                    return product_id
                else:
                    self.log_test("상품 등록", False, data.get('message'))
            else:
                self.log_test("상품 등록", False, f"상태코드: {response.status_code}")
        except Exception as e:
            self.log_test("상품 등록", False, f"오류: {str(e)}")
        return None
    
    def test_5_read_product(self, product_id):
        """5. 상품 조회 테스트"""
        try:
            response = self.session.get(f"{BASE_URL}/product/api/get/{product_id}")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    product = data.get('product')
                    models = data.get('product_models', [])
                    
                    # 타입2 저장 확인
                    type2_stored = False
                    for model in models:
                        if model.get('prod_type2_code'):
                            type2_stored = True
                            break
                    
                    self.log_test("상품 조회", True, 
                                f"상품명: {product.get('product_name')}, 모델수: {len(models)}개, 타입2저장: {type2_stored}")
                    return data
                else:
                    self.log_test("상품 조회", False, data.get('message'))
            else:
                self.log_test("상품 조회", False, f"상태코드: {response.status_code}")
        except Exception as e:
            self.log_test("상품 조회", False, f"오류: {str(e)}")
        return None
    
    def test_6_list_products(self):
        """6. 상품 목록 조회 및 페이징 테스트"""
        try:
            # 첫 페이지 조회
            response = self.session.get(f"{BASE_URL}/product/api/list?page=1&per_page=10")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    products = data.get('data', [])
                    pagination = data.get('pagination', {})
                    stats = data.get('stats', {})
                    
                    self.log_test("상품 목록", True, 
                                f"상품수: {len(products)}개, 총 페이지: {pagination.get('pages', 0)}, " +
                                f"전체: {stats.get('total_products', 0)}개, 자사코드: {stats.get('std_code_products', 0)}개")
                    return True
                else:
                    self.log_test("상품 목록", False, data.get('message'))
            else:
                self.log_test("상품 목록", False, f"상태코드: {response.status_code}")
        except Exception as e:
            self.log_test("상품 목록", False, f"오류: {str(e)}")
        return False
    
    def test_7_update_product(self, product_id):
        """7. 상품 수정 테스트"""
        try:
            payload = {
                'product_name': f'수정된_테스트상품_{int(time.time())}',
                'brand_code_seq': 1,
                'category_code_seq': 1,
                'type_code_seq': 1,
                'year_code_seq': 1,
                'price': 20000,
                'description': '타입2 포함 수정 테스트',
                'is_active': 'true'
            }
            
            response = self.session.put(f"{BASE_URL}/product/api/update/{product_id}", data=payload)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log_test("상품 수정", True, "상품 정보 수정 성공")
                    return True
                else:
                    self.log_test("상품 수정", False, data.get('message'))
            else:
                self.log_test("상품 수정", False, f"상태코드: {response.status_code}")
        except Exception as e:
            self.log_test("상품 수정", False, f"오류: {str(e)}")
        return False
    
    def test_8_delete_product(self, product_id):
        """8. 상품 삭제 테스트"""
        try:
            response = self.session.delete(f"{BASE_URL}/product/api/delete/{product_id}")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log_test("상품 삭제", True, "상품 삭제 성공")
                    return True
                else:
                    self.log_test("상품 삭제", False, data.get('message'))
            else:
                self.log_test("상품 삭제", False, f"상태코드: {response.status_code}")
        except Exception as e:
            self.log_test("상품 삭제", False, f"오류: {str(e)}")
        return False
    
    def run_all_tests(self):
        """전체 테스트 실행"""
        print("🚀 상품 관리 CRUD 전체 테스트 시작")
        print("=" * 60)
        
        # 1. 페이지 로드
        if not self.test_1_page_load():
            print("❌ 페이지 로드 실패 - 테스트 중단")
            return
        
        # 2. 코드 조회
        codes = self.test_2_get_codes()
        if not codes:
            print("❌ 코드 조회 실패 - 테스트 중단")
            return
        
        # 3. 자사코드 생성 (타입2 포함)
        std_code = self.test_3_generate_std_code()
        if not std_code:
            print("❌ 자사코드 생성 실패 - 테스트 중단")
            return
        
        # 4. 상품 등록
        product_id = self.test_4_create_product(std_code)
        if not product_id:
            print("❌ 상품 등록 실패 - 테스트 중단")
            return
        
        # 5. 상품 조회 (타입2 저장 확인)
        product_data = self.test_5_read_product(product_id)
        if not product_data:
            print("❌ 상품 조회 실패")
        
        # 6. 상품 목록 및 페이징
        self.test_6_list_products()
        
        # 7. 상품 수정
        self.test_7_update_product(product_id)
        
        # 8. 상품 삭제
        self.test_8_delete_product(product_id)
        
        # 결과 요약
        print("\n" + "=" * 60)
        print("📊 테스트 결과 요약")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"총 테스트: {total_tests}개")
        print(f"성공: {passed_tests}개")
        print(f"실패: {failed_tests}개")
        print(f"성공률: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print("\n❌ 실패한 테스트:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")
        
        return failed_tests == 0

if __name__ == '__main__':
    tester = ProductCRUDTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 모든 테스트 통과! 상품 관리 시스템이 정상 작동합니다.")
    else:
        print("\n⚠️ 일부 테스트 실패. 로그를 확인해주세요.") 