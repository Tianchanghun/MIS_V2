#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
새로운 레거시 DB 연결 테스트 및 테이블 구조 확인
"""

import pyodbc
import os

# 레거시 DB 설정
LEGACY_DB_CONFIG = {
    'server': '210.109.96.74,2521',
    'database': 'db_mis',
    'username': 'user_mis',
    'password': 'user_mis!@12'
}

def get_legacy_connection():
    """레거시 DB 연결 (ReadOnly)"""
    connection_attempts = [
        # 시도 1: 제공된 연결 문자열 사용
        {
            'connection_string': (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={LEGACY_DB_CONFIG['server']};"
                f"DATABASE={LEGACY_DB_CONFIG['database']};"
                f"UID={LEGACY_DB_CONFIG['username']};"
                f"PWD={LEGACY_DB_CONFIG['password']};"
                f"ApplicationIntent=ReadOnly;"
            ),
            'description': 'ODBC Driver 17 (ReadOnly)'
        },
        # 시도 2: 기본 연결
        {
            'connection_string': (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={LEGACY_DB_CONFIG['server']};"
                f"DATABASE={LEGACY_DB_CONFIG['database']};"
                f"UID={LEGACY_DB_CONFIG['username']};"
                f"PWD={LEGACY_DB_CONFIG['password']};"
                f"Encrypt=no;"
                f"TrustServerCertificate=yes;"
            ),
            'description': 'ODBC Driver 17 (기본)'
        },
        # 시도 3: SQL Server Driver
        {
            'connection_string': (
                f"DRIVER={{SQL Server}};"
                f"SERVER={LEGACY_DB_CONFIG['server']};"
                f"DATABASE={LEGACY_DB_CONFIG['database']};"
                f"UID={LEGACY_DB_CONFIG['username']};"
                f"PWD={LEGACY_DB_CONFIG['password']};"
                f"Trusted_Connection=no;"
            ),
            'description': 'SQL Server Driver'
        }
    ]
    
    for attempt in connection_attempts:
        try:
            print(f"🔄 연결 시도: {attempt['description']}")
            connection = pyodbc.connect(attempt['connection_string'], timeout=10)
            print(f"✅ 레거시 DB 연결 성공: {LEGACY_DB_CONFIG['database']} ({attempt['description']})")
            return connection
        except Exception as e:
            print(f"❌ {attempt['description']} 연결 실패: {str(e)[:150]}...")
            continue
    
    print(f"❌ 모든 연결 시도 실패")
    return None

def check_tables():
    """테이블 존재 여부 및 구조 확인"""
    legacy_conn = get_legacy_connection()
    if not legacy_conn:
        return False
    
    try:
        cursor = legacy_conn.cursor()
        
        # 1. 전체 테이블 목록 확인
        print(f"\n📊 데이터베이스 '{LEGACY_DB_CONFIG['database']}' 테이블 목록:")
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME")
        tables = cursor.fetchall()
        
        for table in tables:
            print(f"  - {table[0]}")
        
        # 2. 상품 관련 테이블 확인
        product_tables = ['tbl_Product', 'tbl_Product_DTL']
        print(f"\n🔍 상품 관련 테이블 확인:")
        
        for table_name in product_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"✅ {table_name}: {count}개 레코드")
                
                # 테이블 구조 확인
                cursor.execute(f"""
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = '{table_name}' 
                    ORDER BY ORDINAL_POSITION
                """)
                columns = cursor.fetchall()
                print(f"   📋 컬럼 구조 ({len(columns)}개):")
                for col in columns:  # 모든 컬럼 표시
                    col_name, data_type, nullable, max_length = col
                    length_info = f"({max_length})" if max_length else ""
                    nullable_info = "NULL" if nullable == "YES" else "NOT NULL"
                    print(f"     - {col_name}: {data_type}{length_info} {nullable_info}")
                    
            except Exception as e:
                print(f"❌ {table_name}: 테이블이 존재하지 않거나 접근 불가 - {e}")
        
        # 3. 샘플 데이터 확인
        print(f"\n🔍 샘플 데이터 확인:")
        try:
            cursor.execute("SELECT TOP 3 * FROM tbl_Product")
            sample_products = cursor.fetchall()
            print(f"✅ tbl_Product 샘플 {len(sample_products)}개:")
            for i, product in enumerate(sample_products):
                print(f"  - 상품 {i+1}: {product[0] if len(product) > 0 else 'N/A'}")
                
        except Exception as e:
            print(f"❌ tbl_Product 샘플 데이터 조회 실패: {e}")
            
        try:
            cursor.execute("SELECT TOP 3 * FROM tbl_Product_DTL")
            sample_details = cursor.fetchall()
            print(f"✅ tbl_Product_DTL 샘플 {len(sample_details)}개:")
            for i, detail in enumerate(sample_details):
                print(f"  - 상세 {i+1}: Seq={detail[0] if len(detail) > 0 else 'N/A'}, MstSeq={detail[1] if len(detail) > 1 else 'N/A'}")
                
        except Exception as e:
            print(f"❌ tbl_Product_DTL 샘플 데이터 조회 실패: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 테이블 확인 실패: {e}")
        return False
    finally:
        legacy_conn.close()

if __name__ == '__main__':
    print("🚀 레거시 DB 연결 테스트 시작")
    print("=" * 60)
    print(f"서버: {LEGACY_DB_CONFIG['server']}")
    print(f"데이터베이스: {LEGACY_DB_CONFIG['database']}")
    print(f"사용자: {LEGACY_DB_CONFIG['username']}")
    print("=" * 60)
    
    if check_tables():
        print(f"\n🎉 레거시 DB 연결 및 테이블 확인 완료!")
    else:
        print(f"\n❌ 레거시 DB 연결 또는 테이블 확인 실패!") 