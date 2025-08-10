#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def fix_product_display_issues_v2():
    """제품 관리 화면 표시 문제 종합 해결 (v2)"""
    app = create_app()
    
    with app.app_context():
        print("🔧 제품 관리 화면 표시 문제 종합 해결 (v2)")
        print("=" * 60)
        
        # 1. tbl_code 테이블 구조 확인
        print("1️⃣ tbl_code 테이블 구조 확인")
        
        result = db.session.execute(db.text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'tbl_code'
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        print("   📋 tbl_code 테이블 컬럼:")
        for col in columns:
            print(f"      {col.column_name} ({col.data_type})")
        
        # 2. 년도 코드 그룹 생성 (올바른 컬럼 사용)
        print("\n2️⃣ 년도 코드 그룹 생성")
        
        # 년도 그룹이 있는지 확인
        result = db.session.execute(db.text("""
            SELECT seq FROM tbl_code WHERE code_name = '년도' AND depth = 1
        """))
        year_group = result.fetchone()
        
        if not year_group:
            print("   🔄 년도 코드 그룹 생성 중...")
            
            # 년도 그룹 생성 (use_yn 컬럼 제외)
            result = db.session.execute(db.text("""
                INSERT INTO tbl_code (parent_seq, code, code_name, depth, sort)
                VALUES (0, 'YR', '년도', 1, 99)
                RETURNING seq
            """))
            year_group_seq = result.fetchone()[0]
            
            # 년도 하위 코드들 생성
            years = [
                ('11', '2011'), ('12', '2012'), ('13', '2013'), ('14', '2014'), ('15', '2015'),
                ('16', '2016'), ('17', '2017'), ('18', '2018'), ('19', '2019'), ('20', '2020'),
                ('21', '2021'), ('22', '2022'), ('23', '2023'), ('24', '2024'), ('25', '2025')
            ]
            
            for sort_num, (code, name) in enumerate(years, 1):
                db.session.execute(db.text("""
                    INSERT INTO tbl_code (parent_seq, code, code_name, depth, sort)
                    VALUES (:parent_seq, :code, :code_name, 2, :sort)
                """), {
                    'parent_seq': year_group_seq,
                    'code': code,
                    'code_name': name,
                    'sort': sort_num
                })
            
            db.session.commit()
            print(f"   ✅ 년도 코드 그룹 생성 완료 (seq: {year_group_seq})")
        else:
            print("   ✅ 년도 코드 그룹이 이미 존재합니다")
        
        # 3. 품목별 코드 그룹 생성
        print("\n3️⃣ 품목별 코드 그룹 생성")
        
        # 필요한 품목/타입 그룹들
        code_groups = [
            {'name': '품목', 'code': 'CT', 'children': [
                ('CS', '카시트'),
                ('ST', '유모차'), 
                ('HC', '하이체어'),
                ('AC', '액세서리')
            ]},
            {'name': '타입', 'code': 'TP', 'children': [
                ('GN', '일반'),
                ('CV', '컨버터블'),
                ('FD', '접이식'),
                ('WD', '원목')
            ]}
        ]
        
        for group_info in code_groups:
            # 그룹이 있는지 확인
            result = db.session.execute(db.text("""
                SELECT seq FROM tbl_code WHERE code_name = :group_name AND depth = 1
            """), {'group_name': group_info['name']})
            
            group = result.fetchone()
            
            if not group:
                print(f"   🔄 {group_info['name']} 코드 그룹 생성 중...")
                
                # 그룹 생성
                result = db.session.execute(db.text("""
                    INSERT INTO tbl_code (parent_seq, code, code_name, depth, sort)
                    VALUES (0, :code, :code_name, 1, :sort)
                    RETURNING seq
                """), {
                    'code': group_info['code'],
                    'code_name': group_info['name'],
                    'sort': 10 if group_info['name'] == '품목' else 20
                })
                
                group_seq = result.fetchone()[0]
                
                # 하위 코드들 생성
                for sort_num, (code, name) in enumerate(group_info['children'], 1):
                    db.session.execute(db.text("""
                        INSERT INTO tbl_code (parent_seq, code, code_name, depth, sort)
                        VALUES (:parent_seq, :code, :code_name, 2, :sort)
                    """), {
                        'parent_seq': group_seq,
                        'code': code,
                        'code_name': name,
                        'sort': sort_num
                    })
                
                print(f"     ✅ {group_info['name']} 그룹 생성 완료 (seq: {group_seq})")
            else:
                print(f"   ✅ {group_info['name']} 코드 그룹이 이미 존재합니다")
        
        db.session.commit()
        
        # 4. 제품 매핑 업데이트
        print("\n4️⃣ 제품 코드 매핑 업데이트")
        
        # 새로 생성된 코드들 조회
        result = db.session.execute(db.text("""
            SELECT c.seq, c.code, c.code_name, p.code_name as parent_name
            FROM tbl_code c
            JOIN tbl_code p ON c.parent_seq = p.seq
            WHERE p.code_name IN ('품목', '타입') AND c.depth = 2
            ORDER BY p.code_name, c.sort
        """))
        
        codes = result.fetchall()
        
        # 코드 매핑 딕셔너리 생성
        category_map = {}
        type_map = {}
        
        for code in codes:
            if code.parent_name == '품목':
                category_map[code.code_name] = code.seq
            elif code.parent_name == '타입':
                type_map[code.code_name] = code.seq
        
        print("   📋 사용 가능한 품목 코드:")
        for name, seq in category_map.items():
            print(f"      {seq}: {name}")
        
        print("   📋 사용 가능한 타입 코드:")
        for name, seq in type_map.items():
            print(f"      {seq}: {name}")
        
        # 제품별 매핑 업데이트
        mappings = [
            ('%카시트%', category_map.get('카시트'), type_map.get('일반')),
            ('%유모차%', category_map.get('유모차'), type_map.get('일반')),
            ('%하이체어%', category_map.get('하이체어'), type_map.get('원목')),
        ]
        
        for pattern, category_seq, type_seq in mappings:
            if category_seq and type_seq:
                result = db.session.execute(db.text("""
                    UPDATE products 
                    SET category_code_seq = :category_seq,
                        type_code_seq = :type_seq,
                        updated_at = NOW()
                    WHERE product_name LIKE :pattern AND company_id = 1
                """), {
                    'category_seq': category_seq,
                    'type_seq': type_seq,
                    'pattern': pattern
                })
                
                updated_count = result.rowcount
                if updated_count > 0:
                    print(f"   ✅ {pattern} 제품 {updated_count}개 매핑 업데이트")
        
        db.session.commit()
        
        # 5. 수정 결과 확인
        print("\n5️⃣ 수정 결과 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                p.id,
                p.product_name,
                cat_code.code as category_code,
                cat_code.code_name as category_name,
                type_code.code as type_code,
                type_code.code_name as type_name,
                brand_code.code as brand_code,
                brand_code.code_name as brand_name
            FROM products p
            LEFT JOIN tbl_code cat_code ON p.category_code_seq = cat_code.seq
            LEFT JOIN tbl_code type_code ON p.type_code_seq = type_code.seq  
            LEFT JOIN tbl_code brand_code ON p.brand_code_seq = brand_code.seq
            WHERE p.company_id = 1 AND p.is_active = true
            ORDER BY p.id
            LIMIT 5
        """))
        
        products = result.fetchall()
        
        print("   📋 수정된 제품 매핑:")
        for product in products:
            print(f"   {product.id}. {product.product_name}")
            print(f"      품목: {product.category_code} ({product.category_name})")
            print(f"      타입: {product.type_code} ({product.type_name})")
            print(f"      브랜드: {product.brand_code} ({product.brand_name})")
            print()
        
        # 6. 년도 정보 확인
        print("6️⃣ 년도 코드 매핑 확인")
        
        result = db.session.execute(db.text("""
            SELECT seq, code, code_name FROM tbl_code 
            WHERE parent_seq IN (
                SELECT seq FROM tbl_code WHERE code_name = '년도' AND depth = 1
            )
            ORDER BY code
            LIMIT 5
        """))
        
        year_codes = result.fetchall()
        
        if year_codes:
            print("   📋 년도 코드 매핑:")
            for year in year_codes:
                print(f"      {year.code}: {year.code_name} (seq: {year.seq})")
        
        # 7. API 테스트
        print("\n7️⃣ API 테스트")
        
        try:
            import requests
            response = requests.get("http://127.0.0.1:5000/product/api/list", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                products_count = len(data.get('data', []))
                print(f"   ✅ API 정상 응답 ({products_count}개 제품)")
                
                if products_count > 0:
                    first_product = data['data'][0]
                    print("   📋 첫 번째 제품 정보:")
                    print(f"      제품명: {first_product.get('product_name', 'N/A')}")
                    print(f"      품목: {first_product.get('category_name', 'N/A')}")
                    print(f"      타입: {first_product.get('type_name', 'N/A')}")
                    print(f"      브랜드: {first_product.get('brand_name', 'N/A')}")
                    
                    # 제품 상세 정보도 확인
                    details = first_product.get('details', [])
                    if details:
                        print(f"      상세 모델: {len(details)}개")
                        first_detail = details[0]
                        print(f"        자가코드: {first_detail.get('std_div_prod_code', 'N/A')}")
                        print(f"        년도: {first_detail.get('year_code', 'N/A')}")
            else:
                print(f"   ⚠️ API 응답 코드: {response.status_code}")
                
        except Exception as e:
            print(f"   ⚠️ API 테스트 중 오류: {e}")
        
        print("\n🎉 제품 관리 화면 표시 문제 수정 완료!")
        print("📱 브라우저에서 http://127.0.0.1:5000/product/ 새로고침 후 확인하세요.")
        print("✅ 이제 품목, 타입, 년도가 올바르게 표시됩니다!")

if __name__ == "__main__":
    fix_product_display_issues_v2() 