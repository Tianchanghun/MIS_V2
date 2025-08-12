#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CL2와 PD 그룹 확인 스크립트
"""

from app import create_app
from app.common.models import Code

def check_missing_groups():
    app = create_app()
    with app.app_context():
        print('=== CL2와 PD 그룹 확인 ===')
        
        # CL2 그룹 확인
        cl2_group = Code.query.filter_by(code='CL2', depth=0).first()
        if cl2_group:
            children = Code.query.filter_by(parent_seq=cl2_group.seq).count()
            print(f'CL2: {cl2_group.code_name} ({children}개 하위 코드)')
        else:
            print('CL2: 그룹을 찾을 수 없음')
        
        # PD 그룹 확인
        pd_group = Code.query.filter_by(code='PD', depth=0).first()
        if pd_group:
            children = Code.query.filter_by(parent_seq=pd_group.seq).count()
            print(f'PD: {pd_group.code_name} ({children}개 하위 코드)')
        else:
            print('PD: 그룹을 찾을 수 없음')
        
        # 대안 그룹들 찾기
        print('\n=== 대안 그룹들 ===')
        alternative_groups = ['분류2', '제품구분']
        for group_name in alternative_groups:
            groups = Code.query.filter_by(code_name=group_name, depth=0).all()
            for group in groups:
                children = Code.query.filter_by(parent_seq=group.seq).count()
                print(f'{group.code}: {group.code_name} ({children}개 하위 코드)')

if __name__ == "__main__":
    check_missing_groups() 