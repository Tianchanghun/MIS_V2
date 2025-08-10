#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 상품 데이터 생성 (오류 수정)
"""

from datetime import datetime
from app import create_app
from app.common.models import db, Product, ProductDetail, Code, Company

app = create_app()

def create_simple_products():
    """간단한 상품 데이터 생성"""
    
    with app.app_context():
        print("🚀 간단한 상품 데이터 생성")
        print("=" * 50)
        
        # 기존 상품 확인
        existing_count = Product.query.count()
        print(f"📦 기존 상품 수: {existing_count}개")
        
        # 코드 정보 확인
        brands = Code.get_codes_by_group_name('브랜드')
        categories = Code.get_codes_by_group_name('품목')
        
        print(f"🏷️ 브랜드 코드: {len(brands)}개")
        print(f"📂 품목 코드: {len(categories)}개")
        
        if not brands or not categories:
            print("❌ 브랜드 또는 품목 코드가 없습니다.")
            return
        
        # 간단한 상품 생성
        sample_products = [
            {
                'name': 'NUNA PIPA 카시트',
                'code': 'PIPA001',
                'price': 450000,
                'company_id': 1
            },
            {
                'name': 'RAVA 컨버터블 카시트',
                'code': 'RAVA001',
                'price': 680000,
                'company_id': 1
            },
            {
                'name': 'DEMI 유모차',
                'code': 'DEMI001',
                'price': 890000,
                'company_id': 2
            }
        ]
        
        created_count = 0
        
        for sample in sample_products:
            try:
                # 중복 확인 (수정)
                existing = Product.query.filter(
                    Product.product_code == sample['code'],
                    Product.company_id == sample['company_id']
                ).first()
                
                if existing:
                    print(f"⏭️ 이미 존재: {sample['name']}")
                    continue
                
                # 상품 생성
                product = Product(
                    company_id=sample['company_id'],
                    brand_code_seq=brands[0]['seq'] if brands else None,
                    category_code_seq=categories[0]['seq'] if categories else None,
                    product_name=sample['name'],
                    product_code=sample['code'],
                    price=sample['price'],
                    description=f"{sample['name']} 상품입니다.",
                    is_active=True,
                    created_by='system',
                    created_at=datetime.utcnow()
                )
                
                db.session.add(product)
                db.session.commit()  # 즉시 커밋
                
                created_count += 1
                print(f"✅ 생성: {sample['name']}")
                
            except Exception as e:
                print(f"❌ 생성 실패 [{sample['name']}]: {e}")
                db.session.rollback()
        
        print(f"\n🎉 상품 생성 완료!")
        print(f"   - 새로 생성: {created_count}개")
        print(f"   - 전체 상품: {Product.query.count()}개")
        
        # 생성된 상품 확인
        if Product.query.count() > 0:
            print("\n📋 생성된 상품 목록:")
            products = Product.query.limit(5).all()
            for i, product in enumerate(products, 1):
                company_name = product.company.company_name if product.company else "미정"
                brand_name = product.brand_code.code_name if product.brand_code else "미정"
                print(f"  {i}. {product.product_name}")
                print(f"     코드: {product.product_code}")
                print(f"     가격: {product.price:,}원")
                print(f"     회사: {company_name}")
                print(f"     브랜드: {brand_name}")
                print()

def test_api_endpoints():
    """API 엔드포인트 테스트"""
    
    print("🧪 API 기능 테스트")
    print("=" * 30)
    
    import requests
    
    try:
        # 1. 상품 목록 API (로그인 없이)
        response = requests.get("http://localhost:5000/product/api/list")
        print(f"📋 상품 목록 API: {response.status_code}")
        
        # 2. 코드 목록 API
        response = requests.get("http://localhost:5000/product/api/get-codes")
        print(f"🏷️ 코드 목록 API: {response.status_code}")
        
        # 3. 메인 페이지
        response = requests.get("http://localhost:5000/")
        print(f"🏠 메인 페이지: {response.status_code}")
        
        print("\n✅ API 테스트 완료!")
        
    except Exception as e:
        print(f"❌ API 테스트 실패: {e}")

if __name__ == "__main__":
    create_simple_products()
    test_api_endpoints() 