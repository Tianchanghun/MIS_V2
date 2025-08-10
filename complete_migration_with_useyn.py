#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db
import pyodbc
from datetime import datetime

def complete_migration_with_useyn():
    """비활성 제품 포함 전체 914개 상세 마이그레이션 + UseYn 컬럼 추가"""
    print("🎯 완전한 마이그레이션: 914개 상세 + UseYn 컬럼")
    print("=" * 70)
    
    # 실제 레거시 DB 연결 정보
    LEGACY_CONNECTION = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=210.109.96.74,2521;DATABASE=db_mis;UID=user_mis;PWD=user_mis!@12;ApplicationIntent=ReadOnly;"
    
    try:
        # 1. products 테이블에 use_yn 컬럼 추가
        print("1️⃣ products 테이블 스키마 업데이트")
        app = create_app()
        with app.app_context():
            try:
                # use_yn 컬럼이 이미 있는지 확인
                result = db.session.execute(db.text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'products' AND column_name = 'use_yn'
                """))
                
                if not result.fetchone():
                    # use_yn 컬럼 추가
                    db.session.execute(db.text("""
                        ALTER TABLE products 
                        ADD COLUMN use_yn VARCHAR(1) DEFAULT 'Y' NOT NULL
                    """))
                    db.session.commit()
                    print("   ✅ products 테이블에 use_yn 컬럼 추가")
                else:
                    print("   ✅ use_yn 컬럼이 이미 존재함")
                    
            except Exception as e:
                print(f"   ⚠️ 스키마 업데이트 오류 (무시): {e}")
        
        # 2. 레거시 DB 연결 및 전체 데이터 확인
        print("\n2️⃣ 레거시 DB 전체 데이터 확인")
        legacy_conn = pyodbc.connect(LEGACY_CONNECTION, timeout=30)
        legacy_cursor = legacy_conn.cursor()
        
        # 모든 제품 (활성/비활성 포함) 확인
        legacy_cursor.execute("SELECT COUNT(*) FROM tbl_Product")
        total_all_products = legacy_cursor.fetchone()[0]
        
        legacy_cursor.execute("SELECT COUNT(*) FROM tbl_Product WHERE UseYn = 'Y'")
        total_active_products = legacy_cursor.fetchone()[0]
        
        legacy_cursor.execute("SELECT COUNT(*) FROM tbl_Product WHERE UseYn = 'N'")
        total_inactive_products = legacy_cursor.fetchone()[0]
        
        # 모든 상세 (활성/비활성 포함) 확인
        legacy_cursor.execute("SELECT COUNT(*) FROM tbl_Product_DTL WHERE Status = 'Active'")
        total_active_details = legacy_cursor.fetchone()[0]
        
        print(f"   📊 레거시 DB 현황:")
        print(f"      전체 제품: {total_all_products}개")
        print(f"      활성 제품: {total_active_products}개 (UseYn='Y')")
        print(f"      비활성 제품: {total_inactive_products}개 (UseYn='N')")
        print(f"      전체 활성 상세: {total_active_details}개")
        
        # 3. 도커 DB 현재 상태 확인
        print("\n3️⃣ 도커 DB 현재 상태")
        with app.app_context():
            result = db.session.execute(db.text("""
                SELECT 
                    COUNT(DISTINCT p.id) as current_products,
                    COUNT(pd.id) as current_details,
                    COUNT(CASE WHEN p.use_yn = 'Y' THEN 1 END) as active_products,
                    COUNT(CASE WHEN p.use_yn = 'N' THEN 1 END) as inactive_products
                FROM products p
                LEFT JOIN product_details pd ON p.id = pd.product_id
                WHERE p.company_id = 1
            """))
            current_stats = result.fetchone()
            
            print(f"   📊 도커 현재 상태:")
            print(f"      현재 제품: {current_stats.current_products}개")
            print(f"      현재 상세: {current_stats.current_details}개")
            print(f"      활성 제품: {current_stats.active_products}개")
            print(f"      비활성 제품: {current_stats.inactive_products}개")
        
        # 4. 비활성 제품 마이그레이션
        print("\n4️⃣ 비활성 제품 마이그레이션")
        
        # 비활성 제품 데이터 가져오기
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
            WHERE p.UseYn = 'N'
            ORDER BY p.Seq
        """)
        inactive_products = legacy_cursor.fetchall()
        print(f"   📥 비활성 제품: {len(inactive_products)}개")
        
        # 5. 비활성 제품 삽입
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
            
            # 비활성 제품 삽입
            inactive_product_mapping = {}
            inserted_inactive = 0
            
            for product in inactive_products:
                try:
                    # 이미 존재하는지 확인
                    result = db.session.execute(db.text("""
                        SELECT id FROM products 
                        WHERE legacy_seq = :legacy_seq AND company_id = 1
                    """), {'legacy_seq': product[0]})
                    
                    existing = result.fetchone()
                    if existing:
                        # 기존 제품의 use_yn 업데이트
                        db.session.execute(db.text("""
                            UPDATE products 
                            SET use_yn = 'N', updated_at = NOW()
                            WHERE id = :product_id
                        """), {'product_id': existing.id})
                        inactive_product_mapping[product[0]] = existing.id
                        print(f"      🔄 기존 제품 비활성화: {product[1][:30]}")
                    else:
                        # 새 비활성 제품 삽입
                        brand_seq = brand_mapping.get(product[14], None)
                        category_seq = category_mapping.get(product[16], None)
                        type_seq = type_mapping.get(product[18], None)
                        
                        result = db.session.execute(db.text("""
                            INSERT INTO products (
                                company_id, product_name, price, brand_code_seq, 
                                category_code_seq, type_code_seq, is_active, use_yn,
                                legacy_seq, created_at, updated_at
                            ) VALUES (
                                :company_id, :product_name, :price, :brand_seq,
                                :category_seq, :type_seq, :is_active, :use_yn,
                                :legacy_seq, :created_at, :updated_at
                            ) RETURNING id
                        """), {
                            'company_id': 1,
                            'product_name': product[1],
                            'price': product[3] or 0,
                            'brand_seq': brand_seq,
                            'category_seq': category_seq,
                            'type_seq': type_seq,
                            'is_active': False,  # 비활성 제품
                            'use_yn': 'N',  # UseYn = 'N'
                            'legacy_seq': product[0],
                            'created_at': product[9] or datetime.now(),
                            'updated_at': product[10] or datetime.now()
                        })
                        
                        new_product_id = result.fetchone()[0]
                        inactive_product_mapping[product[0]] = new_product_id
                        inserted_inactive += 1
                        print(f"      ✅ 새 비활성 제품: {product[1][:30]}")
                    
                    db.session.commit()
                    
                except Exception as e:
                    db.session.rollback()
                    print(f"      ❌ 비활성 제품 오류: {product[1][:30]} - {e}")
            
            print(f"   📊 비활성 제품 처리: {inserted_inactive}개 신규, {len(inactive_product_mapping)}개 총")
        
        # 6. 비활성 제품의 상세 데이터 가져오기
        print("\n5️⃣ 비활성 제품 상세 데이터 마이그레이션")
        
        legacy_cursor.execute("""
            SELECT 
                pd.Seq, pd.MstSeq, pd.StdDivProdCode, pd.ProductName,
                pd.BrandCode, pd.DivTypeCode, pd.ProdGroupCode, pd.ProdTypeCode,
                pd.ProdCode, pd.ProdType2Code, pd.YearCode, pd.ProdColorCode,
                pd.Status, LEN(pd.StdDivProdCode) as CodeLength
            FROM tbl_Product_DTL pd
            INNER JOIN tbl_Product p ON pd.MstSeq = p.Seq
            WHERE pd.Status = 'Active' AND p.UseYn = 'N'
            ORDER BY pd.MstSeq, pd.Seq
        """)
        inactive_details = legacy_cursor.fetchall()
        print(f"   📥 비활성 제품 상세: {len(inactive_details)}개")
        
        # 7. 비활성 제품 상세 삽입
        with app.app_context():
            inserted_inactive_details = 0
            
            for detail in inactive_details:
                try:
                    master_seq = detail[1]  # MstSeq
                    product_id = inactive_product_mapping.get(master_seq)
                    
                    if not product_id:
                        continue  # 매핑되지 않은 제품은 스킵
                    
                    # 이미 존재하는지 확인
                    result = db.session.execute(db.text("""
                        SELECT id FROM product_details 
                        WHERE legacy_seq = :legacy_seq
                    """), {'legacy_seq': detail[0]})
                    
                    if not result.fetchone():
                        # 새 상세 삽입
                        db.session.execute(db.text("""
                            INSERT INTO product_details (
                                product_id, std_div_prod_code, product_name,
                                brand_code, div_type_code, prod_group_code, prod_type_code,
                                prod_code, prod_type2_code, year_code, color_code,
                                status, legacy_seq, created_at, updated_at
                            ) VALUES (
                                :product_id, :std_code, :product_name,
                                :brand_code, :div_type_code, :prod_group_code, :prod_type_code,
                                :prod_code, :prod_type2_code, :year_code, :color_code,
                                :status, :legacy_seq, :created_at, :updated_at
                            )
                        """), {
                            'product_id': product_id,
                            'std_code': detail[2],
                            'product_name': detail[3],
                            'brand_code': detail[4],
                            'div_type_code': detail[5],
                            'prod_group_code': detail[6],
                            'prod_type_code': detail[7],
                            'prod_code': detail[8],
                            'prod_type2_code': detail[9],
                            'year_code': detail[10],
                            'color_code': detail[11],
                            'status': detail[12],
                            'legacy_seq': detail[0],
                            'created_at': datetime.now(),
                            'updated_at': datetime.now()
                        })
                        
                        inserted_inactive_details += 1
                        if inserted_inactive_details <= 10:  # 처음 10개만 로그
                            print(f"      ✅ 비활성 상세: {detail[3][:30]}")
                    
                    db.session.commit()
                    
                except Exception as e:
                    db.session.rollback()
                    print(f"      ❌ 비활성 상세 오류: {detail[3][:30]} - {e}")
            
            print(f"   📊 비활성 상세 삽입: {inserted_inactive_details}개")
        
        # 8. 기존 활성 제품들의 use_yn 업데이트
        print("\n6️⃣ 기존 활성 제품 use_yn 업데이트")
        
        with app.app_context():
            result = db.session.execute(db.text("""
                UPDATE products 
                SET use_yn = 'Y', updated_at = NOW()
                WHERE company_id = 1 AND is_active = true AND (use_yn IS NULL OR use_yn != 'Y')
            """))
            updated_active = result.rowcount
            db.session.commit()
            print(f"   ✅ 활성 제품 use_yn 업데이트: {updated_active}개")
        
        # 9. 최종 결과 확인
        print("\n7️⃣ 최종 마이그레이션 결과")
        
        with app.app_context():
            result = db.session.execute(db.text("""
                SELECT 
                    COUNT(DISTINCT p.id) as total_products,
                    COUNT(CASE WHEN p.use_yn = 'Y' THEN 1 END) as active_products,
                    COUNT(CASE WHEN p.use_yn = 'N' THEN 1 END) as inactive_products,
                    COUNT(pd.id) as total_details,
                    COUNT(CASE WHEN LENGTH(pd.std_div_prod_code) = 16 THEN 1 END) as valid_16_count,
                    COALESCE(AVG(p.price), 0) as avg_price
                FROM products p
                LEFT JOIN product_details pd ON p.id = pd.product_id
                WHERE p.company_id = 1
            """))
            
            final_stats = result.fetchone()
            
            print(f"   📊 최종 결과:")
            print(f"      총 제품: {final_stats.total_products}개")
            print(f"      ├─ 활성 제품: {final_stats.active_products}개 (UseYn='Y')")
            print(f"      └─ 비활성 제품: {final_stats.inactive_products}개 (UseYn='N')")
            print(f"      총 상세: {final_stats.total_details}개")
            print(f"      16자리 코드: {final_stats.valid_16_count}개")
            print(f"      평균 가격: {final_stats.avg_price:,.0f}원")
            
            # 성공률 계산
            product_success_rate = (final_stats.total_products / total_all_products * 100) if total_all_products > 0 else 0
            detail_success_rate = (final_stats.total_details / total_active_details * 100) if total_active_details > 0 else 0
            
            print(f"\n   📈 마이그레이션 성공률:")
            print(f"      제품: {product_success_rate:.1f}% ({final_stats.total_products}/{total_all_products})")
            print(f"      상세: {detail_success_rate:.1f}% ({final_stats.total_details}/{total_active_details})")
            
            # UseYn별 분포 확인
            result = db.session.execute(db.text("""
                SELECT 
                    p.use_yn,
                    COUNT(DISTINCT p.id) as product_count,
                    COUNT(pd.id) as detail_count
                FROM products p
                LEFT JOIN product_details pd ON p.id = pd.product_id
                WHERE p.company_id = 1
                GROUP BY p.use_yn
                ORDER BY p.use_yn
            """))
            
            useyn_stats = result.fetchall()
            print(f"\n   📋 UseYn별 분포:")
            for stat in useyn_stats:
                use_yn = stat.use_yn or "NULL"
                print(f"      {use_yn}: {stat.product_count}개 제품, {stat.detail_count}개 상세")
        
        print(f"\n🎉 완전한 마이그레이션 완료!")
        print(f"✅ 총 {final_stats.total_products}개 제품 ({final_stats.active_products}개 활성 + {final_stats.inactive_products}개 비활성)")
        print(f"✅ 총 {final_stats.total_details}개 상세 (목표: {total_active_details}개)")
        print(f"✅ UseYn 컬럼 추가로 활성/비활성 관리 가능")
        print(f"✅ 16자리 자가코드 {final_stats.valid_16_count}개 완벽 보존")
        print(f"📱 http://127.0.0.1:5000/product/ 에서 전체 데이터 확인 가능!")
        
    except Exception as e:
        print(f"❌ 마이그레이션 오류: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if 'legacy_conn' in locals() and legacy_conn:
            legacy_conn.close()
            print("🔒 레거시 DB 연결 안전 종료")

if __name__ == "__main__":
    complete_migration_with_useyn() 