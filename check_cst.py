#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import create_app
from app.common.models import Code

app = create_app()
with app.app_context():
    print('=== CST 그룹 찾기 ===')
    cst_group = Code.query.filter_by(code='CST', depth=0).first()
    if cst_group:
        print(f'CST 그룹 발견: seq={cst_group.seq}, name={cst_group.code_name}')
        
        print('\n=== CST 하위 그룹들 ===')
        sub_groups = Code.query.filter_by(parent_seq=cst_group.seq, depth=1).all()
        print(f'하위 그룹 수: {len(sub_groups)}')
        for group in sub_groups:
            print(f'  - {group.code}({group.code_name}): seq={group.seq}')
            
            # 각 그룹의 하위 코드들도 확인
            sub_codes = Code.query.filter_by(parent_seq=group.seq, depth=2).limit(3).all()
            print(f'    하위 코드 수: {Code.query.filter_by(parent_seq=group.seq, depth=2).count()}개')
            for code in sub_codes:
                print(f'      - {code.code}: {code.code_name}')
    else:
        print('CST 그룹을 찾을 수 없습니다.')
        
        # 다른 그룹들 확인
        print('\n=== 기존 코드 그룹들 ===')
        all_groups = Code.query.filter_by(depth=0).limit(10).all()
        for group in all_groups:
            print(f'- {group.code}: {group.code_name}') 