#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
직접 DB 연결로 상품 코드 매핑 수정
"""

import pyodbc
import psycopg2
import os

# 레거시 DB 설정
LEGACY_DB_CONFIG = {
    'server': '210.109.96.74,2521',
    'database': 'db_mis',
    'username': 'user_mis',
    'password': 'user_mis!@12'
}

# PostgreSQL 설정
PG_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'mis_v2',
    'user': 'postgres',
    'password': 'password'
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

def get_pg_connection():
    """PostgreSQL 연결"""
    try:
        connection = psycopg2.connect(
            host=PG_CONFIG['host'],
            port=PG_CONFIG['port'],
            database=PG_CONFIG['database'],
            user=PG_CONFIG['user'],
            password=PG_CONFIG['password']
        )
        print("[OK] PostgreSQL 연결 성공")
        return connection
    except Exception as e:
        print(f"[ERROR] PostgreSQL 연결 실패: {e}")
        return None

def build_mapping():
    """매핑 테이블 생성"""
    legacy_conn = get_legacy_connection()
    pg_conn = get_pg_connection()
    
    if not legacy_conn or not pg_conn:
        return {}
    
    mapping = {
        'brand': {},
        'prod_group': {},
        'prod_type': {},
        'year': {}
    }
    
    try:
        legacy_cursor = legacy_conn.cursor()
        pg_cursor = pg_conn.cursor()
        
        # 1. 브랜드 매핑
        print("[INFO] 브랜드 매핑 생성 중...")
        legacy_cursor.execute("SELECT Seq, BrandCode, BrandName FROM tbl_Brand")
        legacy_brands = legacy_cursor.fetchall()
        
        # PostgreSQL 브랜드 그룹 찾기
        pg_cursor.execute("SELECT seq FROM tbl_code WHERE code_name = '브랜드' AND depth = 0")
        brand_group = pg_cursor.fetchone()
        
        if brand_group:
            brand_group_seq = brand_group[0]
            
            for legacy_brand in legacy_brands:
                legacy_seq, brand_code, brand_name = legacy_brand
                
                # PostgreSQL에서 해당 브랜드 찾기
                pg_cursor.execute(
                    "SELECT seq FROM tbl_code WHERE parent_seq = %s AND code = %s",
                    (brand_group_seq, brand_code)
                )
                current_brand = pg_cursor.fetchone()
                
                if current_brand:
                    mapping['brand'][legacy_seq] = current_brand[0]
                    print(f"  브랜드 매핑: {legacy_seq} -> {current_brand[0]} ({brand_code})")
        
        # 2. 제품구분 매핑
        print("[INFO] 제품구분 매핑 생성 중...")
        legacy_cursor.execute("""
            SELECT Seq, Code, CodeName FROM tbl_Code 
            WHERE ParentSeq = (SELECT Seq FROM tbl_Code WHERE Code = 'PRT' AND Depth = 0)
        """)
        legacy_groups = legacy_cursor.fetchall()
        
        # PostgreSQL 제품구분 그룹 찾기
        pg_cursor.execute("SELECT seq FROM tbl_code WHERE code_name = '제품구분' AND depth = 0")
        category_group = pg_cursor.fetchone()
        
        if category_group:
            category_group_seq = category_group[0]
            
            for legacy_group in legacy_groups:
                legacy_seq, group_code, group_name = legacy_group
                
                pg_cursor.execute(
                    "SELECT seq FROM tbl_code WHERE parent_seq = %s AND code = %s",
                    (category_group_seq, group_code)
                )
                current_category = pg_cursor.fetchone()
                
                if current_category:
                    mapping['prod_group'][legacy_seq] = current_category[0]
                    print(f"  제품구분 매핑: {legacy_seq} -> {current_category[0]} ({group_code})")
        
        # 3. 타입 매핑
        print("[INFO] 타입 매핑 생성 중...")
        legacy_cursor.execute("""
            SELECT Seq, Code, CodeName FROM tbl_Code 
            WHERE ParentSeq = (SELECT Seq FROM tbl_Code WHERE Code = 'TP' AND Depth = 0)
        """)
        legacy_types = legacy_cursor.fetchall()
        
        # PostgreSQL 타입 그룹 찾기
        pg_cursor.execute("SELECT seq FROM tbl_code WHERE code_name = '타입' AND depth = 0")
        type_group = pg_cursor.fetchone()
        
        if type_group:
            type_group_seq = type_group[0]
            
            for legacy_type in legacy_types:
                legacy_seq, type_code, type_name = legacy_type
                
                pg_cursor.execute(
                    "SELECT seq FROM tbl_code WHERE parent_seq = %s AND code = %s",
                    (type_group_seq, type_code)
                )
                current_type = pg_cursor.fetchone()
                
                if current_type:
                    mapping['prod_type'][legacy_seq] = current_type[0]
                    print(f"  타입 매핑: {legacy_seq} -> {current_type[0]} ({type_code})")
        
        # 4. 년도 매핑
        print("[INFO] 년도 매핑 생성 중...")
        legacy_cursor.execute("""
            SELECT Seq, Code, CodeName FROM tbl_Code 
            WHERE ParentSeq = (SELECT Seq FROM tbl_Code WHERE Code = 'YR' AND Depth = 0)
        """)
        legacy_years = legacy_cursor.fetchall()
        
        # PostgreSQL 년도 그룹 찾기
        pg_cursor.execute("SELECT seq FROM tbl_code WHERE code_name = '년도' AND depth = 0")
        year_group = pg_cursor.fetchone()
        
        if year_group:
            year_group_seq = year_group[0]
            
            for legacy_year in legacy_years:
                legacy_seq, year_code, year_name = legacy_year
                
                pg_cursor.execute(
                    "SELECT seq FROM tbl_code WHERE parent_seq = %s AND code = %s",
                    (year_group_seq, year_code)
                )
                current_year = pg_cursor.fetchone()
                
                if current_year:
                    mapping['year'][legacy_seq] = current_year[0]
                    print(f"  년도 매핑: {legacy_seq} -> {current_year[0]} ({year_code})")
        
        return mapping
        
    except Exception as e:
        print(f"[ERROR] 매핑 생성 실패: {e}")
        return {}
    finally:
        legacy_conn.close()
        pg_conn.close()

def apply_mapping():
    """매핑 적용"""
    print("\n[INFO] 매핑 테이블 생성...")
    mapping = build_mapping()
    
    if not mapping:
        print("[ERROR] 매핑 테이블 생성 실패")
        return
    
    print(f"\n[INFO] 매핑 통계:")
    print(f"  - 브랜드: {len(mapping['brand'])}개")
    print(f"  - 제품구분: {len(mapping['prod_group'])}개")
    print(f"  - 타입: {len(mapping['prod_type'])}개")
    print(f"  - 년도: {len(mapping['year'])}개")
    
    # PostgreSQL에 매핑 적용
    legacy_conn = get_legacy_connection()
    pg_conn = get_pg_connection()
    
    if not legacy_conn or not pg_conn:
        return
    
    try:
        legacy_cursor = legacy_conn.cursor()
        pg_cursor = pg_conn.cursor()
        
        # 레거시 상품 정보 가져오기
        legacy_cursor.execute("""
            SELECT Seq, Company, Brand, ProdGroup, ProdType, ProdYear, ProdName
            FROM tbl_Product 
            WHERE UseYN = 'Y'
            ORDER BY Seq
        """)
        legacy_products = legacy_cursor.fetchall()
        
        print(f"\n[INFO] {len(legacy_products)}개 상품 매핑 적용 중...")
        
        updated_count = 0
        
        for legacy_product in legacy_products:
            legacy_seq, company, brand, prod_group, prod_type, prod_year, prod_name = legacy_product
            
            try:
                # 업데이트할 값들 준비
                brand_seq = mapping['brand'].get(brand)
                category_seq = mapping['prod_group'].get(prod_group)
                type_seq = mapping['prod_type'].get(prod_type)
                year_seq = mapping['year'].get(prod_year)
                
                # PostgreSQL 상품 업데이트
                pg_cursor.execute("""
                    UPDATE products 
                    SET brand_code_seq = %s,
                        category_code_seq = %s,
                        type_code_seq = %s,
                        year_code_seq = %s,
                        updated_by = 'mapping_fix',
                        updated_at = NOW()
                    WHERE legacy_seq = %s
                """, (brand_seq, category_seq, type_seq, year_seq, legacy_seq))
                
                if pg_cursor.rowcount > 0:
                    updated_count += 1
                    
                    if updated_count % 100 == 0:
                        pg_conn.commit()
                        print(f"  진행률: {updated_count}/{len(legacy_products)}")
                
            except Exception as e:
                print(f"  [ERROR] 상품 {legacy_seq} 업데이트 실패: {e}")
                pg_conn.rollback()
        
        # 최종 커밋
        pg_conn.commit()
        
        print(f"\n[OK] 상품 매핑 적용 완료!")
        print(f"  - 업데이트된 상품: {updated_count}개")
        
        # 결과 확인
        pg_cursor.execute("""
            SELECT p.product_name, p.legacy_seq,
                   b.code_name as brand_name,
                   c.code_name as category_name,
                   t.code_name as type_name,
                   y.code_name as year_name
            FROM products p
            LEFT JOIN tbl_code b ON p.brand_code_seq = b.seq
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            LEFT JOIN tbl_code t ON p.type_code_seq = t.seq
            LEFT JOIN tbl_code y ON p.year_code_seq = y.seq
            WHERE p.legacy_seq IS NOT NULL
            LIMIT 5
        """)
        
        sample_products = pg_cursor.fetchall()
        
        print(f"\n[INFO] 매핑 결과 샘플:")
        for product in sample_products:
            product_name, legacy_seq, brand_name, category_name, type_name, year_name = product
            print(f"  - {product_name} (Legacy:{legacy_seq})")
            print(f"    브랜드:{brand_name}, 품목:{category_name}, 타입:{type_name}, 년도:{year_name}")
        
    except Exception as e:
        print(f"[ERROR] 매핑 적용 실패: {e}")
        pg_conn.rollback()
    finally:
        legacy_conn.close()
        pg_conn.close()

if __name__ == '__main__':
    print("상품 코드 매핑 수정 시작")
    print("=" * 50)
    
    apply_mapping()
    
    print(f"\n[OK] 매핑 수정 완료! 이제 웹 페이지를 새로고침하세요.") 