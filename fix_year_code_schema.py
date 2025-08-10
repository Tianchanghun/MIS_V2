#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def fix_year_code_schema_and_structure():
    """year_code 스키마 수정 및 제품코드 구조 정리"""
    app = create_app()
    
    with app.app_context():
        print("🔧 year_code 스키마 수정 및 제품코드 구조 정리")
        print("=" * 60)
        
        # 1. 현재 year_code 컬럼 정보 확인
        print("1️⃣ 현재 year_code 컬럼 정보 확인")
        result = db.session.execute(db.text("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns 
            WHERE table_name = 'product_details' AND column_name = 'year_code'
        """))
        
        col_info = result.fetchone()
        if col_info:
            print(f"   컬럼: {col_info.column_name}")
            print(f"   타입: {col_info.data_type}")
            print(f"   최대길이: {col_info.character_maximum_length}")
        
        # 2. year_code 컬럼 길이 확장
        print("\n2️⃣ year_code 컬럼 길이 확장 (VARCHAR(1) → VARCHAR(2))")
        try:
            db.session.execute(db.text("""
                ALTER TABLE product_details 
                ALTER COLUMN year_code TYPE VARCHAR(2)
            """))
            db.session.commit()
            print("   ✅ year_code 컬럼 길이 확장 완료")
        except Exception as e:
            print(f"   ❌ 컬럼 수정 실패: {e}")
            db.session.rollback()
            return
        
        # 3. 년도코드 변환 (1자리 → 2자리)
        print("\n3️⃣ 년도코드 변환 (1자리 → 2자리)")
        
        # 현재 년도코드 확인
        result = db.session.execute(db.text("""
            SELECT DISTINCT year_code, COUNT(*) as count
            FROM product_details 
            WHERE year_code IS NOT NULL
            GROUP BY year_code
            ORDER BY year_code
        """))
        
        year_codes = result.fetchall()
        print("   현재 년도코드:")
        for year in year_codes:
            print(f"     {year.year_code}: {year.count}개")
        
        # 년도코드 매핑 및 변환
        year_mapping = {
            '4': '24',  # 2024년
            '3': '23',  # 2023년
            '5': '25',  # 2025년
        }
        
        for old_code, new_code in year_mapping.items():
            result = db.session.execute(db.text("""
                SELECT COUNT(*) as count 
                FROM product_details 
                WHERE year_code = :old_code
            """), {'old_code': old_code})
            
            count = result.fetchone()[0]
            if count > 0:
                print(f"   🔄 {old_code} → {new_code} 변환 중... ({count}개)")
                
                # 년도코드 업데이트
                db.session.execute(db.text("""
                    UPDATE product_details 
                    SET year_code = :new_code,
                        updated_at = NOW()
                    WHERE year_code = :old_code
                """), {'old_code': old_code, 'new_code': new_code})
                
                print(f"     ✅ {old_code} → {new_code} 변환 완료")
        
        db.session.commit()
        
        # 4. 제품코드 재생성 (16자리)
        print("\n4️⃣ 제품코드 재생성 (15자리 → 16자리)")
        
        result = db.session.execute(db.text("""
            UPDATE product_details 
            SET std_div_prod_code = CONCAT(
                brand_code,
                div_type_code, 
                prod_group_code,
                prod_type_code,
                prod_code,
                prod_type2_code,
                year_code,
                color_code
            ),
            updated_at = NOW()
            WHERE brand_code IS NOT NULL 
              AND div_type_code IS NOT NULL
              AND prod_group_code IS NOT NULL
              AND prod_type_code IS NOT NULL
              AND prod_code IS NOT NULL
              AND prod_type2_code IS NOT NULL
              AND year_code IS NOT NULL
              AND color_code IS NOT NULL
        """))
        
        updated_count = result.rowcount
        db.session.commit()
        print(f"   ✅ {updated_count}개 제품코드 재생성 완료")
        
        # 5. 수정 결과 확인
        print("\n5️⃣ 수정 결과 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                std_div_prod_code,
                LENGTH(std_div_prod_code) as code_length,
                brand_code, div_type_code, prod_group_code, prod_type_code,
                prod_code, prod_type2_code, year_code, color_code,
                product_name
            FROM product_details 
            WHERE std_div_prod_code IS NOT NULL
            ORDER BY id
            LIMIT 5
        """))
        
        products = result.fetchall()
        print("   📋 수정된 제품코드 샘플:")
        
        for i, product in enumerate(products, 1):
            code = product.std_div_prod_code
            expected_length = 16
            status = "✅" if product.code_length == expected_length else "❌"
            
            print(f"   {i}. {product.product_name}")
            print(f"      코드: {code} (길이: {product.code_length}자리) {status}")
            print(f"      구성: {product.brand_code}+{product.div_type_code}+{product.prod_group_code}+{product.prod_type_code}+{product.prod_code}+{product.prod_type2_code}+{product.year_code}+{product.color_code}")
            
            # 재구성 검증
            reconstructed = (product.brand_code + product.div_type_code + 
                           product.prod_group_code + product.prod_type_code + 
                           product.prod_code + product.prod_type2_code + 
                           product.year_code + product.color_code)
            
            match_status = "✅" if reconstructed == code else "❌"
            print(f"      검증: {match_status} (재구성: {reconstructed})")
            print()
        
        # 6. 통계 요약
        print("6️⃣ 최종 통계")
        
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(*) as total_count,
                COUNT(CASE WHEN LENGTH(std_div_prod_code) = 16 THEN 1 END) as correct_length_count,
                COUNT(CASE WHEN std_div_prod_code IS NOT NULL THEN 1 END) as code_generated_count
            FROM product_details
        """))
        
        stats = result.fetchone()
        
        print(f"   📊 총 제품 상세: {stats.total_count}개")
        print(f"   📊 제품코드 생성: {stats.code_generated_count}개")
        print(f"   📊 16자리 코드: {stats.correct_length_count}개")
        
        success_rate = (stats.correct_length_count / stats.total_count * 100) if stats.total_count > 0 else 0
        print(f"   📈 성공률: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("\n🎉 제품코드 구조 수정이 성공적으로 완료되었습니다!")
            print("✅ 이제 16자리 레거시 호환 제품코드로 정상 작동합니다.")
        else:
            print(f"\n⚠️ 일부 제품코드 수정이 완료되지 않았습니다.")
            print("🔧 추가 확인이 필요합니다.")

if __name__ == "__main__":
    fix_year_code_schema_and_structure() 