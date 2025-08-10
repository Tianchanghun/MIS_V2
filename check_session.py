#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

print('=== 세션 및 API 테스트 ===')

# 상품 API 테스트
try:
    response = requests.get('http://127.0.0.1:5000/product/api/list')
    print(f'API 응답 상태: {response.status_code}')
    
    if response.status_code == 200:
        data = response.json()
        print(f'API 응답 데이터: {json.dumps(data, indent=2, ensure_ascii=False)}')
    else:
        print(f'API 오류: {response.text}')
        
except Exception as e:
    print(f'API 호출 오류: {e}')

# 직접 브라우저 테스트 안내
print('\n=== 브라우저 테스트 방법 ===')
print('1. 브라우저에서 http://127.0.0.1:5000/product/ 접속')
print('2. F12 → Network 탭 열기')
print('3. 페이지 새로고침')
print('4. /product/api/list 요청 확인')
print('5. Console 탭에서 JavaScript 오류 확인') 