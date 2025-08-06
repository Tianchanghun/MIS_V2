#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데이터베이스 스키마 확인 스크립트
"""

import psycopg2

def check_table_schema():
    """테이블 스키마 확인"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='mis_v2',
            user='postgres',
            password='postgres',
            port=5433
        )
        cur = conn.cursor()
        
        # company_erpia_configs 테이블 스키마 확인
        print("🔍 company_erpia_configs 테이블 스키마:")
        cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'company_erpia_configs'
        ORDER BY ordinal_position;
        """)
        
        rows = cur.fetchall()
        if rows:
            for row in rows:
                print(f"  - {row[0]}: {row[1]} (NULL: {row[2]}, 기본값: {row[3]})")
        else:
            print("  테이블이 존재하지 않습니다.")
        
        # 모든 테이블 목록 확인
        print("\n📋 현재 데이터베이스의 모든 테이블:")
        cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
        """)
        
        tables = cur.fetchall()
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cur.fetchone()[0]
            print(f"  - {table[0]}: {count}건")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    check_table_schema() 