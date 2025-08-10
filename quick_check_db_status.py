#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def quick_check_db_status():
    """도커 DB 제품 데이터 상태 빠르게 확인"""
    print("🔍 도커 DB 제품 데이터 상태 확인")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        # 1. 기본 통계
        print("1️⃣ 기본 통계")
        
        result = db.session.execute(db.text("""
            SELECT 
                (SELECT COUNT(*) FROM products WHERE company_id = 1) as total_products,
                (SELECT COUNT(*) FROM products WHERE company_id = 1 AND use_yn = 'Y') as active_products,
                (SELECT COUNT(*) FROM product_details) as total_details,
                (SELECT COUNT(*) FROM product_details WHERE std_div_prod_code IS NOT NULL) as details_with_code,
                (SELECT COUNT(*) FROM tbl_code WHERE parent_seq = 0) as code_groups
        """))
        
        stats = result.fetchone()
        print(f"   📊 제품: {stats.active_products}/{stats.total_products}개 (활성/전체)")
        print(f"   📊 상세모델: {stats.details_with_code}/{stats.total_details}개 (자가코드 있음/전체)")
        print(f"   📊 코드그룹: {stats.code_groups}개")
        
        # 2. 자가코드 분석
        print(f"\n2️⃣ 자가코드 분석")
        
        result = db.session.execute(db.text("""
            SELECT 
                LENGTH(std_div_prod_code) as code_length,
                COUNT(*) as count
            FROM product_details 
            WHERE std_div_prod_code IS NOT NULL
            GROUP BY LENGTH(std_div_prod_code)
            ORDER BY code_length
        """))
        
        code_lengths = result.fetchall()
        for length_info in code_lengths:
            status = "✅" if length_info.code_length == 16 else "⚠️"
            print(f"   {status} {length_info.code_length}자리: {length_info.count}개")
        
        # 3. 매핑 상태
        print(f"\n3️⃣ 제품 매핑 상태")
        
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(*) as total,
                COUNT(brand_code_seq) as brand_mapped,
                COUNT(category_code_seq) as category_mapped,
                COUNT(type_code_seq) as type_mapped,
                COUNT(year_code_seq) as year_mapped
            FROM products WHERE company_id = 1 AND use_yn = 'Y'
        """))
        
        mapping = result.fetchone()
        print(f"   📊 브랜드: {mapping.brand_mapped}/{mapping.total}개 ({mapping.brand_mapped/mapping.total*100:.1f}%)")
        print(f"   📊 품목: {mapping.category_mapped}/{mapping.total}개 ({mapping.category_mapped/mapping.total*100:.1f}%)")
        print(f"   📊 타입: {mapping.type_mapped}/{mapping.total}개 ({mapping.type_mapped/mapping.total*100:.1f}%)")
        print(f"   📊 년도: {mapping.year_mapped}/{mapping.total}개 ({mapping.year_mapped/mapping.total*100:.1f}%)")
        
        # 4. 샘플 제품 확인
        print(f"\n4️⃣ 샘플 제품 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                p.id,
                p.product_name,
                b.code_name as brand,
                c.code_name as category,
                t.code_name as type_name,
                y.code_name as year,
                pd.std_div_prod_code,
                p.price
            FROM products p
            LEFT JOIN tbl_code b ON p.brand_code_seq = b.seq
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            LEFT JOIN tbl_code t ON p.type_code_seq = t.seq
            LEFT JOIN tbl_code y ON p.year_code_seq = y.seq
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1 AND p.use_yn = 'Y'
            ORDER BY p.id
            LIMIT 5
        """))
        
        samples = result.fetchall()
        print(f"   📋 샘플 데이터:")
        print(f"      {'ID':4} | {'제품명':15} | {'브랜드':6} | {'품목':6} | {'타입':6} | {'년도':6} | {'자가코드':16} | {'가격':8}")
        print(f"      {'-'*4} | {'-'*15} | {'-'*6} | {'-'*6} | {'-'*6} | {'-'*6} | {'-'*16} | {'-'*8}")
        
        for sample in samples:
            brand = sample.brand[:6] if sample.brand else "없음"
            category = sample.category[:6] if sample.category else "없음"
            type_name = sample.type_name[:6] if sample.type_name else "없음"
            year = sample.year[:6] if sample.year else "없음"
            code = sample.std_div_prod_code[:16] if sample.std_div_prod_code else "없음"
            price = f"{sample.price:,}" if sample.price else "0"
            
            print(f"      {sample.id:4} | {sample.product_name[:15]:15} | {brand:6} | {category:6} | {type_name:6} | {year:6} | {code:16} | {price:>8}")
        
        # 5. 최종 상태 판정
        print(f"\n5️⃣ 최종 상태 판정")
        
        # 완성도 점수 계산
        completeness_score = 0
        max_score = 100
        
        # 데이터 존재 점수 (40점)
        if stats.active_products >= 600:
            completeness_score += 40
        else:
            completeness_score += (stats.active_products / 600) * 40
        
        # 자가코드 완성도 (30점)
        code_16_count = sum(info.count for info in code_lengths if info.code_length == 16)
        if code_16_count >= 900:
            completeness_score += 30
        else:
            completeness_score += (code_16_count / 900) * 30
        
        # 매핑 완성도 (30점)
        avg_mapping = (mapping.brand_mapped + mapping.category_mapped + mapping.type_mapped + mapping.year_mapped) / (4 * mapping.total)
        completeness_score += avg_mapping * 30
        
        print(f"   🎯 데이터 완성도: {completeness_score:.1f}/100")
        
        if completeness_score >= 90:
            print(f"   ✅ 우수! 데이터가 완벽하게 저장되어 있습니다.")
            print(f"   📱 UI 표시 문제만 해결하면 됩니다!")
        elif completeness_score >= 70:
            print(f"   ✅ 양호! 대부분의 데이터가 정상입니다.")
            print(f"   📱 일부 매핑 개선과 UI 수정이 필요합니다.")
        else:
            print(f"   ⚠️ 보완 필요! 추가 데이터 작업이 필요합니다.")

if __name__ == "__main__":
    quick_check_db_status() 