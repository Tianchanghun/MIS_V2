#!/usr/bin/env python3
"""
TP 코드 그룹 상세 정보 확인
"""

from app import create_app
from app.common.models import db, Code

def check_tp_codes_detail():
    """TP 코드 그룹 상세 확인"""
    app = create_app('development')
    
    with app.app_context():
        try:
            print("🔍 TP 코드 그룹 상세 분석...")
            
            # 1. TP 그룹 부모 코드 찾기
            tp_parent = db.session.query(Code).filter(
                Code.code_name.like('%TP%'),
                Code.depth == 1
            ).all()
            
            print(f"\n📋 TP 관련 부모 코드들:")
            for parent in tp_parent:
                print(f"  - SEQ: {parent.seq}, 코드: {parent.code}, 이름: {parent.code_name}, 깊이: {parent.depth}")
            
            # 2. TP 자식 코드들 확인
            if tp_parent:
                main_tp_parent = tp_parent[0]  # 첫 번째 TP 부모
                tp_children = db.session.query(Code).filter(
                    Code.parent_seq == main_tp_parent.seq
                ).all()
                
                print(f"\n🔧 TP 자식 코드들 (부모 SEQ: {main_tp_parent.seq}):")
                for child in tp_children:
                    print(f"  - SEQ: {child.seq}, 코드: '{child.code}', 이름: '{child.code_name}', 깊이: {child.depth}")
                    print(f"    코드 길이: {len(child.code) if child.code else 0}")
            
            # 3. 모든 TP 관련 코드 확인 (코드명으로)
            all_tp_codes = db.session.query(Code).filter(
                Code.code_name.like('%타입%')
            ).all()
            
            print(f"\n🔎 '타입' 포함 모든 코드들:")
            for code in all_tp_codes:
                print(f"  - SEQ: {code.seq}, 코드: '{code.code}', 이름: '{code.code_name}', 부모SEQ: {code.parent_seq}")
                
        except Exception as e:
            print(f"❌ 오류: {e}")

if __name__ == '__main__':
    check_tp_codes_detail() 