#!/usr/bin/env python3
"""
ProductDetail 테이블에 새로운 필드들 추가 (PostgreSQL 호환)
"""

from app import create_app
from app.common.models import db
from sqlalchemy import text

def update_product_detail_table_postgres():
    """ProductDetail 테이블 구조 업데이트 (PostgreSQL)"""
    app = create_app('development')
    
    with app.app_context():
        try:
            print("🔧 ProductDetail 테이블 업데이트 시작... (PostgreSQL)")
            
            # 누락된 컬럼들만 추가
            missing_columns = [
                ("color_detail_code_seq", "INTEGER"),
                ("product_division_code_seq", "INTEGER"),
                ("product_group_code_seq", "INTEGER"),
                ("item_code_seq", "INTEGER"),
                ("item_detail_code_seq", "INTEGER"),
                ("product_type_category_code_seq", "INTEGER"),
            ]
            
            for column_name, column_type in missing_columns:
                try:
                    # 컬럼이 이미 존재하는지 확인
                    check_sql = text(f"""
                        SELECT COUNT(*) as count 
                        FROM information_schema.columns 
                        WHERE table_name = 'product_details' 
                        AND column_name = '{column_name}'
                    """)
                    result = db.session.execute(check_sql).fetchone()
                    
                    if result.count == 0:
                        # 컬럼 추가 (PostgreSQL 문법)
                        add_sql = text(f"ALTER TABLE product_details ADD COLUMN {column_name} {column_type}")
                        db.session.execute(add_sql)
                        print(f"✅ 컬럼 추가: {column_name}")
                    else:
                        print(f"⏭️ 컬럼 이미 존재: {column_name}")
                        
                except Exception as e:
                    print(f"❌ 컬럼 {column_name} 추가 실패: {e}")
            
            db.session.commit()
            print("🎉 ProductDetail 테이블 업데이트 완료!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 업데이트 실패: {e}")
            raise

if __name__ == '__main__':
    update_product_detail_table_postgres() 