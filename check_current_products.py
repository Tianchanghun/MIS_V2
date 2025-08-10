#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import create_app
from app.common.models import Product, ProductDetail, db

def check_current_products():
    """현재 상품 데이터 현황 확인"""
    app = create_app()
    with app.app_context():
        product_count = Product.query.count()
        model_count = ProductDetail.query.count()
        
        print("🔍 현재 상품 데이터:")
        print(f"   - 제품: {product_count}개")
        print(f"   - 모델: {model_count}개")
        
        # 상세 분석
        print("\n📊 회사별 분포:")
        companies = db.session.query(Product.company_id, db.func.count(Product.id)).group_by(Product.company_id).all()
        for company_id, count in companies:
            print(f"   - 회사 {company_id}: {count}개")
        
        # 모델이 없는 제품 확인
        products_without_models = db.session.query(Product).outerjoin(ProductDetail).filter(ProductDetail.id == None).count()
        print(f"\n⚠️  모델이 없는 제품: {products_without_models}개")
        
        # 상품가격 분포
        price_stats = db.session.query(
            db.func.min(Product.price),
            db.func.max(Product.price), 
            db.func.avg(Product.price)
        ).first()
        print(f"\n💰 가격 분포:")
        print(f"   - 최소: {price_stats[0]:,}원")
        print(f"   - 최대: {price_stats[1]:,}원") 
        print(f"   - 평균: {price_stats[2]:,.0f}원")

if __name__ == "__main__":
    check_current_products() 