#!/usr/bin/env python3
"""
TP 코드 그룹 확인 스크립트
"""

from app.common.models import Code, db
from app import create_app

def main():
    app = create_app('development')
    with app.app_context():
        # TP 코드들 확인
        tp_codes = Code.get_codes_by_group_name('TP')
        print('=== TP 코드들 ===')
        for code in tp_codes:
            print(f'SEQ: {code.seq}, 코드: "{code.code}", 코드명: "{code.code_name}", 길이: {len(code.code)}자리')
        
        print(f'\n총 {len(tp_codes)}개 TP 코드 존재')
        
        # 2자리 코드만 필터링
        two_digit_codes = [c for c in tp_codes if len(c.code) == 2]
        print(f'\n=== 2자리 TP 코드들 ===')
        for code in two_digit_codes:
            print(f'SEQ: {code.seq}, 코드: "{code.code}", 코드명: "{code.code_name}"')
        
        print(f'\n2자리 코드: {len(two_digit_codes)}개')

if __name__ == '__main__':
    main() 