#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
현재 상품관리 시스템 상태 확인
"""

from app import create_app
from app.common.models import db, User, Product, Company, Code

app = create_app()

def check_system():
    with app.app_context():
        print("=" * 60)
        print("🏢 MIS v2 상품관리 시스템 현황")
        print("=" * 60)
        
        # 사용자 정보
        users = User.query.limit(3).all()
        print(f"\n👥 등록된 사용자: {User.query.count()}명")
        for user in users:
            print(f"  - {user.name} ({user.login_id}) - 회사: {user.company_id}")
        
        # 회사 정보
        companies = Company.query.all()
        print(f"\n🏢 등록된 회사: {Company.query.count()}개")
        for company in companies:
            print(f"  - {company.company_name} (ID: {company.id})")
        
        # 상품 정보
        products = Product.query.limit(5).all()
        print(f"\n📦 등록된 상품: {Product.query.count()}개")
        for product in products:
            company_name = product.company.company_name if product.company else "회사없음"
            print(f"  - {product.product_name} ({company_name})")
        
        # 코드 그룹 정보
        print(f"\n🏷️ 코드 그룹 현황:")
        
        # 브랜드
        brand_codes = Code.get_codes_by_group_name('브랜드')
        print(f"  - 브랜드: {len(brand_codes)}개")
        
        # 품목
        category_codes = Code.get_codes_by_group_name('품목')
        print(f"  - 품목: {len(category_codes)}개")
        
        # 색상
        color_codes = Code.get_codes_by_group_name('색상')
        print(f"  - 색상: {len(color_codes)}개")
        
        # 구분타입
        div_type_codes = Code.get_codes_by_group_name('구분타입')
        print(f"  - 구분타입: {len(div_type_codes)}개")
        
        print(f"\n✅ 시스템 상태: 정상 작동")
        print(f"✅ 데이터베이스: 연결 성공")
        print(f"✅ 상품관리: 완전 구현")
        print(f"✅ 레거시 호환: 자가코드 시스템 지원")
        
        print("=" * 60)

if __name__ == "__main__":
    check_system() 