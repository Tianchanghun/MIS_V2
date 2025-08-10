#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
레거시 상품 코드 매핑 수정 스크립트
SEQ ID 기반 매핑을 올바르게 처리
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pyodbc
from app import create_app
from app.common.models import db, Product, Code

app = create_app()

# 레거시 DB 설정
LEGACY_DB_CONFIG = {
    'server': '210.109.96.74,2521',
    'database': 'db_mis',
    'username': 'user_mis',
    'password': 'user_mis!@12'
}

def get_legacy_connection():
    """레거시 DB 연결"""
    connection_string = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={LEGACY_DB_CONFIG['server']};"
        f"DATABASE={LEGACY_DB_CONFIG['database']};"
        f"UID={LEGACY_DB_CONFIG['username']};"
        f"PWD={LEGACY_DB_CONFIG['password']};"
        f"ApplicationIntent=ReadOnly;"
    )
    
    try:
        connection = pyodbc.connect(connection_string, timeout=10)
        print(f"[OK] 레거시 DB 연결 성공")
        return connection
    except Exception as e:
        print(f"[ERROR] 레거시 DB 연결 실패: {e}")
        return None

def build_legacy_to_current_mapping():
    """레거시 SEQ ID를 현재 PostgreSQL SEQ로 매핑하는 딕셔너리 생성"""
    legacy_conn = get_legacy_connection()
    if not legacy_conn:
        return {}
    
    mapping = {
        'brand': {},      # legacy_brand_seq -> current_brand_seq
        'prod_group': {}, # legacy_prod_group_seq -> current_category_seq  
        'prod_type': {},  # legacy_prod_type_seq -> current_type_seq
        'year': {}        # legacy_year_seq -> current_year_seq
    }
    
    try:
        cursor = legacy_conn.cursor()
        
        with app.app_context():
            # 1. 브랜드 매핑 (tbl_Brand 기반)
            print("[INFO] 브랜드 매핑 생성 중...")
            cursor.execute("SELECT Seq, BrandCode, BrandName FROM tbl_Brand")
            legacy_brands = cursor.fetchall()
            
            for legacy_brand in legacy_brands:
                legacy_seq, brand_code, brand_name = legacy_brand
                
                # 현재 PostgreSQL에서 해당 브랜드 찾기
                brand_group = Code.query.filter_by(code_name='브랜드', depth=0).first()
                if brand_group:
                    current_brand = Code.query.filter_by(
                        parent_seq=brand_group.seq, 
                        code=brand_code
                    ).first()
                    if current_brand:
                        mapping['brand'][legacy_seq] = current_brand.seq
                        print(f"  브랜드 매핑: {legacy_seq} -> {current_brand.seq} ({brand_code}:{brand_name})")
            
            # 2. 제품구분(ProdGroup) 매핑
            print("[INFO] 제품구분 매핑 생성 중...")
            cursor.execute("""
                SELECT Seq, Code, CodeName FROM tbl_Code 
                WHERE ParentSeq = (SELECT Seq FROM tbl_Code WHERE Code = 'PRT' AND Depth = 0)
            """)
            legacy_prod_groups = cursor.fetchall()
            
            for legacy_group in legacy_prod_groups:
                legacy_seq, group_code, group_name = legacy_group
                
                # 현재 PostgreSQL에서 해당 제품구분 찾기
                category_group = Code.query.filter_by(code_name='제품구분', depth=0).first()
                if category_group:
                    current_category = Code.query.filter_by(
                        parent_seq=category_group.seq,
                        code=group_code
                    ).first()
                    if current_category:
                        mapping['prod_group'][legacy_seq] = current_category.seq
                        print(f"  제품구분 매핑: {legacy_seq} -> {current_category.seq} ({group_code}:{group_name})")
            
            # 3. 타입(ProdType) 매핑
            print("[INFO] 타입 매핑 생성 중...")
            cursor.execute("""
                SELECT Seq, Code, CodeName FROM tbl_Code 
                WHERE ParentSeq = (SELECT Seq FROM tbl_Code WHERE Code = 'TP' AND Depth = 0)
            """)
            legacy_types = cursor.fetchall()
            
            for legacy_type in legacy_types:
                legacy_seq, type_code, type_name = legacy_type
                
                # 현재 PostgreSQL에서 해당 타입 찾기
                type_group = Code.query.filter_by(code_name='타입', depth=0).first()
                if type_group:
                    current_type = Code.query.filter_by(
                        parent_seq=type_group.seq,
                        code=type_code
                    ).first()
                    if current_type:
                        mapping['prod_type'][legacy_seq] = current_type.seq
                        print(f"  타입 매핑: {legacy_seq} -> {current_type.seq} ({type_code}:{type_name})")
            
            # 4. 년도(ProdYear) 매핑  
            print("[INFO] 년도 매핑 생성 중...")
            cursor.execute("""
                SELECT Seq, Code, CodeName FROM tbl_Code 
                WHERE ParentSeq = (SELECT Seq FROM tbl_Code WHERE Code = 'YR' AND Depth = 0)
            """)
            legacy_years = cursor.fetchall()
            
            for legacy_year in legacy_years:
                legacy_seq, year_code, year_name = legacy_year
                
                # 현재 PostgreSQL에서 해당 년도 찾기
                year_group = Code.query.filter_by(code_name='년도', depth=0).first()
                if year_group:
                    current_year = Code.query.filter_by(
                        parent_seq=year_group.seq,
                        code=year_code
                    ).first()
                    if current_year:
                        mapping['year'][legacy_seq] = current_year.seq
                        print(f"  년도 매핑: {legacy_seq} -> {current_year.seq} ({year_code}:{year_name})")
        
        return mapping
        
    except Exception as e:
        print(f"[ERROR] 매핑 생성 실패: {e}")
        return {}
    finally:
        legacy_conn.close()

def fix_product_mappings():
    """기존 상품들의 잘못된 매핑 수정"""
    print("[INFO] 매핑 테이블 생성 중...")
    mapping = build_legacy_to_current_mapping()
    
    if not mapping:
        print("[ERROR] 매핑 테이블 생성 실패")
        return
    
    # 레거시 상품 데이터와 매핑
    legacy_conn = get_legacy_connection()
    if not legacy_conn:
        return
    
    try:
        cursor = legacy_conn.cursor()
        
        with app.app_context():
            # 모든 레거시 상품 정보 가져오기
            cursor.execute("""
                SELECT Seq, Company, Brand, ProdGroup, ProdType, ProdYear, ProdName
                FROM tbl_Product 
                WHERE UseYN = 'Y'
                ORDER BY Seq
            """)
            legacy_products = cursor.fetchall()
            
            print(f"[INFO] {len(legacy_products)}개 레거시 상품 매핑 수정 중...")
            
            updated_count = 0
            error_count = 0
            
            for legacy_product in legacy_products:
                legacy_seq, company, brand, prod_group, prod_type, prod_year, prod_name = legacy_product
                
                try:
                    # 현재 PostgreSQL에서 해당 상품 찾기
                    product = Product.query.filter_by(legacy_seq=legacy_seq).first()
                    if not product:
                        continue
                    
                    # 매핑 적용
                    updated = False
                    
                    if brand in mapping['brand']:
                        product.brand_code_seq = mapping['brand'][brand]
                        updated = True
                    
                    if prod_group in mapping['prod_group']:
                        product.category_code_seq = mapping['prod_group'][prod_group]
                        updated = True
                    
                    if prod_type in mapping['prod_type']:
                        product.type_code_seq = mapping['prod_type'][prod_type]
                        updated = True
                    
                    if prod_year in mapping['year']:
                        product.year_code_seq = mapping['year'][prod_year]
                        updated = True
                    
                    if updated:
                        product.updated_by = 'mapping_fix'
                        updated_count += 1
                        
                        if updated_count % 50 == 0:
                            db.session.commit()
                            print(f"  진행률: {updated_count}/{len(legacy_products)}")
                
                except Exception as e:
                    error_count += 1
                    print(f"  [ERROR] 상품 {legacy_seq} 매핑 실패: {e}")
                    db.session.rollback()
            
            # 최종 커밋
            db.session.commit()
            
            print(f"[OK] 상품 매핑 수정 완료!")
            print(f"  - 수정된 상품: {updated_count}개")
            print(f"  - 오류 발생: {error_count}개")
            
    except Exception as e:
        print(f"[ERROR] 매핑 수정 실패: {e}")
        db.session.rollback()
    finally:
        legacy_conn.close()

def check_fix_result():
    """수정 결과 확인"""
    with app.app_context():
        print(f"\n[INFO] 매핑 수정 결과 확인:")
        
        # 매핑된 상품들 샘플 확인
        sample_products = Product.query.filter(
            Product.legacy_seq.isnot(None)
        ).limit(5).all()
        
        for product in sample_products:
            print(f"  - {product.product_name} (Legacy:{product.legacy_seq})")
            print(f"    브랜드: {product.brand_code.code_name if product.brand_code else 'None'}")
            print(f"    품목: {product.category_code.code_name if product.category_code else 'None'}")
            print(f"    타입: {product.type_code.code_name if product.type_code else 'None'}")
            print(f"    년도: {product.year_code.code_name if product.year_code else 'None'}")

if __name__ == '__main__':
    print("상품 코드 매핑 수정 시작")
    print("=" * 50)
    
    fix_product_mappings()
    check_fix_result()
    
    print(f"\n[OK] 매핑 수정 완료! 이제 웹 페이지에서 상품이 올바르게 표시됩니다.") 