#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
상품 삭제 시 연관 데이터 처리 (Cascade Delete)
product_details 관계 정리 후 안전한 삭제
"""

from app.common.models import db, Code, Product, ProductDetail
from app import create_app
from datetime import datetime
from sqlalchemy import text

def main():
    app = create_app()
    with app.app_context():
        print("="*70)
        print("🔧 상품 연관 데이터 정리 및 안전한 삭제")
        print("="*70)
        
        # 1. 문제 상품 및 연관 데이터 확인
        problem_products = Product.query.filter(
            db.or_(
                Product.product_name.is_(None),
                Product.product_name == '',
                Product.brand_code_seq.is_(None),
                Product.category_code_seq.is_(None),
                Product.type_code_seq.is_(None)
            )
        ).all()
        
        print(f"\n📋 문제 상품 확인: {len(problem_products)}개")
        
        for product in problem_products:
            print(f"\n  🔍 상품 ID {product.id}:")
            print(f"    - 상품명: '{product.product_name or '없음'}'")
            print(f"    - 브랜드: {product.brand_code_seq or '없음'}")
            print(f"    - 품목: {product.category_code_seq or '없음'}")
            print(f"    - 타입: {product.type_code_seq or '없음'}")
            
            # 연관된 product_details 확인
            related_details = ProductDetail.query.filter_by(product_id=product.id).all()
            print(f"    - 연관 ProductDetail: {len(related_details)}개")
            
            for detail in related_details:
                print(f"      ∟ Detail ID {detail.id}: {detail.std_div_prod_code or '코드없음'}")
        
        # 2. 해결 방안
        print(f"\n🔧 해결 방안:")
        print(f"  1️⃣ 연관된 ProductDetail 먼저 삭제")
        print(f"  2️⃣ 그 다음 Product 삭제")
        print(f"  3️⃣ 누락된 코드 정보는 기본값 설정")
        
        # 3. 안전한 삭제 수행
        try:
            print(f"\n🚀 안전한 데이터 정리 시작...")
            
            deleted_products = 0
            deleted_details = 0
            fixed_products = 0
            
            for product in problem_products:
                # 상품명이 없는 경우 연관 데이터와 함께 삭제
                if not product.product_name or product.product_name.strip() == '':
                    print(f"\n    🗑️  삭제 시작: 상품 ID {product.id}")
                    
                    # 1단계: 연관된 product_details 먼저 삭제
                    related_details = ProductDetail.query.filter_by(product_id=product.id).all()
                    for detail in related_details:
                        print(f"      ∟ Detail 삭제: {detail.id}")
                        db.session.delete(detail)
                        deleted_details += 1
                    
                    # 2단계: product 삭제
                    print(f"      ∟ Product 삭제: {product.id}")
                    db.session.delete(product)
                    deleted_products += 1
                    
                else:
                    # 상품명이 있지만 코드 정보가 누락된 경우 기본값 설정
                    print(f"\n    🔧 수정: 상품 ID {product.id} - {product.product_name}")
                    updated = False
                    
                    if not product.brand_code_seq:
                        # 기본 브랜드 설정
                        default_brand = Code.query.filter_by(depth=1).filter(
                            Code.parent_seq.in_(
                                db.session.query(Code.seq).filter_by(code='BRAND', depth=0)
                            )
                        ).first()
                        if default_brand:
                            product.brand_code_seq = default_brand.seq
                            print(f"      ∟ 기본 브랜드: {default_brand.code_name}")
                            updated = True
                    
                    if not product.category_code_seq:
                        # 기본 품목 설정
                        default_category = Code.query.filter_by(depth=1).filter(
                            Code.parent_seq.in_(
                                db.session.query(Code.seq).filter_by(code='PRT', depth=0)
                            )
                        ).first()
                        if default_category:
                            product.category_code_seq = default_category.seq
                            print(f"      ∟ 기본 품목: {default_category.code_name}")
                            updated = True
                    
                    if not product.type_code_seq:
                        # 기본 타입 설정
                        default_type = Code.query.filter_by(depth=2).limit(1).first()
                        if default_type:
                            product.type_code_seq = default_type.seq
                            print(f"      ∟ 기본 타입: {default_type.code_name}")
                            updated = True
                    
                    if updated:
                        product.updated_at = datetime.now()
                        product.updated_by = 'system_fix'
                        fixed_products += 1
            
            # 변경사항 저장
            if deleted_products > 0 or deleted_details > 0 or fixed_products > 0:
                db.session.commit()
                print(f"\n✅ 데이터 정리 완료!")
                print(f"  - 삭제된 상품: {deleted_products}개")
                print(f"  - 삭제된 상세정보: {deleted_details}개")
                print(f"  - 수정된 상품: {fixed_products}개")
            else:
                print(f"\n💡 처리할 데이터가 없습니다.")
            
            # 4. 수정 후 검증
            print(f"\n🔍 수정 후 검증:")
            
            # 총 상품 수
            total_products = Product.query.count()
            print(f"  - 총 상품 수: {total_products}개")
            
            # 문제 상품 재확인
            remaining_problems = Product.query.filter(
                db.or_(
                    Product.product_name.is_(None),
                    Product.product_name == '',
                    Product.brand_code_seq.is_(None),
                    Product.category_code_seq.is_(None),
                    Product.type_code_seq.is_(None)
                )
            ).count()
            
            if remaining_problems == 0:
                print(f"  ✅ 모든 상품 데이터가 정상입니다!")
            else:
                print(f"  ⚠️  아직 {remaining_problems}개 상품에 문제가 있습니다.")
            
            # 5. 연관 데이터 무결성 확인
            print(f"\n🔗 연관 데이터 무결성 확인:")
            
            # orphaned product_details 확인 (참조하는 product가 없는 경우)
            orphaned_details = db.session.execute(text("""
                SELECT pd.id, pd.product_id 
                FROM product_details pd 
                LEFT JOIN products p ON pd.product_id = p.id 
                WHERE p.id IS NULL
            """)).fetchall()
            
            if orphaned_details:
                print(f"  ⚠️  고아 ProductDetail: {len(orphaned_details)}개")
                for detail_id, product_id in orphaned_details:
                    print(f"    - Detail ID {detail_id}: product_id={product_id} (존재하지 않음)")
            else:
                print(f"  ✅ 모든 ProductDetail이 올바른 Product를 참조합니다.")
            
            # 6. 최종 통계
            print(f"\n📊 최종 상품 통계:")
            from sqlalchemy import func
            
            # 회사별 상품 수
            company_stats = db.session.query(
                Product.company_id, 
                func.count(Product.id).label('count')
            ).group_by(Product.company_id).all()
            
            for company_id, count in company_stats:
                print(f"  - 회사 {company_id}: {count}개 상품")
            
            # 활성/비활성 상품 수
            active_count = Product.query.filter_by(is_active=True).count()
            inactive_count = Product.query.filter_by(is_active=False).count()
            print(f"  - 활성 상품: {active_count}개")
            print(f"  - 비활성 상품: {inactive_count}개")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ 수정 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            
        print("\n" + "="*70)
        print("🎯 상품 연관 데이터 정리 완료")
        print("="*70)

if __name__ == '__main__':
    main() 