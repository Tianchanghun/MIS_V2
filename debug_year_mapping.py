#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
년도 매핑 디버깅
"""

import sys
import os
import pyodbc
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db, Code, Product

def debug_year_mapping():
    """년도 매핑 문제 디버깅"""
    
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
            print("=== 년도 매핑 디버깅 ===\n")
            
            cursor = legacy_conn.cursor()
            
            # 1. 레거시 상품의 ProdYear 값들 확인
            print("📋 레거시 상품의 ProdYear 값 샘플:")
            cursor.execute("""
                SELECT TOP 10 p.Seq, p.ProdName, p.ProdYear, p.Brand, p.ProdGroup, p.ProdType
                FROM tbl_Product p
                WHERE p.ProdYear IS NOT NULL
                ORDER BY p.Seq
            """)
            
            for row in cursor.fetchall():
                print(f"   상품: {row.ProdName}")
                print(f"   ProdYear: {row.ProdYear} (타입: {type(row.ProdYear)})")
                print()
            
            # 2. 현재 시스템에 레거시 ProdYear 값이 있는지 확인
            print("🔍 현재 시스템에서 ProdYear 값들 확인:")
            prod_years = [18, 14, 16, 17, 19, 20, 21, 22, 23, 24, 25]
            
            for year in prod_years:
                code = Code.query.filter_by(seq=year).first()
                if code:
                    print(f"   seq {year}: code='{code.code}', name='{code.code_name}'")
                else:
                    print(f"   seq {year}: ❌ 없음")
            
            # 3. 샘플 상품의 매핑 상태 확인
            print("\n🔍 샘플 상품 매핑 상태:")
            cursor.execute("""
                SELECT TOP 3 p.Seq as LegacySeq, p.ProdName, p.ProdYear
                FROM tbl_Product p
                WHERE p.ProdYear IS NOT NULL
                ORDER BY p.Seq
            """)
            
            for row in cursor.fetchall():
                print(f"\n   레거시: {row.ProdName}")
                print(f"   ProdYear: {row.ProdYear}")
                
                # 현재 시스템에서 해당 상품 찾기
                product = Product.query.filter_by(legacy_seq=row.LegacySeq).first()
                if product:
                    print(f"   현재 year_code_seq: {product.year_code_seq}")
                    
                    if product.year_code_seq:
                        year_code = Code.query.filter_by(seq=product.year_code_seq).first()
                        if year_code:
                            print(f"   년도 코드: '{year_code.code}' - '{year_code.code_name}'")
                        else:
                            print(f"   ❌ seq {product.year_code_seq}에 해당하는 코드 없음")
                    else:
                        print(f"   ❌ year_code_seq가 NULL")
                        
                        # ProdYear 값이 현재 시스템에 있는지 확인
                        potential_code = Code.query.filter_by(seq=row.ProdYear).first()
                        if potential_code:
                            print(f"   💡 ProdYear {row.ProdYear}는 현재 시스템에 존재: '{potential_code.code}' - '{potential_code.code_name}'")
            
            legacy_conn.close()
            
        except Exception as e:
            print(f"오류 발생: {e}")
            import traceback
            traceback.print_exc()
            if legacy_conn:
                legacy_conn.close()

if __name__ == "__main__":
    debug_year_mapping() 