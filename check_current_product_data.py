#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
현재 상품 데이터 상태 확인
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db, Product, ProductDetail, Code

app = create_app()

def check_product_data():
    """현재 상품 데이터 상태 확인"""
    with app.app_context():
        # 1. 상품 개수 확인
        product_count = Product.query.count()
        print(f"📊 총 상품 개수: {product_count}개")
        
        # 2. 최근 상품 5개 정보 출력
        recent_products = Product.query.order_by(Product.created_at.desc()).limit(5).all()
        print(f"\n🔍 최근 상품 5개:")
        for product in recent_products:
            print(f"  - ID: {product.id}, 이름: {product.product_name}")
            print(f"    회사: {product.company_id}, 브랜드: {product.brand_code_seq}")
            print(f"    품목: {product.category_code_seq}, 타입: {product.type_code_seq}")
            print(f"    년도: {product.year_code_seq}, 가격: {product.price}")
            print(f"    활성: {product.is_active}, 생성일: {product.created_at}")
            
            # 해당 상품의 제품모델 개수 확인
            detail_count = ProductDetail.query.filter_by(product_id=product.id).count()
            print(f"    제품모델 개수: {detail_count}개")
            print()
        
        # 3. 제품모델 개수 확인
        detail_count = ProductDetail.query.count()
        print(f"📊 총 제품모델 개수: {detail_count}개")
        
        # 4. 최근 제품모델 5개 정보 출력
        recent_details = ProductDetail.query.order_by(ProductDetail.created_at.desc()).limit(5).all()
        print(f"\n🔍 최근 제품모델 5개:")
        for detail in recent_details:
            print(f"  - ID: {detail.id}, 제품명: {detail.product_name}")
            print(f"    자가코드: {detail.std_div_prod_code}")
            print(f"    색상코드: {detail.color_code}, 상태: {detail.status}")
            print(f"    상품ID: {detail.product_id}, 생성일: {detail.created_at}")
            print()
        
        # 5. 코드 체계 확인
        brand_codes = Code.query.filter_by(code_seq=1).count()  # BRAND 그룹
        category_codes = Code.query.filter_by(code_seq=2).count()  # PRT 그룹
        type_codes = Code.query.filter_by(code_seq=3).count()  # TP 그룹
        year_codes = Code.query.filter_by(code_seq=4).count()  # YR 그룹
        
        print(f"📊 코드 체계 현황:")
        print(f"  - 브랜드 코드: {brand_codes}개")
        print(f"  - 품목 코드: {category_codes}개") 
        print(f"  - 타입 코드: {type_codes}개")
        print(f"  - 년도 코드: {year_codes}개")

def check_specific_product(product_id):
    """특정 상품 상세 정보 확인"""
    with app.app_context():
        product = Product.query.get(product_id)
        if not product:
            print(f"❌ 상품 ID {product_id}를 찾을 수 없습니다.")
            return
        
        print(f"\n🔍 상품 ID {product_id} 상세 정보:")
        print(f"  - 이름: {product.product_name}")
        print(f"  - 코드: {product.product_code}")
        print(f"  - 회사ID: {product.company_id}")
        print(f"  - 브랜드 코드 SEQ: {product.brand_code_seq}")
        print(f"  - 품목 코드 SEQ: {product.category_code_seq}")
        print(f"  - 타입 코드 SEQ: {product.type_code_seq}")
        print(f"  - 년도 코드 SEQ: {product.year_code_seq}")
        print(f"  - 색상 코드 SEQ: {product.color_code_seq}")
        print(f"  - 구분타입 코드 SEQ: {product.div_type_code_seq}")
        print(f"  - 제품코드 SEQ: {product.product_code_seq}")
        print(f"  - 자가코드: {product.std_product_code}")
        print(f"  - 가격: {product.price}")
        print(f"  - 설명: {product.description}")
        print(f"  - 활성: {product.is_active}")
        
        # 관련 제품모델 확인
        details = ProductDetail.query.filter_by(product_id=product_id).all()
        print(f"\n📦 연관된 제품모델 {len(details)}개:")
        for detail in details:
            print(f"  - {detail.product_name} ({detail.std_div_prod_code})")
            print(f"    색상: {detail.color_code}, 상태: {detail.status}")

if __name__ == '__main__':
    print("🔍 현재 상품 데이터 상태 확인")
    print("=" * 50)
    
    check_product_data()
    
    # 첫 번째 상품의 상세 정보 확인
    with app.app_context():
        first_product = Product.query.first()
        if first_product:
            check_specific_product(first_product.id) 