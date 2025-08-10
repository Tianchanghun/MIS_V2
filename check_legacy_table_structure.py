#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pyodbc

def check_legacy_table_structure():
    """레거시 DB의 실제 테이블 구조 확인"""
    print("🔍 레거시 DB 테이블 구조 확인")
    print("=" * 50)
    
    # 실제 레거시 DB 연결 정보
    LEGACY_CONNECTION = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=210.109.96.74,2521;DATABASE=db_mis;UID=user_mis;PWD=user_mis!@12;ApplicationIntent=ReadOnly;"
    
    try:
        # 레거시 DB 연결
        print("📡 레거시 DB 연결 중...")
        legacy_conn = pyodbc.connect(LEGACY_CONNECTION, timeout=30)
        legacy_cursor = legacy_conn.cursor()
        print("✅ 연결 성공!")
        
        # 1. tbl_Product 테이블 구조 확인
        print("\n1️⃣ tbl_Product 테이블 구조")
        
        legacy_cursor.execute("""
            SELECT 
                COLUMN_NAME, 
                DATA_TYPE, 
                IS_NULLABLE,
                CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'tbl_Product'
            ORDER BY ORDINAL_POSITION
        """)
        
        product_columns = legacy_cursor.fetchall()
        print(f"   📋 tbl_Product 컬럼 ({len(product_columns)}개):")
        for col in product_columns:
            max_len = f"({col[3]})" if col[3] else ""
            nullable = "NULL" if col[2] == "YES" else "NOT NULL"
            print(f"      {col[0]} {col[1]}{max_len} {nullable}")
        
        # 2. tbl_Product_DTL 테이블 구조 확인
        print("\n2️⃣ tbl_Product_DTL 테이블 구조")
        
        legacy_cursor.execute("""
            SELECT 
                COLUMN_NAME, 
                DATA_TYPE, 
                IS_NULLABLE,
                CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'tbl_Product_DTL'
            ORDER BY ORDINAL_POSITION
        """)
        
        detail_columns = legacy_cursor.fetchall()
        print(f"   📋 tbl_Product_DTL 컬럼 ({len(detail_columns)}개):")
        for col in detail_columns:
            max_len = f"({col[3]})" if col[3] else ""
            nullable = "NULL" if col[2] == "YES" else "NOT NULL"
            print(f"      {col[0]} {col[1]}{max_len} {nullable}")
        
        # 3. 샘플 데이터 확인 (컬럼명 검증)
        print("\n3️⃣ 샘플 데이터로 실제 컬럼명 확인")
        
        # tbl_Product 샘플
        legacy_cursor.execute("SELECT TOP 1 * FROM tbl_Product")
        sample_product = legacy_cursor.fetchone()
        product_col_names = [desc[0] for desc in legacy_cursor.description]
        
        print(f"   📋 tbl_Product 실제 컬럼명:")
        for i, col_name in enumerate(product_col_names):
            sample_value = sample_product[i] if sample_product else "NULL"
            print(f"      {i+1:2d}. {col_name}: {sample_value}")
        
        # tbl_Product_DTL 샘플
        print(f"\n   📋 tbl_Product_DTL 실제 컬럼명:")
        legacy_cursor.execute("SELECT TOP 1 * FROM tbl_Product_DTL")
        sample_detail = legacy_cursor.fetchone()
        detail_col_names = [desc[0] for desc in legacy_cursor.description]
        
        for i, col_name in enumerate(detail_col_names):
            sample_value = sample_detail[i] if sample_detail else "NULL"
            print(f"      {i+1:2d}. {col_name}: {sample_value}")
        
        # 4. 날짜 관련 컬럼 확인
        print("\n4️⃣ 날짜 관련 컬럼 확인")
        
        date_columns_product = [col for col in product_col_names if any(keyword in col.lower() for keyword in ['date', 'time', 'created', 'updated', 'modified'])]
        date_columns_detail = [col for col in detail_col_names if any(keyword in col.lower() for keyword in ['date', 'time', 'created', 'updated', 'modified'])]
        
        print(f"   📅 tbl_Product 날짜 컬럼: {date_columns_product}")
        print(f"   📅 tbl_Product_DTL 날짜 컬럼: {date_columns_detail}")
        
        # 5. 정확한 쿼리 생성을 위한 정보 출력
        print("\n5️⃣ 마이그레이션용 정확한 쿼리 정보")
        
        print(f"   🔧 tbl_Product SELECT 쿼리 컬럼:")
        essential_product_cols = []
        for col in product_col_names:
            if col in ['Seq', 'ProdName', 'ProdYear', 'ProdTagAmt', 'UseYn', 'Company', 'Brand', 'ProdGroup', 'ProdType']:
                essential_product_cols.append(col)
        
        print(f"      필수: {', '.join(essential_product_cols)}")
        print(f"      날짜: {', '.join(date_columns_product) if date_columns_product else 'None'}")
        
        print(f"\n   🔧 tbl_Product_DTL SELECT 쿼리 컬럼:")
        essential_detail_cols = []
        for col in detail_col_names:
            if col in ['Seq', 'MstSeq', 'StdDivProdCode', 'ProductName', 'BrandCode', 'DivTypeCode', 'ProdGroupCode', 'ProdTypeCode', 'ProdCode', 'ProdType2Code', 'YearCode', 'ProdColorCode', 'Status']:
                essential_detail_cols.append(col)
        
        print(f"      필수: {', '.join(essential_detail_cols)}")
        print(f"      날짜: {', '.join(date_columns_detail) if date_columns_detail else 'None'}")
        
    except Exception as e:
        print(f"❌ 오류: {e}")
    
    finally:
        if 'legacy_conn' in locals() and legacy_conn:
            legacy_conn.close()
            print("\n🔒 레거시 DB 연결 종료")

if __name__ == "__main__":
    check_legacy_table_structure() 