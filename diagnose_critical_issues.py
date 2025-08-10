#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def diagnose_critical_issues():
    """UI 심각한 문제들 진단"""
    print("🚨 UI 심각한 문제들 진단")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        # 1. 년도 코드 문제 진단
        print("1️⃣ 년도 코드 문제 진단")
        
        # 년도 그룹 존재 확인
        result = db.session.execute(db.text("""
            SELECT seq FROM tbl_code WHERE code_name = '년도' AND parent_seq = 0
        """))
        year_group = result.fetchone()
        
        if not year_group:
            print("   ❌ '년도' 코드 그룹이 존재하지 않음!")
        else:
            print(f"   ✅ '년도' 그룹 존재: seq {year_group.seq}")
            
            # 년도 하위 코드들 확인
            result = db.session.execute(db.text("""
                SELECT code, code_name, seq FROM tbl_code 
                WHERE parent_seq = :parent_seq ORDER BY sort, code
            """), {'parent_seq': year_group.seq})
            
            year_codes = result.fetchall()
            print(f"      하위 년도 코드: {len(year_codes)}개")
            for year in year_codes[:10]:
                print(f"         {year.code}: {year.code_name} (seq: {year.seq})")
        
        # products 테이블의 year_code_seq 매핑 상태
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(*) as total,
                COUNT(year_code_seq) as mapped,
                COUNT(CASE WHEN year_code_seq IS NULL THEN 1 END) as unmapped
            FROM products WHERE company_id = 1 AND use_yn = 'Y'
        """))
        year_stats = result.fetchone()
        print(f"      제품의 년도 매핑: {year_stats.mapped}/{year_stats.total}개 ({year_stats.mapped/year_stats.total*100:.1f}%)")
        
        # 2. 품목/타입 매핑 문제 진단
        print(f"\n2️⃣ 품목/타입 매핑 문제 진단")
        
        # 품목 매핑 상태
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(*) as total,
                COUNT(category_code_seq) as mapped,
                COUNT(CASE WHEN category_code_seq IS NULL THEN 1 END) as unmapped
            FROM products WHERE company_id = 1 AND use_yn = 'Y'
        """))
        category_stats = result.fetchone()
        print(f"   품목 매핑: {category_stats.mapped}/{category_stats.total}개 ({category_stats.mapped/category_stats.total*100:.1f}%)")
        
        # 타입 매핑 상태
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(*) as total,
                COUNT(type_code_seq) as mapped,
                COUNT(CASE WHEN type_code_seq IS NULL THEN 1 END) as unmapped
            FROM products WHERE company_id = 1 AND use_yn = 'Y'
        """))
        type_stats = result.fetchone()
        print(f"   타입 매핑: {type_stats.mapped}/{type_stats.total}개 ({type_stats.mapped/type_stats.total*100:.1f}%)")
        
        # 3. 자가코드 "undefined" 문제 진단
        print(f"\n3️⃣ 자가코드 'undefined' 문제 진단")
        
        # product_details 테이블 상태 확인
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(*) as total_details,
                COUNT(CASE WHEN std_div_prod_code IS NOT NULL AND std_div_prod_code != '' THEN 1 END) as good_codes,
                COUNT(CASE WHEN std_div_prod_code IS NULL OR std_div_prod_code = '' THEN 1 END) as null_codes,
                COUNT(CASE WHEN LENGTH(std_div_prod_code) = 16 THEN 1 END) as valid_length
            FROM product_details
        """))
        code_stats = result.fetchone()
        print(f"   총 상세 모델: {code_stats.total_details}개")
        print(f"   유효한 자가코드: {code_stats.good_codes}개")
        print(f"   NULL/빈 자가코드: {code_stats.null_codes}개")
        print(f"   16자리 자가코드: {code_stats.valid_length}개")
        
        # products와 product_details 연결 상태
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(DISTINCT p.id) as products_with_details,
                COUNT(DISTINCT pd.product_id) as linked_products,
                COUNT(p.id) as total_products
            FROM products p
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1 AND p.use_yn = 'Y'
        """))
        link_stats = result.fetchone()
        print(f"   상세모델이 있는 제품: {link_stats.products_with_details}개")
        print(f"   연결된 제품: {link_stats.linked_products}개")
        print(f"   총 제품: {link_stats.total_products}개")
        
        # 4. 실제 샘플 데이터 확인
        print(f"\n4️⃣ 실제 샘플 데이터 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                p.id,
                p.product_name,
                p.year_code_seq,
                y.code_name as year_name,
                p.category_code_seq,
                c.code_name as category_name,
                p.type_code_seq,
                t.code_name as type_name,
                pd.std_div_prod_code
            FROM products p
            LEFT JOIN tbl_code y ON p.year_code_seq = y.seq
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            LEFT JOIN tbl_code t ON p.type_code_seq = t.seq
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1 AND p.use_yn = 'Y'
            ORDER BY p.id
            LIMIT 10
        """))
        
        samples = result.fetchall()
        print(f"   샘플 데이터 (처음 10개):")
        print(f"      {'ID':4} | {'제품명':20} | {'년도':8} | {'품목':8} | {'타입':8} | {'자가코드':16}")
        print(f"      {'-'*4} | {'-'*20} | {'-'*8} | {'-'*8} | {'-'*8} | {'-'*16}")
        
        for sample in samples:
            year_display = sample.year_name or "❌없음"
            category_display = sample.category_name or "❌없음"
            type_display = sample.type_name or "❌없음"
            code_display = sample.std_div_prod_code or "❌없음"
            
            print(f"      {sample.id:4} | {sample.product_name[:20]:20} | {year_display[:8]:8} | {category_display[:8]:8} | {type_display[:8]:8} | {code_display[:16]:16}")
        
        # 5. 레거시 호환 코드 그룹 체계 확인
        print(f"\n5️⃣ 레거시 호환 코드 그룹 체계 확인")
        
        required_groups = [
            ('브랜드', 'Brand'),
            ('구분타입', 'DivType'),
            ('품목그룹', 'ProdGroup'),
            ('제품타입', 'ProdType'),
            ('제품코드', 'ProdCode'),
            ('타입2', 'Type2'),
            ('년도', 'Year'),
            ('색상', 'Color')
        ]
        
        missing_groups = []
        for group_name, eng_name in required_groups:
            result = db.session.execute(db.text("""
                SELECT seq FROM tbl_code WHERE code_name = :group_name AND parent_seq = 0
            """), {'group_name': group_name})
            
            group = result.fetchone()
            if not group:
                missing_groups.append(group_name)
                print(f"      ❌ {group_name} ({eng_name}): 없음")
            else:
                # 하위 코드 개수 확인
                result = db.session.execute(db.text("""
                    SELECT COUNT(*) as count FROM tbl_code WHERE parent_seq = :parent_seq
                """), {'parent_seq': group.seq})
                count = result.fetchone().count
                print(f"      ✅ {group_name} ({eng_name}): {count}개 코드")
        
        # 6. 문제 요약 및 해결책 제시
        print(f"\n6️⃣ 문제 요약 및 해결책")
        
        critical_issues = []
        
        if year_stats.mapped < year_stats.total * 0.5:
            critical_issues.append("년도 매핑 부족")
        
        if category_stats.mapped < category_stats.total * 0.5:
            critical_issues.append("품목 매핑 부족")
        
        if type_stats.mapped < type_stats.total * 0.5:
            critical_issues.append("타입 매핑 부족")
        
        if code_stats.null_codes > code_stats.good_codes:
            critical_issues.append("자가코드 대량 누락")
        
        if missing_groups:
            critical_issues.append(f"코드 그룹 누락: {', '.join(missing_groups)}")
        
        print(f"   🚨 심각한 문제들:")
        for issue in critical_issues:
            print(f"      - {issue}")
        
        print(f"\n   💡 해결 순서:")
        print(f"      1. 누락된 코드 그룹 생성")
        print(f"      2. 년도 코드 매핑 대폭 개선")
        print(f"      3. 품목/타입 매핑 대폭 개선")
        print(f"      4. 자가코드 재생성")
        print(f"      5. UI 표시 로직 수정")

if __name__ == "__main__":
    diagnose_critical_issues() 