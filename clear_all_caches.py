#!/usr/bin/env python3
"""
모든 캐시 클리어 및 Flask 재시작 스크립트
"""

import subprocess
import time
import os

def clear_all_caches():
    """모든 캐시 클리어"""
    print("🔥 모든 캐시 클리어 시작...")
    
    # 1. Redis 캐시 클리어 (Docker 컨테이너)
    try:
        print("🔄 Redis 캐시 클리어...")
        result = subprocess.run([
            'docker', 'exec', 'mis_redis', 
            'redis-cli', '-a', 'redis123!@#', 'FLUSHALL'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Redis 캐시 클리어 완료")
        else:
            print(f"⚠️ Redis 클리어 오류: {result.stderr}")
    except Exception as e:
        print(f"❌ Redis 캐시 클리어 실패: {e}")
    
    # 2. Python __pycache__ 클리어
    try:
        print("🔄 Python 캐시 클리어...")
        
        # __pycache__ 폴더 찾기 및 삭제
        for root, dirs, files in os.walk('.'):
            for dir_name in dirs[:]:  # 복사본 생성하여 순회 중 수정 방지
                if dir_name == '__pycache__':
                    cache_path = os.path.join(root, dir_name)
                    try:
                        subprocess.run(['rmdir', '/S', '/Q', cache_path], 
                                     shell=True, check=True)
                        print(f"  ✅ 삭제: {cache_path}")
                    except:
                        pass
        
        print("✅ Python 캐시 클리어 완료")
    except Exception as e:
        print(f"❌ Python 캐시 클리어 실패: {e}")
    
    # 3. 브라우저 캐시 무력화를 위한 타임스탬프 업데이트
    timestamp = int(time.time())
    print(f"📅 새로운 타임스탬프: {timestamp}")
    
    # 4. Flask 개발 서버 재시작 안내
    print("\n🎯 추천 작업:")
    print("1. Flask 개발 서버 재시작 (Ctrl+C 후 다시 시작)")
    print("2. 브라우저 완전 새로고침 (Ctrl+Shift+R)")
    print("3. 시크릿 모드와 일반 모드 모두 테스트")
    print("4. 개발자 도구 > Application > Storage > Clear site data")
    
    print(f"\n✅ 캐시 클리어 완료! 타임스탬프: {timestamp}")

if __name__ == '__main__':
    clear_all_caches() 