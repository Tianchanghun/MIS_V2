#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
년도 매핑 최종 수정 (ProdYear는 단순 년도 값)
"""

import sys
import os
import pyodbc
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db, Code, Product

def fix_year_final():
    """레거시 ProdYear(단순 년도)를 올바른 년도 코드로 매핑"""
    
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
            
            # 1. 년도 부모 그룹 생성
            print("📅 년도 코드 그룹 생성:")
            year_parent = Code.query.filter_by(code='Year', depth=0).first()
            if not year_parent:
                # 새로운 Seq 찾기
                max_seq = db.session.query(db.func.max(Code.seq)).scalar() or 0
                new_seq = max_seq + 1
                
                year_parent = Code(
                    seq=new_seq,
                    code_seq=1,
                    parent_seq=None,
                    depth=0,
                    sort=1000,
                    code='Year',
                    code_name='년도',
                    ins_user='system',
                    ins_date=datetime.utcnow()
                )
                db.session.add(year_parent)
                db.session.flush()
                print(f"   ✅ 년도 부모 그룹 생성 (seq: {year_parent.seq})")
            else:
                print(f"   ♻️ 년도 부모 그룹 존재 (seq: {year_parent.seq})")
            
            # 2. 레거시 ProdYear 값들 분석하여 년도 코드 생성
            print(f"\n🔧 레거시 ProdYear 기반 년도 코드 생성:")
            cursor.execute("""
                SELECT DISTINCT p.ProdYear, COUNT(*) as ProductCount
                FROM tbl_Product p
                WHERE p.ProdYear IS NOT NULL AND p.ProdYear != ''
                GROUP BY p.ProdYear
                ORDER BY p.ProdYear
            """)
            
            year_mapping = {}  # legacy_year_string -> current_seq
            
            for row in cursor.fetchall():
                prod_year_str = str(row.ProdYear).strip()
                product_count = row.ProductCount
                
                if prod_year_str and prod_year_str.isdigit():
                    year_num = int(prod_year_str)
                    
                    # 2자리 년도를 4자리로 변환
                    if year_num >= 0 and year_num <= 30:  # 00-30은 2000-2030
                        full_year = 2000 + year_num
                    elif year_num >= 70 and year_num <= 99:  # 70-99는 1970-1999
                        full_year = 1900 + year_num
                    else:
                        full_year = year_num  # 이미 4자리인 경우
                    
                    year_code = str(year_num).zfill(2)
                    year_name = str(full_year)
                    
                    # 기존 코드 확인
                    existing = Code.query.filter_by(
                        code=year_code,
                        parent_seq=year_parent.seq
                    ).first()
                    
                    if not existing:
                        # 새로운 Seq 생성
                        max_seq = db.session.query(db.func.max(Code.seq)).scalar() or 0
                        new_seq = max_seq + 1
                        
                        new_year = Code(
                            seq=new_seq,
                            code_seq=year_num,
                            parent_seq=year_parent.seq,
                            depth=1,
                            sort=year_num,
                            code=year_code,
                            code_name=year_name,
                            ins_user='legacy_year',
                            ins_date=datetime.utcnow()
                        )
                        db.session.add(new_year)
                        db.session.flush()
                        year_mapping[prod_year_str] = new_year.seq
                        print(f"   ✅ {year_code} -> {year_name} (seq: {new_year.seq}, {product_count}개 상품)")
                    else:
                        year_mapping[prod_year_str] = existing.seq
                        print(f"   ♻️ {year_code} -> {year_name} (기존 seq: {existing.seq}, {product_count}개 상품)")
            
            db.session.commit()
            
            # 3. 상품들에 올바른 년도 매핑
            print(f"\n🔄 상품 년도 매핑:")
            cursor.execute("""
                SELECT p.Seq as LegacySeq, p.ProdYear, p.ProdName
                FROM tbl_Product p
                WHERE p.ProdYear IS NOT NULL AND p.ProdYear != ''
                ORDER BY p.Seq
            """)
            
            updated_count = 0
            for row in cursor.fetchall():
                legacy_seq = row.LegacySeq
                prod_year_str = str(row.ProdYear).strip()
                
                # 현재 시스템에서 상품 찾기
                product = Product.query.filter_by(legacy_seq=legacy_seq).first()
                if product and prod_year_str in year_mapping:
                    product.year_code_seq = year_mapping[prod_year_str]
                    updated_count += 1
                    
                    if updated_count <= 5:  # 처음 5개만 출력
                        year_code = Code.query.filter_by(seq=year_mapping[prod_year_str]).first()
                        print(f"   ✅ {row.ProdName}: ProdYear '{prod_year_str}' -> {year_code.code_name}")
                    
                    if updated_count % 100 == 0:
                        db.session.commit()
                        print(f"   진행: {updated_count}개 상품 년도 매핑")
            
            db.session.commit()
            print(f"✅ {updated_count}개 상품 년도 매핑 완료!")
            
            # 4. 결과 확인
            print(f"\n=== 최종 결과 확인 ===")
            sample_products = Product.query.filter(Product.year_code_seq.isnot(None)).limit(3).all()
            for product in sample_products:
                year_code = Code.query.filter_by(seq=product.year_code_seq).first()
                print(f"상품: {product.product_name}")
                print(f"년도: {year_code.code_name if year_code else 'NULL'}")
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
    fix_year_final() 