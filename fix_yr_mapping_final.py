#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YR 코드 기반 년도 매핑 최종 수정
"""

import sys
import os
import pyodbc
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db, Code, Product

def fix_yr_mapping_final():
    """레거시 tbl_code Code='YR' 기준으로 년도 매핑"""
    
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
            print("=== YR 코드 기반 년도 매핑 최종 수정 ===\n")
            
            cursor = legacy_conn.cursor()
            
            # 1. 레거시에서 YR 코드 그룹 전체 가져오기
            print("📅 레거시 YR 코드 그룹 분석:")
            cursor.execute("""
                SELECT Seq, CodeSeq, Code, CodeName, CodeInfo
                FROM tbl_code 
                WHERE Code = 'YR'
                ORDER BY CodeSeq
            """)
            
            yr_codes = cursor.fetchall()
            print(f"   레거시 YR 코드: {len(yr_codes)}개")
            
            yr_mapping = {}  # CodeSeq(ProdYear에서 사용) -> Seq(실제 tbl_code.Seq)
            
            for row in yr_codes:
                seq = row.Seq
                code_seq = row.CodeSeq  # 이게 ProdYear 값
                code_name = row.CodeName
                
                yr_mapping[str(code_seq)] = seq
                print(f"   CodeSeq {code_seq} -> Seq {seq} ({code_name})")
            
            # 2. 현재 시스템에서 해당 Seq들이 존재하는지 확인
            print(f"\n🔍 현재 시스템 YR 코드 확인:")
            valid_mappings = {}
            missing_seqs = []
            
            for code_seq_str, legacy_seq in yr_mapping.items():
                current_code = Code.query.filter_by(seq=legacy_seq).first()
                if current_code:
                    valid_mappings[code_seq_str] = legacy_seq
                    print(f"   ✅ CodeSeq {code_seq_str} -> Seq {legacy_seq}: '{current_code.code_name}'")
                else:
                    missing_seqs.append((code_seq_str, legacy_seq))
                    print(f"   ❌ CodeSeq {code_seq_str} -> Seq {legacy_seq}: 현재 시스템에 없음")
            
            print(f"\n   유효한 매핑: {len(valid_mappings)}개")
            print(f"   누락된 Seq: {len(missing_seqs)}개")
            
            if not valid_mappings:
                print("❌ 유효한 YR 매핑이 없습니다! 레거시 코드 마이그레이션을 먼저 확인하세요.")
                return
            
            # 3. 상품들의 ProdYear를 YR 코드로 매핑
            print(f"\n🔄 상품 년도 매핑:")
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
                prod_name = row.ProdName
                
                # 현재 시스템에서 상품 찾기
                product = Product.query.filter_by(legacy_seq=legacy_seq).first()
                if product:
                    if prod_year_str in valid_mappings:
                        yr_code_seq = valid_mappings[prod_year_str]
                        product.year_code_seq = yr_code_seq
                        updated_count += 1
                        
                        if updated_count <= 5:  # 처음 5개만 출력
                            year_code = Code.query.filter_by(seq=yr_code_seq).first()
                            print(f"   ✅ {prod_name}: ProdYear '{prod_year_str}' -> Seq {yr_code_seq} ({year_code.code_name})")
                    else:
                        if skipped_count < 5:  # 처음 5개 실패만 출력
                            print(f"   ❌ {prod_name}: ProdYear '{prod_year_str}' 매핑 없음")
                        skipped_count += 1
                    
                    if (updated_count + skipped_count) % 100 == 0:
                        db.session.commit()
                        print(f"   진행: {updated_count}개 매핑, {skipped_count}개 실패")
            
            db.session.commit()
            print(f"\n✅ 년도 매핑 완료!")
            print(f"   성공: {updated_count}개")
            print(f"   실패: {skipped_count}개")
            
            # 4. 최종 결과 확인
            print(f"\n=== 최종 결과 확인 ===")
            sample_products = Product.query.filter(Product.year_code_seq.isnot(None)).limit(3).all()
            
            if sample_products:
                for product in sample_products:
                    year_code = Code.query.filter_by(seq=product.year_code_seq).first()
                    print(f"상품: {product.product_name}")
                    print(f"년도: {year_code.code_name if year_code else 'NULL'}")
                    print()
            else:
                print("❌ 년도가 매핑된 상품이 없습니다.")
            
            legacy_conn.close()
            
        except Exception as e:
            print(f"오류 발생: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            if legacy_conn:
                legacy_conn.close()

if __name__ == "__main__":
    fix_yr_mapping_final() 