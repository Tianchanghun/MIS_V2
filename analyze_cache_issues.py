#!/usr/bin/env python3
"""
캐시 문제 분석 스크립트
- Flask 캐시 설정 확인
- Redis 캐시 상태 확인  
- 정적 파일 캐시 확인
"""

from app import create_app
import os
import time

def analyze_cache_issues():
    """캐시 문제 종합 분석"""
    print("🔍 캐시 문제 분석 시작...")
    
    app = create_app('development')
    
    with app.app_context():
        print("\n📋 Flask 앱 캐시 설정:")
        print(f"  - SEND_FILE_MAX_AGE_DEFAULT: {app.config.get('SEND_FILE_MAX_AGE_DEFAULT', 'None')}")
        print(f"  - ENV: {app.config.get('ENV', 'None')}")
        print(f"  - DEBUG: {app.config.get('DEBUG', 'None')}")
        
        print("\n📋 Redis 캐시 설정:")
        redis_config = app.config.get('REDIS_URL', 'None')
        print(f"  - REDIS_URL: {redis_config}")
        
        # Redis 연결 테스트
        try:
            from app.extensions import redis_client
            if redis_client:
                # Redis 키 확인
                keys = redis_client.keys('*')
                print(f"  - Redis 연결: ✅ 성공")
                print(f"  - Redis 키 수: {len(keys)}개")
                
                # 상품 관련 캐시 키 확인
                product_keys = [key for key in keys if b'product' in key.lower() or b'code' in key.lower()]
                if product_keys:
                    print(f"  - 상품/코드 관련 키: {len(product_keys)}개")
                    for key in product_keys[:5]:  # 최대 5개만 표시
                        print(f"    * {key.decode()}")
        except Exception as e:
            print(f"  - Redis 연결: ❌ 실패 ({e})")
        
        print("\n📋 정적 파일 상태:")
        static_files = [
            'static/js/modules/product/product-manager.js',
            'static/js/modules/product/product-list.js',
            'static/js/common/ui-components.js',
            'static/js/common/ajax-helper.js'
        ]
        
        for file_path in static_files:
            full_path = os.path.join(app.root_path, file_path)
            if os.path.exists(full_path):
                stat = os.stat(full_path)
                mtime = time.ctime(stat.st_mtime)
                size = stat.st_size
                print(f"  - {file_path}")
                print(f"    * 수정일: {mtime}")
                print(f"    * 크기: {size:,} bytes")
            else:
                print(f"  - {file_path}: ❌ 파일 없음")
        
        print("\n📋 템플릿 파일 상태:")
        template_path = os.path.join(app.root_path, 'templates/product/index.html')
        if os.path.exists(template_path):
            stat = os.stat(template_path)
            mtime = time.ctime(stat.st_mtime)
            size = stat.st_size
            print(f"  - index.html")
            print(f"    * 수정일: {mtime}")
            print(f"    * 크기: {size:,} bytes")
            
            # 캐시 버스팅 확인
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if '?v=20241224000000' in content:
                    print(f"    * 캐시 버스팅: ✅ 적용됨")
                else:
                    print(f"    * 캐시 버스팅: ❌ 미적용")

if __name__ == '__main__':
    analyze_cache_issues() 