#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
레거시 DB에서 모든 상품 데이터 완전 마이그레이션
- UseYN='N' 포함하여 모든 데이터 가져오기
- 1,228개 product_details 완전 마이그레이션
- 기존 데이터 백업 후 새로운 데이터로 교체
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pyodbc
from datetime import datetime
from app import create_app
from app.common.models import db, Product, ProductDetail, Code
import json

# 레거시 DB 연결 정보
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
        connection = pyodbc.connect(connection_string, timeout=30)
        print("✅ 레거시 DB 연결 성공")
        return connection
    except Exception as e:
        print(f"❌ 레거시 DB 연결 실패: {e}")
        return None

def backup_current_data():
    """현재 데이터 백업"""
    app = create_app()
    
    print("\n📦 현재 데이터 백업 중...")
    with app.app_context():
        # 현재 데이터 수 확인
        product_count = Product.query.count()
        detail_count = ProductDetail.query.count()
        
        print(f"   백업할 데이터: products {product_count}개, product_details {detail_count}개")
        
        # 백업 파일 생성
        backup_data = {
            'backup_date': datetime.now().isoformat(),
            'products': [p.to_dict() for p in Product.query.all()],
            'product_details': [pd.to_dict() for pd in ProductDetail.query.all()]
        }
        
        backup_filename = f"backup_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_filename, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
        print(f"   ✅ 백업 완료: {backup_filename}")
        return backup_filename

def clear_current_data():
    """현재 상품 데이터 삭제"""
    app = create_app()
    
    print("\n🗑️ 현재 상품 데이터 삭제 중...")
    with app.app_context():
        try:
            # ProductDetail 먼저 삭제 (외래키 제약 때문에)
            detail_count = ProductDetail.query.count()
            ProductDetail.query.delete()
            
            # Product 삭제
            product_count = Product.query.count()
            Product.query.delete()
            
            db.session.commit()
            print(f"   ✅ 삭제 완료: products {product_count}개, product_details {detail_count}개")
            
        except Exception as e:
            db.session.rollback()
            print(f"   ❌ 삭제 실패: {e}")
            return False
            
    return True

def get_code_mapping():
    """코드 매핑 테이블 생성"""
    app = create_app()
    
    print("\n🔄 코드 매핑 테이블 생성 중...")
    with app.app_context():
        mapping = {}
        
        # 모든 코드 그룹별로 매핑 생성
        code_groups = ['회사', '브랜드', '품목', '타입', '년도', '제품코드', '타입2', '색상', '구분타입']
        
        for group_name in code_groups:
            codes = Code.get_codes_by_group_name(group_name, company_id=1)
            mapping[group_name] = {}
            
            for code in codes:
                # seq를 키로 하는 매핑
                mapping[group_name][code.seq] = {
                    'code': code.code,
                    'name': code.code_name,
                    'seq': code.seq
                }
        
        print(f"   ✅ 코드 매핑 완료: {len(mapping)} 그룹")
        return mapping

def migrate_products(legacy_conn, code_mapping):
    """상품 마스터 데이터 마이그레이션"""
    app = create_app()
    
    print("\n📋 상품 마스터 데이터 마이그레이션 중...")
    
    cursor = legacy_conn.cursor()
    cursor.execute("""
        SELECT 
            Seq, Company, Brand, ProdGroup, ProdType, ProdYear,
            ProdName, Price, UseYN, InsDate, InsUser, UptDate, UptUser
        FROM tbl_Product
        ORDER BY Seq
    """)
    
    legacy_products = cursor.fetchall()
    print(f"   레거시 상품 수: {len(legacy_products):,}개")
    
    migrated_count = 0
    skipped_count = 0
    
    with app.app_context():
        for row in legacy_products:
            try:
                # UseYN='N'도 포함하여 모든 데이터 마이그레이션
                product = Product(
                    company_id=1,  # 에이원으로 고정
                    brand_code_seq=row[2],
                    category_code_seq=row[3],  # ProdGroup -> category
                    type_code_seq=row[4],      # ProdType -> type
                    year_code_seq=row[5],
                    div_type_code_seq=1,       # 일반으로 고정
                    product_name=row[6],
                    product_code='',
                    price=row[7] if row[7] else 0,
                    description='',
                    is_active=(row[8] == 'Y'),  # UseYN 기반
                    use_yn=row[8],             # 원본 UseYN 값 보존
                    legacy_seq=row[0],         # 레거시 Seq 저장
                    created_by=row[10] if row[10] else 'system',
                    updated_by=row[12] if row[12] else 'system'
                )
                
                # 날짜 설정
                if row[9]:  # InsDate
                    product.created_at = row[9]
                if row[11]:  # UptDate
                    product.updated_at = row[11]
                
                db.session.add(product)
                migrated_count += 1
                
            except Exception as e:
                print(f"   ⚠️ 상품 마이그레이션 실패 (Seq: {row[0]}): {e}")
                skipped_count += 1
                continue
        
        db.session.commit()
        print(f"   ✅ 상품 마이그레이션 완료: {migrated_count:,}개 성공, {skipped_count}개 실패")

def migrate_product_details(legacy_conn):
    """상품 상세 데이터 마이그레이션"""
    app = create_app()
    
    print("\n🎨 상품 상세 데이터 마이그레이션 중...")
    
    cursor = legacy_conn.cursor()
    cursor.execute("""
        SELECT 
            Seq, MstSeq, BrandCode, DivTypeCode, ProdGroupCode,
            ProdTypeCode, ProdCode, ProdType2Code, YearCode, ProdColorCode,
            StdDivProdCode, ProductName, Status
        FROM tbl_Product_DTL
        ORDER BY Seq
    """)
    
    legacy_details = cursor.fetchall()
    print(f"   레거시 상세 수: {len(legacy_details):,}개")
    
    migrated_count = 0
    skipped_count = 0
    
    with app.app_context():
        # 마이그레이션된 Product의 legacy_seq 매핑 생성
        products_map = {}
        for product in Product.query.all():
            if product.legacy_seq:
                products_map[product.legacy_seq] = product.id
        
        for row in legacy_details:
            try:
                # 해당하는 Product 찾기
                product_id = products_map.get(row[1])  # MstSeq로 매핑
                
                if not product_id:
                    print(f"   ⚠️ Product 매핑 실패 (MstSeq: {row[1]})")
                    skipped_count += 1
                    continue
                
                # 16자리 자가코드 확인 및 정제
                std_code = row[10].strip() if row[10] else ''
                
                # 빈 자가코드도 포함하여 마이그레이션 (레거시에 그대로 존재)
                product_detail = ProductDetail(
                    product_id=product_id,
                    brand_code=row[2].strip(),
                    div_type_code=row[3].strip(),
                    prod_group_code=row[4].strip(),
                    prod_type_code=row[5].strip(),
                    prod_code=row[6].strip(),
                    prod_type2_code=row[7].strip(),
                    year_code=row[8].strip(),
                    color_code=row[9].strip(),
                    std_div_prod_code=std_code,
                    product_name=row[11] if row[11] else '',
                    additional_price=0,
                    stock_quantity=0,
                    status=row[12] if row[12] else 'Active',
                    legacy_seq=row[0],  # 레거시 Seq 저장
                    created_by='system',
                    updated_by='system'
                )
                
                db.session.add(product_detail)
                migrated_count += 1
                
            except Exception as e:
                print(f"   ⚠️ 상세 마이그레이션 실패 (Seq: {row[0]}): {e}")
                skipped_count += 1
                continue
        
        db.session.commit()
        print(f"   ✅ 상세 마이그레이션 완료: {migrated_count:,}개 성공, {skipped_count}개 실패")

def verify_migration():
    """마이그레이션 결과 검증"""
    app = create_app()
    
    print("\n🔍 마이그레이션 결과 검증 중...")
    
    with app.app_context():
        # 현재 데이터 수 확인
        product_count = Product.query.count()
        active_product_count = Product.query.filter_by(is_active=True).count()
        inactive_product_count = Product.query.filter_by(is_active=False).count()
        
        detail_count = ProductDetail.query.count()
        active_detail_count = ProductDetail.query.filter_by(status='Active').count()
        
        valid_std_code_count = ProductDetail.query.filter(
            ProductDetail.std_div_prod_code != None,
            ProductDetail.std_div_prod_code != '',
            ProductDetail.std_div_prod_code != '                '
        ).count()
        
        print(f"   📊 마이그레이션 결과:")
        print(f"      상품 총 {product_count:,}개 (활성: {active_product_count:,}, 비활성: {inactive_product_count:,})")
        print(f"      상세 총 {detail_count:,}개 (활성: {active_detail_count:,})")
        print(f"      유효한 자가코드: {valid_std_code_count:,}개")
        
        # 몇 개 샘플 데이터 확인
        print(f"\n   📋 샘플 상품 데이터:")
        for product in Product.query.limit(3).all():
            print(f"      ID:{product.id}, LegacySeq:{product.legacy_seq}, Name:{product.product_name}")
            print(f"      UseYN:{product.use_yn}, Active:{product.is_active}")
            
        print(f"\n   📋 샘플 상세 데이터:")
        for detail in ProductDetail.query.limit(3).all():
            print(f"      ID:{detail.id}, LegacySeq:{detail.legacy_seq}, StdCode:'{detail.std_div_prod_code}'")
            print(f"      Name:'{detail.product_name}', Status:'{detail.status}'")

def main():
    """메인 실행 함수"""
    print("🚀 레거시 DB 완전 마이그레이션 시작...")
    print("=" * 80)
    
    # 1. 레거시 DB 연결 확인
    legacy_conn = get_legacy_connection()
    if not legacy_conn:
        return
    
    # 2. 현재 데이터 백업
    backup_file = backup_current_data()
    if not backup_file:
        print("❌ 백업 실패")
        return
    
    # 3. 현재 데이터 삭제
    if not clear_current_data():
        print("❌ 데이터 삭제 실패")
        return
    
    # 4. 코드 매핑 생성
    code_mapping = get_code_mapping()
    
    # 5. 상품 마스터 마이그레이션
    migrate_products(legacy_conn, code_mapping)
    
    # 6. 상품 상세 마이그레이션
    migrate_product_details(legacy_conn)
    
    # 7. 결과 검증
    verify_migration()
    
    legacy_conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 레거시 DB 완전 마이그레이션 완료!")
    print(f"📦 백업 파일: {backup_file}")
    print("=" * 80)

if __name__ == "__main__":
    main() 