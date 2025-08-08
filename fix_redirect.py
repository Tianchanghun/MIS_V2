import os

# auth/routes.py 파일 읽기
with open('app/auth/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 리다이렉트 부분 수정
old_code = '''                # next 파라미터 확인
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('index'))'''

new_code = '''                # 로그인 성공 후 관리자 페이지로 이동
                return redirect('/admin/')'''

content = content.replace(old_code, new_code)

# 파일 저장
with open('app/auth/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 로그인 리다이렉트 수정 완료")
