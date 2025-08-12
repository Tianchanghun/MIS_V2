from app import create_app, db
from sqlalchemy import text
import sys

app = create_app()

def add_product_detail_fields():
    """ProductDetail 테이블에 새로운 필드들 추가"""
    
    try:
        with app.app_context():
            print("🔧 ProductDetail 테이블 필드 추가 시작")
            print("="*60)
            
            # 추가할 필드들 정의
            new_fields = [
                # 코드 관리
                ("douzone_code", "VARCHAR(20)", "더존코드 (20자)"),
                ("erpia_code", "VARCHAR(13)", "ERPIA코드 (13자)"),
                
                # 가격 관리
                ("official_cost", "DECIMAL(10,0)", "공식원가 (숫자 10자)"),
                ("consumer_price", "DECIMAL(10,0)", "소비자가 (숫자 10자)"),
                ("operation_price", "DECIMAL(10,0)", "운영가 (숫자 10자)"),
                
                # ANS 및 세부 브랜드
                ("ans_value", "INTEGER", "ANS (1~30)"),
                ("detail_brand_code_seq", "INTEGER", "세부 브랜드 코드 SEQ"),
                
                # 추가 분류 코드들 (Excel 파일 기반으로 나중에 추가)
                ("category1_code_seq", "INTEGER", "분류1 코드 SEQ"),
                ("category2_code_seq", "INTEGER", "분류2 코드 SEQ"),
                ("category3_code_seq", "INTEGER", "분류3 코드 SEQ"),
                ("category4_code_seq", "INTEGER", "분류4 코드 SEQ"),
                ("category5_code_seq", "INTEGER", "분류5 코드 SEQ"),
            ]
            
            # 기존 필드 확인
            existing_fields_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'product_details' 
            AND table_schema = 'public'
            """
            
            result = db.session.execute(text(existing_fields_query))
            existing_fields = [row[0] for row in result.fetchall()]
            print(f"📋 기존 필드 개수: {len(existing_fields)}개")
            
            # 필드 추가
            added_count = 0
            skipped_count = 0
            
            for field_name, field_type, description in new_fields:
                if field_name in existing_fields:
                    print(f"⚠️ {field_name}: 이미 존재함 (건너뜀)")
                    skipped_count += 1
                    continue
                
                try:
                    # 필드 추가 SQL
                    alter_sql = f"ALTER TABLE product_details ADD COLUMN {field_name} {field_type}"
                    
                    # 제약조건 추가 (필요한 경우)
                    if field_name == "ans_value":
                        alter_sql += " CHECK (ans_value >= 1 AND ans_value <= 30)"
                    elif field_name.endswith("_code_seq"):
                        alter_sql += " REFERENCES tbl_code(seq)"
                    
                    db.session.execute(text(alter_sql))
                    print(f"✅ {field_name}: {description}")
                    added_count += 1
                    
                except Exception as e:
                    print(f"❌ {field_name}: 추가 실패 - {e}")
                    continue
            
            # 변경사항 저장
            db.session.commit()
            
            print(f"\n📈 필드 추가 결과:")
            print(f"  - 추가됨: {added_count}개")
            print(f"  - 건너뜀: {skipped_count}개")
            print(f"  - 총 필드: {len(existing_fields) + added_count}개")
            
            print("\n✅ ProductDetail 필드 추가 완료!")
            
    except Exception as e:
        db.session.rollback()
        print(f"❌ 필드 추가 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    add_product_detail_fields() 