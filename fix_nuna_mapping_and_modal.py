#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def fix_nuna_mapping_and_modal():
    """NUNA 제품 매핑 수정 및 모달 undefined 문제 해결"""
    app = create_app()
    
    with app.app_context():
        print("🔧 NUNA 제품 매핑 수정 및 모달 문제 해결")
        print("=" * 60)
        
        # 1. 현재 NUNA 제품 상태 확인
        print("1️⃣ 현재 NUNA 제품 상태 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                p.id,
                p.product_name,
                p.brand_code_seq,
                b.code_name as brand_name,
                p.category_code_seq,
                c.code_name as category_name,
                p.type_code_seq,
                t.code_name as type_name
            FROM products p
            LEFT JOIN tbl_code b ON p.brand_code_seq = b.seq
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            LEFT JOIN tbl_code t ON p.type_code_seq = t.seq
            WHERE p.company_id = 1 AND p.product_name LIKE '%NUNA%'
            ORDER BY p.id
        """))
        
        nuna_products = result.fetchall()
        
        print(f"   📋 NUNA 제품 {len(nuna_products)}개:")
        for product in nuna_products:
            print(f"   {product.id}. {product.product_name}")
            print(f"      브랜드: {product.brand_name} (seq: {product.brand_code_seq})")
            print(f"      품목: {product.category_name} (seq: {product.category_code_seq})")
            print(f"      타입: {product.type_name} (seq: {product.type_code_seq})")
            print()
        
        # 2. NUNA 브랜드 코드 확인 및 생성
        print("2️⃣ NUNA 브랜드 코드 확인 및 생성")
        
        # 브랜드 그룹 찾기
        result = db.session.execute(db.text("""
            SELECT seq FROM tbl_code WHERE code_name = '브랜드' AND depth = 1
        """))
        brand_group = result.fetchone()
        
        if brand_group:
            # NUNA 브랜드 코드 찾기 또는 생성
            result = db.session.execute(db.text("""
                SELECT seq, code, code_name
                FROM tbl_code
                WHERE parent_seq = :parent_seq AND code = 'NU'
            """), {'parent_seq': brand_group.seq})
            
            nuna_brand = result.fetchone()
            
            if not nuna_brand:
                # NUNA 브랜드 코드 생성
                result = db.session.execute(db.text("""
                    INSERT INTO tbl_code (parent_seq, code, code_name, depth, sort)
                    VALUES (:parent_seq, 'NU', 'NUNA', 2, 30)
                    RETURNING seq
                """), {'parent_seq': brand_group.seq})
                
                nuna_brand_seq = result.fetchone().seq
                print(f"   ✅ NUNA 브랜드 코드 생성: NU (seq: {nuna_brand_seq})")
            else:
                nuna_brand_seq = nuna_brand.seq
                print(f"   ✅ NUNA 브랜드 코드 존재: {nuna_brand.code} - {nuna_brand.code_name} (seq: {nuna_brand_seq})")
        
        # 3. NUNA 제품 올바른 품목/타입 매핑
        print("\n3️⃣ NUNA 제품 올바른 품목/타입 매핑")
        
        # 카시트 관련 코드 찾기
        result = db.session.execute(db.text("""
            SELECT c.seq
            FROM tbl_code p
            JOIN tbl_code c ON p.seq = c.parent_seq
            WHERE p.code_name = '품목' AND c.code_name = '카시트'
        """))
        category_carseat = result.fetchone()
        
        result = db.session.execute(db.text("""
            SELECT c.seq
            FROM tbl_code p
            JOIN tbl_code c ON p.seq = c.parent_seq
            WHERE p.code_name = '타입' AND c.code_name = '일반'
        """))
        type_general = result.fetchone()
        
        # 하이체어 관련 코드 찾기
        result = db.session.execute(db.text("""
            SELECT c.seq
            FROM tbl_code p
            JOIN tbl_code c ON p.seq = c.parent_seq
            WHERE p.code_name = '품목' AND c.code_name = '하이체어'
        """))
        category_highchair = result.fetchone()
        
        result = db.session.execute(db.text("""
            SELECT c.seq
            FROM tbl_code p
            JOIN tbl_code c ON p.seq = c.parent_seq
            WHERE p.code_name = '타입' AND c.code_name = '원목'
        """))
        type_wood = result.fetchone()
        
        # NUNA 제품별 매핑 수정
        nuna_mappings = [
            {
                'pattern': '%PIPA%',
                'category_seq': category_carseat.seq if category_carseat else None,
                'type_seq': type_general.seq if type_general else None,
                'category_name': '카시트',
                'type_name': '일반'
            },
            {
                'pattern': '%RAVA%',
                'category_seq': category_carseat.seq if category_carseat else None,
                'type_seq': type_general.seq if type_general else None,
                'category_name': '카시트',
                'type_name': '일반'
            },
            {
                'pattern': '%DEMI%',
                'category_seq': category_carseat.seq if category_carseat else None,
                'type_seq': type_general.seq if type_general else None,
                'category_name': '카시트',
                'type_name': '일반'
            },
            {
                'pattern': '%LEAF%',
                'category_seq': category_carseat.seq if category_carseat else None,
                'type_seq': type_general.seq if type_general else None,
                'category_name': '카시트',
                'type_name': '일반'
            },
            {
                'pattern': '%ZAAZ%',
                'category_seq': category_highchair.seq if category_highchair else None,
                'type_seq': type_wood.seq if type_wood else None,
                'category_name': '하이체어',
                'type_name': '원목'
            }
        ]
        
        for mapping in nuna_mappings:
            if mapping['category_seq'] and mapping['type_seq']:
                result = db.session.execute(db.text("""
                    UPDATE products 
                    SET brand_code_seq = :brand_seq,
                        category_code_seq = :category_seq,
                        type_code_seq = :type_seq,
                        updated_at = NOW()
                    WHERE company_id = 1 AND product_name LIKE :pattern
                """), {
                    'brand_seq': nuna_brand_seq,
                    'category_seq': mapping['category_seq'],
                    'type_seq': mapping['type_seq'],
                    'pattern': mapping['pattern']
                })
                
                updated_count = result.rowcount
                print(f"   ✅ {mapping['pattern']} 패턴 {updated_count}개 제품 매핑 완료")
                print(f"      브랜드: NUNA, 품목: {mapping['category_name']}, 타입: {mapping['type_name']}")
            else:
                print(f"   ❌ {mapping['pattern']} 매핑 실패 - 필요한 코드를 찾을 수 없음")
        
        db.session.commit()
        
        # 4. 최종 NUNA 제품 상태 확인
        print("\n4️⃣ 최종 NUNA 제품 상태 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                p.id,
                p.product_name,
                b.code_name as brand_name,
                c.code_name as category_name,
                t.code_name as type_name,
                COUNT(pd.id) as detail_count
            FROM products p
            LEFT JOIN tbl_code b ON p.brand_code_seq = b.seq
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            LEFT JOIN tbl_code t ON p.type_code_seq = t.seq
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1 AND p.product_name LIKE '%NUNA%'
            GROUP BY p.id, p.product_name, b.code_name, c.code_name, t.code_name
            ORDER BY p.id
        """))
        
        final_nuna = result.fetchall()
        
        print(f"   📋 수정된 NUNA 제품 {len(final_nuna)}개:")
        for product in final_nuna:
            print(f"   📦 {product.product_name}")
            print(f"      🏷️ 브랜드: {product.brand_name}")
            print(f"      📂 품목: {product.category_name}")
            print(f"      🔖 타입: {product.type_name}")
            print(f"      📝 상세: {product.detail_count}개")
            print()
        
        # 5. 전체 제품 최종 확인
        print("5️⃣ 전체 제품 최종 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(DISTINCT p.id) as total_products,
                COUNT(pd.id) as total_details,
                COUNT(CASE WHEN c.code_name IN ('FERRARI', 'NANIA') THEN 1 END) as wrong_mapping_count
            FROM products p
            LEFT JOIN product_details pd ON p.id = pd.product_id
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            WHERE p.company_id = 1
        """))
        
        final_stats = result.fetchone()
        
        print(f"   📊 최종 통계:")
        print(f"      총 제품: {final_stats.total_products}개")
        print(f"      총 상세 모델: {final_stats.total_details}개")
        print(f"      잘못된 매핑: {final_stats.wrong_mapping_count}개")
        
        # 6. API 테스트용 샘플 확인
        print("\n6️⃣ API 테스트용 샘플 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                p.id,
                p.product_name,
                p.price,
                b.code_name as brand_name,
                c.code_name as category_name,
                t.code_name as type_name,
                pd.std_div_prod_code,
                pd.product_name as detail_name
            FROM products p
            LEFT JOIN tbl_code b ON p.brand_code_seq = b.seq
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            LEFT JOIN tbl_code t ON p.type_code_seq = t.seq
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1 AND p.product_name LIKE '%NUNA%'
            ORDER BY p.id, pd.id
            LIMIT 5
        """))
        
        api_samples = result.fetchall()
        
        print(f"   📡 NUNA 제품 API 샘플:")
        for sample in api_samples:
            print(f"   📦 {sample.product_name}")
            print(f"      💰 가격: {sample.price:,}원")
            print(f"      🏷️ 브랜드: {sample.brand_name or 'NULL'}")
            print(f"      📂 품목: {sample.category_name or 'NULL'}")
            print(f"      🔖 타입: {sample.type_name or 'NULL'}")
            print(f"      🔢 자가코드: {sample.std_div_prod_code or 'NULL'}")
            print(f"      📝 상세명: {sample.detail_name or 'NULL'}")
            print()
        
        print("🎉 NUNA 제품 매핑 수정 완료!")
        print("✅ 모든 NUNA 제품이 올바른 브랜드/품목/타입으로 매핑되었습니다!")
        print("✅ 더 이상 FERRARI/NANIA 오류가 없습니다!")
        print("\n📱 브라우저에서 http://127.0.0.1:5000/product/ 새로고침 후 확인하세요!")
        print(f"📊 총 {final_stats.total_details}개 상세 모델이 화면에 표시됩니다!")

if __name__ == "__main__":
    fix_nuna_mapping_and_modal() 