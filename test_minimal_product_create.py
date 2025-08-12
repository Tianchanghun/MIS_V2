#!/usr/bin/env python3
"""
최소한의 상품 등록 테스트
"""

import requests
import json

def test_minimal_create():
    """최소한의 데이터로 상품 등록"""
    
    # 제품 모델 없이 기본 상품만 등록
    payload = {
        'product_name': 'Minimal_Test_Product',
        'company_id': '1',
        'brand_code_seq': '1',
        'prod_group_code_seq': '1',
        'prod_type_code_seq': '1',
        'year_code_seq': '1',
        'price': '10000',
        'description': 'Minimal test',
        'use_yn': 'Y'
        # product_models 제외
    }
    
    try:
        print("🔧 최소한의 상품 등록 테스트...")
        response = requests.post("http://127.0.0.1:5000/product/api/create", data=payload)
        
        print(f"응답 코드: {response.status_code}")
        print(f"응답 내용: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ 기본 상품 등록 성공!")
            else:
                print(f"❌ 등록 실패: {data.get('message')}")
        
    except Exception as e:
        print(f"❌ 예외: {e}")

if __name__ == '__main__':
    test_minimal_create() 