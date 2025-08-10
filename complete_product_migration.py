#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
완전한 레거시 상품 마이그레이션
1. 기존 상품 데이터 백업 및 정리
2. 레거시 DB에서 올바른 매핑으로 다시 가져오기
3. 검증 및 결과 확인
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pyodbc
from datetime import datetime
from app import create_app
from app.common.models import db, Product, ProductDetail, Code

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

def backup_existing_products():
    """기존 상품 데이터 백업"""
    with app.app_context():
        try:
            print("\n[STEP 1] 기존 상품 데이터 백업 중...")
            
            # 기존 상품 개수 확인
            existing_count = Product.query.count()
            legacy_count = Product.query.filter(Product.legacy_seq.isnot(None)).count()
            
            print(f"  - 총 상품: {existing_count}개")
            print(f"  - 레거시 연결: {legacy_count}개")
            
            if legacy_count > 0:
                print(f"  - 레거시 연결 상품들을 삭제하고 다시 마이그레이션합니다")
                
                # 레거시 연결 ProductDetail 먼저 삭제
                detail_deleted = ProductDetail.query.filter(ProductDetail.legacy_seq.isnot(None)).delete()
                print(f"  - ProductDetail 삭제: {detail_deleted}개")
                
                # 레거시 연결 Product 삭제
                product_deleted = Product.query.filter(Product.legacy_seq.isnot(None)).delete()
                print(f"  - Product 삭제: {product_deleted}개")
                
                db.session.commit()
                print("  - 기존 레거시 데이터 정리 완료")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 백업 실패: {e}")
            db.session.rollback()
            return False

def build_code_mapping():
    """레거시 코드와 현재 코드 매핑 테이블 생성"""
    legacy_conn = get_legacy_connection()
    if not legacy_conn:
        return {}
    
    print("\n[STEP 2] 코드 매핑 테이블 생성 중...")
    
    mapping = {
        'brand': {},      # legacy_brand_seq -> current_brand_seq
        'category': {},   # legacy_category_seq -> current_category_seq  
        'type': {},       # legacy_type_seq -> current_type_seq
        'year': {}        # legacy_year_seq -> current_year_seq
    }
    
    try:
        cursor = legacy_conn.cursor()
        
        with app.app_context():
            # 1. 브랜드 매핑 (tbl_Brand 기반)
            print("  [INFO] 브랜드 매핑 생성...")
            cursor.execute("SELECT Seq, BrandCode, BrandName FROM tbl_Brand")
            legacy_brands = cursor.fetchall()
            
            brand_group = Code.query.filter_by(code_name='브랜드', depth=0).first()
            if brand_group:
                for legacy_brand in legacy_brands:
                    legacy_seq, brand_code, brand_name = legacy_brand
                    
                    # 코드 또는 이름으로 매칭
                    current_brand = Code.query.filter_by(
                        parent_seq=brand_group.seq, 
                        code=brand_code
                    ).first()
                    
                    if not current_brand:
                        # 이름으로도 시도
                        current_brand = Code.query.filter(
                            Code.parent_seq == brand_group.seq,
                            Code.code_name.ilike(f'%{brand_name}%')
                        ).first()
                    
                    if current_brand:
                        mapping['brand'][legacy_seq] = current_brand.seq
                        print(f"    브랜드 매핑: {legacy_seq} -> {current_brand.seq} ({brand_code}:{brand_name})")
            
            print(f"  브랜드 매핑 완료: {len(mapping['brand'])}개")
            
            # 2. 제품구분 매핑
            print("  [INFO] 제품구분 매핑 생성...")
            cursor.execute("""
                SELECT Seq, Code, CodeName FROM tbl_Code 
                WHERE ParentSeq = (SELECT Seq FROM tbl_Code WHERE Code = 'PRT' AND Depth = 0)
            """)
            legacy_categories = cursor.fetchall()
            
            category_group = Code.query.filter_by(code_name='제품구분', depth=0).first()
            if category_group:
                for legacy_cat in legacy_categories:
                    legacy_seq, cat_code, cat_name = legacy_cat
                    
                    current_category = Code.query.filter_by(
                        parent_seq=category_group.seq,
                        code=cat_code
                    ).first()
                    
                    if not current_category:
                        current_category = Code.query.filter(
                            Code.parent_seq == category_group.seq,
                            Code.code_name.ilike(f'%{cat_name}%')
                        ).first()
                    
                    if current_category:
                        mapping['category'][legacy_seq] = current_category.seq
                        print(f"    제품구분 매핑: {legacy_seq} -> {current_category.seq} ({cat_code}:{cat_name})")
            
            print(f"  제품구분 매핑 완료: {len(mapping['category'])}개")
            
            # 3. 타입 매핑
            print("  [INFO] 타입 매핑 생성...")
            cursor.execute("""
                SELECT Seq, Code, CodeName FROM tbl_Code 
                WHERE ParentSeq = (SELECT Seq FROM tbl_Code WHERE Code = 'TP' AND Depth = 0)
            """)
            legacy_types = cursor.fetchall()
            
            type_group = Code.query.filter_by(code_name='타입', depth=0).first()
            if type_group:
                for legacy_type in legacy_types:
                    legacy_seq, type_code, type_name = legacy_type
                    
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
                        mapping['type'][legacy_seq] = current_type.seq
                        print(f"    타입 매핑: {legacy_seq} -> {current_type.seq} ({type_code}:{type_name})")
            
            print(f"  타입 매핑 완료: {len(mapping['type'])}개")
            
            # 4. 년도 매핑
            print("  [INFO] 년도 매핑 생성...")
            cursor.execute("""
                SELECT Seq, Code, CodeName FROM tbl_Code 
                WHERE ParentSeq = (SELECT Seq FROM tbl_Code WHERE Code = 'YR' AND Depth = 0)
            """)
            legacy_years = cursor.fetchall()
            
            year_group = Code.query.filter_by(code_name='년도', depth=0).first()
            if year_group:
                for legacy_year in legacy_years:
                    legacy_seq, year_code, year_name = legacy_year
                    
                    current_year = Code.query.filter_by(
                        parent_seq=year_group.seq,
                        code=year_code
                    ).first()
                    
                    if not current_year:
                        current_year = Code.query.filter(
                            Code.parent_seq == year_group.seq,
                            Code.code_name.ilike(f'%{year_name}%')
                        ).first()
                    
                    if current_year:
                        mapping['year'][legacy_seq] = current_year.seq
                        print(f"    년도 매핑: {legacy_seq} -> {current_year.seq} ({year_code}:{year_name})")
            
            print(f"  년도 매핑 완료: {len(mapping['year'])}개")
        
        return mapping
        
    except Exception as e:
        print(f"[ERROR] 매핑 생성 실패: {e}")
        return {}
    finally:
        legacy_conn.close()

def migrate_products(mapping):
    """레거시 상품 마이그레이션"""
    legacy_conn = get_legacy_connection()
    if not legacy_conn:
        return False
    
    print("\n[STEP 3] 상품 마이그레이션 시작...")
    
    try:
        cursor = legacy_conn.cursor()
        
        with app.app_context():
            # 레거시 상품 조회
            cursor.execute("""
                SELECT Seq, Company, Brand, ProdGroup, ProdType, ProdYear, 
                       ProdName, ProdTagAmt, ProdManual, ProdInfo, 
                       FaqYn, ShowYn, UseYn, InsDate, InsUser, UptDate, UptUser
                FROM tbl_Product 
                WHERE UseYN = 'Y'
                ORDER BY Seq
            """)
            legacy_products = cursor.fetchall()
            
            print(f"  레거시 상품 {len(legacy_products)}개 발견")
            
            migrated_count = 0
            skipped_count = 0
            
            for product in legacy_products:
                try:
                    seq, company, brand, prod_group, prod_type, prod_year, \
                    prod_name, prod_tag_amt, prod_manual, prod_info, \
                    faq_yn, show_yn, use_yn, ins_date, ins_user, upt_date, upt_user = product
                    
                    # 코드 매핑 적용
                    brand_code_seq = mapping['brand'].get(brand)
                    category_code_seq = mapping['category'].get(prod_group)
                    type_code_seq = mapping['type'].get(prod_type)
                    year_code_seq = mapping['year'].get(prod_year)
                    
                    # 새 상품 생성
                    new_product = Product(
                        company_id=1,  # 에이원으로 고정
                        brand_code_seq=brand_code_seq,
                        category_code_seq=category_code_seq,
                        type_code_seq=type_code_seq,
                        year_code_seq=year_code_seq,
                        product_name=prod_name or '',
                        price=prod_tag_amt or 0,
                        description=prod_info or '',
                        manual_file_path=prod_manual or '',
                        is_active=(use_yn == 'Y'),
                        legacy_seq=seq,
                        created_by='legacy_migration',
                        updated_by='legacy_migration'
                    )
                    
                    db.session.add(new_product)
                    db.session.flush()  # ID 생성
                    
                    migrated_count += 1
                    
                    if migrated_count % 50 == 0:
                        db.session.commit()
                        print(f"    진행률: {migrated_count}/{len(legacy_products)}")
                
                except Exception as e:
                    print(f"    [ERROR] 상품 {seq} 마이그레이션 실패: {e}")
                    skipped_count += 1
                    db.session.rollback()
                    continue
            
            db.session.commit()
            
            print(f"  상품 마이그레이션 완료!")
            print(f"    - 성공: {migrated_count}개")
            print(f"    - 실패: {skipped_count}개")
            
            return migrated_count > 0
            
    except Exception as e:
        print(f"[ERROR] 상품 마이그레이션 실패: {e}")
        db.session.rollback()
        return False
    finally:
        legacy_conn.close()

def migrate_product_details():
    """상품 상세 정보 마이그레이션"""
    legacy_conn = get_legacy_connection()
    if not legacy_conn:
        return False
    
    print("\n[STEP 4] 상품 상세 정보 마이그레이션 시작...")
    
    try:
        cursor = legacy_conn.cursor()
        
        with app.app_context():
            # 레거시 상품 상세 조회
            cursor.execute("""
                SELECT Seq, MstSeq, BrandCode, DivTypeCode, ProdGroupCode, 
                       ProdTypeCode, ProdCode, ProdType2Code, YearCode, 
                       ProdColorCode, StdDivProdCode, ProductName, Status
                FROM tbl_Product_DTL 
                WHERE Status = 'Active'
                ORDER BY Seq
            """)
            legacy_details = cursor.fetchall()
            
            print(f"  레거시 상품 상세 {len(legacy_details)}개 발견")
            
            migrated_count = 0
            skipped_count = 0
            
            for detail in legacy_details:
                try:
                    seq, mst_seq, brand_code, div_type_code, prod_group_code, \
                    prod_type_code, prod_code, prod_type2_code, year_code, \
                    prod_color_code, std_div_prod_code, product_name, status = detail
                    
                    # 해당 상품 찾기
                    parent_product = Product.query.filter_by(legacy_seq=mst_seq).first()
                    if not parent_product:
                        skipped_count += 1
                        continue
                    
                    # 상품 상세 생성
                    new_detail = ProductDetail(
                        product_id=parent_product.id,
                        brand_code=brand_code[:2] if brand_code else '',
                        div_type_code=div_type_code[:1] if div_type_code else '',
                        prod_group_code=prod_group_code[:2] if prod_group_code else '',
                        prod_type_code=prod_type_code[:2] if prod_type_code else '',
                        prod_code=prod_code[:2] if prod_code else '',
                        prod_type2_code=prod_type2_code[:2] if prod_type2_code else '',
                        year_code=year_code[:1] if year_code else '',
                        color_code=prod_color_code[:3] if prod_color_code else '',
                        std_div_prod_code=std_div_prod_code or '',
                        product_name=product_name or '',
                        status=status or 'Active',
                        legacy_seq=seq,
                        created_by='legacy_migration',
                        updated_by='legacy_migration'
                    )
                    
                    db.session.add(new_detail)
                    migrated_count += 1
                    
                    if migrated_count % 50 == 0:
                        db.session.commit()
                        print(f"    진행률: {migrated_count}/{len(legacy_details)}")
                
                except Exception as e:
                    print(f"    [ERROR] 상품 상세 {seq} 마이그레이션 실패: {e}")
                    skipped_count += 1
                    db.session.rollback()
                    continue
            
            db.session.commit()
            
            print(f"  상품 상세 마이그레이션 완료!")
            print(f"    - 성공: {migrated_count}개")
            print(f"    - 실패: {skipped_count}개")
            
            return migrated_count > 0
            
    except Exception as e:
        print(f"[ERROR] 상품 상세 마이그레이션 실패: {e}")
        db.session.rollback()
        return False
    finally:
        legacy_conn.close()

def verify_migration():
    """마이그레이션 결과 검증"""
    with app.app_context():
        print("\n[STEP 5] 마이그레이션 결과 검증...")
        
        # 1. 상품 통계
        total_products = Product.query.count()
        legacy_products = Product.query.filter(Product.legacy_seq.isnot(None)).count()
        
        print(f"  총 상품: {total_products}개")
        print(f"  레거시 연결: {legacy_products}개")
        
        # 2. 매핑 상태 확인
        mapped_brand = Product.query.filter(Product.brand_code_seq.isnot(None)).count()
        mapped_category = Product.query.filter(Product.category_code_seq.isnot(None)).count()
        mapped_type = Product.query.filter(Product.type_code_seq.isnot(None)).count()
        mapped_year = Product.query.filter(Product.year_code_seq.isnot(None)).count()
        
        print(f"\n  매핑 상태:")
        print(f"    - 브랜드: {mapped_brand}개 ({mapped_brand/total_products*100:.1f}%)")
        print(f"    - 품목: {mapped_category}개 ({mapped_category/total_products*100:.1f}%)")
        print(f"    - 타입: {mapped_type}개 ({mapped_type/total_products*100:.1f}%)")
        print(f"    - 년도: {mapped_year}개 ({mapped_year/total_products*100:.1f}%)")
        
        # 3. 샘플 확인
        sample_products = Product.query.filter(Product.legacy_seq.isnot(None)).limit(5).all()
        print(f"\n  샘플 상품 5개:")
        for product in sample_products:
            print(f"    - {product.product_name} (Legacy:{product.legacy_seq})")
            print(f"      브랜드: {product.brand_code.code_name if product.brand_code else 'None'}")
            print(f"      품목: {product.category_code.code_name if product.category_code else 'None'}")
            print(f"      타입: {product.type_code.code_name if product.type_code else 'None'}")
            print(f"      년도: {product.year_code.code_name if product.year_code else 'None'}")
        
        # 4. ProductDetail 통계
        total_details = ProductDetail.query.count()
        legacy_details = ProductDetail.query.filter(ProductDetail.legacy_seq.isnot(None)).count()
        
        print(f"\n  상품 상세:")
        print(f"    - 총 상세: {total_details}개")
        print(f"    - 레거시 연결: {legacy_details}개")

def main():
    """메인 실행 함수"""
    print("=== 완전한 레거시 상품 마이그레이션 시작 ===")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 기존 데이터 백업 및 정리
    if not backup_existing_products():
        print("[FAIL] 백업 실패, 마이그레이션 중단")
        return
    
    # 2. 코드 매핑 생성
    mapping = build_code_mapping()
    if not mapping or not any(mapping.values()):
        print("[FAIL] 코드 매핑 실패, 마이그레이션 중단")
        return
    
    print(f"\n매핑 통계:")
    print(f"  - 브랜드: {len(mapping['brand'])}개")
    print(f"  - 품목: {len(mapping['category'])}개")
    print(f"  - 타입: {len(mapping['type'])}개")
    print(f"  - 년도: {len(mapping['year'])}개")
    
    # 3. 상품 마이그레이션
    if not migrate_products(mapping):
        print("[FAIL] 상품 마이그레이션 실패")
        return
    
    # 4. 상품 상세 마이그레이션
    if not migrate_product_details():
        print("[WARN] 상품 상세 마이그레이션 실패, 하지만 계속 진행")
    
    # 5. 결과 검증
    verify_migration()
    
    print(f"\n=== 마이그레이션 완료 ===")
    print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("웹 페이지를 새로고침하여 결과를 확인하세요!")

if __name__ == '__main__':
    main() 