#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
실제 tbl_code 테이블의 코드 그룹 구조 확인
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db, Code

app = create_app()

def check_code_groups():
    """코드 그룹 구조 확인"""
    with app.app_context():
        print("🔍 tbl_code 테이블 코드 그룹 구조 확인")
        print("=" * 60)
        
        # 1. 전체 depth별 코드 확인
        for depth in [0, 1, 2]:
            codes = Code.query.filter_by(depth=depth).order_by(Code.sort.asc()).all()
            print(f"\n📊 Depth {depth} 코드: {len(codes)}개")
            for code in codes[:20]:  # 처음 20개만 표시
                print(f"  - SEQ:{code.seq}, 코드:{code.code}, 이름:{code.code_name}, Parent:{code.parent_seq}")
        
        # 2. 특정 그룹 코드 찾기
        target_groups = ['BRAND', 'COLOR', 'TP', 'PRD', 'YR', 'PRT']
        print(f"\n🎯 특정 그룹 코드 찾기:")
        
        for group_code in target_groups:
            group_codes = Code.query.filter_by(code=group_code).all()
            print(f"\n📦 '{group_code}' 그룹:")
            for group in group_codes:
                print(f"  - SEQ:{group.seq}, 이름:{group.code_name}, Depth:{group.depth}, Parent:{group.parent_seq}")
                
                # 하위 코드들 확인
                child_codes = Code.query.filter_by(parent_seq=group.seq).limit(10).all()
                if child_codes:
                    print(f"    📂 하위 코드 {len(child_codes)}개:")
                    for child in child_codes:
                        print(f"      - {child.code}: {child.code_name}")

def check_specific_groups():
    """사용자가 언급한 그룹들 구체적으로 확인"""
    with app.app_context():
        print("\n🎯 사용자 언급 그룹 상세 확인")
        print("=" * 60)
        
        groups_to_check = [
            ('BRAND', '브랜드'),
            ('COLOR', '색상'),
            ('TP', '타입'),
            ('PRD', '제품'),
            ('YR', '년도'),
            ('PRT', '품목')
        ]
        
        for group_code, group_name in groups_to_check:
            print(f"\n🔍 {group_name} ({group_code}) 그룹:")
            
            # 다양한 depth에서 해당 코드 찾기
            found_groups = Code.query.filter_by(code=group_code).all()
            
            if found_groups:
                for group in found_groups:
                    print(f"  ✅ 발견: SEQ={group.seq}, 이름='{group.code_name}', Depth={group.depth}")
                    
                    # 하위 코드 개수 확인
                    child_count = Code.query.filter_by(parent_seq=group.seq).count()
                    print(f"     📊 하위 코드 개수: {child_count}개")
                    
                    # 샘플 하위 코드 3개 표시
                    sample_children = Code.query.filter_by(parent_seq=group.seq).limit(3).all()
                    for child in sample_children:
                        print(f"     - {child.code}: {child.code_name}")
            else:
                print(f"  ❌ '{group_code}' 그룹을 찾을 수 없습니다.")

if __name__ == '__main__':
    check_code_groups()
    check_specific_groups() 