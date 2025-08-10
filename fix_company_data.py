#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모든 상품 데이터를 에이원으로 이전 및 API 접근 권한 수정
"""

from app import create_app
from app.common.models import db, Product, ProductDetail

app = create_app()

def fix_company_data():
    """모든 상품을 에이원(company_id=1)으로 이전"""
    
    with app.app_context():
        print("🔧 모든 상품 데이터를 에이원으로 이전")
        print("=" * 50)
        
        # 1. 현재 회사별 분포 확인
        result = db.session.execute(db.text("""
            SELECT c.company_name, COUNT(p.id) as count
            FROM companies c
            LEFT JOIN products p ON c.id = p.company_id
            GROUP BY c.id, c.company_name
            ORDER BY c.id
        """))
        
        print("📊 현재 회사별 상품 분포:")
        for row in result:
            print(f"  - {row.company_name}: {row.count}개")
        
        # 2. 모든 상품을 에이원(company_id=1)으로 이전
        try:
            update_result = db.session.execute(db.text("""
                UPDATE products 
                SET company_id = 1, updated_at = NOW() 
                WHERE company_id != 1
            """))
            
            updated_count = update_result.rowcount
            print(f"\n✅ {updated_count}개 상품을 에이원으로 이전했습니다.")
            
            db.session.commit()
            
        except Exception as e:
            print(f"❌ 상품 이전 실패: {e}")
            db.session.rollback()
            return False
        
        # 3. 이전 후 확인
        result = db.session.execute(db.text("""
            SELECT c.company_name, COUNT(p.id) as count
            FROM companies c
            LEFT JOIN products p ON c.id = p.company_id
            GROUP BY c.id, c.company_name
            ORDER BY c.id
        """))
        
        print("\n📊 이전 후 회사별 상품 분포:")
        for row in result:
            print(f"  - {row.company_name}: {row.count}개")
        
        # 4. 전체 상품 목록 확인
        products_result = db.session.execute(db.text("""
            SELECT p.product_name, p.product_code, p.price, c.company_name, b.code_name as brand_name
            FROM products p
            LEFT JOIN companies c ON p.company_id = c.id
            LEFT JOIN tbl_code b ON p.brand_code_seq = b.seq
            ORDER BY p.id
        """))
        
        print("\n📋 전체 상품 목록 (에이원 통합):")
        for i, row in enumerate(products_result, 1):
            print(f"  {i:2d}. {row.product_name}")
            print(f"      코드: {row.product_code} | 가격: {row.price:,}원")
            print(f"      회사: {row.company_name} | 브랜드: {row.brand_name}")
            print()
        
        return True

def check_api_routes():
    """API 라우트 확인"""
    
    print("\n🔍 API 라우트 상태 확인")
    print("=" * 40)
    
    import requests
    base_url = "http://localhost:5000"
    
    # 테스트할 API 엔드포인트들
    api_endpoints = [
        "/",
        "/auth/login", 
        "/product/",
        "/product/api/list",
        "/product/api/get-codes"
    ]
    
    for endpoint in api_endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            status = "✅ 정상" if response.status_code in [200, 302] else "❌ 오류"
            print(f"  {endpoint}: {response.status_code} - {status}")
        except Exception as e:
            print(f"  {endpoint}: 연결 실패 - {e}")

def generate_updated_report():
    """업데이트된 시스템 보고서"""
    
    with app.app_context():
        print("\n📋 업데이트된 시스템 현황")
        print("=" * 50)
        
        # 전체 통계
        product_count = db.session.execute(db.text("SELECT COUNT(*) FROM products")).scalar()
        detail_count = db.session.execute(db.text("SELECT COUNT(*) FROM product_details")).scalar()
        
        print(f"📊 데이터 현황:")
        print(f"  ✅ 전체 상품: {product_count}개 (모두 에이원)")
        print(f"  ✅ 상품 상세: {detail_count}개")
        
        # 자가코드 샘플
        code_samples = db.session.execute(db.text("""
            SELECT pd.std_div_prod_code, pd.product_name
            FROM product_details pd
            JOIN products p ON pd.product_id = p.id
            WHERE p.company_id = 1
            ORDER BY p.id, pd.id
            LIMIT 5
        """))
        
        print(f"\n🔧 자가코드 샘플 (에이원 통합):")
        for row in code_samples:
            print(f"  ✅ {row.std_div_prod_code} - {row.product_name}")
        
        print(f"\n🎉 모든 데이터가 에이원으로 성공적으로 통합되었습니다!")

def main():
    """메인 실행 함수"""
    
    print("🎯 에이원 데이터 통합 및 시스템 수정")
    print("=" * 60)
    
    # 1. 회사 데이터 수정
    if not fix_company_data():
        print("❌ 데이터 이전 실패")
        return
    
    # 2. API 라우트 확인
    check_api_routes()
    
    # 3. 업데이트된 보고서
    generate_updated_report()
    
    print(f"\n🚀 모든 작업 완료!")
    print(f"   모든 상품이 에이원으로 통합되었습니다.")

if __name__ == "__main__":
    main() 