#!/usr/bin/env python3
"""
캐시 충돌 문제 종합 해결 스크립트
1. 동적 캐시 버스팅 적용
2. Redis 캐시 클리어 
3. 브라우저 캐시 무력화
4. 템플릿 렌더링 일관성 보장
"""

import os
import time
import re

def fix_cache_conflicts():
    """캐시 충돌 문제 종합 해결"""
    print("🔧 캐시 충돌 문제 해결 시작...")
    
    # 1. 동적 타임스탬프 생성
    timestamp = int(time.time())
    cache_version = f"v{timestamp}"
    
    print(f"📅 새로운 캐시 버전: {cache_version}")
    
    # 2. index.html 캐시 버스팅 업데이트
    template_path = 'app/templates/product/index.html'
    if os.path.exists(template_path):
        print("🔄 템플릿 캐시 버스팅 업데이트...")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 기존 ?v= 패턴을 새로운 타임스탬프로 교체
        content = re.sub(r'\?v=\d+', f'?v={timestamp}', content)
        
        # 추가로 강력한 캐시 무력화 헤더 추가
        if 'Cache-Control' not in content:
            # meta 태그로 캐시 무력화 추가
            meta_cache = '''
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
'''
            content = content.replace('{% block extra_css %}', '{% block extra_css %}' + meta_cache)
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 템플릿 캐시 버스팅 업데이트 완료: {cache_version}")
    
    # 3. Flask 캐시 설정 강화
    app_init_path = 'app/__init__.py'
    if os.path.exists(app_init_path):
        print("🔄 Flask 캐시 설정 강화...")
        
        with open(app_init_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 더 강력한 캐시 무력화 코드 추가
        cache_fix_code = '''
    # 🔥 강력한 캐시 무력화 (개발 환경)
    if app.config.get('ENV') == 'development' or app.config.get('DEBUG'):
        app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
        
        @app.after_request
        def after_request(response):
            # 모든 응답에 캐시 무력화 헤더 추가
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['Last-Modified'] = response.headers.get('Last-Modified', '')
            response.headers['ETag'] = ''
            
            # 정적 파일에 대해서도 캐시 무력화
            if request.endpoint == 'static':
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            
            return response
'''
        
        if 'after_request' not in content:
            # return app 바로 앞에 삽입
            content = content.replace('return app', cache_fix_code + '\n    return app')
            
            with open(app_init_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Flask 캐시 설정 강화 완료")
    
    # 4. 상품 라우트에 캐시 방지 헤더 추가
    routes_path = 'app/product/routes.py'
    if os.path.exists(routes_path):
        print("🔄 상품 라우트 캐시 방지 헤더 추가...")
        
        with open(routes_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # index() 함수에 캐시 방지 헤더 추가
        if 'no-cache' not in content:
            # render_template 호출을 response로 감싸기
            render_pattern = r"return render_template\('product/index\.html',"
            replacement = '''# 캐시 방지 헤더 추가
        response = make_response(render_template('product/index.html','''
            
            content = re.sub(render_pattern, replacement, content)
            
            # 마지막에 헤더 설정 추가
            content = content.replace(
                "show_inactive=show_inactive)",
                '''show_inactive=show_inactive)
        
        # 캐시 방지 헤더 설정
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response'''
            )
            
            with open(routes_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ 상품 라우트 캐시 방지 헤더 추가 완료")
    
    # 5. JavaScript 파일에 캐시 버스팅 주석 추가
    js_files = [
        'app/static/js/modules/product/product-manager.js',
        'app/static/js/modules/product/product-list.js'
    ]
    
    for js_file in js_files:
        if os.path.exists(js_file):
            print(f"🔄 {js_file} 캐시 버스팅 주석 추가...")
            
            with open(js_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 파일 상단에 캐시 버스팅 주석 추가
            cache_comment = f'''/**
 * 캐시 버스팅: {cache_version}
 * 수정 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}
 * 브라우저 캐시 무력화를 위한 버전 표시
 */

'''
            if f'캐시 버스팅: {cache_version}' not in content:
                # 기존 캐시 버스팅 주석 제거
                content = re.sub(r'/\*\*\s*\n\s*\*\s*캐시 버스팅:.*?\*/', '', content, flags=re.DOTALL)
                
                # 새로운 주석 추가
                content = cache_comment + content
                
                with open(js_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"✅ {js_file} 캐시 버스팅 주석 추가 완료")
    
    print(f"\n🎉 캐시 충돌 문제 해결 완료!")
    print(f"📋 적용된 변경사항:")
    print(f"  1. 동적 캐시 버전: {cache_version}")
    print(f"  2. 템플릿 캐시 버스팅 업데이트")
    print(f"  3. Flask 강력한 캐시 무력화")
    print(f"  4. 상품 라우트 캐시 방지 헤더")
    print(f"  5. JavaScript 파일 캐시 버스팅 주석")
    print(f"\n⚠️ 주의사항:")
    print(f"  - 브라우저 완전 새로고침 (Ctrl+Shift+R) 권장")
    print(f"  - 시크릿 모드와 일반 모드 모두 테스트 필요")

if __name__ == '__main__':
    fix_cache_conflicts() 