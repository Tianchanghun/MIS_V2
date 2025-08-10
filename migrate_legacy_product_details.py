#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
레거시 tbl_Product_DTL 데이터를 새로운 ProductDetail 모델로 마이그레이션
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pyodbc
from datetime import datetime
from app import create_app
from app.common.models import db, ProductDetail, Product

# 환경 설정
app = create_app()

# 레거시 DB 연결 정보
import os
LEGACY_DB_CONFIG = {
    'server': os.getenv('LEGACY_DB_SERVER', 'DESKTOP-HIROO5D\\SQLEXPRESS'),
    'database': os.getenv('LEGACY_DB_NAME', 'AoneMIS'),
    'username': os.getenv('LEGACY_DB_USER', 'sa'),
    'password': os.getenv('LEGACY_DB_PASSWORD', 'Sksmsqnwk14!')
}

def get_legacy_connection():
    """레거시 DB 연결 (다중 연결 시도)"""
    connection_attempts = [
        # 시도 1: TCP/IP 연결
        {
            'connection_string': (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={LEGACY_DB_CONFIG['server']};"
                f"DATABASE={LEGACY_DB_CONFIG['database']};"
                f"UID={LEGACY_DB_CONFIG['username']};"
                f"PWD={LEGACY_DB_CONFIG['password']};"
                f"Encrypt=no;"
                f"TrustServerCertificate=yes;"
            ),
            'description': 'ODBC Driver 17 (TCP/IP)'
        },
        # 시도 2: Named Pipes 연결
        {
            'connection_string': (
                f"DRIVER={{SQL Server}};"
                f"SERVER={LEGACY_DB_CONFIG['server']};"
                f"DATABASE={LEGACY_DB_CONFIG['database']};"
                f"UID={LEGACY_DB_CONFIG['username']};"
                f"PWD={LEGACY_DB_CONFIG['password']};"
                f"Trusted_Connection=no;"
            ),
            'description': 'SQL Server Driver (Named Pipes)'
        },
        # 시도 3: Windows 인증
        {
            'connection_string': (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={LEGACY_DB_CONFIG['server']};"
                f"DATABASE={LEGACY_DB_CONFIG['database']};"
                f"Trusted_Connection=yes;"
                f"Encrypt=no;"
            ),
            'description': 'Windows 인증'
        }
    ]
    
    for attempt in connection_attempts:
        try:
            print(f"🔄 연결 시도: {attempt['description']}")
            connection = pyodbc.connect(attempt['connection_string'], timeout=10)
            print(f"✅ 레거시 DB 연결 성공: {LEGACY_DB_CONFIG['database']} ({attempt['description']})")
            return connection
            
        except Exception as e:
            print(f"❌ {attempt['description']} 연결 실패: {str(e)[:100]}...")
            continue
    
    print(f"❌ 모든 연결 시도 실패")
    return None

def migrate_product_details():
    """제품모델 데이터 마이그레이션"""
    
    legacy_conn = get_legacy_connection()
    if not legacy_conn:
        return False
    
    try:
        with app.app_context():
            cursor = legacy_conn.cursor()
            
            # 레거시 제품모델 데이터 조회
            query = """
                SELECT 
                    Seq,
                    MstSeq,
                    BrandCode,
                    DivTypeCode,
                    ProdGroupCode,
                    ProdTypeCode,
                    ProdCode,
                    ProdType2Code,
                    YearCode,
                    ProdColorCode,
                    StdDivProdCode,
                    ProductName,
                    Status
                FROM tbl_Product_DTL 
                WHERE Status = 'Active'
                ORDER BY Seq
            """
            
            cursor.execute(query)
            legacy_details = cursor.fetchall()
            
            print(f"📊 레거시 제품모델 {len(legacy_details)}개 발견")
            
            migrated_count = 0
            skipped_count = 0
            error_count = 0
            
            for detail in legacy_details:
                try:
                    seq, mst_seq, brand_code, div_type_code, prod_group_code, \
                    prod_type_code, prod_code, prod_type2_code, year_code, \
                    prod_color_code, std_div_prod_code, product_name, status = detail
                    
                    # 중복 검사 (자가코드 기준)
                    existing_detail = ProductDetail.query.filter_by(
                        std_div_prod_code=std_div_prod_code.strip()
                    ).first()
                    
                    if existing_detail:
                        skipped_count += 1
                        continue
                    
                    # 연관된 상품 찾기 (MstSeq를 통해)
                    product = Product.query.filter_by(legacy_seq=mst_seq).first()
                    if not product:
                        print(f"⚠️  연관 상품을 찾을 수 없음: MstSeq={mst_seq}, ProductName={product_name}")
                        # 상품이 없어도 제품모델만 저장 (product_id는 None)
                    
                    # 새로운 제품모델 생성
                    new_detail = ProductDetail(
                        product_id=product.id if product else None,
                        brand_code=brand_code.strip() if brand_code else '',
                        div_type_code=div_type_code.strip() if div_type_code else '',
                        prod_group_code=prod_group_code.strip() if prod_group_code else '',
                        prod_type_code=prod_type_code.strip() if prod_type_code else '',
                        prod_code=prod_code.strip() if prod_code else '',
                        prod_type2_code=prod_type2_code.strip() if prod_type2_code else '',
                        year_code=year_code.strip() if year_code else '',
                        color_code=prod_color_code.strip() if prod_color_code else '',
                        std_div_prod_code=std_div_prod_code.strip() if std_div_prod_code else '',
                        product_name=product_name.strip() if product_name else '',
                        additional_price=0,  # 기본값
                        stock_quantity=0,    # 기본값
                        status=status.strip() if status else 'Active',
                        legacy_seq=seq,
                        created_by='migration',
                        updated_by='migration'
                    )
                    
                    db.session.add(new_detail)
                    migrated_count += 1
                    
                    if migrated_count % 50 == 0:
                        db.session.commit()
                        print(f"📥 진행률: {migrated_count}/{len(legacy_details)} ({migrated_count/len(legacy_details)*100:.1f}%)")
                        
                except Exception as e:
                    error_count += 1
                    print(f"❌ 제품모델 마이그레이션 오류: {e}")
                    db.session.rollback()
            
            # 최종 커밋
            db.session.commit()
            
            print(f"\n🎉 제품모델 마이그레이션 완료!")
            print(f"✅ 마이그레이션: {migrated_count}개")
            print(f"⏭️  건너뜀: {skipped_count}개")
            print(f"❌ 오류: {error_count}개")
            
            return True
            
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        db.session.rollback()
        return False
        
    finally:
        legacy_conn.close()

def check_product_detail_table():
    """ProductDetail 테이블 상태 확인"""
    with app.app_context():
        try:
            count = ProductDetail.query.count()
            print(f"📊 현재 ProductDetail 테이블: {count}개 레코드")
            
            # 최근 5개 제품모델 출력
            recent_details = ProductDetail.query.order_by(ProductDetail.created_at.desc()).limit(5).all()
            if recent_details:
                print(f"\n🔍 최근 제품모델 5개:")
                for detail in recent_details:
                    print(f"  - {detail.product_name} ({detail.std_div_prod_code})")
            
        except Exception as e:
            print(f"❌ 테이블 확인 실패: {e}")

if __name__ == '__main__':
    print("🚀 레거시 제품모델 마이그레이션 시작")
    print("=" * 50)
    
    # 현재 상태 확인
    check_product_detail_table()
    
    # 마이그레이션 실행
    if migrate_product_details():
        print("\n" + "=" * 50)
        print("🎊 마이그레이션 성공!")
        
        # 마이그레이션 후 상태 확인
        check_product_detail_table()
    else:
        print("\n" + "=" * 50)
        print("💥 마이그레이션 실패") 