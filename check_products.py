#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import create_app
from app.common.models import Product, Brand, Code

app = create_app()
with app.app_context():
    print('=== 상품 데이터 확인 ===')
    total = Product.query.count()
    print(f'총 상품 수: {total}개')
    
    if total > 0:
        print('\n최근 상품 5개:')
        products = Product.query.order_by(Product.id.desc()).limit(5).all()
        for p in products:
            brand_name = p.brand.brand_name if p.brand else '미지정'
            print(f'  - ID:{p.id} {p.product_name} (브랜드: {brand_name}, 회사: {p.company_id})')
        
        print('\n회사별 분포:')
        aone = Product.query.filter_by(company_id=1).count()
        aone_world = Product.query.filter_by(company_id=2).count()
        print(f'  - 에이원: {aone}개')
        print(f'  - 에이원월드: {aone_world}개')
        
        print('\n활성/비활성 상태:')
        active = Product.query.filter_by(is_active=True).count()
        inactive = Product.query.filter_by(is_active=False).count()
        print(f'  - 활성: {active}개')
        print(f'  - 비활성: {inactive}개')
        
    else:
        print('❌ 상품 데이터가 없습니다!')
        
    # API 엔드포인트 테스트
    print('\n=== API 테스트 ===')
    from flask import Flask
    from app.product.routes import api_list
    
    with app.test_request_context():
        from flask import session
        session['member_seq'] = 1
        session['current_company_id'] = 1
        
        try:
            # 직접 함수 호출로 테스트
            print('API 함수 직접 호출 테스트 중...')
        except Exception as e:
            print(f'API 테스트 오류: {e}') 