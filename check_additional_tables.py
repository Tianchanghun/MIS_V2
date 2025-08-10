#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
추가 레거시 테이블 구조 확인 (tbl_Product_CodeMatch, tbl_Product_CBM)
"""

import pyodbc

# 레거시 DB 연결 정보
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
        connection = pyodbc.connect(connection_string, timeout=30)
        print("✅ 레거시 DB 연결 성공")
        return connection
    except Exception as e:
        print(f"❌ 레거시 DB 연결 실패: {e}")
        return None

def check_table_structure(conn, table_name):
    """테이블 구조 확인"""
    print(f"\n🔍 {table_name} 테이블 구조:")
    cursor = conn.cursor()
    
    try:
        # 테이블 컬럼 정보 조회
        cursor.execute(f"""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                CHARACTER_MAXIMUM_LENGTH,
                COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
        """)
        
        columns = cursor.fetchall()
        print(f"   📋 컬럼 목록 ({len(columns)}개):")
        for col in columns:
            col_name = col[0]
            data_type = col[1]
            is_nullable = col[2]
            max_length = col[3] if col[3] else ''
            default_val = col[4] if col[4] else ''
            
            print(f"      {col_name:<25} {data_type}{f'({max_length})' if max_length else '':<15} {'NULL' if is_nullable == 'YES' else 'NOT NULL':<10} {default_val}")
            
    except Exception as e:
        print(f"   ❌ 테이블 구조 조회 실패: {e}")

def check_sample_data(conn, table_name, limit=5):
    """샘플 데이터 확인"""
    print(f"\n📋 {table_name} 샘플 데이터:")
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"SELECT TOP {limit} * FROM {table_name}")
        rows = cursor.fetchall()
        
        if rows:
            # 컬럼명 가져오기
            columns = [desc[0] for desc in cursor.description]
            print(f"   컬럼: {', '.join(columns)}")
            
            for i, row in enumerate(rows):
                print(f"   Row {i+1}: {dict(zip(columns, row))}")
        else:
            print("   데이터가 없습니다.")
            
    except Exception as e:
        print(f"   ❌ 샘플 데이터 조회 실패: {e}")

def check_data_count(conn, table_name):
    """데이터 수 확인"""
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"   총 데이터 수: {count:,}개")
        return count
    except Exception as e:
        print(f"   ❌ 데이터 수 조회 실패: {e}")
        return 0

def main():
    """메인 실행 함수"""
    print("🔄 추가 레거시 테이블 구조 확인 시작...")
    
    conn = get_legacy_connection()
    if not conn:
        return
    
    # 확인할 테이블 목록
    additional_tables = ['tbl_Product_CodeMatch', 'tbl_Product_CBM']
    
    for table_name in additional_tables:
        print("\n" + "=" * 80)
        check_table_structure(conn, table_name)
        check_data_count(conn, table_name)
        check_sample_data(conn, table_name)
    
    # 전체 Product 관련 테이블 목록도 다시 확인
    print("\n" + "=" * 80)
    print("📚 모든 Product 관련 테이블 목록:")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT TABLE_NAME, 
                   (SELECT COUNT(*) FROM sys.tables WHERE name = TABLE_NAME) as table_exists
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            AND TABLE_NAME LIKE '%Product%'
            ORDER BY TABLE_NAME
        """)
        
        tables = cursor.fetchall()
        for table in tables:
            print(f"   - {table[0]}")
            
    except Exception as e:
        print(f"❌ 테이블 목록 조회 실패: {e}")
    
    conn.close()
    print("\n✅ 확인 완료")

if __name__ == "__main__":
    main() 