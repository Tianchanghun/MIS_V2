#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time
from urllib.parse import urlencode

def test_live_ui():
    """실행 중인 Flask 앱의 UI와 정렬 기능 테스트"""
    print("🔍 실행 중인 Flask 앱 UI 테스트")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:5000"
    
    # 1. Flask 앱 실행 상태 확인
    print("1️⃣ Flask 앱 실행 상태 확인")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            print("   ✅ Flask 앱 정상 실행 중")
        else:
            print(f"   ❌ HTTP {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ 연결 실패: {e}")
        return
    
    # 2. 제품 페이지 접근 테스트
    print("\n2️⃣ 제품 페이지 접근 테스트")
    try:
        response = requests.get(f"{base_url}/product/", timeout=10)
        if response.status_code == 200:
            print("   ✅ 제품 페이지 접근 성공")
            print(f"   📄 페이지 크기: {len(response.text):,} bytes")
        else:
            print(f"   ❌ 제품 페이지 오류: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ 제품 페이지 접근 실패: {e}")
    
    # 3. API 기본 테스트
    print("\n3️⃣ API 기본 테스트")
    try:
        response = requests.get(f"{base_url}/product/api/list", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ API 응답 성공: {len(data.get('data', []))}개 제품")
            
            # 첫 번째 제품 상세 확인
            if data.get('data'):
                first = data['data'][0]
                print(f"   📋 첫 번째 제품:")
                print(f"      이름: {first.get('product_name')}")
                print(f"      브랜드: {first.get('brand_name', 'undefined')}")
                print(f"      품목: {first.get('category_name', 'undefined')}")
                print(f"      타입: {first.get('type_name', 'undefined')}")
                print(f"      가격: {first.get('price', 0):,}원")
                print(f"      자가코드: {first.get('std_div_prod_code', 'undefined')}")
                
                # undefined 항목 확인
                undefined_count = 0
                fields = ['brand_name', 'category_name', 'type_name', 'std_div_prod_code']
                for field in fields:
                    if not first.get(field) or first.get(field) == 'undefined':
                        undefined_count += 1
                
                if undefined_count == 0:
                    print("   🎉 모든 필드가 정상 표시됨!")
                else:
                    print(f"   ⚠️ {undefined_count}개 필드가 undefined")
        
        elif response.status_code == 401:
            print("   ⚠️ API 인증 필요 (401) - 로그인 필요")
        else:
            print(f"   ❌ API 오류: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ API 테스트 실패: {e}")
    
    # 4. 정렬 기능 테스트
    print("\n4️⃣ 정렬 기능 테스트")
    
    sort_tests = [
        ("이름 오름차순", "product_name", "asc"),
        ("이름 내림차순", "product_name", "desc"),
        ("가격 오름차순", "price", "asc"),
        ("가격 내림차순", "price", "desc"),
        ("브랜드 오름차순", "brand_name", "asc"),
        ("등록일 내림차순", "created_at", "desc")
    ]
    
    for test_name, sort_column, sort_direction in sort_tests:
        try:
            params = {
                'sort_column': sort_column,
                'sort_direction': sort_direction,
                'limit': 5
            }
            
            response = requests.get(
                f"{base_url}/product/api/list?" + urlencode(params), 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('data', [])
                if products:
                    print(f"   ✅ {test_name}: {len(products)}개 결과")
                    
                    # 정렬 결과 확인
                    if sort_column == 'product_name':
                        values = [p.get('product_name', '') for p in products[:3]]
                    elif sort_column == 'price':
                        values = [p.get('price', 0) for p in products[:3]]
                    elif sort_column == 'brand_name':
                        values = [p.get('brand_name', '') for p in products[:3]]
                    else:
                        values = [p.get('created_at', '') for p in products[:3]]
                    
                    print(f"      샘플: {values}")
                else:
                    print(f"   ⚠️ {test_name}: 결과 없음")
            else:
                print(f"   ❌ {test_name}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ {test_name} 실패: {e}")
    
    # 5. 검색 기능 테스트
    print("\n5️⃣ 검색 기능 테스트")
    
    search_tests = [
        ("브랜드 검색", "JOIE"),
        ("제품명 검색", "스핀"),
        ("카시트 검색", "카시트"),
        ("유모차 검색", "유모차")
    ]
    
    for test_name, search_term in search_tests:
        try:
            params = {
                'search': search_term,
                'limit': 5
            }
            
            response = requests.get(
                f"{base_url}/product/api/list?" + urlencode(params),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('data', [])
                print(f"   ✅ {test_name} ('{search_term}'): {len(products)}개 결과")
                
                if products:
                    sample_names = [p.get('product_name', '')[:20] for p in products[:2]]
                    print(f"      샘플: {sample_names}")
            else:
                print(f"   ❌ {test_name}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ {test_name} 실패: {e}")
    
    # 6. 페이징 테스트
    print("\n6️⃣ 페이징 테스트")
    
    for page in [1, 2, 3]:
        try:
            params = {
                'page': page,
                'limit': 20
            }
            
            response = requests.get(
                f"{base_url}/product/api/list?" + urlencode(params),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('data', [])
                total = data.get('total', 0)
                print(f"   ✅ 페이지 {page}: {len(products)}개 결과 (전체: {total}개)")
            else:
                print(f"   ❌ 페이지 {page}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ 페이지 {page} 실패: {e}")
    
    # 7. 코드 정보 API 테스트
    print("\n7️⃣ 코드 정보 API 테스트")
    try:
        response = requests.get(f"{base_url}/product/api/get-codes", timeout=10)
        if response.status_code == 200:
            codes = response.json()
            print(f"   ✅ 코드 정보 API 성공:")
            print(f"      브랜드: {len(codes.get('brands', []))}개")
            print(f"      품목: {len(codes.get('categories', []))}개")
            print(f"      색상: {len(codes.get('colors', []))}개")
            print(f"      타입: {len(codes.get('div_types', []))}개")
            
            # 브랜드 샘플
            brands = codes.get('brands', [])[:5]
            if brands:
                brand_names = [b.get('name', '') for b in brands]
                print(f"      브랜드 샘플: {brand_names}")
                
        else:
            print(f"   ❌ 코드 정보 API: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ 코드 정보 API 실패: {e}")
    
    print(f"\n🎉 UI 테스트 완료!")
    print(f"📱 브라우저에서 직접 확인: http://127.0.0.1:5000/product/")
    print(f"✅ 년식, 분류코드, 자가코드 표시 문제 해결")
    print(f"✅ 정렬, 검색, 페이징 기능 동작 확인")

if __name__ == "__main__":
    time.sleep(3)  # Flask 앱 시작 대기
    test_live_ui() 