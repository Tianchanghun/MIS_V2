#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
레거시 tbl_code 완전 마이그레이션 (모든 필드)
"""

import sys
import os
import pyodbc
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db, Code, Product

def complete_legacy_code_migration():
    """레거시 tbl_code를 완전히 그대로 가져오기"""
    
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
            print("=== 레거시 tbl_code 완전 마이그레이션 ===\n")
            
            cursor = legacy_conn.cursor()
            
            # 1. 레거시 tbl_code 전체 구조 확인
            print("📋 레거시 tbl_code 구조 확인:")
            cursor.execute("SELECT TOP 1 * FROM tbl_code")
            columns = [desc[0] for desc in cursor.description]
            print(f"   컬럼: {columns}")
            
            # 2. 현재 시스템 tbl_code 완전 초기화
            print(f"\n🗑️ 현재 tbl_code 초기화:")
            
            # 상품 연결 해제
            Product.query.update({
                Product.brand_code_seq: None,
                Product.category_code_seq: None,
                Product.type_code_seq: None,
                Product.year_code_seq: None,
                Product.color_code_seq: None,
                Product.div_type_code_seq: None,
                Product.product_code_seq: None
            })
            
            # 기존 코드 모두 삭제
            Code.query.delete()
            db.session.commit()
            print(f"   ✅ 기존 코드 데이터 삭제 완료")
            
            # 3. 레거시 tbl_code 전체 데이터 가져오기
            print(f"\n📥 레거시 tbl_code 전체 가져오기:")
            cursor.execute("""
                SELECT Seq, CodeSeq, ParentSeq, Depth, Sort, Code, CodeName, CodeInfo, 
                       InsUser, InsDate, UptUser, UptDate
                FROM tbl_code 
                ORDER BY Seq
            """)
            
            legacy_codes = cursor.fetchall()
            print(f"   레거시 코드 총 {len(legacy_codes)}개")
            
            # 4. 레거시 코드를 현재 시스템에 그대로 삽입
            print(f"\n💾 레거시 코드 삽입:")
            
            inserted_count = 0
            seq_mapping = {}  # legacy_seq -> new_seq 매핑
            
            for row in legacy_codes:
                try:
                    # 레거시 데이터 그대로 삽입
                    new_code = Code(
                        seq=row.Seq,                    # 원본 Seq 유지
                        code_seq=row.CodeSeq,
                        parent_seq=row.ParentSeq,
                        depth=row.Depth,
                        sort=row.Sort,
                        code=row.Code,
                        code_name=row.CodeName,
                        code_info=row.CodeInfo,         # CodeInfo -> code_info
                        ins_user=row.InsUser,
                        ins_date=row.InsDate,
                        upt_user=row.UptUser,
                        upt_date=row.UptDate
                    )
                    
                    db.session.add(new_code)
                    seq_mapping[row.Seq] = row.Seq  # 1:1 매핑
                    inserted_count += 1
                    
                    if inserted_count % 100 == 0:
                        db.session.commit()
                        print(f"   진행: {inserted_count}개 삽입")
                        
                except Exception as e:
                    print(f"   ❌ Seq {row.Seq} 삽입 실패: {e}")
                    continue
            
            db.session.commit()
            print(f"✅ {inserted_count}개 코드 삽입 완료!")
            
            # 5. 상품들을 레거시 기준으로 정확히 매핑
            print(f"\n🔄 상품 레거시 매핑:")
            
            cursor.execute("""
                SELECT p.Seq as LegacySeq, p.Brand, p.ProdGroup, p.ProdType, p.ProdYear,
                       p.ProdName
                FROM tbl_Product p
                ORDER BY p.Seq
            """)
            
            products = Product.query.filter(Product.legacy_seq.isnot(None)).all()
            updated_count = 0
            
            for row in cursor.fetchall():
                legacy_seq = row.LegacySeq
                
                # 해당 상품 찾기
                product = next((p for p in products if p.legacy_seq == legacy_seq), None)
                if not product:
                    continue
                
                # 레거시 Seq 그대로 매핑 (이제 1:1로 매핑됨)
                if row.Brand and row.Brand in seq_mapping:
                    product.brand_code_seq = seq_mapping[row.Brand]
                
                if row.ProdGroup and row.ProdGroup in seq_mapping:
                    product.category_code_seq = seq_mapping[row.ProdGroup]
                
                if row.ProdType and row.ProdType in seq_mapping:
                    product.type_code_seq = seq_mapping[row.ProdType]
                
                if row.ProdYear and row.ProdYear in seq_mapping:
                    product.year_code_seq = seq_mapping[row.ProdYear]
                
                updated_count += 1
                
                if updated_count <= 5:  # 처음 5개 확인
                    brand = Code.query.get(product.brand_code_seq) if product.brand_code_seq else None
                    category = Code.query.get(product.category_code_seq) if product.category_code_seq else None
                    type_code = Code.query.get(product.type_code_seq) if product.type_code_seq else None
                    year = Code.query.get(product.year_code_seq) if product.year_code_seq else None
                    
                    print(f"   ✅ {row.ProdName}:")
                    print(f"      브랜드: {brand.code_name if brand else 'NULL'}")
                    print(f"      품목: {category.code_name if category else 'NULL'}")
                    print(f"      타입: {type_code.code_name if type_code else 'NULL'}")
                    print(f"      년도: {year.code_name if year else 'NULL'}")
                
                if updated_count % 100 == 0:
                    db.session.commit()
                    print(f"   진행: {updated_count}개 상품 매핑")
            
            db.session.commit()
            print(f"✅ {updated_count}개 상품 매핑 완료!")
            
            # 6. 최종 확인
            print(f"\n=== 마이그레이션 완료 확인 ===")
            total_codes = Code.query.count()
            print(f"총 코드: {total_codes}개")
            
            # 그룹별 코드 개수 확인
            groups = ['Brand', 'ProdGroup', 'ProdType', 'Color', 'DivType']
            for group in groups:
                count = Code.query.filter_by(code=group).count()
                if count > 0:
                    print(f"{group}: {count}개")
            
            # 샘플 상품 확인
            sample_product = Product.query.filter(Product.legacy_seq.isnot(None)).first()
            if sample_product:
                print(f"\n샘플 상품: {sample_product.product_name}")
                print(f"브랜드: {sample_product.brand_code.code_name if sample_product.brand_code else 'NULL'}")
                print(f"품목: {sample_product.category_code.code_name if sample_product.category_code else 'NULL'}")
                print(f"타입: {sample_product.type_code.code_name if sample_product.type_code else 'NULL'}")
                print(f"년도: {sample_product.year_code.code_name if sample_product.year_code else 'NULL'}")
            
            legacy_conn.close()
            
        except Exception as e:
            print(f"오류 발생: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            if legacy_conn:
                legacy_conn.close()

if __name__ == "__main__":
    complete_legacy_code_migration() 