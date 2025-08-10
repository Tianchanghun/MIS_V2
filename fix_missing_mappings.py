#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
누락된 매핑 수정 및 상품 업데이트
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
        print("[OK] 레거시 DB 연결 성공")
        return connection
    except Exception as e:
        print(f"[ERROR] 레거시 DB 연결 실패: {e}")
        return None

def build_complete_mapping():
    """모든 레거시 코드의 완전한 매핑 생성"""
    legacy_conn = get_legacy_connection()
    if not legacy_conn:
        return {}
    
    print("완전한 코드 매핑 생성 중...")
    
    mapping = {
        'brand': {},
        'category': {},
        'type': {},
        'year': {}
    }
    
    try:
        cursor = legacy_conn.cursor()
        
        with app.app_context():
            # 1. 브랜드 매핑 - 모든 브랜드 포함
            print("  브랜드 매핑...")
            
            # 실제 사용 중인 브랜드 SEQ들을 직접 확인
            cursor.execute("SELECT DISTINCT Brand FROM tbl_Product WHERE UseYN = 'Y' AND Brand IS NOT NULL AND Brand != 0")
            used_brands = [row[0] for row in cursor.fetchall()]
            
            brand_group = Code.query.filter_by(code_name='브랜드', depth=0).first()
            if brand_group:
                for brand_seq in used_brands:
                    # tbl_Brand에서 정보 조회
                    cursor.execute("SELECT BrandCode, BrandName FROM tbl_Brand WHERE Seq = ?", brand_seq)
                    brand_info = cursor.fetchone()
                    
                    if brand_info:
                        brand_code, brand_name = brand_info
                        
                        # PostgreSQL에서 매칭 시도
                        current_brand = Code.query.filter_by(
                            parent_seq=brand_group.seq,
                            code=brand_code
                        ).first()
                        
                        if not current_brand:
                            # 이름으로 매칭 시도
                            current_brand = Code.query.filter(
                                Code.parent_seq == brand_group.seq,
                                Code.code_name.ilike(f'%{brand_name}%')
                            ).first()
                        
                        if current_brand:
                            mapping['brand'][brand_seq] = current_brand.seq
                            print(f"    브랜드 매핑: {brand_seq} -> {current_brand.seq} ({brand_code}:{brand_name})")
                        else:
                            print(f"    브랜드 매핑 실패: {brand_seq} ({brand_code}:{brand_name}) - 현재 DB에 없음")
            
            # 2. 제품구분 매핑 - 모든 그룹 포함
            print("  제품구분 매핑...")
            
            cursor.execute("SELECT DISTINCT ProdGroup FROM tbl_Product WHERE UseYN = 'Y' AND ProdGroup IS NOT NULL AND ProdGroup != 0")
            used_groups = [row[0] for row in cursor.fetchall()]
            
            category_group = Code.query.filter_by(code_name='제품구분', depth=0).first()
            if category_group:
                for group_seq in used_groups:
                    cursor.execute("SELECT Code, CodeName FROM tbl_Code WHERE Seq = ?", group_seq)
                    group_info = cursor.fetchone()
                    
                    if group_info:
                        group_code, group_name = group_info
                        
                        current_category = Code.query.filter_by(
                            parent_seq=category_group.seq,
                            code=group_code
                        ).first()
                        
                        if not current_category:
                            current_category = Code.query.filter(
                                Code.parent_seq == category_group.seq,
                                Code.code_name.ilike(f'%{group_name}%')
                            ).first()
                        
                        if current_category:
                            mapping['category'][group_seq] = current_category.seq
                            print(f"    제품구분 매핑: {group_seq} -> {current_category.seq} ({group_code}:{group_name})")
                        else:
                            print(f"    제품구분 매핑 실패: {group_seq} ({group_code}:{group_name})")
            
            # 3. 타입 매핑 - 모든 타입 포함
            print("  타입 매핑...")
            
            cursor.execute("SELECT DISTINCT ProdType FROM tbl_Product WHERE UseYN = 'Y' AND ProdType IS NOT NULL AND ProdType != 0")
            used_types = [row[0] for row in cursor.fetchall()]
            
            type_group = Code.query.filter_by(code_name='타입', depth=0).first()
            if type_group:
                for type_seq in used_types:
                    cursor.execute("SELECT Code, CodeName FROM tbl_Code WHERE Seq = ?", type_seq)
                    type_info = cursor.fetchone()
                    
                    if type_info:
                        type_code, type_name = type_info
                        
                        current_type = Code.query.filter_by(
                            parent_seq=type_group.seq,
                            code=type_code
                        ).first()
                        
                        if not current_type:
                            current_type = Code.query.filter(
                                Code.parent_seq == type_group.seq,
                                Code.code_name.ilike(f'%{type_name}%')
                            ).first()
                        
                        if current_type:
                            mapping['type'][type_seq] = current_type.seq
                            print(f"    타입 매핑: {type_seq} -> {current_type.seq} ({type_code}:{type_name})")
                        else:
                            print(f"    타입 매핑 실패: {type_seq} ({type_code}:{type_name})")
            
            # 4. 년도 매핑 - 문자열 값 처리
            print("  년도 매핑...")
            
            cursor.execute("SELECT DISTINCT ProdYear FROM tbl_Product WHERE UseYN = 'Y' AND ProdYear IS NOT NULL AND ProdYear != '' AND ProdYear != '  '")
            used_years = [row[0] for row in cursor.fetchall()]
            
            year_group = Code.query.filter_by(code_name='년도', depth=0).first()
            if year_group:
                for year_value in used_years:
                    year_str = str(year_value).strip()
                    if len(year_str) >= 2:
                        # 2자리 년도 코드로 매칭
                        current_year = Code.query.filter_by(
                            parent_seq=year_group.seq,
                            code=year_str
                        ).first()
                        
                        if not current_year:
                            # 년도명으로 매칭 시도 (예: "2015" 포함)
                            full_year = f"20{year_str}" if len(year_str) == 2 else year_str
                            current_year = Code.query.filter(
                                Code.parent_seq == year_group.seq,
                                Code.code_name.ilike(f'%{full_year}%')
                            ).first()
                        
                        if current_year:
                            mapping['year'][year_value] = current_year.seq
                            print(f"    년도 매핑: '{year_value}' -> {current_year.seq} ({current_year.code}:{current_year.code_name})")
                        else:
                            print(f"    년도 매핑 실패: '{year_value}'")
        
        return mapping
        
    except Exception as e:
        print(f"[ERROR] 매핑 생성 실패: {e}")
        return {}
    finally:
        legacy_conn.close()

def update_products_with_mapping(mapping):
    """매핑을 이용해 상품 정보 업데이트"""
    legacy_conn = get_legacy_connection()
    if not legacy_conn:
        return False
    
    print("\n상품 매핑 정보 업데이트 중...")
    
    try:
        cursor = legacy_conn.cursor()
        
        with app.app_context():
            # 매핑이 안된 상품들 조회
            unmapped_products = Product.query.filter(
                Product.legacy_seq.isnot(None),
                db.or_(
                    Product.brand_code_seq.is_(None),
                    Product.category_code_seq.is_(None),
                    Product.type_code_seq.is_(None),
                    Product.year_code_seq.is_(None)
                )
            ).all()
            
            print(f"매핑 업데이트 대상: {len(unmapped_products)}개")
            
            updated_count = 0
            
            for product in unmapped_products:
                # 레거시 정보 조회
                cursor.execute("""
                    SELECT Brand, ProdGroup, ProdType, ProdYear
                    FROM tbl_Product 
                    WHERE Seq = ?
                """, product.legacy_seq)
                
                legacy_info = cursor.fetchone()
                if not legacy_info:
                    continue
                
                brand, prod_group, prod_type, prod_year = legacy_info
                
                # 매핑 적용
                updated = False
                
                if brand and brand in mapping['brand'] and not product.brand_code_seq:
                    product.brand_code_seq = mapping['brand'][brand]
                    updated = True
                
                if prod_group and prod_group in mapping['category'] and not product.category_code_seq:
                    product.category_code_seq = mapping['category'][prod_group]
                    updated = True
                
                if prod_type and prod_type in mapping['type'] and not product.type_code_seq:
                    product.type_code_seq = mapping['type'][prod_type]
                    updated = True
                
                if prod_year and prod_year in mapping['year'] and not product.year_code_seq:
                    product.year_code_seq = mapping['year'][prod_year]
                    updated = True
                
                if updated:
                    product.updated_by = 'mapping_fix'
                    updated_count += 1
                    
                    if updated_count % 50 == 0:
                        db.session.commit()
                        print(f"    진행률: {updated_count}/{len(unmapped_products)}")
            
            db.session.commit()
            
            print(f"매핑 업데이트 완료: {updated_count}개")
            return True
            
    except Exception as e:
        print(f"[ERROR] 업데이트 실패: {e}")
        db.session.rollback()
        return False
    finally:
        legacy_conn.close()

def verify_fix():
    """수정 결과 검증"""
    with app.app_context():
        print("\n수정 결과 검증...")
        
        # 매핑 상태 재확인
        total_products = Product.query.filter(Product.legacy_seq.isnot(None)).count()
        mapped_brand = Product.query.filter(Product.legacy_seq.isnot(None), Product.brand_code_seq.isnot(None)).count()
        mapped_category = Product.query.filter(Product.legacy_seq.isnot(None), Product.category_code_seq.isnot(None)).count()
        mapped_type = Product.query.filter(Product.legacy_seq.isnot(None), Product.type_code_seq.isnot(None)).count()
        mapped_year = Product.query.filter(Product.legacy_seq.isnot(None), Product.year_code_seq.isnot(None)).count()
        
        print(f"레거시 상품 매핑 상태:")
        print(f"  - 브랜드: {mapped_brand}/{total_products} ({mapped_brand/total_products*100:.1f}%)")
        print(f"  - 품목: {mapped_category}/{total_products} ({mapped_category/total_products*100:.1f}%)")
        print(f"  - 타입: {mapped_type}/{total_products} ({mapped_type/total_products*100:.1f}%)")
        print(f"  - 년도: {mapped_year}/{total_products} ({mapped_year/total_products*100:.1f}%)")
        
        # 수정된 샘플 확인
        sample_products = Product.query.filter(Product.legacy_seq.isnot(None)).limit(5).all()
        print(f"\n수정된 샘플 5개:")
        for product in sample_products:
            print(f"  - {product.product_name} (Legacy:{product.legacy_seq})")
            print(f"    브랜드: {product.brand_code.code_name if product.brand_code else 'None'}")
            print(f"    품목: {product.category_code.code_name if product.category_code else 'None'}")
            print(f"    타입: {product.type_code.code_name if product.type_code else 'None'}")
            print(f"    년도: {product.year_code.code_name if product.year_code else 'None'}")

def main():
    print("=== 누락된 매핑 수정 시작 ===")
    
    # 1. 완전한 매핑 생성
    mapping = build_complete_mapping()
    
    print(f"\n완전 매핑 통계:")
    print(f"  - 브랜드: {len(mapping['brand'])}개")
    print(f"  - 품목: {len(mapping['category'])}개")
    print(f"  - 타입: {len(mapping['type'])}개")
    print(f"  - 년도: {len(mapping['year'])}개")
    
    # 2. 상품 업데이트
    if update_products_with_mapping(mapping):
        print("매핑 업데이트 성공")
    else:
        print("매핑 업데이트 실패")
        return
    
    # 3. 결과 검증
    verify_fix()
    
    print(f"\n=== 매핑 수정 완료 ===")
    print("웹 페이지를 새로고침하여 품목/타입 정보가 올바르게 표시되는지 확인하세요!")

if __name__ == '__main__':
    main() 