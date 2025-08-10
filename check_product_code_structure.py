#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def check_product_codes():
    """실제 데이터베이스의 제품코드 구조 확인"""
    app = create_app()
    
    with app.app_context():
        print("🔍 실제 데이터베이스의 제품코드 구조 분석")
        print("=" * 60)
        
        # 제품 상세 테이블에서 실제 코드 확인
        result = db.session.execute(db.text("""
            SELECT 
                std_code,
                LENGTH(std_code) as code_length,
                brand_code,
                div_type_code, 
                prod_group_code,
                prod_type_code,
                prod_code,
                prod_type2_code,
                year_code,
                color_code,
                product_name
            FROM product_detail 
            WHERE std_code IS NOT NULL
            ORDER BY seq
            LIMIT 10
        """))
        
        products = result.fetchall()
        
        if not products:
            print("❌ 제품코드가 없습니다.")
            return
            
        print(f"📊 총 {len(products)}개 제품코드 분석:")
        print()
        
        for i, product in enumerate(products, 1):
            std_code = product.std_code
            print(f"{i}. 제품명: {product.product_name}")
            print(f"   전체코드: {std_code} (길이: {product.code_length}자리)")
            print(f"   브랜드: {product.brand_code}")
            print(f"   구분타입: {product.div_type_code}")
            print(f"   품목: {product.prod_group_code}")
            print(f"   타입: {product.prod_type_code}")
            print(f"   제품: {product.prod_code}")
            print(f"   타입2: {product.prod_type2_code}")
            print(f"   년도: {product.year_code}")
            print(f"   색상: {product.color_code}")
            
            # 실제 코드를 위치별로 분석
            if std_code and len(std_code) >= 15:
                print(f"   위치별 분석:")
                print(f"     0-1: '{std_code[0:2]}' (브랜드)")
                print(f"     2: '{std_code[2:3]}' (구분타입)")
                print(f"     3: '{std_code[3:4]}' (빈자리?)")
                print(f"     4-5: '{std_code[4:6]}' (품목)")
                print(f"     6-7: '{std_code[6:8]}' (타입)")  # 레거시는 5-6
                print(f"     8-9: '{std_code[8:10]}' (제품)")  # 레거시는 7-8
                print(f"     10-11: '{std_code[10:12]}' (타입2)")  # 레거시는 9-10
                print(f"     12: '{std_code[12:13]}' (년도)")
                if len(std_code) >= 16:
                    print(f"     13-15: '{std_code[13:16]}' (색상)")  # 레거시는 13-15
                
            print("-" * 40)

if __name__ == "__main__":
    check_product_codes() 