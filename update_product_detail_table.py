#!/usr/bin/env python3
"""
ProductDetail 테이블에 새로운 필드들 추가
- douzone_code, erpia_code 등 코드 관리 필드들
- official_cost, consumer_price, operation_price 등 가격 관리 필드들  
- ans_value, detail_brand_code_seq 등 추가 관리 필드들
- 새로운 분류 체계 필드들
"""

from app import create_app
from app.common.models import db
from sqlalchemy import text

def update_product_detail_table():
    """ProductDetail 테이블 구조 업데이트"""
    app = create_app('development')
    
    with app.app_context():
        try:
            print("🔧 ProductDetail 테이블 업데이트 시작...")
            
            # 새로운 컬럼들 추가
            new_columns = [
                ("douzone_code", "VARCHAR(50) NULL COMMENT '더존코드'"),
                ("erpia_code", "VARCHAR(50) NULL COMMENT 'ERPIA코드'"), 
                ("official_cost", "INT DEFAULT 0 COMMENT '공식원가'"),
                ("consumer_price", "INT DEFAULT 0 COMMENT '소비자가'"),
                ("operation_price", "INT DEFAULT 0 COMMENT '운영가'"),
                ("ans_value", "INT NULL COMMENT 'ANS (01-30)'"),
                ("detail_brand_code_seq", "INT NULL COMMENT '세부브랜드 코드 seq (CL2)'"),
                ("color_detail_code_seq", "INT NULL COMMENT '색상별(상세) 코드 seq (CLD)'"),
                ("product_division_code_seq", "INT NULL COMMENT '제품구분 코드 seq (PD)'"),
                ("product_group_code_seq", "INT NULL COMMENT '제품군 코드 seq (PG)'"),
                ("item_code_seq", "INT NULL COMMENT '아이템별 코드 seq (IT)'"),
                ("item_detail_code_seq", "INT NULL COMMENT '아이템상세 코드 seq (ITD)'"),
                ("product_type_category_code_seq", "INT NULL COMMENT '제품타입 코드 seq (PT)'"),
            ]
            
            for column_name, column_def in new_columns:
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
                        # 컬럼 추가
                        add_sql = text(f"ALTER TABLE product_details ADD COLUMN {column_name} {column_def}")
                        db.session.execute(add_sql)
                        print(f"✅ 컬럼 추가: {column_name}")
                    else:
                        print(f"⏭️ 컬럼 이미 존재: {column_name}")
                        
                except Exception as e:
                    print(f"❌ 컬럼 {column_name} 추가 실패: {e}")
            
            # 외래키 제약조건 추가 (선택사항)
            foreign_keys = [
                ("fk_product_details_detail_brand", "detail_brand_code_seq", "tbl_code(seq)"),
                ("fk_product_details_color_detail", "color_detail_code_seq", "tbl_code(seq)"),
                ("fk_product_details_product_division", "product_division_code_seq", "tbl_code(seq)"),
                ("fk_product_details_product_group", "product_group_code_seq", "tbl_code(seq)"),
                ("fk_product_details_item", "item_code_seq", "tbl_code(seq)"),
                ("fk_product_details_item_detail", "item_detail_code_seq", "tbl_code(seq)"),
                ("fk_product_details_product_type_category", "product_type_category_code_seq", "tbl_code(seq)"),
            ]
            
            for fk_name, column, reference in foreign_keys:
                try:
                    fk_sql = text(f"""
                        ALTER TABLE product_details 
                        ADD CONSTRAINT {fk_name} 
                        FOREIGN KEY ({column}) REFERENCES {reference}
                    """)
                    db.session.execute(fk_sql)
                    print(f"✅ 외래키 추가: {fk_name}")
                except Exception as e:
                    if "Duplicate key name" in str(e) or "already exists" in str(e):
                        print(f"⏭️ 외래키 이미 존재: {fk_name}")
                    else:
                        print(f"⚠️ 외래키 {fk_name} 추가 실패: {e}")
            
            db.session.commit()
            print("🎉 ProductDetail 테이블 업데이트 완료!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 업데이트 실패: {e}")
            raise

if __name__ == '__main__':
    update_product_detail_table() 