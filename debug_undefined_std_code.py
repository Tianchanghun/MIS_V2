#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def debug_undefined_std_code():
    """자가코드 undefined 문제 진단"""
    print("🐛 자가코드 'undefined' 문제 진단")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        # 1. API 응답 구조 확인
        print("1️⃣ API 응답 구조 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                p.id,
                p.product_name,
                pd.std_div_prod_code,
                pd.product_name as detail_name,
                LENGTH(pd.std_div_prod_code) as code_length
            FROM products p
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1 AND p.use_yn = 'Y'
            ORDER BY p.id
            LIMIT 10
        """))
        
        samples = result.fetchall()
        print(f"   📋 데이터베이스 샘플:")
        print(f"      {'ID':4} | {'제품명':20} | {'자가코드':16} | {'길이':4} | {'상세명':15}")
        print(f"      {'-'*4} | {'-'*20} | {'-'*16} | {'-'*4} | {'-'*15}")
        
        for sample in samples:
            code_display = sample.std_div_prod_code or "NULL"
            length_display = sample.code_length or 0
            detail_display = sample.detail_name[:15] if sample.detail_name else "NULL"
            
            print(f"      {sample.id:4} | {sample.product_name[:20]:20} | {code_display[:16]:16} | {length_display:4} | {detail_display:15}")
        
        # 2. Product 모델의 to_dict 메서드 확인
        print(f"\n2️⃣ Product 모델의 자가코드 필드 확인")
        
        from app.common.models import Product
        sample_product = Product.query.filter_by(company_id=1).first()
        
        if sample_product:
            product_dict = sample_product.to_dict()
            print(f"   📋 Product.to_dict() 결과 중 자가코드 관련:")
            
            # 자가코드 관련 필드들 확인
            std_code_fields = [key for key in product_dict.keys() if 'std' in key.lower() or 'code' in key.lower()]
            for field in std_code_fields:
                print(f"      {field}: {product_dict.get(field)}")
        
        # 3. ProductDetail과의 연결 확인
        print(f"\n3️⃣ ProductDetail과의 연결 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(DISTINCT p.id) as total_products,
                COUNT(DISTINCT pd.product_id) as products_with_details,
                COUNT(pd.id) as total_details,
                COUNT(CASE WHEN pd.std_div_prod_code IS NOT NULL THEN 1 END) as details_with_code
            FROM products p
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1 AND p.use_yn = 'Y'
        """))
        
        stats = result.fetchone()
        print(f"   📊 연결 통계:")
        print(f"      총 제품: {stats.total_products}개")
        print(f"      상세모델 있는 제품: {stats.products_with_details}개")
        print(f"      총 상세모델: {stats.total_details}개")
        print(f"      자가코드 있는 상세모델: {stats.details_with_code}개")
        
        # 4. API에서 실제로 반환되는 자가코드 확인
        print(f"\n4️⃣ API 반환값에서 자가코드 필드 확인")
        
        # API처럼 쿼리해보기
        result = db.session.execute(db.text("""
            SELECT 
                p.id,
                p.product_name,
                p.price,
                b.code_name as brand_name,
                c.code_name as category_name,
                t.code_name as type_name,
                y.code_name as year_name,
                pd.std_div_prod_code
            FROM products p
            LEFT JOIN tbl_code b ON p.brand_code_seq = b.seq
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            LEFT JOIN tbl_code t ON p.type_code_seq = t.seq
            LEFT JOIN tbl_code y ON p.year_code_seq = y.seq
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1 AND p.use_yn = 'Y'
            ORDER BY p.id
            LIMIT 5
        """))
        
        api_samples = result.fetchall()
        print(f"   📋 API 스타일 쿼리 결과:")
        for sample in api_samples:
            print(f"      ID {sample.id}: 자가코드={sample.std_div_prod_code}")
        
        # 5. Product 모델에 std_product_code 필드가 있는지 확인
        print(f"\n5️⃣ Product 모델의 std_product_code 필드 확인")
        
        try:
            if hasattr(sample_product, 'std_product_code'):
                print(f"   ✅ Product.std_product_code 필드 존재: {sample_product.std_product_code}")
            else:
                print(f"   ❌ Product.std_product_code 필드 없음")
                
            # 모든 필드 나열
            product_fields = [attr for attr in dir(sample_product) if not attr.startswith('_') and not callable(getattr(sample_product, attr))]
            code_fields = [field for field in product_fields if 'code' in field.lower()]
            print(f"   📋 Product 모델의 코드 관련 필드들: {code_fields}")
            
        except Exception as e:
            print(f"   ❌ 오류: {e}")
        
        # 6. 해결책 제시
        print(f"\n6️⃣ 문제 해결책")
        
        if stats.products_with_details < stats.total_products:
            print(f"   🔧 해결책 1: Product와 ProductDetail 연결 누락 해결")
            print(f"      - {stats.total_products - stats.products_with_details}개 제품에 상세모델 없음")
        
        if stats.details_with_code < stats.total_details:
            print(f"   🔧 해결책 2: ProductDetail의 자가코드 누락 해결")
            print(f"      - {stats.total_details - stats.details_with_code}개 상세모델에 자가코드 없음")
        
        if not hasattr(sample_product, 'std_product_code'):
            print(f"   🔧 해결책 3: Product 모델에 std_product_code 필드 추가")
            print(f"      - to_dict()에서 ProductDetail의 자가코드를 가져오도록 수정")
        
        print(f"\n   💡 우선순위:")
        print(f"      1. Product.to_dict()에서 자가코드 반환 로직 수정")
        print(f"      2. ProductDetail과의 연결 확인 및 수정")
        print(f"      3. API 응답에서 자가코드 필드명 확인")

if __name__ == "__main__":
    debug_undefined_std_code() 