#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
색상 관련 그룹 확인 스크립트
"""

from app import create_app
from app.common.models import Code

def check_color_groups():
    app = create_app()
    with app.app_context():
        # 모든 그룹 찾기 (색상별 포함)
        print('=== 모든 그룹들 ===')
        all_groups = Code.query.filter_by(depth=0).order_by(Code.code).all()
        for group in all_groups:
            children = Code.query.filter_by(parent_seq=group.seq).count()
            print(f'{group.code}: {group.code_name} ({children}개 하위 코드)')

if __name__ == "__main__":
    check_color_groups() 