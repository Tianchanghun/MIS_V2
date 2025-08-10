#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db
import pyodbc
from datetime import datetime

def import_full_legacy_data():
    """실제 레거시 DB에서 모든 제품 데이터를 손상없이 도커로 가져오기"""
    print("🚀 실제 레거시 DB에서 전체 데이터 마이그레이션 시작")
    print("=" * 70)
    
    # 실제 레거시 DB 연결 정보
    LEGACY_CONNECTION = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=210.109.96.74,2521;DATABASE=db_mis;UID=user_mis;PWD=user_mis!@12;ApplicationIntent=ReadOnly;"
    
    try:
        # 1. 레거시 DB 연결
        print("1️⃣ 레거시 DB 연결")
        print(f"   서버: 210.109.96.74:2521")
        print(f"   DB: db_mis")
        print(f"   사용자: user_mis")
        print(f"   모드: ReadOnly (안전)")
        
        legacy_conn = pyodbc.connect(LEGACY_CONNECTION, timeout=30)
        legacy_cursor = legacy_conn.cursor()
        print("   ✅ 레거시 DB 연결 성공!")
        
        # 2. 레거시 데이터 현황 확인
        print("\n2️⃣ 레거시 데이터 현황 확인")
        
        # 전체 제품 수 확인
        legacy_cursor.execute("SELECT COUNT(*) FROM tbl_Product WHERE UseYn = 'Y'")
        total_products = legacy_cursor.fetchone()[0]
        print(f"   📊 활성 제품: {total_products}개")
        
        # 전체 상세 수 확인
        legacy_cursor.execute("SELECT COUNT(*) FROM tbl_Product_DTL WHERE Status = 'Active'")
        total_details = legacy_cursor.fetchone()[0]
        print(f"   📊 활성 상세: {total_details}개")
        
        # 회사별 분포
        legacy_cursor.execute("""
            SELECT c.CodeName, COUNT(*) as count
            FROM tbl_Product p
            LEFT JOIN tbl_Code c ON p.Company = c.Seq
            WHERE p.UseYn = 'Y'
            GROUP BY c.CodeName
            ORDER BY count DESC
        """)
        company_dist = legacy_cursor.fetchall()
        
        print(f"   📈 회사별 분포:")
        for company in company_dist:
            print(f"      {company[0] or 'NULL'}: {company[1]}개")
        
        # 3. 도커 DB 초기화 (기존 데이터 백업)
        print("\n3️⃣ 도커 DB 안전 초기화")
        
        app = create_app()
        with app.app_context():
            # 기존 데이터 백업용 테이블 생성
            backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            print(f"   🔄 기존 데이터 백업 ({backup_timestamp})")
            
            # 기존 products 백업
            db.session.execute(db.text(f"""
                CREATE TABLE IF NOT EXISTS products_backup_{backup_timestamp} AS 
                SELECT * FROM products WHERE company_id = 1
            """))
            
            # 기존 product_details 백업
            db.session.execute(db.text(f"""
                CREATE TABLE IF NOT EXISTS product_details_backup_{backup_timestamp} AS 
                SELECT pd.* FROM product_details pd
                JOIN products p ON pd.product_id = p.id
                WHERE p.company_id = 1
            """))
            
            db.session.commit()
            print("   ✅ 기존 데이터 백업 완료")
            
            # 기존 데이터 삭제 (에이원 제품만)
            print("   🗑️ 기존 에이원 제품 데이터 삭제")
            
            # product_details 먼저 삭제 (외래키 제약)
            delete_details = db.session.execute(db.text("""
                DELETE FROM product_details 
                WHERE product_id IN (SELECT id FROM products WHERE company_id = 1)
            """))
            print(f"      삭제된 상세: {delete_details.rowcount}개")
            
            # products 삭제
            delete_products = db.session.execute(db.text("""
                DELETE FROM products WHERE company_id = 1
            """))
            print(f"      삭제된 제품: {delete_products.rowcount}개")
            
            db.session.commit()
            print("   ✅ 기존 데이터 삭제 완료")
        
        # 4. 레거시 제품 마스터 데이터 가져오기
        print("\n4️⃣ 레거시 제품 마스터 데이터 가져오기")
        
        legacy_cursor.execute("""
            SELECT 
                p.Seq,
                p.ProdName,
                p.ProdYear,
                p.ProdTagAmt,
                p.UseYn,
                p.Company,
                p.Brand,
                p.ProdGroup,
                p.ProdType,
                p.CreateDate,
                p.UpdateDate,
                cb.CodeName as CompanyName,
                cb.Code as CompanyCode,
                bb.CodeName as BrandName,
                bb.Code as BrandCode,
                pgb.CodeName as ProdGroupName,
                pgb.Code as ProdGroupCode,
                ptb.CodeName as ProdTypeName,
                ptb.Code as ProdTypeCode
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
        
        # 5. 도커 DB에 제품 마스터 삽입
        print("\n5️⃣ 도커 DB에 제품 마스터 삽입")
        
        with app.app_context():
            # 브랜드/품목/타입 코드 매핑 준비
            brand_mapping = {}
            category_mapping = {}
            type_mapping = {}
            
            # 기존 코드 조회
            result = db.session.execute(db.text("""
                SELECT c.seq, c.code, c.code_name
                FROM tbl_code p
                JOIN tbl_code c ON p.seq = c.parent_seq
                WHERE p.code_name = '브랜드'
            """))
            for row in result.fetchall():
                brand_mapping[row.code] = row.seq
            
            result = db.session.execute(db.text("""
                SELECT c.seq, c.code, c.code_name
                FROM tbl_code p
                JOIN tbl_code c ON p.seq = c.parent_seq
                WHERE p.code_name = '품목'
            """))
            for row in result.fetchall():
                category_mapping[row.code] = row.seq
            
            result = db.session.execute(db.text("""
                SELECT c.seq, c.code, c.code_name
                FROM tbl_code p
                JOIN tbl_code c ON p.seq = c.parent_seq
                WHERE p.code_name = '타입'
            """))
            for row in result.fetchall():
                type_mapping[row.code] = row.seq
            
            # 제품 삽입
            product_id_mapping = {}  # 레거시 Seq -> 도커 ID 매핑
            
            inserted_count = 0
            for product in legacy_products:
                try:
                    # 회사 ID (에이원 = 1)
                    company_id = 1  # 모든 데이터를 에이원으로
                    
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
                        'company_id': company_id,
                        'product_name': product[1],  # ProdName
                        'price': product[3] or 0,  # ProdTagAmt
                        'brand_seq': brand_seq,
                        'category_seq': category_seq,
                        'type_seq': type_seq,
                        'created_at': product[9] or datetime.now(),  # CreateDate
                        'updated_at': product[10] or datetime.now()  # UpdateDate
                    })
                    
                    new_product_id = result.fetchone()[0]
                    product_id_mapping[product[0]] = new_product_id  # 레거시 Seq -> 도커 ID
                    
                    inserted_count += 1
                    
                    if inserted_count % 100 == 0:
                        print(f"      진행률: {inserted_count}/{len(legacy_products)} ({inserted_count/len(legacy_products)*100:.1f}%)")
                
                except Exception as e:
                    print(f"      ❌ 제품 삽입 실패: {product[1]} - {e}")
                    continue
            
            db.session.commit()
            print(f"   ✅ 제품 마스터 삽입 완료: {inserted_count}개")
        
        # 6. 레거시 제품 상세 데이터 가져오기
        print("\n6️⃣ 레거시 제품 상세 데이터 가져오기")
        
        legacy_cursor.execute("""
            SELECT 
                pd.Seq,
                pd.MstSeq,
                pd.StdDivProdCode,
                pd.ProductName,
                pd.BrandCode,
                pd.DivTypeCode,
                pd.ProdGroupCode,
                pd.ProdTypeCode,
                pd.ProdCode,
                pd.ProdType2Code,
                pd.YearCode,
                pd.ProdColorCode,
                pd.Status,
                pd.CreateDate,
                pd.UpdateDate,
                LEN(pd.StdDivProdCode) as CodeLength
            FROM tbl_Product_DTL pd
            WHERE pd.Status = 'Active' 
            AND pd.MstSeq IN (SELECT Seq FROM tbl_Product WHERE UseYn = 'Y')
            ORDER BY pd.MstSeq, pd.Seq
        """)
        
        legacy_details = legacy_cursor.fetchall()
        print(f"   📥 조회된 상세: {len(legacy_details)}개")
        
        # 7. 도커 DB에 제품 상세 삽입
        print("\n7️⃣ 도커 DB에 제품 상세 삽입")
        
        with app.app_context():
            detail_inserted_count = 0
            
            for detail in legacy_details:
                try:
                    # 매핑된 제품 ID 찾기
                    master_seq = detail[1]  # MstSeq
                    product_id = product_id_mapping.get(master_seq)
                    
                    if not product_id:
                        continue  # 매핑되지 않은 제품은 스킵
                    
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
                        'created_at': detail[13] or datetime.now(),  # CreateDate
                        'updated_at': detail[14] or datetime.now()  # UpdateDate
                    })
                    
                    detail_inserted_count += 1
                    
                    if detail_inserted_count % 200 == 0:
                        print(f"      진행률: {detail_inserted_count}/{len(legacy_details)} ({detail_inserted_count/len(legacy_details)*100:.1f}%)")
                
                except Exception as e:
                    print(f"      ❌ 상세 삽입 실패: {detail[3]} - {e}")
                    continue
            
            db.session.commit()
            print(f"   ✅ 제품 상세 삽입 완료: {detail_inserted_count}개")
        
        # 8. 최종 결과 확인
        print("\n8️⃣ 최종 마이그레이션 결과 확인")
        
        with app.app_context():
            result = db.session.execute(db.text("""
                SELECT 
                    COUNT(DISTINCT p.id) as product_count,
                    COUNT(pd.id) as detail_count,
                    COUNT(CASE WHEN LENGTH(pd.std_div_prod_code) = 16 THEN 1 END) as valid_16_count,
                    AVG(p.price) as avg_price
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
            
            # 성공률 계산
            product_success_rate = (final_stats.product_count / total_products * 100) if total_products > 0 else 0
            detail_success_rate = (final_stats.detail_count / total_details * 100) if total_details > 0 else 0
            code_success_rate = (final_stats.valid_16_count / final_stats.detail_count * 100) if final_stats.detail_count > 0 else 0
            
            print(f"\n   📈 마이그레이션 성공률:")
            print(f"      제품: {product_success_rate:.1f}% ({final_stats.product_count}/{total_products})")
            print(f"      상세: {detail_success_rate:.1f}% ({final_stats.detail_count}/{total_details})")
            print(f"      16자리 코드: {code_success_rate:.1f}%")
        
        # 9. 샘플 데이터 확인
        print("\n9️⃣ 마이그레이션된 샘플 데이터 확인")
        
        with app.app_context():
            result = db.session.execute(db.text("""
                SELECT 
                    p.id,
                    p.product_name,
                    p.price,
                    COUNT(pd.id) as detail_count
                FROM products p
                LEFT JOIN product_details pd ON p.id = pd.product_id
                WHERE p.company_id = 1
                GROUP BY p.id, p.product_name, p.price
                ORDER BY p.id
                LIMIT 10
            """))
            
            samples = result.fetchall()
            print(f"   📋 샘플 제품 (처음 10개):")
            for sample in samples:
                print(f"      {sample.id}. {sample.product_name}")
                print(f"         가격: {sample.price:,}원, 상세: {sample.detail_count}개")
        
        print(f"\n🎉 레거시 DB 마이그레이션 완료!")
        print(f"✅ 총 {final_stats.product_count}개 제품, {final_stats.detail_count}개 상세 모델을 성공적으로 가져왔습니다!")
        print(f"✅ 레거시 DB는 ReadOnly 모드로 접근하여 손상 없이 안전하게 마이그레이션되었습니다!")
        print(f"📱 브라우저에서 http://127.0.0.1:5000/product/ 에서 확인하세요!")
        
    except Exception as e:
        print(f"❌ 마이그레이션 오류: {e}")
        print("💡 네트워크 연결이나 DB 접근 권한을 확인해주세요.")
    
    finally:
        if 'legacy_conn' in locals() and legacy_conn:
            legacy_conn.close()
            print("🔒 레거시 DB 연결 종료")

if __name__ == "__main__":
    import_full_legacy_data() 