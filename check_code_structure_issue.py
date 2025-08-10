#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
코드 구조 문제 확인 및 수정
"""

import sys
import os
import pyodbc
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db, Code, Product

def check_code_structure_issue():
    """레거시 DB와 현재 코드 구조 비교"""
    
    # 레거시 DB 연결
    legacy_conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=210.109.96.74,2521;"
        "DATABASE=db_mis;"
        "UID=user_mis;"
        "PWD=user_mis!@12;"
        "ApplicationIntent=ReadOnly;",
        timeout=30
    )
    
    app = create_app()
    
    with app.app_context():
        try:
            print("=== 코드 구조 문제 분석 ===\n")
            
            # 1. 레거시에서 실제 년도 코드 확인
            cursor = legacy_conn.cursor()
            
            print("📋 레거시 DB 년도 코드:")
            cursor.execute("""
                SELECT Seq, Code, CodeName 
                FROM tbl_code 
                WHERE Code = 'Year'
                ORDER BY Seq
            """)
            
            legacy_years = cursor.fetchall()
            for row in legacy_years:
                print(f"   seq: {row.Seq}, code: '{row.Code}', name: '{row.CodeName}'")
            
            print(f"\n📋 현재 시스템 년도 코드:")
            current_years = Code.get_codes_by_group_name('년도')
            for year in current_years[:10]:
                print(f"   seq: {year.seq}, code: '{year.code}', name: '{year.code_name}'")
            
            # 2. 실제 상품 매핑 확인
            print(f"\n🔍 상품 매핑 확인:")
            
            # 문제가 있는 상품들 찾기
            products_with_issues = Product.query.filter(
                Product.year_code_seq.isnot(None)
            ).limit(5).all()
            
            for product in products_with_issues:
                print(f"\n   상품: {product.product_name}")
                print(f"   year_code_seq: {product.year_code_seq}")
                
                # 해당 seq의 코드 정보 확인
                year_code = Code.query.get(product.year_code_seq)
                if year_code:
                    print(f"   매핑된 코드: '{year_code.code}' - '{year_code.code_name}'")
                    print(f"   parent_seq: {year_code.parent_seq}, depth: {year_code.depth}")
                    
                    # 부모 코드 확인
                    if year_code.parent_seq:
                        parent = Code.query.get(year_code.parent_seq)
                        if parent:
                            print(f"   부모 그룹: '{parent.code}' - '{parent.code_name}'")
                else:
                    print(f"   ❌ seq {product.year_code_seq}에 해당하는 코드 없음")
            
            # 3. 잘못된 매핑 찾기 - "직책" 관련
            print(f"\n🔍 '직책' 코드 찾기:")
            wrong_codes = Code.query.filter(Code.code_name.like('%직책%')).all()
            for code in wrong_codes:
                print(f"   seq: {code.seq}, code: '{code.code}', name: '{code.code_name}', parent: {code.parent_seq}")
                
                # 이 코드를 사용하는 상품들 찾기
                products_using_this = Product.query.filter(
                    (Product.year_code_seq == code.seq) |
                    (Product.brand_code_seq == code.seq) |
                    (Product.category_code_seq == code.seq) |
                    (Product.type_code_seq == code.seq)
                ).count()
                
                if products_using_this > 0:
                    print(f"      ❌ {products_using_this}개 상품이 이 잘못된 코드 사용 중")
            
            # 4. 레거시 상품별 실제 년도 확인
            print(f"\n🔍 레거시 상품의 실제 년도 매핑:")
            cursor.execute("""
                SELECT TOP 3 p.Seq, p.ProdName, p.ProdYear, y.CodeName as YearName
                FROM tbl_Product p
                LEFT JOIN tbl_code y ON p.ProdYear = y.Seq
                WHERE p.ProdYear IS NOT NULL
                ORDER BY p.Seq
            """)
            
            for row in cursor.fetchall():
                print(f"   레거시 상품: {row.ProdName}")
                print(f"   ProdYear seq: {row.ProdYear}, name: '{row.YearName}'")
                
                # 현재 시스템에서 이 상품 찾기
                current_product = Product.query.filter_by(legacy_seq=row.Seq).first()
                if current_product:
                    current_year = Code.query.get(current_product.year_code_seq) if current_product.year_code_seq else None
                    current_year_name = current_year.code_name if current_year else 'NULL'
                    print(f"   현재 시스템: year_code_seq: {current_product.year_code_seq}, name: '{current_year_name}'")
                    
                    if row.YearName != current_year_name:
                        print(f"   ❌ 불일치: '{row.YearName}' vs '{current_year_name}'")
                print()
            
            legacy_conn.close()
            
        except Exception as e:
            print(f"오류 발생: {e}")
            import traceback
            traceback.print_exc()
            if legacy_conn:
                legacy_conn.close()

if __name__ == "__main__":
    check_code_structure_issue() 