#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db
import requests
import time

def fix_api_auth():
    """API 인증 문제 해결"""
    print("🔧 API 인증 문제 해결")
    print("=" * 40)
    
    # 1. 환경 변수 설정
    print("1️⃣ 환경 변수 설정")
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_DEBUG'] = '1'
    print("   ✅ FLASK_ENV=development 설정")
    print("   ✅ FLASK_DEBUG=1 설정")
    
    # 2. Flask 앱 설정 확인
    print("\n2️⃣ Flask 앱 설정 확인")
    app = create_app()
    with app.app_context():
        flask_env = app.config.get('FLASK_ENV', 'production')
        debug_mode = app.config.get('DEBUG', False)
        print(f"   📋 FLASK_ENV: {flask_env}")
        print(f"   📋 DEBUG: {debug_mode}")
        
        # 강제로 개발 환경으로 설정
        app.config['FLASK_ENV'] = 'development'
        app.config['DEBUG'] = True
        print("   ✅ 강제로 development 모드 설정")
    
    # 3. API 테스트
    print("\n3️⃣ API 접근 테스트")
    
    # 잠시 대기 후 테스트
    time.sleep(2)
    
    try:
        response = requests.get('http://127.0.0.1:5000/product/api/list?limit=3', timeout=10)
        print(f"   📡 API 응답: HTTP {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            products = data.get('data', [])
            print(f"   ✅ API 성공: {len(products)}개 제품")
            
            if products:
                first = products[0]
                print(f"   📋 첫 번째 제품:")
                print(f"      이름: {first.get('product_name')}")
                print(f"      브랜드: {first.get('brand_name', 'undefined')}")
                print(f"      자가코드: {first.get('std_div_prod_code', 'undefined')}")
        
        elif response.status_code == 401:
            print("   ❌ 여전히 401 오류 - 코드 수정 필요")
            return False
        else:
            print(f"   ❌ HTTP {response.status_code} 오류")
            return False
            
    except requests.ConnectionError:
        print("   ⚠️ Flask 앱 연결 실패")
        return False
    except Exception as e:
        print(f"   ❌ 테스트 오류: {e}")
        return False
    
    print(f"\n🎉 API 인증 문제 해결 완료!")
    return True

if __name__ == "__main__":
    success = fix_api_auth()
    if success:
        print("✅ 이제 API가 정상 작동합니다!")
        print("📱 http://127.0.0.1:5000/product/ 에서 확인 가능")
    else:
        print("❌ 추가 수정이 필요합니다") 