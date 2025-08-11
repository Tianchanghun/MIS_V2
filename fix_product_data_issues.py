#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
상품관리 데이터 무결성 문제 해결
빈 상품 데이터 정리 및 검증
"""

from app.common.models import db, Code, Product
from app import create_app
from datetime import datetime

def main():
    app = create_app()
    with app.app_context():
        print("="*70)
        print("🔧 상품관리 데이터 무결성 문제 해결")
        print("="*70)
        
        # 1. 문제 상품 상세 확인
        problem_products = Product.query.filter(
            db.or_(
                Product.product_name.is_(None),
                Product.product_name == '',
                Product.brand_code_seq.is_(None),
                Product.category_code_seq.is_(None),
                Product.type_code_seq.is_(None)
            )
        ).all()
        
        print(f"\n📋 문제 상품 상세 분석: {len(problem_products)}개")
        
        for product in problem_products:
            print(f"\n  🔍 상품 ID {product.id}:")
            print(f"    - 상품명: '{product.product_name or '없음'}'")
            print(f"    - 브랜드: {product.brand_code_seq or '없음'}")
            print(f"    - 품목: {product.category_code_seq or '없음'}")
            print(f"    - 타입: {product.type_code_seq or '없음'}")
            print(f"    - 생성일: {product.created_at}")
            print(f"    - 활성화: {product.is_active}")
        
        # 2. 해결 방안 제시
        print(f"\n🔧 해결 방안:")
        print(f"  1️⃣ 빈 상품명/데이터 상품 삭제")
        print(f"  2️⃣ 누락된 코드 정보 기본값 설정")
        print(f"  3️⃣ 데이터 무결성 검증")
        
        # 3. 자동 수정 시도
        try:
            print(f"\n🚀 자동 수정 시작...")
            
            deleted_count = 0
            fixed_count = 0
            
            for product in problem_products:
                # 상품명이 완전히 없는 경우 삭제
                if not product.product_name or product.product_name.strip() == '':
                    print(f"    🗑️  삭제: ID {product.id} (상품명 없음)")
                    db.session.delete(product)
                    deleted_count += 1
                else:
                    # 코드 정보 누락 시 기본값 설정
                    updated = False
                    
                    if not product.brand_code_seq:
                        # 기본 브랜드 설정 (첫 번째 브랜드)
                        default_brand = Code.query.filter_by(depth=1).filter(
                            Code.parent_seq.in_(
                                db.session.query(Code.seq).filter_by(code='BRAND', depth=0)
                            )
                        ).first()
                        if default_brand:
                            product.brand_code_seq = default_brand.seq
                            print(f"    🔧 ID {product.id}: 기본 브랜드 설정 ({default_brand.code_name})")
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
                            print(f"    🔧 ID {product.id}: 기본 품목 설정 ({default_category.code_name})")
                            updated = True
                    
                    if not product.type_code_seq:
                        # 기본 타입 설정
                        default_type = Code.query.filter_by(depth=2).limit(1).first()
                        if default_type:
                            product.type_code_seq = default_type.seq
                            print(f"    🔧 ID {product.id}: 기본 타입 설정 ({default_type.code_name})")
                            updated = True
                    
                    if updated:
                        product.updated_at = datetime.now()
                        product.updated_by = 'system_fix'
                        fixed_count += 1
            
            # 변경사항 저장
            if deleted_count > 0 or fixed_count > 0:
                db.session.commit()
                print(f"\n✅ 데이터 정리 완료!")
                print(f"  - 삭제된 상품: {deleted_count}개")
                print(f"  - 수정된 상품: {fixed_count}개")
            else:
                print(f"\n💡 수정할 데이터가 없습니다.")
            
            # 4. 수정 후 검증
            print(f"\n🔍 수정 후 검증:")
            
            # 전체 상품 수
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
            
            # 5. 상품 통계 현황
            print(f"\n📊 상품 데이터 통계:")
            
            # 회사별 상품 수
            from sqlalchemy import func
            company_stats = db.session.query(
                Product.company_id, 
                func.count(Product.id).label('count')
            ).group_by(Product.company_id).all()
            
            for company_id, count in company_stats:
                print(f"  - 회사 {company_id}: {count}개 상품")
            
            # 브랜드별 상품 수 (상위 5개)
            brand_stats = db.session.query(
                Code.code_name,
                func.count(Product.id).label('count')
            ).join(Product, Code.seq == Product.brand_code_seq)\
             .group_by(Code.code_name)\
             .order_by(func.count(Product.id).desc())\
             .limit(5).all()
            
            print(f"\n  📈 브랜드별 상품 수 (상위 5개):")
            for brand_name, count in brand_stats:
                print(f"    - {brand_name}: {count}개")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ 수정 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            
        print("\n" + "="*70)
        print("🎯 상품관리 데이터 무결성 개선 완료")
        print("="*70)

if __name__ == '__main__':
    main() 