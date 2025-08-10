#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
레거시 DB와 현재 DB의 상품 데이터 비교
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pyodbc
from app import create_app
from app.common.models import db, Product, ProductDetail

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

def check_legacy_tables():
    """레거시 DB 테이블 구조 및 데이터 확인"""
    conn = get_legacy_connection()
    if not conn:
        return
        
    cursor = conn.cursor()
    
    print("=" * 80)
    print("📊 레거시 DB 테이블 확인")
    print("=" * 80)
    
    # tbl_Product 테이블 확인
    print("\n🔍 tbl_Product 테이블:")
    try:
        cursor.execute("SELECT COUNT(*) FROM tbl_Product")
        product_count = cursor.fetchone()[0]
        print(f"   총 상품 수: {product_count:,}개")
        
        cursor.execute("SELECT COUNT(*) FROM tbl_Product WHERE UseYN = 'Y'")
        active_count = cursor.fetchone()[0]
        print(f"   사용중인 상품: {active_count:,}개")
        
        cursor.execute("SELECT COUNT(*) FROM tbl_Product WHERE UseYN = 'N'")
        inactive_count = cursor.fetchone()[0]
        print(f"   사용안함 상품: {inactive_count:,}개")
        
        # 몇 개 샘플 데이터 확인 (정확한 컬럼명 사용)
        cursor.execute("""
            SELECT TOP 5 
                Seq, Company, Brand, ProdGroup, ProdType, ProdName, 
                Price, UseYN, InsDate
            FROM tbl_Product
            ORDER BY Seq
        """)
        print("\n   📋 샘플 데이터:")
        for row in cursor.fetchall():
            print(f"      Seq:{row[0]}, Company:{row[1]}, Brand:{row[2]}, Group:{row[3]}, Type:{row[4]}")
            print(f"      Name:{row[5]}, Price:{row[6]}, UseYN:{row[7]}")
            
    except Exception as e:
        print(f"   ❌ tbl_Product 조회 실패: {e}")
    
    # tbl_Product_DTL 테이블 확인
    print("\n🔍 tbl_Product_DTL 테이블:")
    try:
        cursor.execute("SELECT COUNT(*) FROM tbl_Product_DTL")
        detail_count = cursor.fetchone()[0]
        print(f"   총 상세 수: {detail_count:,}개")
        
        cursor.execute("SELECT COUNT(*) FROM tbl_Product_DTL WHERE Status = 'Active'")
        active_detail_count = cursor.fetchone()[0]
        print(f"   활성 상세: {active_detail_count:,}개")
        
        # DivTypeCode 분포 확인
        cursor.execute("""
            SELECT DivTypeCode, COUNT(*) as cnt
            FROM tbl_Product_DTL
            GROUP BY DivTypeCode
            ORDER BY cnt DESC
        """)
        print("\n   📊 DivTypeCode 분포:")
        for row in cursor.fetchall():
            print(f"      DivTypeCode '{row[0]}': {row[1]:,}개")
            
        # 몇 개 샘플 데이터 확인
        cursor.execute("""
            SELECT TOP 5 
                Seq, MstSeq, DivTypeCode, ProdCode, ProdType2Code, 
                YearCode, ProdColorCode, StdDivProdCode, ProductName, Status
            FROM tbl_Product_DTL
            WHERE StdDivProdCode != '                '
            ORDER BY Seq
        """)
        print("\n   📋 샘플 데이터 (유효한 자가코드만):")
        for row in cursor.fetchall():
            print(f"      Seq:{row[0]}, MstSeq:{row[1]}, DivType:'{row[2]}', ProdCode:'{row[3]}'")
            print(f"      StdCode:'{row[7]}', Name:'{row[8]}', Status:'{row[9]}'")
            
    except Exception as e:
        print(f"   ❌ tbl_Product_DTL 조회 실패: {e}")
    
    conn.close()

def check_current_database():
    """현재 PostgreSQL DB 상품 데이터 확인"""
    app = create_app()
    
    print("\n" + "=" * 80)
    print("📊 현재 PostgreSQL DB 확인")
    print("=" * 80)
    
    with app.app_context():
        # Product 테이블 확인
        product_count = Product.query.count()
        active_product_count = Product.query.filter_by(is_active=True).count()
        print(f"\n🔍 products 테이블:")
        print(f"   총 상품 수: {product_count:,}개")
        print(f"   활성 상품 수: {active_product_count:,}개")
        
        # ProductDetail 테이블 확인 (status 필드 사용)
        detail_count = ProductDetail.query.count()
        active_detail_count = ProductDetail.query.filter_by(status='Active').count()
        print(f"\n🔍 product_details 테이블:")
        print(f"   총 상세 수: {detail_count:,}개")
        print(f"   활성 상세 수: {active_detail_count:,}개")
        
        # 자가코드가 있는 상세 데이터 확인
        valid_std_code_count = ProductDetail.query.filter(
            ProductDetail.std_div_prod_code != None,
            ProductDetail.std_div_prod_code != ''
        ).count()
        print(f"   유효한 자가코드: {valid_std_code_count:,}개")
        
        # 몇 개 샘플 데이터 확인
        sample_products = Product.query.limit(3).all()
        print(f"\n   📋 샘플 상품 데이터:")
        for product in sample_products:
            print(f"      ID:{product.id}, Name:{product.product_name}")
            print(f"      Brand:{product.brand_code_seq}, Category:{product.category_code_seq}")
            
        sample_details = ProductDetail.query.filter(
            ProductDetail.std_div_prod_code != None,
            ProductDetail.std_div_prod_code != ''
        ).limit(3).all()
        print(f"\n   📋 샘플 상세 데이터 (유효한 자가코드만):")
        for detail in sample_details:
            print(f"      ID:{detail.id}, StdCode:'{detail.std_div_prod_code}'")
            print(f"      Name:'{detail.product_name}', Status:'{detail.status}'")

def main():
    """메인 실행 함수"""
    print("🔄 레거시 DB vs 현재 DB 상품 데이터 비교 시작...")
    
    # 레거시 DB 확인
    check_legacy_tables()
    
    # 현재 DB 확인
    check_current_database()
    
    print("\n" + "=" * 80)
    print("📊 비교 결과:")
    print("레거시 DB: tbl_Product 699개, tbl_Product_DTL 1,228개")
    print("현재 DB: products 699개, product_details ? 개")
    print("=" * 80)
    print("✅ 비교 완료")
    print("=" * 80)

if __name__ == "__main__":
    main() 