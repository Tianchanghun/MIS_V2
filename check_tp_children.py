#!/usr/bin/env python3
"""
TP(타입) 그룹의 자식 코드들 확인
"""

from app import create_app
from app.common.models import db, Code

def check_tp_children():
    """TP 자식 코드들 상세 확인"""
    app = create_app('development')
    
    with app.app_context():
        try:
            # TP 부모 코드 (SEQ: 210)의 자식들 확인
            tp_children = db.session.query(Code).filter(
                Code.parent_seq == 210
            ).all()
            
            print(f"🔧 TP 그룹(SEQ: 210) 자식 코드들: {len(tp_children)}개")
            
            tp2_codes = []
            for child in tp_children:
                code_str = str(child.code) if child.code else ''
                print(f"  - SEQ: {child.seq}, 코드: '{child.code}', 이름: '{child.code_name}', 길이: {len(code_str)}")
                
                # 2자리 코드만 필터링
                if len(code_str) == 2:
                    tp2_codes.append({
                        'seq': child.seq,
                        'code': child.code,
                        'code_name': child.code_name
                    })
            
            print(f"\n✅ 2자리 TP 코드들: {len(tp2_codes)}개")
            for code in tp2_codes:
                print(f"  - {code}")
                
        except Exception as e:
            print(f"❌ 오류: {e}")

if __name__ == '__main__':
    check_tp_children() 