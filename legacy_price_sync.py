import pyodbc
from app import create_app, db
from app.common.models import Product
import sys
import os

# 레거시 DB 연결 정보
LEGACY_DB_CONNECTION = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=210.109.96.74,2521;DATABASE=db_mis;UID=user_mis;PWD=user_mis!@12;ApplicationIntent=ReadOnly;"

app = create_app()

def connect_legacy_db():
    """레거시 DB 연결"""
    try:
        conn = pyodbc.connect(LEGACY_DB_CONNECTION)
        print("✅ 레거시 DB 연결 성공")
        return conn
    except Exception as e:
        print(f"❌ 레거시 DB 연결 실패: {e}")
        return None

def sync_product_prices():
    """레거시 DB에서 가격 정보 동기화"""
    legacy_conn = connect_legacy_db()
    if not legacy_conn:
        return
    
    try:
        with app.app_context():
            print("💰 레거시 DB에서 가격 정보 동기화 시작")
            print("="*60)
            
            # 현재 시스템에서 가격이 0인 상품들 조회
            zero_price_products = Product.query.filter_by(price=0).all()
            print(f"📊 가격이 0인 상품: {len(zero_price_products)}개")
            
            if not zero_price_products:
                print("📭 가격이 0인 상품이 없습니다.")
                return
            
            # 레거시 DB에서 가격 정보 조회
            cursor = legacy_conn.cursor()
            
            updated_count = 0
            not_found_count = 0
            
            for product in zero_price_products:
                try:
                    # legacy_seq를 이용해 레거시 DB에서 가격 조회
                    if not product.legacy_seq:
                        print(f"⚠️ {product.product_name}: legacy_seq 없음")
                        not_found_count += 1
                        continue
                    
                    # 레거시 DB 쿼리 (tbl_Product의 ProdTagAmt 필드)
                    query = """
                    SELECT ProdTagAmt 
                    FROM tbl_Product 
                    WHERE seq = ?
                    """
                    
                    cursor.execute(query, product.legacy_seq)
                    result = cursor.fetchone()
                    
                    if result and result[0] and result[0] > 0:
                        legacy_price = int(result[0])
                        
                        # 현재 시스템 업데이트
                        product.price = legacy_price
                        print(f"✅ {product.product_name[:30]:30s}: 0원 → {legacy_price:>8,}원")
                        updated_count += 1
                    else:
                        print(f"❌ {product.product_name[:30]:30s}: 레거시에도 가격 없음")
                        not_found_count += 1
                        
                except Exception as e:
                    print(f"❌ {product.product_name}: 오류 - {e}")
                    not_found_count += 1
                    continue
            
            # 변경사항 저장
            if updated_count > 0:
                db.session.commit()
                print(f"\n💾 {updated_count}개 상품 가격 업데이트 완료!")
            
            print(f"\n📈 동기화 결과:")
            print(f"  - 업데이트됨: {updated_count}개")
            print(f"  - 찾을 수 없음: {not_found_count}개")
            
    except Exception as e:
        db.session.rollback()
        print(f"❌ 가격 동기화 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if legacy_conn:
            legacy_conn.close()
            print("🔌 레거시 DB 연결 종료")

if __name__ == "__main__":
    sync_product_prices() 