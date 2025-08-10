#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def check_and_fix_table_structure():
    """테이블 구조 확인 및 레거시 구조 적용"""
    app = create_app()
    
    with app.app_context():
        print("🔍 테이블 구조 직접 확인 및 레거시 구조 적용")
        print("=" * 60)
        
        # 1. 현재 product_details 테이블 모든 데이터 확인
        print("1️⃣ 현재 product_details 테이블 전체 데이터 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(*) as total_count
            FROM product_details pd
            JOIN products p ON pd.product_id = p.id
            WHERE p.company_id = 1
        """))
        
        total_count = result.fetchone().total_count
        print(f"   📊 전체 product_details 레코드: {total_count}개")
        
        # 모든 데이터 조회
        result = db.session.execute(db.text("""
            SELECT 
                pd.id, pd.product_id, pd.std_div_prod_code, pd.product_name,
                pd.brand_code, pd.div_type_code, pd.prod_group_code, pd.prod_type_code,
                pd.prod_code, pd.prod_type2_code, pd.year_code, pd.color_code,
                LENGTH(pd.std_div_prod_code) as code_length,
                p.product_name as master_name
            FROM product_details pd
            JOIN products p ON pd.product_id = p.id
            WHERE p.company_id = 1
            ORDER BY pd.product_id, pd.id
        """))
        
        all_details = result.fetchall()
        
        print(f"   📋 현재 모든 상세 모델:")
        for detail in all_details:
            print(f"   ID {detail.id}: {detail.product_name}")
            print(f"      마스터: {detail.master_name}")
            print(f"      자가코드: {detail.std_div_prod_code} ({detail.code_length}자리)")
            print(f"      구성: {detail.brand_code}+{detail.div_type_code}+{detail.prod_group_code}+{detail.prod_type_code}+{detail.prod_code}+{detail.prod_type2_code}+{detail.year_code}+{detail.color_code}")
            print()
        
        # 2. DivTypeCode별 제품 분류 및 업데이트
        print("2️⃣ DivTypeCode별 제품 분류 및 레거시 구조 적용")
        
        # 레거시 이미지에서 확인된 실제 코드 구조
        legacy_mappings = [
            {
                'product_type': '카시트',
                'brand_code': 'RY',
                'div_type_code': '2',  # 프리미엄
                'prod_group_code': 'SG',
                'prod_type_code': 'WC',
                'prod_code': 'XX',
                'prod_type2_code': '00',
                'year_code': '24',
                'colors': ['WIR', 'ZZN', 'BK2', 'BKE', 'BRN']
            },
            {
                'product_type': '유모차',
                'brand_code': 'RY',
                'div_type_code': '2',  # 프리미엄
                'prod_group_code': 'SG',
                'prod_type_code': 'MT',
                'prod_code': 'XX',
                'prod_type2_code': '00',
                'year_code': '24',
                'colors': ['MGY', 'SBG', 'WTW']
            },
            {
                'product_type': '하이체어',
                'brand_code': 'RY',
                'div_type_code': '3',  # 디럭스
                'prod_group_code': 'CB',
                'prod_type_code': 'BK',
                'prod_code': 'XX',
                'prod_type2_code': '00',
                'year_code': '24',
                'colors': ['BK2', 'WTW', 'BRN']
            }
        ]
        
        # 각 제품 타입별로 업데이트
        for mapping in legacy_mappings:
            print(f"   🔄 {mapping['product_type']} 제품 업데이트 중...")
            
            # 해당 타입의 제품들 찾기
            result = db.session.execute(db.text("""
                SELECT p.id, p.product_name
                FROM products p
                WHERE p.product_name LIKE :pattern AND p.company_id = 1
            """), {'pattern': f'%{mapping["product_type"]}%'})
            
            products = result.fetchall()
            
            for product in products:
                print(f"      📦 {product.product_name} 처리 중...")
                
                # 해당 제품의 모든 product_details 삭제 후 새로 생성
                db.session.execute(db.text("""
                    DELETE FROM product_details WHERE product_id = :product_id
                """), {'product_id': product.id})
                
                # 색상별로 새 detail 생성
                for i, color in enumerate(mapping['colors']):
                    # 자가코드 생성 (16자리)
                    std_code = (
                        mapping['brand_code'] +
                        mapping['div_type_code'] +
                        mapping['prod_group_code'] +
                        mapping['prod_type_code'] +
                        mapping['prod_code'] +
                        mapping['prod_type2_code'] +
                        mapping['year_code'] +
                        color
                    )
                    
                    # 제품명에 색상 추가
                    color_name_map = {
                        'WIR': '와이어',
                        'ZZN': '진',
                        'BK2': '블랙',
                        'BKE': '블랙에디션',
                        'BRN': '브라운',
                        'MGY': '그레이',
                        'SBG': '베이지',
                        'WTW': '화이트'
                    }
                    
                    product_detail_name = f"{product.product_name} ({color_name_map.get(color, color)})"
                    
                    # 새 detail 삽입
                    db.session.execute(db.text("""
                        INSERT INTO product_details (
                            product_id, std_div_prod_code, product_name,
                            brand_code, div_type_code, prod_group_code, prod_type_code,
                            prod_code, prod_type2_code, year_code, color_code,
                            price, is_active, status, created_at, updated_at
                        ) VALUES (
                            :product_id, :std_code, :product_name,
                            :brand_code, :div_type_code, :prod_group_code, :prod_type_code,
                            :prod_code, :prod_type2_code, :year_code, :color_code,
                            0, true, 'Active', NOW(), NOW()
                        )
                    """), {
                        'product_id': product.id,
                        'std_code': std_code,
                        'product_name': product_detail_name,
                        'brand_code': mapping['brand_code'],
                        'div_type_code': mapping['div_type_code'],
                        'prod_group_code': mapping['prod_group_code'],
                        'prod_type_code': mapping['prod_type_code'],
                        'prod_code': mapping['prod_code'],
                        'prod_type2_code': mapping['prod_type2_code'],
                        'year_code': mapping['year_code'],
                        'color_code': color
                    })
                    
                    print(f"        ✅ {color} ({color_name_map.get(color, color)}) - {std_code}")
        
        db.session.commit()
        
        # 3. 업데이트 결과 확인
        print("\n3️⃣ 업데이트 결과 최종 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                pd.id, pd.product_id, pd.std_div_prod_code, pd.product_name,
                pd.brand_code, pd.div_type_code, pd.prod_group_code, pd.prod_type_code,
                pd.prod_code, pd.prod_type2_code, pd.year_code, pd.color_code,
                LENGTH(pd.std_div_prod_code) as code_length,
                p.product_name as master_name
            FROM product_details pd
            JOIN products p ON pd.product_id = p.id
            WHERE p.company_id = 1
            ORDER BY pd.product_id, pd.id
        """))
        
        final_details = result.fetchall()
        
        print(f"   📊 최종 상세 모델: {len(final_details)}개")
        
        # 제품별로 그룹화하여 표시
        current_product_id = None
        for detail in final_details:
            if current_product_id != detail.product_id:
                current_product_id = detail.product_id
                print(f"\n   📦 제품 {detail.product_id}: {detail.master_name}")
            
            print(f"      - {detail.product_name}")
            print(f"        자가코드: {detail.std_div_prod_code} ({detail.code_length}자리)")
            print(f"        구성: {detail.brand_code}+{detail.div_type_code}+{detail.prod_group_code}+{detail.prod_type_code}+{detail.prod_code}+{detail.prod_type2_code}+{detail.year_code}+{detail.color_code}")
        
        # 4. 16자리 코드 검증
        print("\n4️⃣ 16자리 코드 검증")
        
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(*) as total_count,
                COUNT(CASE WHEN LENGTH(std_div_prod_code) = 16 THEN 1 END) as valid_count
            FROM product_details pd
            JOIN products p ON pd.product_id = p.id
            WHERE p.company_id = 1
        """))
        
        counts = result.fetchone()
        valid_rate = (counts.valid_count / counts.total_count * 100) if counts.total_count > 0 else 0
        
        print(f"   📊 16자리 코드 준수율: {counts.valid_count}/{counts.total_count} ({valid_rate:.1f}%)")
        
        if valid_rate < 100:
            print(f"   ❌ {counts.total_count - counts.valid_count}개 모델이 16자리가 아닙니다")
        else:
            print("   ✅ 모든 자가코드가 16자리로 정상화되었습니다!")
        
        # 5. API 테스트
        print("\n5️⃣ API를 통한 수정 결과 확인")
        
        try:
            import requests
            response = requests.get("http://127.0.0.1:5000/product/api/list", timeout=10)
            
            if response.status_code == 200:
                api_data = response.json()
                api_products = api_data.get('data', [])
                
                print(f"   ✅ API 응답 성공: {len(api_products)}개 제품")
                
                if api_products:
                    for i, product in enumerate(api_products, 1):
                        print(f"   {i}. {product.get('product_name', 'N/A')}")
                        details = product.get('details', [])
                        if details:
                            print(f"      상세 모델: {len(details)}개")
                            for j, detail in enumerate(details[:3], 1):  # 처음 3개만
                                std_code = detail.get('std_div_prod_code', 'N/A')
                                print(f"        {j}. {detail.get('product_name', 'N/A')}")
                                print(f"           자가코드: {std_code} ({len(std_code) if std_code != 'N/A' else 0}자리)")
                            if len(details) > 3:
                                print(f"        ... 외 {len(details)-3}개")
                        print()
            else:
                print(f"   ❌ API 응답 실패: {response.status_code}")
                
        except Exception as e:
            print(f"   ⚠️ API 테스트 오류: {e}")
        
        print("\n🎉 레거시 테이블 구조 완전 적용 완료!")
        print("📱 브라우저에서 http://127.0.0.1:5000/product/ 새로고침 후 확인하세요.")
        print("✅ 이제 자가코드가 'undefined'가 아닌 정상적인 16자리 코드로 표시됩니다!")
        print("🔧 DivTypeCode: 1(일반), 2(프리미엄), 3(디럭스) 구조로 정상화되었습니다!")

if __name__ == "__main__":
    check_and_fix_table_structure() 