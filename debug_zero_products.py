#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def debug_zero_products():
    """API에서 0개 제품이 반환되는 문제 디버깅"""
    print("🔍 제품 목록 0개 문제 디버깅")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        # 1. 전체 제품 수 확인
        print("1️⃣ 전체 제품 수 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(*) as total_products,
                COUNT(CASE WHEN company_id = 1 THEN 1 END) as company_1_products,
                COUNT(CASE WHEN use_yn = 'Y' THEN 1 END) as active_products,
                COUNT(CASE WHEN is_active = true THEN 1 END) as is_active_products,
                COUNT(CASE WHEN company_id = 1 AND use_yn = 'Y' THEN 1 END) as company_1_active,
                COUNT(CASE WHEN company_id = 1 AND is_active = true THEN 1 END) as company_1_is_active
            FROM products
        """))
        
        stats = result.fetchone()
        print(f"   📊 제품 통계:")
        print(f"      전체 제품: {stats.total_products}개")
        print(f"      회사 ID=1: {stats.company_1_products}개")
        print(f"      use_yn='Y': {stats.active_products}개")
        print(f"      is_active=true: {stats.is_active_products}개")
        print(f"      회사1 + use_yn='Y': {stats.company_1_active}개")
        print(f"      회사1 + is_active=true: {stats.company_1_is_active}개")
        
        # 2. API에서 사용하는 필터 조건 확인
        print(f"\n2️⃣ API 필터 조건 확인")
        
        # API에서 실제 사용하는 쿼리 실행
        result = db.session.execute(db.text("""
            SELECT COUNT(*) as api_count
            FROM products p
            WHERE p.company_id = :company_id
        """), {'company_id': 1})
        
        api_basic = result.fetchone().api_count
        print(f"   📋 기본 API 필터 (company_id=1): {api_basic}개")
        
        # use_yn 필터 추가
        result = db.session.execute(db.text("""
            SELECT COUNT(*) as api_count
            FROM products p
            WHERE p.company_id = :company_id AND p.use_yn = 'Y'
        """), {'company_id': 1})
        
        api_useyn = result.fetchone().api_count
        print(f"   📋 use_yn 필터 추가: {api_useyn}개")
        
        # is_active 필터 확인
        result = db.session.execute(db.text("""
            SELECT COUNT(*) as api_count
            FROM products p
            WHERE p.company_id = :company_id AND p.is_active = true
        """), {'company_id': 1})
        
        api_isactive = result.fetchone().api_count
        print(f"   📋 is_active 필터 추가: {api_isactive}개")
        
        # 3. 샘플 제품 확인
        print(f"\n3️⃣ 샘플 제품 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                id, product_name, company_id, use_yn, is_active,
                brand_code_seq, category_code_seq, type_code_seq
            FROM products
            WHERE company_id = 1
            ORDER BY id
            LIMIT 10
        """))
        
        samples = result.fetchall()
        print(f"   📋 상위 10개 제품:")
        print(f"      {'ID':4} | {'제품명':25} | {'회사':3} | {'사용':4} | {'활성':4} | {'브랜드':4} | {'품목':4} | {'타입':4}")
        print(f"      {'-'*4} | {'-'*25} | {'-'*3} | {'-'*4} | {'-'*4} | {'-'*4} | {'-'*4} | {'-'*4}")
        
        for sample in samples:
            use_yn = sample.use_yn or "NULL"
            is_active = "Y" if sample.is_active else "N"
            brand = str(sample.brand_code_seq) if sample.brand_code_seq else "NULL"
            category = str(sample.category_code_seq) if sample.category_code_seq else "NULL"
            type_seq = str(sample.type_code_seq) if sample.type_code_seq else "NULL"
            
            print(f"      {sample.id:4} | {sample.product_name[:25]:25} | {sample.company_id:3} | {use_yn:4} | {is_active:4} | {brand:4} | {category:4} | {type_seq:4}")
        
        # 4. API 라우트 조건 분석
        print(f"\n4️⃣ API 라우트 조건 분석")
        
        # API에서 실제 사용되는 조건들 확인
        conditions = [
            ("기본 (company_id=1)", "p.company_id = 1"),
            ("+ use_yn='Y'", "p.company_id = 1 AND p.use_yn = 'Y'"),
            ("+ is_active=true", "p.company_id = 1 AND p.is_active = true"),
            ("+ 둘 다", "p.company_id = 1 AND p.use_yn = 'Y' AND p.is_active = true"),
        ]
        
        for desc, condition in conditions:
            result = db.session.execute(db.text(f"""
                SELECT COUNT(*) as count
                FROM products p
                WHERE {condition}
            """))
            count = result.fetchone().count
            print(f"   📋 {desc}: {count}개")
        
        # 5. 해결 방안 제시
        print(f"\n5️⃣ 해결 방안")
        
        if api_basic > 0:
            print(f"   ✅ company_id=1에 {api_basic}개 제품 존재")
            
            if api_useyn == 0:
                print(f"   ❌ use_yn='Y' 필터에서 0개 - use_yn 값 수정 필요")
                
                # use_yn 값 분포 확인
                result = db.session.execute(db.text("""
                    SELECT use_yn, COUNT(*) as count
                    FROM products
                    WHERE company_id = 1
                    GROUP BY use_yn
                    ORDER BY use_yn
                """))
                
                useyn_dist = result.fetchall()
                print(f"      use_yn 분포:")
                for dist in useyn_dist:
                    use_yn = dist.use_yn or "NULL"
                    print(f"        '{use_yn}': {dist.count}개")
                    
            if api_isactive == 0:
                print(f"   ❌ is_active=true 필터에서 0개 - is_active 값 수정 필요")
                
                # is_active 값 분포 확인
                result = db.session.execute(db.text("""
                    SELECT is_active, COUNT(*) as count
                    FROM products
                    WHERE company_id = 1
                    GROUP BY is_active
                    ORDER BY is_active
                """))
                
                isactive_dist = result.fetchall()
                print(f"      is_active 분포:")
                for dist in isactive_dist:
                    is_active = "true" if dist.is_active else "false"
                    print(f"        {is_active}: {dist.count}개")
        else:
            print(f"   ❌ company_id=1에 제품이 없음 - 기본적인 데이터 문제")

if __name__ == "__main__":
    debug_zero_products() 