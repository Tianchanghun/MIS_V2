#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def check_product_display_data():
    """제품 관리 화면 데이터 표시 문제 진단"""
    app = create_app()
    
    with app.app_context():
        print("🔍 제품 관리 화면 데이터 표시 문제 진단")
        print("=" * 60)
        
        # 1. 제품 데이터와 코드 매핑 확인
        print("1️⃣ 제품 데이터와 코드 매핑 상태 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                p.id,
                p.product_name,
                p.category_code_seq,
                p.type_code_seq,
                p.brand_code_seq,
                
                -- 품목 정보
                cat_code.code as category_code,
                cat_code.code_name as category_name,
                
                -- 타입 정보  
                type_code.code as type_code,
                type_code.code_name as type_name,
                
                -- 브랜드 정보
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
        
        print("   📋 제품별 코드 매핑 상태:")
        for product in products:
            print(f"   {product.id}. {product.product_name}")
            print(f"      품목: {product.category_code_seq} → {product.category_code} ({product.category_name})")
            print(f"      타입: {product.type_code_seq} → {product.type_code} ({product.type_name})")  
            print(f"      브랜드: {product.brand_code_seq} → {product.brand_code} ({product.brand_name})")
            print()
        
        # 2. 제품 상세에서 년도 정보 확인
        print("2️⃣ 제품 상세의 년도 정보 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                pd.product_id,
                pd.year_code,
                p.product_name,
                COUNT(*) as detail_count
            FROM product_details pd
            JOIN products p ON pd.product_id = p.id
            WHERE p.company_id = 1
            GROUP BY pd.product_id, pd.year_code, p.product_name
            ORDER BY pd.product_id
        """))
        
        year_data = result.fetchall()
        
        print("   📋 제품별 년도 정보:")
        for data in year_data:
            print(f"   제품 {data.product_id} ({data.product_name}): 년도 {data.year_code} ({data.detail_count}개 모델)")
        
        # 3. API에서 실제 반환되는 데이터 확인
        print("\n3️⃣ API 응답 데이터 구조 확인")
        
        try:
            import requests
            response = requests.get("http://127.0.0.1:5000/product/api/list", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                products_api = data.get('data', [])
                
                print(f"   ✅ API 응답 성공 ({len(products_api)}개 제품)")
                
                if products_api:
                    first_product = products_api[0]
                    print("   📋 첫 번째 제품 API 응답 구조:")
                    for key, value in first_product.items():
                        if key == 'details':
                            print(f"      {key}: {len(value)}개 상세 모델")
                            if value:
                                detail = value[0]
                                print(f"        첫 번째 상세:")
                                for detail_key, detail_value in detail.items():
                                    print(f"          {detail_key}: {detail_value}")
                        else:
                            print(f"      {key}: {value}")
            else:
                print(f"   ❌ API 응답 실패: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ API 테스트 오류: {e}")
        
        # 4. 년도 코드 매핑 테이블 확인
        print("\n4️⃣ 년도 코드 매핑 테이블 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                seq, code, code_name, parent_seq
            FROM tbl_code 
            WHERE parent_seq IN (
                SELECT seq FROM tbl_code WHERE code_name = '년도' AND depth = 1
            )
            ORDER BY code
        """))
        
        year_codes = result.fetchall()
        
        if year_codes:
            print("   📋 년도 코드 매핑:")
            for year in year_codes:
                print(f"      {year.code}: {year.code_name} (seq: {year.seq})")
        else:
            print("   ⚠️ 년도 코드 그룹이 없습니다!")
        
        # 5. 코드 그룹 전체 확인
        print("\n5️⃣ 모든 코드 그룹 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                code_name as group_name,
                COUNT(CASE WHEN depth > 1 THEN 1 END) as child_count
            FROM tbl_code 
            WHERE depth = 1
            GROUP BY code_name
            ORDER BY code_name
        """))
        
        code_groups = result.fetchall()
        
        print("   📋 코드 그룹별 하위 항목 수:")
        for group in code_groups:
            print(f"      {group.group_name}: {group.child_count}개")
        
        # 6. 문제점 분석 및 해결 방안 제시
        print("\n6️⃣ 문제점 분석 및 해결 방안")
        
        issues = []
        
        # 년도 코드 매핑 확인
        if not year_codes:
            issues.append("년도 코드 그룹이 설정되지 않음")
        
        # 제품의 코드 매핑 확인
        null_mappings = 0
        for product in products:
            if not product.category_name or not product.type_name or not product.brand_name:
                null_mappings += 1
        
        if null_mappings > 0:
            issues.append(f"{null_mappings}개 제품의 코드 매핑이 누락됨")
        
        if issues:
            print("   ❌ 발견된 문제점:")
            for i, issue in enumerate(issues, 1):
                print(f"      {i}. {issue}")
            
            print("\n   🔧 해결 방안:")
            if "년도 코드 그룹이 설정되지 않음" in str(issues):
                print("      - 년도 코드 그룹 및 하위 코드 생성 필요")
            if "코드 매핑이 누락됨" in str(issues):
                print("      - 제품 테이블의 코드 참조 필드 업데이트 필요")
        else:
            print("   ✅ 코드 매핑 상태 정상")

if __name__ == "__main__":
    check_product_display_data() 