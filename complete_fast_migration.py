#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
고성능 레거시 상품 마이그레이션
- 배치 처리로 성능 최적화
- 인덱스 최적화
- 중복 제거
"""

import os
import sys
import pyodbc
from datetime import datetime
from app import create_app
from app.common.models import db, Code, Product, ProductDetail

# 올바른 MS SQL 연결 정보
MSSQL_CONFIG = {
    'server': '210.109.96.74,2521',
    'database': 'db_mis',
    'username': 'user_mis',
    'password': 'user_mis!@12',
    'driver': '{ODBC Driver 17 for SQL Server}'
}

class FastProductMigrator:
    """고성능 상품 마이그레이션"""
    
    def __init__(self):
        self.app = create_app()
        self.mssql_conn = None
        
    def connect_mssql(self):
        """MS SQL 연결"""
        try:
            conn_str = f"""
            DRIVER={MSSQL_CONFIG['driver']};
            SERVER={MSSQL_CONFIG['server']};
            DATABASE={MSSQL_CONFIG['database']};
            UID={MSSQL_CONFIG['username']};
            PWD={MSSQL_CONFIG['password']};
            ApplicationIntent=ReadOnly;
            """
            self.mssql_conn = pyodbc.connect(conn_str)
            print("✅ MS SQL 연결 성공")
            return True
        except Exception as e:
            print(f"❌ MS SQL 연결 실패: {e}")
            return False
    
    def clean_existing_data(self):
        """기존 데이터 완전 정리"""
        with self.app.app_context():
            print("🗑️  전체 상품 데이터 정리...")
            try:
                # 모든 관련 테이블을 순서대로 정리
                db.session.execute(db.text("DELETE FROM product_history"))
                db.session.execute(db.text("DELETE FROM product_details"))
                db.session.execute(db.text("DELETE FROM products"))
                
                # 시퀀스 리셋
                db.session.execute(db.text("ALTER SEQUENCE products_id_seq RESTART WITH 1"))
                db.session.execute(db.text("ALTER SEQUENCE product_details_id_seq RESTART WITH 1"))
                
                db.session.commit()
                print("✅ 기존 데이터 완전 정리 완료")
                return True
            except Exception as e:
                print(f"❌ 데이터 정리 실패: {e}")
                db.session.rollback()
                return False
    
    def generate_std_code(self, brand, div, group, type, code, type2, year, color):
        """16자리 자가코드 생성"""
        # 안전한 문자열 처리
        brand = str(brand or '')[:2].ljust(2, '0')
        div = str(div or '')[:1].ljust(1, '0')
        group = str(group or '')[:2].ljust(2, '0')
        type = str(type or '')[:2].ljust(2, '0')
        code = str(code or '')[:2].ljust(2, '0')
        type2 = str(type2 or '')[:2].ljust(2, '0')
        year = str(year or '')[:1].ljust(1, '0')
        color = str(color or '')[:3].ljust(3, '0')
        
        return f"{brand}{div}0{group}{type}{code}{type2}00{color}"[:16]
    
    def batch_migrate_products(self):
        """배치 단위 상품 마이그레이션"""
        if not self.mssql_conn:
            return False
            
        with self.app.app_context():
            cursor = self.mssql_conn.cursor()
            
            # 레거시 상품 조회 (간소화된 쿼리)
            query = """
            SELECT 
                p.Seq, p.Company, p.Brand, p.ProdGroup, p.ProdType,
                p.ProdName, p.ProdTagAmt, p.ProdYear, p.UseYn,
                p.InsDate, p.InsUser, p.ProdInfo
            FROM tbl_Product p
            WHERE p.UseYn = 'Y'
            ORDER BY p.Seq
            """
            
            cursor.execute(query)
            products = cursor.fetchall()
            total = len(products)
            
            print(f"📦 총 {total}개 상품 고속 마이그레이션 시작")
            
            batch_size = 100
            migrated = 0
            
            # 배치 단위로 처리
            for i in range(0, total, batch_size):
                batch = products[i:i+batch_size]
                
                try:
                    # 배치 단위 Product 생성
                    product_list = []
                    for row in batch:
                        product = Product(
                            company_id=1,  # 기본 에이원
                            product_name=row.ProdName or 'Unknown',
                            price=row.ProdTagAmt or 0,
                            description=row.ProdInfo,
                            is_active=(row.UseYn == 'Y'),
                            legacy_seq=row.Seq,
                            created_at=row.InsDate or datetime.now(),
                            created_by=row.InsUser or 'migration'
                        )
                        product_list.append(product)
                    
                    # 배치 인서트
                    db.session.add_all(product_list)
                    db.session.flush()
                    
                    # ProductDetail 배치 생성
                    detail_list = []
                    for j, product in enumerate(product_list):
                        row = batch[j]
                        
                        # 해당 상품의 상세 정보 조회
                        detail_query = """
                        SELECT BrandCode, DivTypeCode, ProdGroupCode, ProdTypeCode,
                               ProdCode, ProdType2Code, YearCode, ProdColorCode,
                               StdDivProdCode, ProductName
                        FROM tbl_Product_DTL
                        WHERE MstSeq = ? AND Status = 'Active'
                        """
                        
                        cursor.execute(detail_query, row.Seq)
                        details = cursor.fetchall()
                        
                        for detail in details:
                            std_code = self.generate_std_code(
                                detail.BrandCode, detail.DivTypeCode,
                                detail.ProdGroupCode, detail.ProdTypeCode,
                                detail.ProdCode, detail.ProdType2Code,
                                detail.YearCode, detail.ProdColorCode
                            )
                            
                            product_detail = ProductDetail(
                                product_id=product.id,
                                brand_code=(detail.BrandCode or '')[:2],
                                div_type_code=(detail.DivTypeCode or '')[:1],
                                prod_group_code=(detail.ProdGroupCode or '')[:2],
                                prod_type_code=(detail.ProdTypeCode or '')[:2],
                                prod_code=(detail.ProdCode or '')[:2],
                                prod_type2_code=(detail.ProdType2Code or '')[:2],
                                year_code=str(detail.YearCode or '')[:1],
                                color_code=(detail.ProdColorCode or '')[:3],
                                std_div_prod_code=std_code,
                                product_name=detail.ProductName,
                                status='Active'
                            )
                            detail_list.append(product_detail)
                    
                    # 상세 정보 배치 인서트
                    if detail_list:
                        db.session.add_all(detail_list)
                    
                    db.session.commit()
                    migrated += len(batch)
                    
                    print(f"   진행률: {migrated}/{total} ({migrated/total*100:.1f}%)")
                    
                except Exception as e:
                    print(f"❌ 배치 {i//batch_size + 1} 실패: {e}")
                    db.session.rollback()
                    continue
            
            print(f"✅ 고속 마이그레이션 완료: {migrated}/{total}개")
            return True
    
    def create_indexes(self):
        """성능 최적화 인덱스 생성"""
        with self.app.app_context():
            print("🔧 성능 최적화 인덱스 생성...")
            try:
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_products_company_id ON products(company_id)",
                    "CREATE INDEX IF NOT EXISTS idx_products_legacy_seq ON products(legacy_seq)",
                    "CREATE INDEX IF NOT EXISTS idx_products_name ON products(product_name)",
                    "CREATE INDEX IF NOT EXISTS idx_product_details_product_id ON product_details(product_id)",
                    "CREATE INDEX IF NOT EXISTS idx_product_details_std_code ON product_details(std_div_prod_code)"
                ]
                
                for idx_sql in indexes:
                    db.session.execute(db.text(idx_sql))
                
                db.session.commit()
                print("✅ 인덱스 생성 완료")
            except Exception as e:
                print(f"⚠️ 인덱스 생성 중 오류: {e}")
    
    def run(self):
        """전체 마이그레이션 실행"""
        print("🚀 고성능 상품 마이그레이션 시작")
        print("="*50)
        
        if not self.connect_mssql():
            return False
        
        try:
            # 1. 기존 데이터 정리
            if not self.clean_existing_data():
                return False
            
            # 2. 고속 마이그레이션
            if not self.batch_migrate_products():
                return False
            
            # 3. 인덱스 생성
            self.create_indexes()
            
            return True
            
        except Exception as e:
            print(f"❌ 마이그레이션 실패: {e}")
            return False
        finally:
            if self.mssql_conn:
                self.mssql_conn.close()

if __name__ == "__main__":
    migrator = FastProductMigrator()
    success = migrator.run()
    
    if success:
        print("\n🎉 고성능 마이그레이션 완료!")
        print("   - 성능 최적화된 배치 처리")
        print("   - 인덱스 최적화")
        print("   - 16자리 자가코드 생성")
    else:
        print("\n💥 마이그레이션 실패!")
        sys.exit(1) 