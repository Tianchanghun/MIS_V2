#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def fix_and_test_product_system():
    """제품코드 구조 수정 및 전체 시스템 테스트"""
    app = create_app()
    
    with app.app_context():
        print("🔧 제품코드 구조 수정 및 시스템 테스트")
        print("=" * 60)
        
        # 1. 현재 상태 확인
        print("1️⃣ 현재 제품 데이터 상태 확인")
        result = db.session.execute(db.text("""
            SELECT COUNT(*) as total_products FROM products WHERE company_id = 1
        """))
        total_products = result.fetchone()[0]
        
        result = db.session.execute(db.text("""
            SELECT COUNT(*) as total_details FROM product_details 
            WHERE product_id IN (SELECT id FROM products WHERE company_id = 1)
        """))
        total_details = result.fetchone()[0]
        
        print(f"   📊 총 제품 수: {total_products}개")
        print(f"   📊 총 제품 상세 수: {total_details}개")
        
        # 2. 년도코드 수정 (1자리 → 2자리)
        print("\n2️⃣ 년도코드 수정 (1자리 → 2자리)")
        
        # 현재 년도코드 상태 확인
        result = db.session.execute(db.text("""
            SELECT DISTINCT year_code, LENGTH(year_code) as code_length
            FROM product_details 
            WHERE year_code IS NOT NULL
            ORDER BY year_code
        """))
        year_codes = result.fetchall()
        
        print("   현재 년도코드 상태:")
        for year in year_codes:
            print(f"     {year.year_code} (길이: {year.code_length}자리)")
        
        # 년도코드가 1자리인 경우 2자리로 변환
        if any(len(str(year.year_code)) == 1 for year in year_codes):
            print("   🔄 년도코드를 1자리에서 2자리로 변환 중...")
            
            # 년도코드 매핑 (2024년 기준으로 변환)
            year_mapping = {
                '4': '24',  # 2024년
                '3': '23',  # 2023년
                '5': '25',  # 2025년
            }
            
            for old_code, new_code in year_mapping.items():
                update_result = db.session.execute(db.text("""
                    UPDATE product_details 
                    SET year_code = :new_code,
                        std_div_prod_code = CONCAT(
                            brand_code,
                            div_type_code, 
                            prod_group_code,
                            prod_type_code,
                            prod_code,
                            prod_type2_code,
                            :new_code,
                            color_code
                        ),
                        updated_at = NOW()
                    WHERE year_code = :old_code
                """), {'old_code': old_code, 'new_code': new_code})
                
                updated_count = update_result.rowcount
                if updated_count > 0:
                    print(f"     ✅ {old_code} → {new_code}: {updated_count}개 업데이트")
            
            db.session.commit()
            print("   ✅ 년도코드 변환 완료")
        
        # 3. 수정된 제품코드 확인
        print("\n3️⃣ 수정된 제품코드 구조 확인")
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
            LIMIT 3
        """))
        
        products = result.fetchall()
        for i, product in enumerate(products, 1):
            code = product.std_div_prod_code
            print(f"   {i}. {product.product_name}")
            print(f"      코드: {code} (길이: {product.code_length}자리)")
            print(f"      구성: {product.brand_code}+{product.div_type_code}+{product.prod_group_code}+{product.prod_type_code}+{product.prod_code}+{product.prod_type2_code}+{product.year_code}+{product.color_code}")
        
        # 4. API 테스트
        print("\n4️⃣ 제품 관리 API 테스트")
        
        # Flask 앱이 실행 중인지 확인하고 API 테스트
        try:
            import requests
            api_url = "http://127.0.0.1:5000/product/api/list"
            
            print(f"   🌐 API 호출 테스트: {api_url}")
            response = requests.get(api_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ API 응답 성공")
                print(f"   📊 조회된 제품 수: {len(data.get('data', []))}개")
                
                # 첫 번째 제품 정보 출력
                if data.get('data'):
                    first_product = data['data'][0]
                    print(f"   📋 첫 번째 제품 예시:")
                    print(f"      제품명: {first_product.get('product_name', 'N/A')}")
                    print(f"      제품코드: {first_product.get('std_product_code', 'N/A')}")
                    print(f"      브랜드: {first_product.get('brand_name', 'N/A')}")
                    print(f"      가격: {first_product.get('price', 'N/A'):,}원")
            else:
                print(f"   ❌ API 응답 실패: {response.status_code}")
                print(f"   응답 내용: {response.text[:200]}")
                
        except requests.exceptions.ConnectionError:
            print("   ⚠️ Flask 앱이 실행되지 않음 - 수동으로 실행 필요")
            print("   💡 터미널에서 'python run.py' 실행 후 다시 테스트")
        except Exception as e:
            print(f"   ❌ API 테스트 오류: {e}")
        
        # 5. 코드 그룹 정보 확인
        print("\n5️⃣ 제품 관련 코드 그룹 확인")
        
        code_groups = ['브랜드', '품목', '색상', '구분타입']
        for group_name in code_groups:
            result = db.session.execute(db.text("""
                SELECT COUNT(*) as count
                FROM tbl_code 
                WHERE seq IN (
                    SELECT seq FROM tbl_code 
                    WHERE code_name = :group_name AND depth = 1
                    UNION
                    SELECT c.seq FROM tbl_code c
                    JOIN tbl_code p ON c.parent_seq = p.seq
                    WHERE p.code_name = :group_name AND p.depth = 1
                )
            """), {'group_name': group_name})
            
            count = result.fetchone()[0]
            print(f"   📋 {group_name}: {count}개")
        
        # 6. 최종 상태 요약
        print("\n6️⃣ 최종 시스템 상태")
        
        # 총 상품 수 재확인
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(p.id) as product_count,
                COUNT(pd.id) as detail_count,
                COUNT(CASE WHEN pd.std_div_prod_code IS NOT NULL THEN 1 END) as code_count
            FROM products p
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1 AND p.is_active = true
        """))
        
        summary = result.fetchone()
        print(f"   📊 활성 상품: {summary.product_count}개")
        print(f"   📊 상품 상세: {summary.detail_count}개")  
        print(f"   📊 제품코드 생성: {summary.code_count}개")
        
        success_rate = (summary.code_count / summary.detail_count * 100) if summary.detail_count > 0 else 0
        print(f"   📈 제품코드 생성률: {success_rate:.1f}%")
        
        if success_rate >= 100:
            print("\n🎉 제품 관리 시스템이 정상적으로 작동합니다!")
            print("✅ 모든 상품 정보를 정상적으로 가져올 수 있습니다.")
        else:
            print(f"\n⚠️ 일부 제품코드가 누락되었습니다 ({100-success_rate:.1f}%)")
            print("🔧 추가 수정이 필요할 수 있습니다.")

if __name__ == "__main__":
    fix_and_test_product_system() 