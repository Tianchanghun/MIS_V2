#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
년도 매핑 최종 수정
"""

import sys
import os
import pyodbc
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db, Code, Product

def fix_year_mapping_final():
    """레거시 DB ProdYear를 올바른 년도로 매핑"""
    
    # 레거시 DB 연결
    legacy_conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=210.109.96.74,2521;"
        "DATABASE=db_mis;"
        "UID=user_mis;"
        "PWD=user_mis!@12;"
        "ApplicationIntent=ReadOnly;",
        timeout=30
    )
    
    app = create_app()
    
    with app.app_context():
        try:
            print("=== 년도 매핑 최종 수정 ===\n")
            
            cursor = legacy_conn.cursor()
            
            # 1. 레거시 DB에서 실제 ProdYear 값들 확인
            print("📋 레거시 ProdYear 값 분석:")
            cursor.execute("""
                SELECT DISTINCT p.ProdYear, COUNT(*) as ProductCount
                FROM tbl_Product p
                WHERE p.ProdYear IS NOT NULL
                GROUP BY p.ProdYear
                ORDER BY p.ProdYear
            """)
            
            legacy_years = {}
            for row in cursor.fetchall():
                legacy_years[row.ProdYear] = row.ProductCount
                print(f"   ProdYear {row.ProdYear}: {row.ProductCount}개 상품")
            
            # 2. 년도 부모 그룹 확인/생성
            year_parent = Code.query.filter_by(code_name='년도', depth=0).first()
            if not year_parent:
                year_parent = Code(
                    code_seq=1,
                    parent_seq=None,
                    depth=0,
                    sort=200,
                    code='YEAR',
                    code_name='년도',
                    ins_user='system',
                    ins_date=datetime.utcnow()
                )
                db.session.add(year_parent)
                db.session.flush()
                print(f"✅ 년도 부모 그룹 생성 (seq: {year_parent.seq})")
            
            # 3. 레거시 ProdYear 값을 실제 년도로 매핑
            # ProdYear는 보통 년도의 2자리 표현 (14=2014, 18=2018 등)
            print(f"\n🔧 년도 코드 생성:")
            year_mapping = {}
            
            for prod_year in legacy_years.keys():
                if prod_year:
                    # 2자리 년도를 4자리로 변환
                    if prod_year >= 10 and prod_year <= 25:  # 2010-2025
                        full_year = 2000 + prod_year
                    elif prod_year >= 0 and prod_year <= 9:   # 2000-2009
                        full_year = 2000 + prod_year
                    else:
                        full_year = None
                    
                    if full_year:
                        year_code = str(prod_year).zfill(2)  # 2자리로 패딩
                        year_name = str(full_year)
                        
                        # 기존 코드 확인
                        existing = Code.query.filter_by(
                            code=year_code, 
                            parent_seq=year_parent.seq
                        ).first()
                        
                        if not existing:
                            new_year = Code(
                                code_seq=prod_year,
                                parent_seq=year_parent.seq,
                                depth=1,
                                sort=prod_year,
                                code=year_code,
                                code_name=year_name,
                                ins_user='legacy_import',
                                ins_date=datetime.utcnow()
                            )
                            db.session.add(new_year)
                            db.session.flush()
                            year_mapping[prod_year] = new_year.seq
                            print(f"   ✅ {year_code} -> {year_name} (seq: {new_year.seq})")
                        else:
                            year_mapping[prod_year] = existing.seq
                            print(f"   ♻️ {year_code} -> {year_name} (기존 seq: {existing.seq})")
            
            db.session.commit()
            
            # 4. 상품들에 올바른 년도 매핑
            print(f"\n🔄 상품 년도 매핑:")
            cursor.execute("""
                SELECT p.Seq as LegacySeq, p.ProdYear, p.ProdName
                FROM tbl_Product p
                WHERE p.ProdYear IS NOT NULL
                ORDER BY p.Seq
            """)
            
            updated_count = 0
            for row in cursor.fetchall():
                legacy_seq = row.LegacySeq
                prod_year = row.ProdYear
                
                # 현재 시스템에서 상품 찾기
                product = Product.query.filter_by(legacy_seq=legacy_seq).first()
                if product and prod_year in year_mapping:
                    product.year_code_seq = year_mapping[prod_year]
                    updated_count += 1
                    
                    if updated_count <= 5:  # 처음 5개만 출력
                        year_code = Code.query.get(year_mapping[prod_year])
                        print(f"   ✅ {row.ProdName}: ProdYear {prod_year} -> {year_code.code_name}")
                    
                    if updated_count % 100 == 0:
                        db.session.commit()
                        print(f"   진행: {updated_count}개 상품 년도 매핑")
            
            db.session.commit()
            print(f"✅ {updated_count}개 상품 년도 매핑 완료!")
            
            # 5. 결과 확인
            print(f"\n=== 최종 결과 확인 ===")
            sample_products = Product.query.filter(Product.year_code_seq.isnot(None)).limit(3).all()
            for product in sample_products:
                print(f"상품: {product.product_name}")
                print(f"년도: {product.year_code.code_name if product.year_code else 'NULL'}")
                print()
            
            legacy_conn.close()
            
        except Exception as e:
            print(f"오류 발생: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            if legacy_conn:
                legacy_conn.close()

if __name__ == "__main__":
    fix_year_mapping_final() 