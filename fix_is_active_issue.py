#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def fix_is_active_issue():
    """is_active=False인 활성 제품들을 True로 수정"""
    print("🔧 is_active 필드 수정")
    print("=" * 40)
    
    app = create_app()
    with app.app_context():
        # 1. 현재 상태 확인
        print("1️⃣ 현재 상태 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN use_yn = 'Y' AND is_active = true THEN 1 END) as both_active,
                COUNT(CASE WHEN use_yn = 'Y' AND is_active = false THEN 1 END) as useyn_true_isactive_false,
                COUNT(CASE WHEN use_yn = 'N' AND is_active = true THEN 1 END) as useyn_false_isactive_true,
                COUNT(CASE WHEN use_yn = 'N' AND is_active = false THEN 1 END) as both_inactive
            FROM products
            WHERE company_id = 1
        """))
        
        stats = result.fetchone()
        print(f"   📊 현재 상태:")
        print(f"      총 제품: {stats.total}개")
        print(f"      use_yn='Y' + is_active=true: {stats.both_active}개 ✅")
        print(f"      use_yn='Y' + is_active=false: {stats.useyn_true_isactive_false}개 ❌")
        print(f"      use_yn='N' + is_active=true: {stats.useyn_false_isactive_true}개 ❌")
        print(f"      use_yn='N' + is_active=false: {stats.both_inactive}개 ✅")
        
        # 2. 문제 있는 제품들 샘플 확인
        print(f"\n2️⃣ 문제 있는 제품들 확인")
        
        result = db.session.execute(db.text("""
            SELECT id, product_name, use_yn, is_active
            FROM products
            WHERE company_id = 1 
            AND ((use_yn = 'Y' AND is_active = false) OR (use_yn = 'N' AND is_active = true))
            ORDER BY id
            LIMIT 10
        """))
        
        problematic = result.fetchall()
        print(f"   📋 문제 있는 제품 (샘플 10개):")
        print(f"      {'ID':4} | {'제품명':30} | {'use_yn':6} | {'is_active':9}")
        print(f"      {'-'*4} | {'-'*30} | {'-'*6} | {'-'*9}")
        
        for product in problematic:
            use_yn = product.use_yn or "NULL"
            is_active = "true" if product.is_active else "false"
            print(f"      {product.id:4} | {product.product_name[:30]:30} | {use_yn:6} | {is_active:9}")
        
        # 3. use_yn='Y'인 제품들의 is_active를 true로 수정
        print(f"\n3️⃣ use_yn='Y' 제품들의 is_active를 true로 수정")
        
        result = db.session.execute(db.text("""
            UPDATE products 
            SET is_active = true, updated_at = NOW()
            WHERE company_id = 1 AND use_yn = 'Y' AND is_active = false
        """))
        
        updated_active = result.rowcount
        db.session.commit()
        print(f"   ✅ {updated_active}개 제품의 is_active를 true로 수정")
        
        # 4. use_yn='N'인 제품들의 is_active를 false로 수정
        print(f"\n4️⃣ use_yn='N' 제품들의 is_active를 false로 수정")
        
        result = db.session.execute(db.text("""
            UPDATE products 
            SET is_active = false, updated_at = NOW()
            WHERE company_id = 1 AND use_yn = 'N' AND is_active = true
        """))
        
        updated_inactive = result.rowcount
        db.session.commit()
        print(f"   ✅ {updated_inactive}개 제품의 is_active를 false로 수정")
        
        # 5. 수정 후 상태 확인
        print(f"\n5️⃣ 수정 후 상태 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN use_yn = 'Y' AND is_active = true THEN 1 END) as both_active,
                COUNT(CASE WHEN use_yn = 'Y' AND is_active = false THEN 1 END) as useyn_true_isactive_false,
                COUNT(CASE WHEN use_yn = 'N' AND is_active = true THEN 1 END) as useyn_false_isactive_true,
                COUNT(CASE WHEN use_yn = 'N' AND is_active = false THEN 1 END) as both_inactive
            FROM products
            WHERE company_id = 1
        """))
        
        final_stats = result.fetchone()
        print(f"   📊 수정 후 상태:")
        print(f"      총 제품: {final_stats.total}개")
        print(f"      use_yn='Y' + is_active=true: {final_stats.both_active}개 ✅")
        print(f"      use_yn='Y' + is_active=false: {final_stats.useyn_true_isactive_false}개")
        print(f"      use_yn='N' + is_active=true: {final_stats.useyn_false_isactive_true}개") 
        print(f"      use_yn='N' + is_active=false: {final_stats.both_inactive}개 ✅")
        
        # 6. API 조건에 맞는 제품 수 확인
        print(f"\n6️⃣ API 조건 제품 수 확인")
        
        result = db.session.execute(db.text("""
            SELECT COUNT(*) as api_ready_count
            FROM products
            WHERE company_id = 1 AND is_active = true
        """))
        
        api_ready = result.fetchone().api_ready_count
        print(f"   📊 API 조건 만족 제품: {api_ready}개")
        
        if api_ready > 0:
            print(f"   🎉 이제 API에서 {api_ready}개 제품이 표시됩니다!")
        else:
            print(f"   ❌ 여전히 0개 - 추가 확인 필요")
        
        print(f"\n🎉 is_active 필드 수정 완료!")
        print(f"✅ 활성 제품 {updated_active}개 수정")
        print(f"✅ 비활성 제품 {updated_inactive}개 수정")
        print(f"📱 이제 API에서 {api_ready}개 제품 표시 가능!")

if __name__ == "__main__":
    fix_is_active_issue() 