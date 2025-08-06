#!/usr/bin/env python3
"""
빠른 DB 연결 테스트
"""

import psycopg2
import pyodbc
import time

def test_postgresql():
    """PostgreSQL 연결 테스트"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5433,
            database='db_mis',
            user='mis_user',
            password='mis123!@#'
        )
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM tbl_serial')
        count = cursor.fetchone()[0]
        conn.close()
        print(f"✅ PostgreSQL 연결 성공 - tbl_serial: {count:,}건")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL 연결 실패: {e}")
        return False

def test_mssql():
    """MS-SQL 연결 테스트"""
    try:
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=210.109.96.74,2521;"
            "DATABASE=db_mis;"
            "UID=user_mis;"
            "PWD=user_mis!@12;"
            "ApplicationIntent=ReadOnly;"
            "TrustServerCertificate=yes;"
            "ConnectRetryCount=3;"
            "ConnectRetryInterval=5;"
        )
        
        print("🔄 MS-SQL 연결 시도 중...")
        start_time = time.time()
        
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM tbl_Serial')
        count = cursor.fetchone()[0]
        conn.close()
        
        elapsed = time.time() - start_time
        print(f"✅ MS-SQL 연결 성공 - tbl_Serial: {count:,}건 (소요시간: {elapsed:.1f}초)")
        return True
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ MS-SQL 연결 실패 (소요시간: {elapsed:.1f}초): {e}")
        return False

if __name__ == "__main__":
    print("🚀 DB 연결 상태 테스트")
    print("=" * 50)
    
    pg_ok = test_postgresql()
    ms_ok = test_mssql()
    
    print("=" * 50)
    if pg_ok and ms_ok:
        print("🎉 모든 DB 연결 정상!")
    else:
        print("⚠️ 일부 DB 연결에 문제가 있습니다.") 