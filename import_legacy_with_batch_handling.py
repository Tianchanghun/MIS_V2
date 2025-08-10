#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db
import pyodbc
from datetime import datetime

def import_legacy_with_batch_handling():
    """배치 처리와 트랜잭션 롤백 처리로 안전한 레거시 DB 마이그레이션"""
    print("🚀 개선된 레거시 DB 마이그레이션 시작 (배치 처리)")
    print("=" * 70)
    
    # 실제 레거시 DB 연결 정보
    LEGACY_CONNECTION = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=210.109.96.74,2521;DATABASE=db_mis;UID=user_mis;PWD=user_mis!@12;ApplicationIntent=ReadOnly;"
    
    try:
        # 1. 레거시 DB 연결
        print("1️⃣ 레거시 DB 연결")
        legacy_conn = pyodbc.connect(LEGACY_CONNECTION, timeout=30)
        legacy_cursor = legacy_conn.cursor()
        print("   ✅ 레거시 DB 연결 성공!")
        
        # 2. 레거시 데이터 현황 확인
        print("\n2️⃣ 레거시 데이터 현황 확인")
        
        legacy_cursor.execute("SELECT COUNT(*) FROM tbl_Product WHERE UseYn = 'Y'")
        total_products = legacy_cursor.fetchone()[0]
        print(f"   📊 활성 제품: {total_products}개")
        
        legacy_cursor.execute("SELECT COUNT(*) FROM tbl_Product_DTL WHERE Status = 'Active'")
        total_details = legacy_cursor.fetchone()[0]
        print(f"   📊 활성 상세: {total_details}개")
        
        # 3. 도커 DB 초기화
        print("\n3️⃣ 도커 DB 초기화")
        
        app = create_app()
        with app.app_context():
            # 기존 데이터 백업 및 삭제
            backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            try:
                db.session.execute(db.text(f"""
                    CREATE TABLE IF NOT EXISTS products_backup_{backup_timestamp} AS 
                    SELECT * FROM products WHERE company_id = 1
                """))
                db.session.execute(db.text(f"""
                    CREATE TABLE IF NOT EXISTS product_details_backup_{backup_timestamp} AS 
                    SELECT pd.* FROM product_details pd
                    JOIN products p ON pd.product_id = p.id
                    WHERE p.company_id = 1
                """))
                db.session.commit()
                print(f"   ✅ 기존 데이터 백업 완료 ({backup_timestamp})")
            except Exception as e:
                print(f"   ⚠️ 백업 스킵: {e}")
            
            # 기존 데이터 삭제
            delete_details = db.session.execute(db.text("""
                DELETE FROM product_details 
                WHERE product_id IN (SELECT id FROM products WHERE company_id = 1)
            """))
            delete_products = db.session.execute(db.text("""
                DELETE FROM products WHERE company_id = 1
            """))
            db.session.commit()
            print(f"   🗑️ 기존 데이터 삭제: 제품 {delete_products.rowcount}개, 상세 {delete_details.rowcount}개")
        
        # 4. 레거시 제품 데이터 가져오기
        print("\n4️⃣ 레거시 제품 데이터 가져오기")
        
        legacy_cursor.execute("""
            SELECT 
                p.Seq, p.ProdName, p.ProdYear, p.ProdTagAmt, p.UseYn,
                p.Company, p.Brand, p.ProdGroup, p.ProdType,
                p.InsDate, p.UptDate,
                cb.CodeName as CompanyName, cb.Code as CompanyCode,
                bb.CodeName as BrandName, bb.Code as BrandCode,
                pgb.CodeName as ProdGroupName, pgb.Code as ProdGroupCode,
                ptb.CodeName as ProdTypeName, ptb.Code as ProdTypeCode
            FROM tbl_Product p
            LEFT JOIN tbl_Code cb ON p.Company = cb.Seq
            LEFT JOIN tbl_Code bb ON p.Brand = bb.Seq
            LEFT JOIN tbl_Code pgb ON p.ProdGroup = pgb.Seq
            LEFT JOIN tbl_Code ptb ON p.ProdType = ptb.Seq
            WHERE p.UseYn = 'Y'
            ORDER BY p.Seq
        """)
        legacy_products = legacy_cursor.fetchall()
        print(f"   📥 조회된 제품: {len(legacy_products)}개")
        
        # 5. 제품 배치 삽입 (50개씩)
        print("\n5️⃣ 제품 배치 삽입 (50개씩)")
        
        with app.app_context():
            # 코드 매핑 준비
            brand_mapping = {}
            category_mapping = {}
            type_mapping = {}
            
            # 브랜드 매핑
            result = db.session.execute(db.text("""
                SELECT c.seq, c.code, c.code_name
                FROM tbl_code p
                JOIN tbl_code c ON p.seq = c.parent_seq
                WHERE p.code_name = '브랜드'
            """))
            for row in result.fetchall():
                brand_mapping[row.code] = row.seq
            
            # 품목 매핑
            result = db.session.execute(db.text("""
                SELECT c.seq, c.code, c.code_name
                FROM tbl_code p
                JOIN tbl_code c ON p.seq = c.parent_seq
                WHERE p.code_name = '품목'
            """))
            for row in result.fetchall():
                category_mapping[row.code] = row.seq
            
            # 타입 매핑
            result = db.session.execute(db.text("""
                SELECT c.seq, c.code, c.code_name
                FROM tbl_code p
                JOIN tbl_code c ON p.seq = c.parent_seq
                WHERE p.code_name = '타입'
            """))
            for row in result.fetchall():
                type_mapping[row.code] = row.seq
            
            print(f"   📋 코드 매핑: 브랜드 {len(brand_mapping)}개, 품목 {len(category_mapping)}개, 타입 {len(type_mapping)}개")
            
            # 배치 단위로 제품 삽입
            product_id_mapping = {}
            inserted_count = 0
            batch_size = 50
            
            for i in range(0, len(legacy_products), batch_size):
                batch = legacy_products[i:i+batch_size]
                batch_start = i + 1
                batch_end = min(i + batch_size, len(legacy_products))
                
                print(f"   🔄 배치 {batch_start}-{batch_end} 처리 중...")
                
                batch_success = 0
                for product in batch:
                    try:
                        # 새 트랜잭션 시작
                        db.session.begin()
                        
                        # 브랜드/품목/타입 코드 매핑
                        brand_seq = brand_mapping.get(product[14], None)  # BrandCode
                        category_seq = category_mapping.get(product[16], None)  # ProdGroupCode  
                        type_seq = type_mapping.get(product[18], None)  # ProdTypeCode
                        
                        # 제품 삽입
                        result = db.session.execute(db.text("""
                            INSERT INTO products (
                                company_id, product_name, price, brand_code_seq, 
                                category_code_seq, type_code_seq, status, 
                                created_at, updated_at
                            ) VALUES (
                                :company_id, :product_name, :price, :brand_seq,
                                :category_seq, :type_seq, 'Active',
                                :created_at, :updated_at
                            ) RETURNING id
                        """), {
                            'company_id': 1,  # 모든 데이터를 에이원으로
                            'product_name': product[1],  # ProdName
                            'price': product[3] or 0,  # ProdTagAmt
                            'brand_seq': brand_seq,
                            'category_seq': category_seq,
                            'type_seq': type_seq,
                            'created_at': product[9] or datetime.now(),  # InsDate
                            'updated_at': product[10] or datetime.now()  # UptDate
                        })
                        
                        new_product_id = result.fetchone()[0]
                        product_id_mapping[product[0]] = new_product_id  # 레거시 Seq -> 도커 ID
                        
                        db.session.commit()
                        batch_success += 1
                        inserted_count += 1
                        
                    except Exception as e:
                        db.session.rollback()
                        print(f"      ❌ 제품 삽입 실패: {product[1][:30]}... - {str(e)[:100]}")
                        continue
                
                print(f"      ✅ 배치 완료: {batch_success}/{len(batch)}개 성공")
            
            print(f"   ✅ 제품 마스터 삽입 완료: {inserted_count}/{len(legacy_products)}개")
        
        # 6. 레거시 제품 상세 데이터 가져오기
        print("\n6️⃣ 레거시 제품 상세 데이터 가져오기")
        
        legacy_cursor.execute("""
            SELECT 
                pd.Seq, pd.MstSeq, pd.StdDivProdCode, pd.ProductName,
                pd.BrandCode, pd.DivTypeCode, pd.ProdGroupCode, pd.ProdTypeCode,
                pd.ProdCode, pd.ProdType2Code, pd.YearCode, pd.ProdColorCode,
                pd.Status, LEN(pd.StdDivProdCode) as CodeLength
            FROM tbl_Product_DTL pd
            WHERE pd.Status = 'Active' 
            AND pd.MstSeq IN (SELECT Seq FROM tbl_Product WHERE UseYn = 'Y')
            ORDER BY pd.MstSeq, pd.Seq
        """)
        legacy_details = legacy_cursor.fetchall()
        print(f"   📥 조회된 상세: {len(legacy_details)}개")
        
        # 7. 제품 상세 배치 삽입 (100개씩)
        print("\n7️⃣ 제품 상세 배치 삽입 (100개씩)")
        
        with app.app_context():
            detail_inserted_count = 0
            detail_batch_size = 100
            
            for i in range(0, len(legacy_details), detail_batch_size):
                batch = legacy_details[i:i+detail_batch_size]
                batch_start = i + 1
                batch_end = min(i + detail_batch_size, len(legacy_details))
                
                print(f"   🔄 상세 배치 {batch_start}-{batch_end} 처리 중...")
                
                batch_success = 0
                for detail in batch:
                    try:
                        # 매핑된 제품 ID 찾기
                        master_seq = detail[1]  # MstSeq
                        product_id = product_id_mapping.get(master_seq)
                        
                        if not product_id:
                            continue  # 매핑되지 않은 제품은 스킵
                        
                        # 새 트랜잭션 시작
                        db.session.begin()
                        
                        # 상세 삽입
                        db.session.execute(db.text("""
                            INSERT INTO product_details (
                                product_id, std_div_prod_code, product_name,
                                brand_code, div_type_code, prod_group_code, prod_type_code,
                                prod_code, prod_type2_code, year_code, color_code,
                                status, created_at, updated_at
                            ) VALUES (
                                :product_id, :std_code, :product_name,
                                :brand_code, :div_type_code, :prod_group_code, :prod_type_code,
                                :prod_code, :prod_type2_code, :year_code, :color_code,
                                :status, :created_at, :updated_at
                            )
                        """), {
                            'product_id': product_id,
                            'std_code': detail[2],  # StdDivProdCode
                            'product_name': detail[3],  # ProductName
                            'brand_code': detail[4],  # BrandCode
                            'div_type_code': detail[5],  # DivTypeCode
                            'prod_group_code': detail[6],  # ProdGroupCode
                            'prod_type_code': detail[7],  # ProdTypeCode
                            'prod_code': detail[8],  # ProdCode
                            'prod_type2_code': detail[9],  # ProdType2Code
                            'year_code': detail[10],  # YearCode
                            'color_code': detail[11],  # ProdColorCode
                            'status': detail[12],  # Status
                            'created_at': datetime.now(),
                            'updated_at': datetime.now()
                        })
                        
                        db.session.commit()
                        batch_success += 1
                        detail_inserted_count += 1
                        
                    except Exception as e:
                        db.session.rollback()
                        print(f"      ❌ 상세 삽입 실패: {detail[3][:30]}... - {str(e)[:100]}")
                        continue
                
                print(f"      ✅ 상세 배치 완료: {batch_success}/{len(batch)}개 성공")
            
            print(f"   ✅ 제품 상세 삽입 완료: {detail_inserted_count}/{len(legacy_details)}개")
        
        # 8. 최종 결과 확인
        print("\n8️⃣ 최종 마이그레이션 결과")
        
        with app.app_context():
            result = db.session.execute(db.text("""
                SELECT 
                    COUNT(DISTINCT p.id) as product_count,
                    COUNT(pd.id) as detail_count,
                    COUNT(CASE WHEN LENGTH(pd.std_div_prod_code) = 16 THEN 1 END) as valid_16_count,
                    AVG(p.price) as avg_price,
                    MIN(p.price) as min_price,
                    MAX(p.price) as max_price
                FROM products p
                LEFT JOIN product_details pd ON p.id = pd.product_id
                WHERE p.company_id = 1
            """))
            
            final_stats = result.fetchone()
            
            print(f"   📊 최종 결과:")
            print(f"      총 제품: {final_stats.product_count}개")
            print(f"      총 상세: {final_stats.detail_count}개")
            print(f"      16자리 코드: {final_stats.valid_16_count}개")
            print(f"      평균 가격: {final_stats.avg_price:,.0f}원")
            print(f"      가격 범위: {final_stats.min_price:,}원 ~ {final_stats.max_price:,}원")
            
            # 성공률 계산
            product_success_rate = (final_stats.product_count / total_products * 100) if total_products > 0 else 0
            detail_success_rate = (final_stats.detail_count / total_details * 100) if total_details > 0 else 0
            code_success_rate = (final_stats.valid_16_count / final_stats.detail_count * 100) if final_stats.detail_count > 0 else 0
            
            print(f"\n   📈 마이그레이션 성공률:")
            print(f"      제품: {product_success_rate:.1f}% ({final_stats.product_count}/{total_products})")
            print(f"      상세: {detail_success_rate:.1f}% ({final_stats.detail_count}/{total_details})")
            print(f"      16자리 코드: {code_success_rate:.1f}%")
            
            # 샘플 데이터 확인
            result = db.session.execute(db.text("""
                SELECT p.product_name, COUNT(pd.id) as detail_count
                FROM products p
                LEFT JOIN product_details pd ON p.id = pd.product_id
                WHERE p.company_id = 1
                GROUP BY p.product_name
                ORDER BY detail_count DESC
                LIMIT 10
            """))
            
            samples = result.fetchall()
            print(f"\n   📋 상위 제품 (상세수 기준):")
            for sample in samples:
                print(f"      {sample.product_name}: {sample.detail_count}개 상세")
        
        print(f"\n🎉 배치 처리 마이그레이션 완료!")
        print(f"✅ 총 {final_stats.product_count}개 제품, {final_stats.detail_count}개 상세를 성공적으로 가져왔습니다!")
        print(f"✅ 레거시 DB 손상 없이 안전하게 ReadOnly 접근 완료!")
        print(f"📱 http://127.0.0.1:5000/product/ 에서 {final_stats.product_count}개 제품 확인 가능!")
        
    except Exception as e:
        print(f"❌ 마이그레이션 오류: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if 'legacy_conn' in locals() and legacy_conn:
            legacy_conn.close()
            print("🔒 레거시 DB 연결 안전 종료")

if __name__ == "__main__":
    import_legacy_with_batch_handling() 