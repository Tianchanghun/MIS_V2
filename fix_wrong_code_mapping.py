#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
잘못된 코드 매핑 수정 (레거시 DB 기준)
"""

import sys
import os
import pyodbc
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db, Code, Product

def fix_wrong_code_mapping():
    """레거시 DB 기준으로 잘못된 코드 매핑 수정"""
    
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
            print("=== 잘못된 코드 매핑 수정 시작 ===\n")
            
            cursor = legacy_conn.cursor()
            
            # 1. 레거시 DB의 실제 코드 그룹 확인
            print("📋 레거시 DB 코드 그룹 확인:")
            cursor.execute("""
                SELECT DISTINCT Code as GroupName, COUNT(*) as CodeCount
                FROM tbl_code 
                GROUP BY Code
                ORDER BY Code
            """)
            
            for row in cursor.fetchall():
                print(f"   {row.GroupName}: {row.CodeCount}개")
            
            # 2. 현재 시스템에서 잘못된 코드들 제거
            print(f"\n🗑️ 잘못된 코드들 제거:")
            
            # "직책" 관련 코드 제거
            wrong_codes = Code.query.filter(
                (Code.code_name.like('%직책%')) |
                (Code.code == 'JPT')
            ).all()
            
            for code in wrong_codes:
                print(f"   제거: seq={code.seq}, code='{code.code}', name='{code.code_name}'")
                
                # 이 코드를 사용하는 상품들의 매핑 해제
                products_using = Product.query.filter(
                    (Product.year_code_seq == code.seq) |
                    (Product.brand_code_seq == code.seq) |
                    (Product.category_code_seq == code.seq) |
                    (Product.type_code_seq == code.seq)
                ).all()
                
                for product in products_using:
                    if product.year_code_seq == code.seq:
                        product.year_code_seq = None
                    if product.brand_code_seq == code.seq:
                        product.brand_code_seq = None
                    if product.category_code_seq == code.seq:
                        product.category_code_seq = None
                    if product.type_code_seq == code.seq:
                        product.type_code_seq = None
                
                print(f"      → {len(products_using)}개 상품 매핑 해제")
                db.session.delete(code)
            
            db.session.commit()
            
            # 3. 레거시 DB 기준으로 올바른 코드 체계 구축
            print(f"\n🔧 레거시 기준 코드 체계 재구축:")
            
            # 레거시 코드 그룹별 매핑
            legacy_groups = {
                'Brand': '브랜드',
                'ProdGroup': '품목', 
                'ProdType': '타입',
                'Color': '색상',
                'DivType': '구분타입'
            }
            
            # 년도는 별도 처리 (레거시에 Year 그룹이 없으므로)
            print(f"   📅 년도 코드 그룹 생성:")
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
                print(f"      ✅ 년도 부모 그룹 생성 (seq: {year_parent.seq})")
            
            # 기본 년도들 추가
            current_year = datetime.now().year
            basic_years = [
                ('10', '2010'), ('11', '2011'), ('12', '2012'), ('13', '2013'), ('14', '2014'),
                ('15', '2015'), ('16', '2016'), ('17', '2017'), ('18', '2018'), ('19', '2019'),
                ('20', '2020'), ('21', '2021'), ('22', '2022'), ('23', '2023'), ('24', '2024'),
                ('25', '2025')
            ]
            
            year_mapping = {}  # legacy seq -> current seq
            for code, name in basic_years:
                existing = Code.query.filter_by(code=code, parent_seq=year_parent.seq).first()
                if not existing:
                    new_year = Code(
                        code_seq=int(code),
                        parent_seq=year_parent.seq,
                        depth=1,
                        sort=int(code),
                        code=code,
                        code_name=name,
                        ins_user='system',
                        ins_date=datetime.utcnow()
                    )
                    db.session.add(new_year)
                    db.session.flush()
                    year_mapping[int(code)] = new_year.seq
                    print(f"      ✅ 년도 코드 추가: {code} -> {name} (seq: {new_year.seq})")
                else:
                    year_mapping[int(code)] = existing.seq
            
            db.session.commit()
            
            # 4. 상품들을 올바른 코드로 재매핑
            print(f"\n🔄 상품 재매핑:")
            
            cursor.execute("""
                SELECT p.Seq as LegacySeq, p.ProdYear,
                       b.CodeName as BrandName,
                       pg.CodeName as ProdGroupName,
                       pt.CodeName as ProdTypeName
                FROM tbl_Product p
                LEFT JOIN tbl_code b ON p.Brand = b.Seq
                LEFT JOIN tbl_code pg ON p.ProdGroup = pg.Seq  
                LEFT JOIN tbl_code pt ON p.ProdType = pt.Seq
                ORDER BY p.Seq
            """)
            
            updated_count = 0
            products = Product.query.filter(Product.legacy_seq.isnot(None)).all()
            
            for row in cursor.fetchall():
                legacy_seq = row.LegacySeq
                
                # 해당 상품 찾기
                product = next((p for p in products if p.legacy_seq == legacy_seq), None)
                if not product:
                    continue
                
                # 년도 매핑 (레거시 ProdYear를 년도 코드로)
                if row.ProdYear and row.ProdYear in year_mapping:
                    product.year_code_seq = year_mapping[row.ProdYear]
                else:
                    product.year_code_seq = None
                
                # 나머지 코드들은 기존 로직 유지
                if row.BrandName:
                    brand_code = Code.query.filter_by(code_name=row.BrandName).first()
                    product.brand_code_seq = brand_code.seq if brand_code else None
                
                if row.ProdGroupName:
                    category_code = Code.query.filter_by(code_name=row.ProdGroupName).first()
                    product.category_code_seq = category_code.seq if category_code else None
                
                if row.ProdTypeName:
                    type_code = Code.query.filter_by(code_name=row.ProdTypeName).first()
                    product.type_code_seq = type_code.seq if type_code else None
                
                updated_count += 1
                
                if updated_count % 100 == 0:
                    db.session.commit()
                    print(f"   진행: {updated_count}개 상품 재매핑")
            
            db.session.commit()
            print(f"✅ {updated_count}개 상품 재매핑 완료!")
            
            # 5. 결과 확인
            print(f"\n=== 수정 결과 확인 ===")
            sample_product = products[0] if products else None
            if sample_product:
                print(f"샘플 상품: {sample_product.product_name}")
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
    fix_wrong_code_mapping() 