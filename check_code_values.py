#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def check_code_values():
    """브랜드, 구분타입, 제품그룹, 제품타입, 제품코드, 타입2, 년도, 색상 코드 값 확인"""
    print("🔍 모든 코드 값 확인")
    print("=" * 70)
    
    app = create_app()
    with app.app_context():
        # 레거시 순서에 맞는 코드 그룹들
        code_groups = [
            '브랜드',
            '구분타입', 
            '품목그룹',
            '제품타입',
            '제품코드',
            '타입2',
            '년도',
            '색상'
        ]
        
        all_complete = True
        
        for i, group_name in enumerate(code_groups, 1):
            print(f"\n{i}️⃣ {group_name} 코드 확인")
            
            # 코드 그룹 존재 확인
            result = db.session.execute(db.text("""
                SELECT seq FROM tbl_code 
                WHERE code_name = :group_name AND parent_seq = 0
            """), {'group_name': group_name})
            
            group = result.fetchone()
            
            if not group:
                print(f"   ❌ '{group_name}' 그룹이 존재하지 않음")
                all_complete = False
                continue
                
            group_seq = group.seq
            print(f"   ✅ '{group_name}' 그룹 존재 (seq: {group_seq})")
            
            # 하위 코드들 확인
            result = db.session.execute(db.text("""
                SELECT seq, code, code_name, sort
                FROM tbl_code 
                WHERE parent_seq = :parent_seq
                ORDER BY sort, code
            """), {'parent_seq': group_seq})
            
            codes = result.fetchall()
            
            if not codes:
                print(f"   ❌ '{group_name}' 그룹에 하위 코드가 없음")
                all_complete = False
                continue
                
            print(f"   📋 {len(codes)}개 코드 존재:")
            for j, code in enumerate(codes[:10]):  # 최대 10개만 표시
                print(f"      {code.code}: {code.code_name} (seq: {code.seq})")
                
            if len(codes) > 10:
                print(f"      ... 외 {len(codes) - 10}개 더")
        
        # 특별 확인: 필수 코드들이 있는지
        print(f"\n🔍 필수 코드 값들 특별 확인")
        
        # 브랜드 확인 (레거시에서 사용하는 주요 브랜드들)
        essential_brands = ['RY', 'JI', 'NU', 'LI', 'NA', 'FR']
        print(f"\n   📋 필수 브랜드 코드 확인:")
        for brand in essential_brands:
            result = db.session.execute(db.text("""
                SELECT c.seq, c.code_name
                FROM tbl_code p
                JOIN tbl_code c ON p.seq = c.parent_seq
                WHERE p.code_name = '브랜드' AND c.code = :brand_code
            """), {'brand_code': brand})
            
            brand_info = result.fetchone()
            if brand_info:
                print(f"      ✅ {brand}: {brand_info.code_name}")
            else:
                print(f"      ❌ {brand}: 없음")
        
        # 구분타입 확인 (1, 2, 3)
        essential_div_types = ['1', '2', '3']
        print(f"\n   📋 필수 구분타입 코드 확인:")
        for div_type in essential_div_types:
            result = db.session.execute(db.text("""
                SELECT c.seq, c.code_name
                FROM tbl_code p
                JOIN tbl_code c ON p.seq = c.parent_seq
                WHERE p.code_name = '구분타입' AND c.code = :div_type_code
            """), {'div_type_code': div_type})
            
            div_info = result.fetchone()
            if div_info:
                print(f"      ✅ {div_type}: {div_info.code_name}")
            else:
                print(f"      ❌ {div_type}: 없음")
        
        # 품목그룹 확인 (SG, CB, PT, DM 등)
        essential_prod_groups = ['SG', 'CB', 'PT', 'DM']
        print(f"\n   📋 필수 품목그룹 코드 확인:")
        for prod_group in essential_prod_groups:
            result = db.session.execute(db.text("""
                SELECT c.seq, c.code_name
                FROM tbl_code p
                JOIN tbl_code c ON p.seq = c.parent_seq
                WHERE p.code_name = '품목그룹' AND c.code = :prod_group_code
            """), {'prod_group_code': prod_group})
            
            group_info = result.fetchone()
            if group_info:
                print(f"      ✅ {prod_group}: {group_info.code_name}")
            else:
                print(f"      ❌ {prod_group}: 없음")
        
        # 제품타입 확인 (WC, MT, BK 등)
        essential_prod_types = ['WC', 'MT', 'BK', 'WO', 'AC']
        print(f"\n   📋 필수 제품타입 코드 확인:")
        for prod_type in essential_prod_types:
            result = db.session.execute(db.text("""
                SELECT c.seq, c.code_name
                FROM tbl_code p
                JOIN tbl_code c ON p.seq = c.parent_seq
                WHERE p.code_name = '제품타입' AND c.code = :prod_type_code
            """), {'prod_type_code': prod_type})
            
            type_info = result.fetchone()
            if type_info:
                print(f"      ✅ {prod_type}: {type_info.code_name}")
            else:
                print(f"      ❌ {prod_type}: 없음")
        
        # 년도 확인 (14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24)
        essential_years = ['14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24']
        print(f"\n   📋 필수 년도 코드 확인:")
        for year in essential_years:
            result = db.session.execute(db.text("""
                SELECT c.seq, c.code_name
                FROM tbl_code p
                JOIN tbl_code c ON p.seq = c.parent_seq
                WHERE p.code_name = '년도' AND c.code = :year_code
            """), {'year_code': year})
            
            year_info = result.fetchone()
            if year_info:
                print(f"      ✅ {year}: {year_info.code_name}")
            else:
                print(f"      ❌ {year}: 없음")
        
        # 색상 확인 (주요 색상들)
        essential_colors = ['WIR', 'ZZN', 'BK2', 'BKE', 'BRN', 'MGY', 'SBG', 'WTW', 'GRG', 'CHM']
        print(f"\n   📋 필수 색상 코드 확인 (처음 10개):")
        for color in essential_colors:
            result = db.session.execute(db.text("""
                SELECT c.seq, c.code_name
                FROM tbl_code p
                JOIN tbl_code c ON p.seq = c.parent_seq
                WHERE p.code_name = '색상' AND c.code = :color_code
            """), {'color_code': color})
            
            color_info = result.fetchone()
            if color_info:
                print(f"      ✅ {color}: {color_info.code_name}")
            else:
                print(f"      ❌ {color}: 없음")
        
        # 총 색상 개수 확인
        result = db.session.execute(db.text("""
            SELECT COUNT(*) as total_colors
            FROM tbl_code p
            JOIN tbl_code c ON p.seq = c.parent_seq
            WHERE p.code_name = '색상'
        """))
        total_colors = result.fetchone().total_colors
        print(f"      📊 총 색상 코드: {total_colors}개 (목표: 324개)")
        
        # 최종 결과
        print(f"\n🎯 최종 결과:")
        if all_complete:
            print(f"   ✅ 모든 코드 그룹이 존재합니다!")
        else:
            print(f"   ❌ 일부 코드 그룹이 누락되었습니다!")
            
        print(f"\n📝 레거시 호환 모달 필드 순서:")
        print(f"   1. 브랜드 (Brand)")
        print(f"   2. 구분타입 (DivType)")  
        print(f"   3. 품목그룹 (ProdGroup)")
        print(f"   4. 제품타입 (ProdType)")
        print(f"   5. 제품코드 (ProdCode)")
        print(f"   6. 타입2 (ProdType2)")
        print(f"   7. 년도 (Year)")
        print(f"   8. 색상 (Color)")

if __name__ == "__main__":
    check_code_values() 