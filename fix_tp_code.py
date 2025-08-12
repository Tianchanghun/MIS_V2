#!/usr/bin/env python3
"""
routes.py에서 safe_get_codes('TP')를 safe_get_codes('타입')으로 안전하게 변경
"""

def fix_tp_code():
    file_path = 'app/product/routes.py'
    
    # 파일 읽기 (UTF-8 인코딩)
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 'TP'를 '타입'으로 변경
    old_line = "        tp_codes_raw = safe_get_codes('TP')  # 🔥 'TP' → '타입' 그룹명으로 변경"
    new_line = "        tp_codes_raw = safe_get_codes('타입')  # 🔥 실제 그룹명 '타입' 사용"
    
    if old_line in content:
        content = content.replace(old_line, new_line)
        print("✅ TP → 타입으로 변경 완료")
    else:
        print("❌ 변경할 줄을 찾을 수 없습니다.")
        return
    
    # 로그 메시지도 변경
    old_log = "        current_app.logger.info(f\"🔧 TP 코드 원본 데이터: {len(tp_codes_raw)}개\")"
    new_log = "        current_app.logger.info(f\"🔧 '타입' 그룹 원본 데이터: {len(tp_codes_raw)}개\")"
    
    if old_log in content:
        content = content.replace(old_log, new_log)
        print("✅ 로그 메시지 변경 완료")
    
    # 파일 쓰기 (UTF-8 인코딩)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("🎉 수정 완료!")

if __name__ == '__main__':
    fix_tp_code() 