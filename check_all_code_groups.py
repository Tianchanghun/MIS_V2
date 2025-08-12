#!/usr/bin/env python3
"""
모든 코드 그룹 확인 스크립트
"""

from app.common.models import Code, db
from app import create_app

def main():
    app = create_app('development')
    with app.app_context():
        # 모든 코드 그룹 확인
        all_codes = Code.query.filter_by(depth=1).all()  # 최상위 그룹들
        print('=== 모든 코드 그룹들 ===')
        for code in all_codes:
            print(f'그룹: "{code.code_name}" (코드: {code.code})')
        
        # 타입, TP, 타입2 관련 그룹들 찾기
        type_related = []
        for code in all_codes:
            if any(keyword in code.code_name.lower() for keyword in ['타입', 'type', 'tp']):
                type_related.append(code)
        
        print(f'\n=== 타입 관련 그룹들 ===')
        for code in type_related:
            print(f'그룹: "{code.code_name}" (코드: {code.code})')
            
            # 하위 코드들 확인
            child_codes = Code.query.filter_by(parent_seq=code.seq).all()
            for child in child_codes[:5]:  # 최대 5개만
                print(f'  - SEQ: {child.seq}, 코드: "{child.code}", 코드명: "{child.code_name}", 길이: {len(child.code)}자리')
            if len(child_codes) > 5:
                print(f'  ... 총 {len(child_codes)}개')

if __name__ == '__main__':
    main() 