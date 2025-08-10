#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def check_current_data_status():
    """현재 데이터베이스 상태 정확 확인"""
    app = create_app()
    
    with app.app_context():
        print("🔍 현재 데이터베이스 상태 정확 확인")
        print("=" * 60)
        
        # 1. 총 레코드 수 확인
        print("1️⃣ 총 레코드 수 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(DISTINCT p.id) as product_count,
                COUNT(pd.id) as total_detail_count,
                COUNT(CASE WHEN LENGTH(pd.std_div_prod_code) = 16 THEN 1 END) as valid_16_count
            FROM products p
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1
        """))
        
        totals = result.fetchone()
        print(f"   📊 제품: {totals.product_count}개")
        print(f"   📊 총 상세 모델: {totals.total_detail_count}개")
        print(f"   📊 16자리 코드: {totals.valid_16_count}개")
        
        # 2. 제품별 상세 개수 확인
        print("\n2️⃣ 제품별 상세 개수 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                p.id,
                p.product_name,
                p.price,
                COUNT(pd.id) as detail_count,
                STRING_AGG(DISTINCT pd.std_div_prod_code, ', ' ORDER BY pd.std_div_prod_code) as codes
            FROM products p
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1
            GROUP BY p.id, p.product_name, p.price
            ORDER BY p.id
        """))
        
        products = result.fetchall()
        
        print(f"   📋 제품별 상세 현황:")
        total_details = 0
        for product in products:
            total_details += product.detail_count
            print(f"   {product.id}. {product.product_name}")
            print(f"      💰 가격: {product.price:,}원")
            print(f"      📝 상세: {product.detail_count}개")
            if product.codes:
                codes_list = product.codes.split(', ')
                for i, code in enumerate(codes_list[:3]):  # 처음 3개만 표시
                    print(f"         {i+1}. {code}")
                if len(codes_list) > 3:
                    print(f"         ... 외 {len(codes_list)-3}개")
            print()
        
        print(f"   ✅ 총합: {total_details}개 상세 모델")
        
        # 3. UI 표시 문제 진단
        print("\n3️⃣ UI 표시 문제 진단")
        
        # 자가코드가 undefined로 나오는 원인 확인
        result = db.session.execute(db.text("""
            SELECT 
                pd.id,
                pd.product_id,
                pd.std_div_prod_code,
                pd.product_name,
                LENGTH(pd.std_div_prod_code) as code_length,
                CASE 
                    WHEN pd.std_div_prod_code IS NULL THEN 'NULL'
                    WHEN pd.std_div_prod_code = '' THEN 'EMPTY'
                    WHEN LENGTH(pd.std_div_prod_code) != 16 THEN 'WRONG_LENGTH'
                    ELSE 'OK'
                END as code_status
            FROM product_details pd
            ORDER BY pd.product_id, pd.id
            LIMIT 10
        """))
        
        details = result.fetchall()
        
        print(f"   🔍 상세 모델 자가코드 상태 (처음 10개):")
        for detail in details:
            print(f"   ID: {detail.id} | 제품ID: {detail.product_id}")
            print(f"      자가코드: '{detail.std_div_prod_code}' ({detail.code_length}자리)")
            print(f"      상태: {detail.code_status}")
            print(f"      상세명: {detail.product_name}")
            print()
        
        # 4. 브랜드/품목/타입 매핑 상태 확인
        print("4️⃣ 브랜드/품목/타입 매핑 상태 확인")
        
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
            WHERE p.company_id = 1
            ORDER BY p.id
        """))
        
        mappings = result.fetchall()
        
        print(f"   🏷️ 제품 매핑 상태:")
        for mapping in mappings:
            print(f"   {mapping.id}. {mapping.product_name}")
            print(f"      브랜드: {mapping.brand_name or 'NULL'} (seq: {mapping.brand_code_seq})")
            print(f"      품목: {mapping.category_name or 'NULL'} (seq: {mapping.category_code_seq})")
            print(f"      타입: {mapping.type_name or 'NULL'} (seq: {mapping.type_code_seq})")
            print()
        
        # 5. API 응답 시뮬레이션
        print("5️⃣ API 응답 시뮬레이션")
        
        result = db.session.execute(db.text("""
            SELECT 
                p.id,
                p.product_name,
                p.price,
                b.code_name as brand_name,
                c.code_name as category_name,
                t.code_name as type_name,
                JSON_AGG(
                    JSON_BUILD_OBJECT(
                        'id', pd.id,
                        'std_div_prod_code', pd.std_div_prod_code,
                        'product_name', pd.product_name,
                        'status', pd.status
                    ) ORDER BY pd.id
                ) as details
            FROM products p
            LEFT JOIN tbl_code b ON p.brand_code_seq = b.seq
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            LEFT JOIN tbl_code t ON p.type_code_seq = t.seq
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1
            GROUP BY p.id, p.product_name, p.price, b.code_name, c.code_name, t.code_name
            ORDER BY p.id
            LIMIT 3
        """))
        
        api_products = result.fetchall()
        
        print(f"   📡 API 응답 시뮬레이션 (첫 3개 제품):")
        for product in api_products:
            print(f"   📦 {product.product_name}")
            print(f"      💰 가격: {product.price:,}원")
            print(f"      🏷️ 브랜드: {product.brand_name or 'NULL'}")
            print(f"      📂 품목: {product.category_name or 'NULL'}")
            print(f"      🔖 타입: {product.type_name or 'NULL'}")
            
            details = product.details[0] if product.details and product.details[0] else {}
            if details and 'std_div_prod_code' in details:
                print(f"      🔢 첫 번째 자가코드: {details.get('std_div_prod_code', 'NULL')}")
                print(f"      📝 첫 번째 상세명: {details.get('product_name', 'NULL')}")
            else:
                print(f"      ❌ 상세 정보 없음")
            print()
        
        # 6. 문제 원인 분석
        print("6️⃣ 문제 원인 분석")
        
        issues = []
        
        # NULL 자가코드 체크
        result = db.session.execute(db.text("""
            SELECT COUNT(*) as null_count
            FROM product_details
            WHERE std_div_prod_code IS NULL OR std_div_prod_code = ''
        """))
        null_count = result.fetchone().null_count
        if null_count > 0:
            issues.append(f"❌ {null_count}개 상세 모델에 자가코드가 NULL/빈값")
        
        # 잘못된 길이 체크
        result = db.session.execute(db.text("""
            SELECT COUNT(*) as wrong_length_count
            FROM product_details
            WHERE LENGTH(std_div_prod_code) != 16
        """))
        wrong_length = result.fetchone().wrong_length_count
        if wrong_length > 0:
            issues.append(f"❌ {wrong_length}개 상세 모델의 자가코드가 16자리가 아님")
        
        # 잘못된 브랜드/품목/타입 매핑 체크
        result = db.session.execute(db.text("""
            SELECT COUNT(*) as wrong_mapping_count
            FROM products p
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            WHERE p.company_id = 1 AND (c.code_name IN ('FERRARI', 'NANIA') OR c.code_name IS NULL)
        """))
        wrong_mapping = result.fetchone().wrong_mapping_count
        if wrong_mapping > 0:
            issues.append(f"❌ {wrong_mapping}개 제품에 잘못된 품목/타입 매핑 (FERRARI, NANIA 등)")
        
        if issues:
            print("   🚨 발견된 문제들:")
            for issue in issues:
                print(f"   {issue}")
        else:
            print("   ✅ 데이터 상태 양호")
        
        print("\n📊 요약:")
        print(f"   총 제품: {totals.product_count}개")
        print(f"   총 상세 모델: {totals.total_detail_count}개")
        print(f"   화면에 표시되어야 할 레코드: {totals.total_detail_count}개")

if __name__ == "__main__":
    check_current_data_status() 