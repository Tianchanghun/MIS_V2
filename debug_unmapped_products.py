#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
매핑되지 않은 상품들 디버깅
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
        print("[OK] 레거시 DB 연결 성공")
        return connection
    except Exception as e:
        print(f"[ERROR] 레거시 DB 연결 실패: {e}")
        return None

def debug_unmapped_products():
    """매핑되지 않은 상품들 분석"""
    legacy_conn = get_legacy_connection()
    if not legacy_conn:
        return
    
    try:
        cursor = legacy_conn.cursor()
        
        print("매핑되지 않은 상품들 분석")
        print("=" * 50)
        
        # 문제 상품들 확인
        problem_seqs = [1111, 1116, 1117, 1118, 1119]
        
        for seq in problem_seqs:
            cursor.execute("""
                SELECT Seq, Company, Brand, ProdGroup, ProdType, ProdYear, ProdName
                FROM tbl_Product 
                WHERE Seq = ?
            """, seq)
            product = cursor.fetchone()
            
            if product:
                p_seq, company, brand, prod_group, prod_type, prod_year, prod_name = product
                print(f"\n[상품 {seq}] {prod_name}")
                print(f"  Company: {company}")
                print(f"  Brand: {brand}")
                print(f"  ProdGroup: {prod_group}")
                print(f"  ProdType: {prod_type}")
                print(f"  ProdYear: {prod_year}")
                
                # 각 코드가 실제로 존재하는지 확인
                if brand:
                    cursor.execute("SELECT BrandCode, BrandName FROM tbl_Brand WHERE Seq = ?", brand)
                    brand_info = cursor.fetchone()
                    if brand_info:
                        print(f"    -> 브랜드 정보: {brand_info[0]} ({brand_info[1]})")
                    else:
                        print(f"    -> 브랜드 정보 없음 (Seq: {brand})")
                
                if prod_group:
                    cursor.execute("SELECT Code, CodeName FROM tbl_Code WHERE Seq = ?", prod_group)
                    group_info = cursor.fetchone()
                    if group_info:
                        print(f"    -> 제품구분 정보: {group_info[0]} ({group_info[1]})")
                    else:
                        print(f"    -> 제품구분 정보 없음 (Seq: {prod_group})")
                
                if prod_type:
                    cursor.execute("SELECT Code, CodeName FROM tbl_Code WHERE Seq = ?", prod_type)
                    type_info = cursor.fetchone()
                    if type_info:
                        print(f"    -> 타입 정보: {type_info[0]} ({type_info[1]})")
                    else:
                        print(f"    -> 타입 정보 없음 (Seq: {prod_type})")
                
                if prod_year:
                    cursor.execute("SELECT Code, CodeName FROM tbl_Code WHERE Seq = ?", prod_year)
                    year_info = cursor.fetchone()
                    if year_info:
                        print(f"    -> 년도 정보: {year_info[0]} ({year_info[1]})")
                    else:
                        print(f"    -> 년도 정보 없음 (Seq: {prod_year})")
        
        # 전체 상품의 코드 분포 확인
        print(f"\n전체 상품의 코드 분포:")
        
        # 고유한 Brand 값들
        cursor.execute("SELECT DISTINCT Brand FROM tbl_Product WHERE UseYN = 'Y' AND Brand IS NOT NULL ORDER BY Brand")
        brands = cursor.fetchall()
        print(f"사용 중인 Brand SEQ 값들: {[b[0] for b in brands]}")
        
        # 고유한 ProdGroup 값들
        cursor.execute("SELECT DISTINCT ProdGroup FROM tbl_Product WHERE UseYN = 'Y' AND ProdGroup IS NOT NULL ORDER BY ProdGroup")
        groups = cursor.fetchall()
        print(f"사용 중인 ProdGroup SEQ 값들: {[g[0] for g in groups]}")
        
        # 고유한 ProdType 값들
        cursor.execute("SELECT DISTINCT ProdType FROM tbl_Product WHERE UseYN = 'Y' AND ProdType IS NOT NULL ORDER BY ProdType")
        types = cursor.fetchall()
        print(f"사용 중인 ProdType SEQ 값들: {[t[0] for t in types]}")
        
        # 고유한 ProdYear 값들
        cursor.execute("SELECT DISTINCT ProdYear FROM tbl_Product WHERE UseYN = 'Y' AND ProdYear IS NOT NULL ORDER BY ProdYear")
        years = cursor.fetchall()
        print(f"사용 중인 ProdYear SEQ 값들: {[y[0] for y in years]}")
        
    except Exception as e:
        print(f"[ERROR] 분석 실패: {e}")
    finally:
        legacy_conn.close()

if __name__ == '__main__':
    debug_unmapped_products() 