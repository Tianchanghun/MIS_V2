#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
새로운 레거시 DB 연결 테스트 및 테이블 구조 확인
"""

import pyodbc

def test_legacy_connection():
    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=210.109.96.74,2521;"
            "DATABASE=db_mis;"
            "UID=user_mis;"
            "PWD=user_mis!@12;"
            "ApplicationIntent=ReadOnly;"
        )
        print('✅ 레거시 DB 연결 테스트 성공')
        
        cursor = conn.cursor()
        cursor.execute('SELECT TOP 5 seq, ProdNm, ProdTagAmt FROM tbl_Product WHERE ProdTagAmt > 0')
        rows = cursor.fetchall()
        
        print(f'📊 가격이 있는 레거시 상품 샘플:')
        for row in rows:
            print(f'  SEQ: {row[0]:4d}, 상품명: {row[1][:30]:30s}, 가격: {row[2]:>8,}원')
        
        conn.close()
        print('🔌 연결 종료')
        
    except Exception as e:
        print(f'❌ 연결 실패: {e}')

if __name__ == "__main__":
    test_legacy_connection() 