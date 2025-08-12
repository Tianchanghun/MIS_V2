#!/usr/bin/env python3
"""
상품 등록 API 직접 테스트 및 디버깅
"""

import requests
import json

def test_create_product():
    """상품 등록 직접 테스트"""
    
    # 간단한 제품 모델 데이터
    product_models = [{
        'name': 'Simple_Test_Product',
        'std_code': 'JP00TP00TJ0025BLK',  # 16자리 코드
        'additional_price': 0,
        'stock_quantity': 100
    }]
    
    # 최소한의 데이터로 테스트
    payload = {
        'product_name': 'Simple_Test_Product',
        'company_id': '1',
        'brand_code_seq': '1',
        'prod_group_code_seq': '1',
        'prod_type_code_seq': '1',
        'year_code_seq': '1',
        'price': '15000',
        'description': 'Simple test product',
        'use_yn': 'Y',
        'product_models': json.dumps(product_models)
    }
    
    try:
        print("🔧 상품 등록 테스트 중...")
        print(f"페이로드: {payload}")
        
        response = requests.post("http://127.0.0.1:5000/product/api/create", data=payload)
        
        print(f"응답 코드: {response.status_code}")
        print(f"응답 헤더: {dict(response.headers)}")
        print(f"응답 내용: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ 상품 등록 성공!")
                print(f"상품 ID: {data.get('product', {}).get('id')}")
            else:
                print(f"❌ 상품 등록 실패: {data.get('message')}")
        else:
            print(f"❌ HTTP 에러: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 예외 발생: {e}")

if __name__ == '__main__':
    test_create_product() 