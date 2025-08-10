#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def fix_products_table_schema():
    """products 테이블 구조 확인 및 올바른 컬럼명 파악"""
    print("🔍 products 테이블 구조 확인")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        try:
            # 1. products 테이블 구조 확인
            print("1️⃣ products 테이블 컬럼 확인")
            
            result = db.session.execute(db.text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'products' 
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            print(f"   📋 products 테이블 컬럼 ({len(columns)}개):")
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                default = f", DEFAULT: {col[3]}" if col[3] else ""
                print(f"      {col[0]} ({col[1]}) {nullable}{default}")
            
            # 2. product_details 테이블 구조 확인
            print("\n2️⃣ product_details 테이블 컬럼 확인")
            
            result = db.session.execute(db.text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'product_details' 
                ORDER BY ordinal_position
            """))
            
            detail_columns = result.fetchall()
            print(f"   📋 product_details 테이블 컬럼 ({len(detail_columns)}개):")
            for col in detail_columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                default = f", DEFAULT: {col[3]}" if col[3] else ""
                print(f"      {col[0]} ({col[1]}) {nullable}{default}")
            
            # 3. 현재 데이터 확인
            print("\n3️⃣ 현재 데이터 현황")
            
            result = db.session.execute(db.text("""
                SELECT COUNT(*) as total_products FROM products
            """))
            total_products = result.fetchone()[0]
            print(f"   📊 현재 제품 수: {total_products}개")
            
            result = db.session.execute(db.text("""
                SELECT COUNT(*) as total_details FROM product_details
            """))
            total_details = result.fetchone()[0]
            print(f"   📊 현재 상세 수: {total_details}개")
            
            # 4. 올바른 INSERT 쿼리 제안
            print("\n4️⃣ 올바른 INSERT 쿼리 제안")
            
            # products 테이블용 INSERT 구성
            product_col_names = [col[0] for col in columns if col[0] not in ['id', 'created_at', 'updated_at']]
            products_insert_cols = ', '.join(product_col_names)
            products_insert_values = ', '.join([f':{col}' for col in product_col_names])
            
            print(f"   🔧 products INSERT 쿼리:")
            print(f"      컬럼: {products_insert_cols}")
            print(f"      값: {products_insert_values}")
            
            # product_details 테이블용 INSERT 구성  
            detail_col_names = [col[0] for col in detail_columns if col[0] not in ['id', 'created_at', 'updated_at']]
            details_insert_cols = ', '.join(detail_col_names)
            details_insert_values = ', '.join([f':{col}' for col in detail_col_names])
            
            print(f"\n   🔧 product_details INSERT 쿼리:")
            print(f"      컬럼: {details_insert_cols}")
            print(f"      값: {details_insert_values}")
            
            # 5. 샘플 제품 확인 (있다면)
            if total_products > 0:
                print("\n5️⃣ 샘플 제품 데이터")
                
                result = db.session.execute(db.text("""
                    SELECT * FROM products LIMIT 3
                """))
                
                samples = result.fetchall()
                print(f"   📋 샘플 제품 ({len(samples)}개):")
                for i, sample in enumerate(samples):
                    print(f"      {i+1}. ID: {sample[0]}, 이름: {sample[2] if len(sample) > 2 else 'N/A'}")
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    fix_products_table_schema() 