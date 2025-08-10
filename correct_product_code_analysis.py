#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def analyze_correct_product_code():
    """년도코드 2자리를 반영한 정확한 제품코드 구조 분석"""
    app = create_app()
    
    with app.app_context():
        print("🔍 정확한 제품코드 구조 분석 (년도코드 2자리)")
        print("=" * 60)
        
        # 실제 제품코드 샘플 확인
        result = db.session.execute(db.text("""
            SELECT 
                std_div_prod_code,
                LENGTH(std_div_prod_code) as code_length,
                brand_code,
                div_type_code, 
                prod_group_code,
                prod_type_code,
                prod_code,
                prod_type2_code,
                year_code,
                color_code,
                product_name
            FROM product_details 
            WHERE std_div_prod_code IS NOT NULL
            ORDER BY id
            LIMIT 5
        """))
        
        products = result.fetchall()
        
        if not products:
            print("❌ 제품코드가 없습니다.")
            return
            
        print(f"📊 제품코드 샘플 분석:")
        print()
        
        for i, product in enumerate(products, 1):
            std_code = product.std_div_prod_code
            print(f"{i}. 제품명: {product.product_name}")
            print(f"   전체코드: {std_code} (길이: {product.code_length}자리)")
            print(f"   개별 필드:")
            print(f"     브랜드: {product.brand_code}")
            print(f"     구분타입: {product.div_type_code}")
            print(f"     품목: {product.prod_group_code}")
            print(f"     타입: {product.prod_type_code}")
            print(f"     제품: {product.prod_code}")
            print(f"     타입2: {product.prod_type2_code}")
            print(f"     년도: {product.year_code}")
            print(f"     색상: {product.color_code}")
            
            # 실제 코드를 위치별로 분석 (년도코드 2자리 가정)
            if std_code and len(std_code) >= 16:
                print(f"   📋 위치별 분석 (년도코드 2자리):")
                print(f"     0-1: '{std_code[0:2]}' → 브랜드코드 ({product.brand_code})")
                print(f"     2: '{std_code[2:3]}' → 구분타입코드 ({product.div_type_code})")
                print(f"     3-4: '{std_code[3:5]}' → 품목코드 ({product.prod_group_code})")
                print(f"     5-6: '{std_code[5:7]}' → 타입코드 ({product.prod_type_code})")
                print(f"     7-8: '{std_code[7:9]}' → 제품코드 ({product.prod_code})")
                print(f"     9-10: '{std_code[9:11]}' → 타입2코드 ({product.prod_type2_code})")
                print(f"     11-12: '{std_code[11:13]}' → 년도코드 ({product.year_code})")
                print(f"     13-15: '{std_code[13:16]}' → 색상코드 ({product.color_code})")
                
                # 검증
                reconstructed = (product.brand_code + product.div_type_code + 
                               product.prod_group_code + product.prod_type_code + 
                               product.prod_code + product.prod_type2_code + 
                               product.year_code + product.color_code)
                
                print(f"   ✅ 재구성된 코드: {reconstructed}")
                print(f"   {'✅ 일치!' if reconstructed == std_code else '❌ 불일치!'}")
                
            print("-" * 50)
        
        # 구조 요약
        print("\n📋 **최종 제품코드 구조 (16자리)**")
        print("=" * 60)
        print("| 위치  | 필드명        | 길이 | 설명        | 예시  |")
        print("|-------|---------------|------|-------------|-------|")
        print("| 0-1   | brand_code    | 2자리 | 브랜드코드   | LI    |")
        print("| 2     | div_type_code | 1자리 | 구분타입코드 | 1     |")
        print("| 3-4   | prod_group_code| 2자리 | 품목코드    | X0    |")
        print("| 5-6   | prod_type_code | 2자리 | 타입코드    | 00    |")
        print("| 7-8   | prod_code     | 2자리 | 제품코드    | 01    |")
        print("| 9-10  | prod_type2_code| 2자리 | 타입2코드   | A1    |")
        print("| 11-12 | year_code     | 2자리 | 년도코드    | 14    |")
        print("| 13-15 | color_code    | 3자리 | 색상코드    | PLG   |")
        print("=" * 60)
        print("**총 16자리**: LI1X00001A114PLG")

if __name__ == "__main__":
    analyze_correct_product_code() 