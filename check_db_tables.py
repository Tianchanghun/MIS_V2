#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def check_database_structure():
    """데이터베이스 테이블 구조 확인"""
    app = create_app()
    
    with app.app_context():
        print("🔍 데이터베이스 테이블 구조 확인")
        print("=" * 60)
        
        # 모든 테이블 조회
        result = db.session.execute(db.text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """))
        
        tables = [row[0] for row in result.fetchall()]
        print("📊 전체 테이블 목록:")
        for table in tables:
            print(f"  - {table}")
        print()
        
        # product 관련 테이블 찾기
        product_tables = [t for t in tables if 'product' in t.lower()]
        print("🎯 제품 관련 테이블:")
        for table in product_tables:
            print(f"  - {table}")
        print()
        
        # 각 제품 테이블의 구조 확인
        for table in product_tables:
            print(f"📋 {table} 테이블 구조:")
            try:
                result = db.session.execute(db.text(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                """))
                columns = result.fetchall()
                for col in columns:
                    print(f"    {col[0]} ({col[1]})")
                
                # 샘플 데이터 확인
                print(f"  📊 {table} 샘플 데이터:")
                sample_result = db.session.execute(db.text(f"SELECT * FROM {table} LIMIT 3"))
                samples = sample_result.fetchall()
                if samples:
                    for i, sample in enumerate(samples, 1):
                        print(f"    샘플 {i}: {dict(zip([col[0] for col in columns], sample))}")
                else:
                    print("    ❌ 데이터가 없습니다")
                print()
            except Exception as e:
                print(f"    ❌ 오류: {e}")
                print()

if __name__ == "__main__":
    check_database_structure() 