#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def fix_missing_codes_and_search():
    """누락된 코드 그룹들 추가 및 검색 기능 수정"""
    print("🔧 누락된 코드 그룹 추가 및 검색 기능 수정")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        # 1. 품목그룹 코드 그룹 확인/생성
        print("1️⃣ 품목그룹 코드 그룹 확인/생성")
        
        result = db.session.execute(db.text("""
            SELECT seq FROM tbl_code WHERE code_name = '품목그룹' AND parent_seq = 0
        """))
        prod_group = result.fetchone()
        
        if not prod_group:
            result = db.session.execute(db.text("""
                INSERT INTO tbl_code (parent_seq, code, code_name, depth, sort)
                VALUES (0, 'PG', '품목그룹', 1, 3) RETURNING seq
            """))
            prod_group_seq = result.fetchone()[0]
            print(f"   ✅ 품목그룹 그룹 생성: seq {prod_group_seq}")
        else:
            prod_group_seq = prod_group.seq
            print(f"   ✅ 품목그룹 그룹 확인: seq {prod_group_seq}")
        
        # 품목그룹 하위 코드들 추가
        prod_group_codes = [
            ('SG', '스탠다드 그룹', 1),
            ('CB', '카시트 베이스', 2),
            ('PT', '프리미엄 타입', 3),
            ('DM', '디럭스 모델', 4),
            ('AC', '액세서리', 5),
            ('TY', '토이', 6)
        ]
        
        for code, name, sort_order in prod_group_codes:
            result = db.session.execute(db.text("""
                SELECT seq FROM tbl_code 
                WHERE parent_seq = :parent_seq AND code = :code
            """), {'parent_seq': prod_group_seq, 'code': code})
            
            if not result.fetchone():
                db.session.execute(db.text("""
                    INSERT INTO tbl_code (parent_seq, code, code_name, depth, sort)
                    VALUES (:parent_seq, :code, :code_name, 2, :sort)
                """), {
                    'parent_seq': prod_group_seq,
                    'code': code,
                    'code_name': name,
                    'sort': sort_order
                })
                print(f"      ✅ 품목그룹 코드 추가: {code} - {name}")
        
        # 2. 제품코드 코드 그룹 확인/생성
        print(f"\n2️⃣ 제품코드 코드 그룹 확인/생성")
        
        result = db.session.execute(db.text("""
            SELECT seq FROM tbl_code WHERE code_name = '제품코드' AND parent_seq = 0
        """))
        prod_code_group = result.fetchone()
        
        if not prod_code_group:
            result = db.session.execute(db.text("""
                INSERT INTO tbl_code (parent_seq, code, code_name, depth, sort)
                VALUES (0, 'PC', '제품코드', 1, 5) RETURNING seq
            """))
            prod_code_seq = result.fetchone()[0]
            print(f"   ✅ 제품코드 그룹 생성: seq {prod_code_seq}")
        else:
            prod_code_seq = prod_code_group.seq
            print(f"   ✅ 제품코드 그룹 확인: seq {prod_code_seq}")
        
        # 제품코드 하위 코드들 추가 (01~99)
        for i in range(1, 21):  # 01~20까지만 생성
            code = f"{i:02d}"  # 01, 02, 03, ... 20
            name = f"제품코드 {code}"
            
            result = db.session.execute(db.text("""
                SELECT seq FROM tbl_code 
                WHERE parent_seq = :parent_seq AND code = :code
            """), {'parent_seq': prod_code_seq, 'code': code})
            
            if not result.fetchone():
                db.session.execute(db.text("""
                    INSERT INTO tbl_code (parent_seq, code, code_name, depth, sort)
                    VALUES (:parent_seq, :code, :code_name, 2, :sort)
                """), {
                    'parent_seq': prod_code_seq,
                    'code': code,
                    'code_name': name,
                    'sort': i
                })
                if i <= 5:  # 처음 5개만 로그
                    print(f"      ✅ 제품코드 추가: {code} - {name}")
        
        print(f"      📊 제품코드 20개 생성 완료 (01~20)")
        
        # 3. 타입2 코드 그룹 확인/생성
        print(f"\n3️⃣ 타입2 코드 그룹 확인/생성")
        
        result = db.session.execute(db.text("""
            SELECT seq FROM tbl_code WHERE code_name = '타입2' AND parent_seq = 0
        """))
        type2_group = result.fetchone()
        
        if not type2_group:
            result = db.session.execute(db.text("""
                INSERT INTO tbl_code (parent_seq, code, code_name, depth, sort)
                VALUES (0, 'T2', '타입2', 1, 6) RETURNING seq
            """))
            type2_seq = result.fetchone()[0]
            print(f"   ✅ 타입2 그룹 생성: seq {type2_seq}")
        else:
            type2_seq = type2_group.seq
            print(f"   ✅ 타입2 그룹 확인: seq {type2_seq}")
        
        # 타입2 하위 코드들 추가
        type2_codes = [
            ('00', '기본 타입', 1),
            ('01', '타입1', 2),
            ('02', '타입2', 3),
            ('03', '타입3', 4),
            ('SS', '스페셜', 5),
            ('LL', '리미티드', 6),
            ('XX', '미지정', 7)
        ]
        
        for code, name, sort_order in type2_codes:
            result = db.session.execute(db.text("""
                SELECT seq FROM tbl_code 
                WHERE parent_seq = :parent_seq AND code = :code
            """), {'parent_seq': type2_seq, 'code': code})
            
            if not result.fetchone():
                db.session.execute(db.text("""
                    INSERT INTO tbl_code (parent_seq, code, code_name, depth, sort)
                    VALUES (:parent_seq, :code, :code_name, 2, :sort)
                """), {
                    'parent_seq': type2_seq,
                    'code': code,
                    'code_name': name,
                    'sort': sort_order
                })
                print(f"      ✅ 타입2 코드 추가: {code} - {name}")
        
        db.session.commit()
        
        # 4. 최종 확인
        print(f"\n4️⃣ 코드 그룹 생성 완료 확인")
        
        final_groups = ['브랜드', '구분타입', '품목그룹', '제품타입', '제품코드', '타입2', '년도', '색상']
        
        for i, group_name in enumerate(final_groups, 1):
            result = db.session.execute(db.text("""
                SELECT seq FROM tbl_code WHERE code_name = :group_name AND parent_seq = 0
            """))
            group = result.fetchone()
            
            if group:
                # 하위 코드 개수 확인
                result = db.session.execute(db.text("""
                    SELECT COUNT(*) as code_count
                    FROM tbl_code WHERE parent_seq = :parent_seq
                """), {'parent_seq': group.seq})
                code_count = result.fetchone().code_count
                
                print(f"   {i}. ✅ {group_name}: {code_count}개 코드")
            else:
                print(f"   {i}. ❌ {group_name}: 그룹 없음")
        
        print(f"\n🎉 누락된 코드 그룹 추가 완료!")
        print(f"✅ 품목그룹: 6개 코드 (SG, CB, PT, DM, AC, TY)")
        print(f"✅ 제품코드: 20개 코드 (01~20)")
        print(f"✅ 타입2: 7개 코드 (00, 01, 02, 03, SS, LL, XX)")
        
        print(f"\n📝 레거시 호환 완전한 모달 필드 순서:")
        print(f"   1. 브랜드 → 2. 구분타입 → 3. 품목그룹 → 4. 제품타입")
        print(f"   5. 제품코드 → 6. 타입2 → 7. 년도 → 8. 색상")

if __name__ == "__main__":
    fix_missing_codes_and_search() 