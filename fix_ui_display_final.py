#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def fix_ui_display_final():
    """웹 UI에서 레거시 구조 데이터가 올바르게 표시되도록 최종 수정"""
    app = create_app()
    
    with app.app_context():
        print("🔧 웹 UI 레거시 구조 표시 최종 수정")
        print("=" * 60)
        
        # 1. 현재 products 테이블의 코드 매핑 상태 확인
        print("1️⃣ 현재 products 테이블 코드 매핑 상태 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                p.id,
                p.product_name,
                p.brand_code_seq,
                p.category_code_seq,
                p.type_code_seq,
                p.price,
                COUNT(pd.id) as detail_count
            FROM products p
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1
            GROUP BY p.id, p.product_name, p.brand_code_seq, p.category_code_seq, p.type_code_seq, p.price
            ORDER BY p.id
        """))
        
        products = result.fetchall()
        
        print(f"   📊 현재 제품 {len(products)}개:")
        for product in products:
            print(f"   {product.id}. {product.product_name}")
            print(f"      브랜드seq: {product.brand_code_seq}, 품목seq: {product.category_code_seq}, 타입seq: {product.type_code_seq}")
            print(f"      가격: {product.price:,}원, 상세: {product.detail_count}개")
        
        # 2. 코드 그룹 매핑 정보 확인 및 수정
        print("\n2️⃣ 코드 그룹 매핑 정보 확인 및 수정")
        
        # 브랜드 코드 확인
        result = db.session.execute(db.text("""
            SELECT c.seq, c.code, c.code_name
            FROM tbl_code p
            JOIN tbl_code c ON p.seq = c.parent_seq
            WHERE p.code_name = '브랜드' AND c.code = 'RY'
        """))
        ry_brand = result.fetchone()
        
        if ry_brand:
            print(f"   ✅ RY 브랜드 코드: seq={ry_brand.seq}, 이름={ry_brand.code_name}")
        else:
            print("   ❌ RY 브랜드 코드를 찾을 수 없음")
        
        # 품목 코드 확인 및 생성
        result = db.session.execute(db.text("""
            SELECT c.seq, c.code, c.code_name
            FROM tbl_code p
            JOIN tbl_code c ON p.seq = c.parent_seq
            WHERE p.code_name = '품목' AND c.code_name IN ('카시트', '유모차', '하이체어')
        """))
        category_codes = result.fetchall()
        
        print(f"   📋 품목 코드 {len(category_codes)}개:")
        for code in category_codes:
            print(f"      {code.code}: {code.code_name} (seq: {code.seq})")
        
        # 타입 코드 확인 및 생성
        result = db.session.execute(db.text("""
            SELECT c.seq, c.code, c.code_name
            FROM tbl_code p
            JOIN tbl_code c ON p.seq = c.parent_seq
            WHERE p.code_name = '타입' AND c.code_name IN ('일반', '프리미엄', '스마트')
        """))
        type_codes = result.fetchall()
        
        print(f"   📋 타입 코드 {len(type_codes)}개:")
        for code in type_codes:
            print(f"      {code.code}: {code.code_name} (seq: {code.seq})")
        
        # 3. products 테이블 코드 매핑 업데이트
        print("\n3️⃣ products 테이블 코드 매핑 업데이트")
        
        # 브랜드 매핑 (모든 제품을 RY로)
        if ry_brand:
            db.session.execute(db.text("""
                UPDATE products 
                SET brand_code_seq = :brand_seq, updated_at = NOW()
                WHERE company_id = 1
            """), {'brand_seq': ry_brand.seq})
            print(f"   ✅ 모든 제품의 브랜드를 RY (seq: {ry_brand.seq})로 설정")
        
        # 제품별 품목 및 타입 매핑
        product_mappings = [
            {
                'name_pattern': '%카시트%',
                'category_name': '카시트',
                'type_name': '일반'
            },
            {
                'name_pattern': '%유모차%',
                'category_name': '유모차', 
                'type_name': '프리미엄'
            },
            {
                'name_pattern': '%하이체어%',
                'category_name': '하이체어',
                'type_name': '스마트'
            }
        ]
        
        for mapping in product_mappings:
            # 품목 코드 찾기
            result = db.session.execute(db.text("""
                SELECT c.seq
                FROM tbl_code p
                JOIN tbl_code c ON p.seq = c.parent_seq
                WHERE p.code_name = '품목' AND c.code_name = :category_name
            """), {'category_name': mapping['category_name']})
            category_code = result.fetchone()
            
            # 타입 코드 찾기
            result = db.session.execute(db.text("""
                SELECT c.seq
                FROM tbl_code p
                JOIN tbl_code c ON p.seq = c.parent_seq
                WHERE p.code_name = '타입' AND c.code_name = :type_name
            """), {'type_name': mapping['type_name']})
            type_code = result.fetchone()
            
            if category_code and type_code:
                # 해당 패턴의 제품들 업데이트
                result = db.session.execute(db.text("""
                    UPDATE products 
                    SET category_code_seq = :category_seq,
                        type_code_seq = :type_seq,
                        updated_at = NOW()
                    WHERE company_id = 1 AND product_name LIKE :pattern
                """), {
                    'category_seq': category_code.seq,
                    'type_seq': type_code.seq,
                    'pattern': mapping['name_pattern']
                })
                
                updated_count = result.rowcount
                print(f"   ✅ {mapping['category_name']} 제품 {updated_count}개 매핑 완료")
                print(f"      품목: {mapping['category_name']} (seq: {category_code.seq})")
                print(f"      타입: {mapping['type_name']} (seq: {type_code.seq})")
            else:
                print(f"   ❌ {mapping['category_name']} 또는 {mapping['type_name']} 코드를 찾을 수 없음")
        
        # 4. 년도 코드 그룹에 실제 사용중인 년도 추가
        print("\n4️⃣ 년도 코드 그룹에 실제 사용중인 년도 추가")
        
        # 사용중인 년도 확인
        result = db.session.execute(db.text("""
            SELECT DISTINCT year_code
            FROM product_details
            WHERE year_code IS NOT NULL
            ORDER BY year_code
        """))
        used_years = result.fetchall()
        
        print(f"   📊 사용중인 년도: {[year.year_code for year in used_years]}")
        
        # 년도 그룹 찾기
        result = db.session.execute(db.text("""
            SELECT seq FROM tbl_code WHERE code_name = '년도' AND depth = 1
        """))
        year_group = result.fetchone()
        
        if year_group:
            # 각 년도 코드 추가 (중복 체크)
            for year in used_years:
                # 이미 존재하는지 확인
                result = db.session.execute(db.text("""
                    SELECT seq FROM tbl_code 
                    WHERE parent_seq = :parent_seq AND code = :code
                """), {
                    'parent_seq': year_group.seq,
                    'code': year.year_code
                })
                
                existing = result.fetchone()
                
                if not existing:
                    # 년도 이름 생성 (14 -> 2014, 24 -> 2024)
                    if len(year.year_code) == 2:
                        if int(year.year_code) > 50:  # 50 이상이면 19xx년
                            year_name = f"19{year.year_code}"
                        else:  # 50 이하면 20xx년
                            year_name = f"20{year.year_code}"
                    else:
                        year_name = year.year_code
                    
                    db.session.execute(db.text("""
                        INSERT INTO tbl_code (parent_seq, code, code_name, depth, sort)
                        VALUES (:parent_seq, :code, :code_name, 2, :sort)
                    """), {
                        'parent_seq': year_group.seq,
                        'code': year.year_code,
                        'code_name': year_name,
                        'sort': int(year.year_code) if year.year_code.isdigit() else 99
                    })
                    
                    print(f"      ✅ 년도 코드 추가: {year.year_code} -> {year_name}")
                else:
                    print(f"      ✅ 년도 코드 이미 존재: {year.year_code}")
        
        db.session.commit()
        
        # 5. 최종 매핑 결과 확인
        print("\n5️⃣ 최종 매핑 결과 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                p.id,
                p.product_name,
                p.price,
                b.code_name as brand_name,
                c.code_name as category_name,
                t.code_name as type_name,
                COUNT(pd.id) as detail_count
            FROM products p
            LEFT JOIN tbl_code b ON p.brand_code_seq = b.seq
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            LEFT JOIN tbl_code t ON p.type_code_seq = t.seq
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1
            GROUP BY p.id, p.product_name, p.price, b.code_name, c.code_name, t.code_name
            ORDER BY p.id
        """))
        
        final_products = result.fetchall()
        
        print(f"   📊 최종 매핑 결과 ({len(final_products)}개 제품):")
        for product in final_products:
            print(f"   📦 {product.product_name}")
            print(f"      💰 가격: {product.price:,}원")
            print(f"      🏷️ 브랜드: {product.brand_name or 'N/A'}")
            print(f"      📂 품목: {product.category_name or 'N/A'}")
            print(f"      🔖 타입: {product.type_name or 'N/A'}")
            print(f"      📝 상세: {product.detail_count}개")
            print()
        
        # 6. API 응답 테스트용 샘플 조회
        print("6️⃣ API 응답 테스트용 샘플 조회")
        
        result = db.session.execute(db.text("""
            SELECT 
                p.id,
                p.product_name,
                p.price,
                b.code_name as brand_name,
                c.code_name as category_name,
                t.code_name as type_name,
                pd.std_div_prod_code,
                pd.product_name as detail_name,
                LENGTH(pd.std_div_prod_code) as code_length
            FROM products p
            LEFT JOIN tbl_code b ON p.brand_code_seq = b.seq
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            LEFT JOIN tbl_code t ON p.type_code_seq = t.seq
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1
            LIMIT 3
        """))
        
        api_samples = result.fetchall()
        
        print(f"   📡 API 응답 샘플:")
        for sample in api_samples:
            print(f"   📦 {sample.product_name}")
            print(f"      💰 가격: {sample.price:,}원")
            print(f"      🏷️ 브랜드: {sample.brand_name or 'N/A'}")
            print(f"      📂 품목: {sample.category_name or 'N/A'}")
            print(f"      🔖 타입: {sample.type_name or 'N/A'}")
            print(f"      🔢 자가코드: {sample.std_div_prod_code} ({sample.code_length}자리)")
            print(f"      📝 상세명: {sample.detail_name}")
            print()
        
        print("🎉 웹 UI 레거시 구조 표시 최종 수정 완료!")
        print("✅ products 테이블의 브랜드, 품목, 타입 매핑이 완료되었습니다!")
        print("✅ 년도 코드가 실제 사용 데이터 기준으로 추가되었습니다!")
        print("✅ 이제 웹 UI와 모달에서 올바른 정보가 표시됩니다!")
        print("\n📱 브라우저에서 http://127.0.0.1:5000/product/ 새로고침 후 확인하세요!")

if __name__ == "__main__":
    fix_ui_display_final() 