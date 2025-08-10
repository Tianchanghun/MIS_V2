#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
레거시 DB 단순 확인
"""

import pyodbc

# 레거시 DB 설정
LEGACY_DB_CONFIG = {
    'server': '210.109.96.74,2521',
    'database': 'db_mis',
    'username': 'user_mis',
    'password': 'user_mis!@12'
}

def get_legacy_connection():
    """레거시 DB 연결"""
    connection_string = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={LEGACY_DB_CONFIG['server']};"
        f"DATABASE={LEGACY_DB_CONFIG['database']};"
        f"UID={LEGACY_DB_CONFIG['username']};"
        f"PWD={LEGACY_DB_CONFIG['password']};"
        f"ApplicationIntent=ReadOnly;"
    )
    
    try:
        connection = pyodbc.connect(connection_string, timeout=10)
        print(f"[OK] 레거시 DB 연결 성공")
        return connection
    except Exception as e:
        print(f"[ERROR] 레거시 DB 연결 실패: {e}")
        return None

def main():
    print("레거시 DB 코드 체계 확인")
    print("=" * 50)
    
    legacy_conn = get_legacy_connection()
    if not legacy_conn:
        return
    
    try:
        cursor = legacy_conn.cursor()
        
        # 1. tbl_Product 샘플 데이터의 실제 Brand, ProdGroup, ProdType, ProdYear 값 확인
        print(f"\n[INFO] tbl_Product 샘플 데이터의 코드 값들:")
        cursor.execute("""
            SELECT TOP 5 Seq, Company, Brand, ProdGroup, ProdType, ProdYear, ProdName 
            FROM tbl_Product 
            ORDER BY Seq
        """)
        products = cursor.fetchall()
        
        for product in products:
            seq, company, brand, prod_group, prod_type, prod_year, prod_name = product
            print(f"  - 상품 {seq}: {prod_name}")
            print(f"    Company={company}, Brand={brand}, ProdGroup={prod_group}, ProdType={prod_type}, ProdYear={prod_year}")
        
        # 2. tbl_Brand 확인 (Brand 값이 ID인지 확인)
        print(f"\n[INFO] tbl_Brand 테이블:")
        cursor.execute("SELECT TOP 10 Seq, BrandCode, BrandName FROM tbl_Brand ORDER BY Seq")
        brands = cursor.fetchall()
        for brand in brands:
            seq, code, name = brand
            print(f"  - Seq:{seq}, Code:{code}, Name:{name}")
            
        # 3. tbl_Code 그룹 확인
        print(f"\n[INFO] tbl_Code 그룹들 (Depth=0):")
        cursor.execute("SELECT Seq, Code, CodeName FROM tbl_Code WHERE Depth = 0 ORDER BY Sort")
        code_groups = cursor.fetchall()
        for group in code_groups:
            seq, code, name = group
            print(f"  - Seq:{seq}, Code:{code}, Name:{name}")
            
        # 4. 특정 그룹의 하위 코드들 (ProdGroup, ProdType 등의 실제 값 매핑 확인)
        print(f"\n[INFO] 각 그룹의 하위 코드 샘플:")
        
        target_groups = [
            ('PRT', '제품구분'),
            ('TP', '타입'), 
            ('YR', '년도'),
            ('BRAND', '브랜드')
        ]
        
        for group_code, group_desc in target_groups:
            cursor.execute("SELECT Seq FROM tbl_Code WHERE Code = ? AND Depth = 0", group_code)
            group_result = cursor.fetchone()
            
            if group_result:
                group_seq = group_result[0]
                cursor.execute("SELECT TOP 5 Seq, Code, CodeName FROM tbl_Code WHERE ParentSeq = ? ORDER BY Sort", group_seq)
                child_codes = cursor.fetchall()
                
                print(f"  [{group_desc}] ({group_code}):")
                for code in child_codes:
                    seq, code_val, code_name = code
                    print(f"    - Seq:{seq}, Code:{code_val}, Name:{code_name}")
            else:
                print(f"  [ERROR] {group_desc} ({group_code}) 그룹을 찾을 수 없음")
                
    except Exception as e:
        print(f"[ERROR] 확인 실패: {e}")
    finally:
        legacy_conn.close()

if __name__ == '__main__':
    main() 