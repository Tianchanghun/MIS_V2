#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DB 스키마 업데이트: legacy_seq 컬럼 추가
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db
from sqlalchemy import text

app = create_app()

def update_schema():
    """DB 스키마 업데이트"""
    with app.app_context():
        try:
            # Product 테이블에 legacy_seq 컬럼 추가
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE products 
                    ADD COLUMN legacy_seq INTEGER UNIQUE;
                """))
                conn.commit()
            print("✅ products 테이블에 legacy_seq 컬럼 추가 완료")
            
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("⚠️  products.legacy_seq 컬럼이 이미 존재함")
            else:
                print(f"❌ products 테이블 업데이트 실패: {e}")
        
        try:
            # ProductDetail 테이블에 legacy_seq 컬럼 추가
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE product_details 
                    ADD COLUMN legacy_seq INTEGER UNIQUE;
                """))
                conn.commit()
            print("✅ product_details 테이블에 legacy_seq 컬럼 추가 완료")
            
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("⚠️  product_details.legacy_seq 컬럼이 이미 존재함")
            else:
                print(f"❌ product_details 테이블 업데이트 실패: {e}")

if __name__ == '__main__':
    print("🔧 DB 스키마 업데이트 시작")
    update_schema()
    print("🎉 스키마 업데이트 완료") 