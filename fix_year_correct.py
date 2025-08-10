#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
년도 매핑 올바른 수정 (YR 코드 그룹 기준)
"""

import sys
import os
import pyodbc
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db, Code, Product

def fix_year_correct():
    """레거시 ProdYear를 YR 코드 그룹의 CodeSeq로 올바르게 매핑"""
    
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
            print("=== 년도 매핑 올바른 수정 (YR 기준) ===\n")
            
            cursor = legacy_conn.cursor()
            
            # 1. 레거시에서 YR 코드 그룹의 매핑 테이블 생성
            print("📅 레거시 YR 코드 그룹 분석:")
            cursor.execute("""
                SELECT Seq, CodeSeq, CodeName
                FROM tbl_code 
                WHERE Code = 'YR'
                ORDER BY CodeSeq
            """)
            
            yr_mapping = {}  # legacy_prod_year_str -> legacy_yr_seq
            
            for row in cursor.fetchall():
                legacy_seq = row.Seq
                code_seq = row.CodeSeq  # 이게 ProdYear와 매칭될 값
                code_name = row.CodeName
                
                yr_mapping[str(code_seq)] = legacy_seq
                print(f"   YR CodeSeq {code_seq} -> Seq {legacy_seq} ({code_name})")
            
            print(f"   총 {len(yr_mapping)}개 년도 코드")
            
            # 2. 현재 시스템에서 해당 YR 코드들 확인
            print(f"\n🔍 현재 시스템 YR 코드 확인:")
            found_count = 0
            missing_years = []
            
            for prod_year_str, legacy_yr_seq in yr_mapping.items():
                current_code = Code.query.filter_by(seq=legacy_yr_seq).first()
                if current_code:
                    print(f"   ProdYear {prod_year_str} -> 현재 seq {legacy_yr_seq}: '{current_code.code_name}'")
                    found_count += 1
                else:
                    print(f"   ❌ ProdYear {prod_year_str} -> 현재 seq {legacy_yr_seq}: 없음")
                    missing_years.append(prod_year_str)
            
            print(f"   매핑 가능: {found_count}개, 누락: {len(missing_years)}개")
            
            # 3. 상품들에 올바른 년도 매핑
            print(f"\n🔄 상품 년도 매핑 (YR 기준):")
            cursor.execute("""
                SELECT p.Seq as LegacySeq, p.ProdYear, p.ProdName
                FROM tbl_Product p
                WHERE p.ProdYear IS NOT NULL AND p.ProdYear != ''
                ORDER BY p.Seq
            """)
            
            updated_count = 0
            skipped_count = 0
            
            for row in cursor.fetchall():
                legacy_seq = row.LegacySeq
                prod_year_str = str(row.ProdYear).strip()
                
                # 현재 시스템에서 상품 찾기
                product = Product.query.filter_by(legacy_seq=legacy_seq).first()
                if product:
                    if prod_year_str in yr_mapping:
                        # YR 코드의 Seq로 매핑
                        yr_code_seq = yr_mapping[prod_year_str]
                        current_code = Code.query.filter_by(seq=yr_code_seq).first()
                        
                        if current_code:
                            product.year_code_seq = yr_code_seq
                            updated_count += 1
                            
                            if updated_count <= 5:  # 처음 5개만 출력
                                print(f"   ✅ {row.ProdName}: ProdYear '{prod_year_str}' -> Seq {yr_code_seq} ({current_code.code_name})")
                        else:
                            print(f"   ❌ {row.ProdName}: YR Seq {yr_code_seq} 현재 시스템에 없음")
                            skipped_count += 1
                    else:
                        print(f"   ❌ {row.ProdName}: ProdYear '{prod_year_str}' YR 매핑 없음")
                        skipped_count += 1
                    
                    if updated_count % 100 == 0:
                        db.session.commit()
                        print(f"   진행: {updated_count}개 매핑, {skipped_count}개 건너뜀")
            
            db.session.commit()
            print(f"✅ {updated_count}개 상품 년도 매핑 완료! ({skipped_count}개 실패)")
            
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
    fix_year_correct() 