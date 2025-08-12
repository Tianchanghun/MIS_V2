#!/usr/bin/env python3
"""
간단한 API 테스트
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_apis():
    try:
        # 1. 코드 조회 API
        print("1. 코드 조회 API 테스트...")
        response = requests.get(f"{BASE_URL}/product/api/get-codes")
        print(f"응답 코드: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"브랜드: {len(data.get('brands', []))}개")
            print(f"색상: {len(data.get('colors', []))}개")
        else:
            print(f"응답 내용: {response.text[:200]}")
        
        # 2. 자사코드 생성 API
        print("\n2. 자사코드 생성 API 테스트...")
        payload = {
            'brandSeq': 1,
            'prodGroupSeq': 1,
            'prodCodeSeq': 1,
            'prodTypeSeq': 1,
            'yearSeq': 1,
            'colorSeq': 1,
            'type2Seq': 1
        }
        response = requests.post(f"{BASE_URL}/product/api/generate-code", json=payload)
        print(f"응답 코드: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"생성된 코드: {data.get('generated_code')}")
                print(f"타입2: {data.get('components', {}).get('type2')}")
            else:
                print(f"실패: {data.get('message')}")
        else:
            print(f"응답 내용: {response.text[:200]}")
            
        # 3. 상품 목록 API
        print("\n3. 상품 목록 API 테스트...")
        response = requests.get(f"{BASE_URL}/product/api/list?page=1&per_page=5")
        print(f"응답 코드: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"상품 수: {len(data.get('data', []))}개")
                print(f"전체: {data.get('stats', {}).get('total_products', 0)}개")
            else:
                print(f"실패: {data.get('message')}")
        else:
            print(f"응답 내용: {response.text[:200]}")
            
    except Exception as e:
        print(f"테스트 오류: {e}")

if __name__ == '__main__':
    test_apis() 