#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
기존 상품들의 None 필드들을 실제 코드 데이터로 업데이트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db, Product, Code

app = create_app()

def update_existing_products():
    """기존 상품들의 코드 필드 업데이트"""
    with app.app_context():
        print("🔧 기존 상품 코드 필드 업데이트 시작")
        print("=" * 50)
        
        # 1. 기본 코드들을 동적 WHERE 절로 가져오기
        brand_group = Code.query.filter_by(code_name='브랜드', depth=0).first()
        default_brand = Code.query.filter_by(parent_seq=brand_group.seq).first() if brand_group else None
        
        category_group = Code.query.filter_by(code_name='제품구분', depth=0).first() 
        default_category = Code.query.filter_by(parent_seq=category_group.seq).first() if category_group else None
        
        type_group = Code.query.filter_by(code_name='타입', depth=0).first()
        default_type = Code.query.filter_by(parent_seq=type_group.seq).first() if type_group else None
        
        year_group = Code.query.filter_by(code_name='년도', depth=0).first()
        # 2025년을 우선 찾고, 없으면 최신 년도 사용
        default_year = None
        if year_group:
            default_year = Code.query.filter_by(parent_seq=year_group.seq, code='25').first()
            if not default_year:
                default_year = Code.query.filter_by(parent_seq=year_group.seq).order_by(Code.code.desc()).first()
        
        print(f"📊 기본값으로 사용할 코드:")
        print(f"  - 브랜드: {default_brand.code_name if default_brand else 'None'} ({default_brand.seq if default_brand else 'None'})")
        print(f"  - 품목: {default_category.code_name if default_category else 'None'} ({default_category.seq if default_category else 'None'})")
        print(f"  - 타입: {default_type.code_name if default_type else 'None'} ({default_type.seq if default_type else 'None'})")
        print(f"  - 년도: {default_year.code_name if default_year else 'None'} ({default_year.seq if default_year else 'None'})")
        
        # 2. 코드 필드가 None인 상품들 업데이트
        products = Product.query.all()
        updated_count = 0
        
        for product in products:
            updated = False
            
            # brand_code_seq가 None이거나 잘못된 값인 경우
            if not product.brand_code_seq and default_brand:
                product.brand_code_seq = default_brand.seq
                updated = True
            
            # category_code_seq가 None인 경우
            if not product.category_code_seq and default_category:
                product.category_code_seq = default_category.seq
                updated = True
            
            # type_code_seq가 None인 경우
            if not product.type_code_seq and default_type:
                product.type_code_seq = default_type.seq
                updated = True
            
            # year_code_seq가 None이거나 잘못된 값인 경우
            if not product.year_code_seq and default_year:
                product.year_code_seq = default_year.seq
                updated = True
            elif product.year_code_seq and product.year_code_seq > 1000:  # 잘못된 년도 코드 수정
                product.year_code_seq = default_year.seq
                updated = True
            
            if updated:
                updated_count += 1
                print(f"  ✅ 상품 '{product.product_name}' 업데이트")
        
        # 3. 커밋
        try:
            db.session.commit()
            print(f"\n🎉 상품 코드 필드 업데이트 완료: {updated_count}개")
        except Exception as e:
            db.session.rollback()
            print(f"❌ 업데이트 실패: {e}")

def check_updated_products():
    """업데이트된 상품들 확인"""
    with app.app_context():
        print(f"\n🔍 업데이트 후 상품 상태 확인")
        print("=" * 50)
        
        products = Product.query.limit(5).all()
        for product in products:
            print(f"\n📦 상품: {product.product_name}")
            print(f"  - 브랜드: {product.brand_code.code_name if product.brand_code else 'None'} (SEQ: {product.brand_code_seq})")
            print(f"  - 품목: {product.category_code.code_name if product.category_code else 'None'} (SEQ: {product.category_code_seq})")
            print(f"  - 타입: {product.type_code.code_name if product.type_code else 'None'} (SEQ: {product.type_code_seq})")
            print(f"  - 년도: {product.year_code.code_name if product.year_code else 'None'} (SEQ: {product.year_code_seq})")

if __name__ == '__main__':
    update_existing_products()
    check_updated_products() 