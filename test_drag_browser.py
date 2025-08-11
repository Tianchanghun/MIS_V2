#!/usr/bin/env python3
"""
드래그 앤 드롭 브라우저 테스트
"""
import webbrowser
import time
import subprocess
import sys

def main():
    print("🌐 브라우저에서 드래그 앤 드롭 테스트를 시작합니다...")
    
    # 브라우저 열기
    url = "http://127.0.0.1:5000/admin/code_management"
    print(f"📱 브라우저로 열기: {url}")
    
    # Chrome 또는 기본 브라우저로 열기
    try:
        # Chrome으로 개발자 도구와 함께 열기
        subprocess.run([
            'start', 'chrome', 
            '--new-window',
            '--auto-open-devtools-for-tabs',
            url
        ], shell=True, check=False)
        print("✅ Chrome 브라우저로 열었습니다 (개발자 도구 포함)")
    except:
        # 기본 브라우저로 열기
        webbrowser.open(url)
        print("✅ 기본 브라우저로 열었습니다")
    
    print("\n" + "="*60)
    print("🎯 드래그 앤 드롭 테스트 가이드")
    print("="*60)
    print("1. 페이지가 로드되면 F12를 눌러 개발자 도구를 여세요")
    print("2. Console 탭에서 다음 메시지들을 확인하세요:")
    print("   - '🔧 TableDnD 초기화 시작...'")
    print("   - '✅ TableDnD 초기화 완료'")
    print("   - '🎮 드래그 핸들 설정 완료, 총 개수: X'")
    print()
    print("3. 드래그 핸들(≡)에 마우스를 올리면:")
    print("   - 배경색이 파란색으로 변해야 함")
    print("   - 커서가 grab(손모양)으로 변해야 함")
    print("   - Console에 '🎯 드래그 핸들에 마우스 진입' 메시지")
    print()
    print("4. 드래그 핸들을 클릭하고 드래그하면:")
    print("   - Console에 '🎯 드래그 시작 - SEQ: X' 메시지")
    print("   - 행이 노란색으로 변하고 크기가 커져야 함")
    print("   - 드롭하면 '🎯 드롭 완료 - SEQ: X' 메시지")
    print()
    print("5. 문제가 있다면 Console의 에러 메시지를 확인하세요")
    print("="*60)
    
    # 디버그 테스트 페이지도 열기
    debug_url = f"file:///{sys.path[0].replace('\\', '/')}/debug_drag_drop.html"
    print(f"\n🔧 디버그 테스트 페이지도 열겠습니다: {debug_url}")
    webbrowser.open(debug_url)
    
    print("\n⏳ 테스트를 진행하세요. 문제가 있으면 아무 키나 누르세요...")
    input()

if __name__ == "__main__":
    main() 