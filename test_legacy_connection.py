#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
레거시 MS-SQL DB 연결 테스트
"""
import pyodbc
import socket
from datetime import datetime

def test_network_connectivity():
    """네트워크 연결 테스트"""
    print("🌐 네트워크 연결 테스트:")
    
    try:
        # 서버 연결 테스트
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex(("210.109.96.74", 2521))
        sock.close()
        
        if result == 0:
            print("  ✅ 서버 포트 2521 연결 가능")
            return True
        else:
            print(f"  ❌ 서버 포트 2521 연결 실패 (코드: {result})")
            return False
            
    except Exception as e:
        print(f"  ❌ 네트워크 테스트 오류: {e}")
        return False

def test_legacy_connection():
    """레거시 MS-SQL 연결 테스트"""
    print("🔍 레거시 MS-SQL DB 연결 테스트 시작...")
    print(f"⏰ 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 연결 정보
    server = "210.109.96.74,2521"
    database = "db_mis"
    username = "user_mis"
    password = "user_mis!@12"
    
    print(f"📡 서버: {server}")
    print(f"🗄️ 데이터베이스: {database}")
    print(f"👤 사용자: {username}")
    
    try:
        # 연결 문자열 구성
        connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"ApplicationIntent=ReadOnly;"
        )
        
        print("🔗 연결 시도 중...")
        
        # 연결 테스트 (타임아웃 30초)
        conn = pyodbc.connect(connection_string, timeout=30)
        cursor = conn.cursor()
        
        print("✅ 연결 성공!")
        
        # 기본 정보 확인
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        print(f"🔧 SQL Server 버전: {version[:100]}...")
        
        cursor.execute("SELECT DB_NAME()")
        current_db = cursor.fetchone()[0]
        print(f"📊 현재 데이터베이스: {current_db}")
        
        cursor.execute("SELECT GETDATE()")
        server_time = cursor.fetchone()[0]
        print(f"⏰ 서버 시간: {server_time}")
        
        # 주요 테이블 확인
        print("📋 주요 테이블 확인:")
        test_tables = [
            'tbl_Member', 'tbl_Department', 'tbl_category', 
            'tbl_Code', 'tbl_Customer', 'tbl_Product',
            'tbl_Trade_Order_Mst', 'tbl_Serial', 'tbl_Shop'
        ]
        
        for table_name in test_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  ✅ {table_name}: {count:,}건")
            except Exception as e:
                print(f"  ❌ {table_name}: 오류 ({str(e)[:50]}...)")
        
        cursor.close()
        conn.close()
        
        print("✅ 레거시 DB 연결 테스트 성공!")
        return True
        
    except pyodbc.Error as e:
        print(f"❌ ODBC 연결 오류:")
        print(f"   오류 코드: {e.args[0]}")
        print(f"   오류 메시지: {e.args[1]}")
        return False
        
    except Exception as e:
        print(f"❌ 일반 오류: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("🧪 MIS v2 레거시 DB 연결 테스트")
    print("="*60)
    
    # 네트워크 연결 테스트
    network_ok = test_network_connectivity()
    
    if network_ok:
        # DB 연결 테스트
        db_ok = test_legacy_connection()
        
        if db_ok:
            print("🎉 모든 테스트 통과! 마이그레이션 진행 가능합니다.")
        else:
            print("⚠️ DB 연결 실패. 네트워크 설정이나 인증 정보를 확인해주세요.")
    else:
        print("⚠️ 네트워크 연결 실패. 방화벽이나 네트워크 설정을 확인해주세요.")
    
    print("="*60) 