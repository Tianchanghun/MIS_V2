#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
코드 그룹명 확인 스크립트
"""

from app import create_app
from app.common.models import Code

def check_code_groups():
    app = create_app()
    with app.app_context():
        # 모든 부모 코드들(depth=0) 조회
        parent_codes = Code.query.filter_by(depth=0).order_by(Code.code).all()
        print('=== 모든 부모 그룹들 ===')
        for code in parent_codes:
            children_count = Code.query.filter_by(parent_seq=code.seq).count()
            print(f'{code.code}: {code.code_name} ({children_count}개 하위 코드)')
        
        print('\n=== 특정 그룹 확인 ===')
        groups_to_check = ['PG', 'IT', 'ITD', 'PT', 'CLD']
        for group_code in groups_to_check:
            group = Code.query.filter_by(code=group_code, depth=0).first()
            if group:
                children = Code.query.filter_by(parent_seq=group.seq).count()
                print(f'{group_code}: {group.code_name} ({children}개 하위 코드)')
            else:
                print(f'{group_code}: 그룹을 찾을 수 없음')

if __name__ == "__main__":
    check_code_groups() 