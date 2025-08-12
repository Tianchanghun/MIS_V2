#!/usr/bin/env python3
"""
제품구분(PD) 코드 확인 스크립트
"""

from app.common.models import Code, db
from app import create_app

def main():
    app = create_app('development')
    with app.app_context():
        # 제품구분(PD) 코드들 확인
        product_division_codes = Code.get_codes_by_group_name('제품구분')
        print('=== 제품구분(PD) 코드들 ===')
        for code in product_division_codes:
            print(f'SEQ: {code.seq}, 코드: "{code.code}", 코드명: "{code.code_name}"')
        
        print(f'\n총 {len(product_division_codes)}개 제품구분 코드 존재')
        
        # 코드 '1'인 제품구분이 있는지 확인
        code_1 = [c for c in product_division_codes if c.code == '1']
        if code_1:
            print(f'\n✅ 코드 "1"인 제품구분 발견: "{code_1[0].code_name}"')
        else:
            print('\n⚠️ 코드 "1"인 제품구분이 없습니다.')

if __name__ == '__main__':
    main() 