#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데이터베이스 컬럼명 확인
"""

import sys
sys.path.append('.')

from app import create_app
from app.common.models import db
from sqlalchemy import text

def check_db_columns():
    app = create_app()
    with app.app_context():
        # 테이블 목록 확인
        tables = ['tbl_member', 'tbl_memberdept', 'tbl_department']
        
        for table_name in tables:
            print(f'\n=== {table_name} 테이블 컬럼 목록 ===')
            result = db.session.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}' ORDER BY ordinal_position"))
            columns = [row[0] for row in result.fetchall()]
            
            for i, col in enumerate(columns, 1):
                print(f'  {i:2d}. {col}')
            
            # 샘플 데이터
            print(f'\n{table_name} 샘플 데이터:')
            try:
                result = db.session.execute(text(f"SELECT * FROM {table_name} LIMIT 1"))
                row = result.fetchone()
                if row:
                    for col, val in zip(columns, row):
                        print(f'  {col}: {val}')
                else:
                    print('  데이터가 없습니다.')
            except Exception as e:
                print(f'  데이터 조회 오류: {e}')

if __name__ == '__main__':
    check_db_columns() 