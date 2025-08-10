#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
상품관리 시스템 테스트용 샘플 데이터 생성
레거시 호환 자가코드 시스템 포함
"""

from datetime import datetime
from app import create_app
from app.common.models import db, Product, ProductDetail, Code, Company

app = create_app()

def create_sample_products():
    """레거시 호환 샘플 상품 데이터 생성"""
    
    with app.app_context():
        print("🚀 상품관리 시스템 테스트용 샘플 데이터 생성")
        print("=" * 60)
        
        # 기존 상품 데이터 확인
        existing_count = Product.query.count()
        print(f"📦 기존 상품 수: {existing_count}개")
        
        if existing_count > 0:
            print("⚠️ 기존 상품 데이터가 있습니다. 샘플 데이터를 추가합니다.")
        
        # 코드 데이터 가져오기
        companies = Company.query.all()
        brands = Code.get_codes_by_group_name('브랜드')
        categories = Code.get_codes_by_group_name('품목')
        types = Code.get_codes_by_group_name('타입')
        colors = Code.get_codes_by_group_name('색상')
        
        print(f"🏢 회사: {len(companies)}개")
        print(f"🏷️ 브랜드: {len(brands)}개")
        print(f"📂 품목: {len(categories)}개")
        print(f"🎨 색상: {len(colors)}개")
        
        # 샘플 상품 데이터
        sample_products = [
            {
                'name': 'NUNA PIPA lite lx 신생아용 카시트',
                'code': 'PIPA001',
                'price': 450000,
                'company_id': 1,
                'brand_idx': 0,  # 첫 번째 브랜드
                'category_idx': 0,  # 첫 번째 품목
                'description': 'NUNA의 프리미엄 신생아용 카시트입니다.'
            },
            {
                'name': 'RAVA 컨버터블 카시트',
                'code': 'RAVA001', 
                'price': 680000,
                'company_id': 1,
                'brand_idx': 0,
                'category_idx': 1 if len(categories) > 1 else 0,
                'description': 'NUNA의 컨버터블 카시트로 신생아부터 사용 가능합니다.'
            },
            {
                'name': 'DEMI Next 유모차',
                'code': 'DEMI001',
                'price': 890000,
                'company_id': 1,
                'brand_idx': 1 if len(brands) > 1 else 0,
                'category_idx': 0,
                'description': 'NUNA의 프리미엄 유모차입니다.'
            },
            {
                'name': 'LEAF curv 바운서',
                'code': 'LEAF001',
                'price': 320000,
                'company_id': 2,  # 에이원월드
                'brand_idx': 0,
                'category_idx': 0,
                'description': 'NUNA의 스마트 바운서입니다.'
            },
            {
                'name': 'ZAAZ 하이체어',
                'code': 'ZAAZ001',
                'price': 450000,
                'company_id': 2,
                'brand_idx': 0,
                'category_idx': 0,
                'description': 'NUNA의 프리미엄 하이체어입니다.'
            }
        ]
        
        created_count = 0
        
        for i, sample in enumerate(sample_products):
            try:
                # 중복 확인
                existing = Product.query.filter_by(
                    product_code=sample['code'],
                    company_id=sample['company_id']
                ).first()
                
                if existing:
                    print(f"⏭️ 이미 존재하는 상품: {sample['name']}")
                    continue
                
                # 브랜드와 카테고리 선택
                brand_seq = brands[sample['brand_idx']]['seq'] if brands else None
                category_seq = categories[sample['category_idx']]['seq'] if categories else None
                type_seq = types[0]['seq'] if types else None
                
                # 상품 생성
                product = Product(
                    company_id=sample['company_id'],
                    brand_code_seq=brand_seq,
                    category_code_seq=category_seq,
                    type_code_seq=type_seq,
                    product_name=sample['name'],
                    product_code=sample['code'],
                    price=sample['price'],
                    description=sample['description'],
                    is_active=True,
                    created_by='system',
                    created_at=datetime.utcnow()
                )
                
                db.session.add(product)
                db.session.flush()  # ID 할당을 위해
                
                # 색상별 상품 상세 생성 (2-3개 색상)
                color_variants = colors[:3] if len(colors) >= 3 else colors
                
                for j, color in enumerate(color_variants):
                    # 16자리 자가코드 생성 (레거시 호환)
                    brand_code = "PL"  # 팔리
                    div_type_code = "1"  # 일반
                    prod_group_code = "X0"  # 럭스
                    prod_type_code = "00"  # 기본
                    prod_code = f"{j+1:02d}"  # 01, 02, 03
                    prod_type2_code = "A1"  # 일반
                    year_code = "1"  # 2021년
                    color_code = color['code'][:3]  # 색상코드 3자리
                    
                    std_code = ProductDetail.generate_std_code(
                        brand_code, div_type_code, prod_group_code,
                        prod_type_code, prod_code, prod_type2_code,
                        year_code, color_code
                    )
                    
                    # 중복 확인
                    existing_detail = ProductDetail.query.filter_by(
                        std_div_prod_code=std_code
                    ).first()
                    
                    if not existing_detail:
                        detail = ProductDetail(
                            product_id=product.id,
                            brand_code=brand_code,
                            div_type_code=div_type_code,
                            prod_group_code=prod_group_code,
                            prod_type_code=prod_type_code,
                            prod_code=prod_code,
                            prod_type2_code=prod_type2_code,
                            year_code=year_code,
                            color_code=color_code,
                            std_div_prod_code=std_code,
                            product_name=f"{sample['name']} ({color['code_name']})",
                            additional_price=j * 10000,  # 색상별 차등 가격
                            stock_quantity=50,
                            status='Active',
                            created_by='system',
                            created_at=datetime.utcnow()
                        )
                        
                        db.session.add(detail)
                
                created_count += 1
                print(f"✅ 생성: {sample['name']} (색상 {len(color_variants)}개)")
                
            except Exception as e:
                print(f"❌ 상품 생성 실패 [{sample['name']}]: {e}")
                db.session.rollback()
                continue
        
        # 커밋
        try:
            db.session.commit()
            print(f"\n🎉 샘플 데이터 생성 완료!")
            print(f"   - 새로 생성된 상품: {created_count}개")
            print(f"   - 전체 상품 수: {Product.query.count()}개")
            print(f"   - 상품 상세 수: {ProductDetail.query.count()}개")
            
        except Exception as e:
            print(f"❌ 데이터 저장 실패: {e}")
            db.session.rollback()

def test_product_features():
    """상품 관리 기능 테스트"""
    
    with app.app_context():
        print("\n🧪 상품관리 기능 테스트")
        print("=" * 40)
        
        # 1. 상품 목록 조회
        products = Product.query.limit(3).all()
        print(f"📋 상품 목록 조회: {len(products)}개")
        
        for product in products:
            print(f"  - {product.product_name}")
            print(f"    가격: {product.price:,}원")
            print(f"    회사: {product.company.company_name if product.company else '미정'}")
            print(f"    브랜드: {product.brand_code.code_name if product.brand_code else '미정'}")
            
            # 색상별 상세 정보
            details = ProductDetail.query.filter_by(product_id=product.id).all()
            if details:
                print(f"    색상: {len(details)}개")
                for detail in details[:2]:  # 처음 2개만
                    print(f"      • {detail.color_code} - {detail.std_div_prod_code}")
            print()
        
        # 2. 자가코드 생성 테스트
        print("🔧 자가코드 생성 테스트:")
        test_code = ProductDetail.generate_std_code(
            "PL", "1", "X0", "00", "01", "A1", "1", "PLG"
        )
        print(f"   생성된 코드: {test_code}")
        print(f"   예상 형식: PL1X00001A11PLG")
        print(f"   ✅ 형식 일치: {'OK' if test_code == 'PL1X00001A11PLG' else 'FAIL'}")
        
        # 3. 검색 기능 테스트
        print("\n🔍 검색 기능 테스트:")
        search_results = Product.search_products(
            company_id=1,
            search_term="NUNA"
        )
        print(f"   'NUNA' 검색 결과: {len(search_results)}개")
        
        print("\n✅ 모든 테스트 완료!")

if __name__ == "__main__":
    create_sample_products()
    test_product_features() 