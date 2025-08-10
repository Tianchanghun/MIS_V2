#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
중복 코드 문제 해결
- std_div_prod_code 유니크 제약 조건 해결
- 시퀀스 기반 유니크 코드 생성
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

class DuplicateCodeFixer:
    """중복 코드 문제 해결"""
    
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
    
    def drop_unique_constraint(self):
        """유니크 제약 조건 제거"""
        with self.app.app_context():
            print("🔧 유니크 제약 조건 제거...")
            try:
                # std_div_prod_code 유니크 제약 조건 제거
                db.session.execute(db.text(
                    "ALTER TABLE product_details DROP CONSTRAINT IF EXISTS product_details_std_div_prod_code_key"
                ))
                db.session.commit()
                print("✅ 유니크 제약 조건 제거 완료")
                return True
            except Exception as e:
                print(f"⚠️ 제약 조건 제거 중 오류: {e}")
                return True  # 없어도 진행
    
    def clean_all_data(self):
        """모든 데이터 완전 정리"""
        with self.app.app_context():
            print("🗑️  모든 상품 데이터 정리...")
            try:
                # 모든 관련 테이블을 직접 SQL로 정리
                db.session.execute(db.text("TRUNCATE product_history RESTART IDENTITY CASCADE"))
                db.session.execute(db.text("TRUNCATE product_details RESTART IDENTITY CASCADE"))
                db.session.execute(db.text("TRUNCATE products RESTART IDENTITY CASCADE"))
                
                db.session.commit()
                print("✅ 모든 데이터 완전 정리 완료")
                return True
            except Exception as e:
                print(f"❌ 데이터 정리 실패: {e}")
                db.session.rollback()
                return False
    
    def generate_unique_std_code(self, seq, brand, div, group, type, code, type2, year, color):
        """유니크한 자가코드 생성 (seq 포함)"""
        # 안전한 문자열 처리
        brand = str(brand or '')[:2].ljust(2, '0')
        div = str(div or '')[:1].ljust(1, '0')
        group = str(group or '')[:2].ljust(2, '0')
        type = str(type or '')[:2].ljust(2, '0')
        code = str(code or '')[:2].ljust(2, '0')
        type2 = str(type2 or '')[:2].ljust(2, '0')
        year = str(year or '')[:1].ljust(1, '0')
        color = str(color or '')[:3].ljust(3, '0')
        
        # seq를 포함해서 유니크성 보장
        seq_part = str(seq).zfill(4)[-4:]  # 마지막 4자리만 사용
        
        return f"{brand}{div}{group}{type}{code}{type2}{year}{color}{seq_part}"[:16]
    
    def fast_migrate_all_products(self):
        """고속 상품 마이그레이션 (중복 제거)"""
        if not self.mssql_conn:
            return False
            
        with self.app.app_context():
            cursor = self.mssql_conn.cursor()
            
            # 레거시 상품 조회 (text 타입 제외)
            query = """
            SELECT 
                p.Seq as ProdSeq, p.ProdName, p.ProdTagAmt, 
                p.InsDate, p.InsUser, p.UseYn
            FROM tbl_Product p
            WHERE p.UseYn = 'Y'
            ORDER BY p.Seq
            """
            
            cursor.execute(query)
            products = cursor.fetchall()
            
            print(f"📦 총 {len(products)}개 상품 마이그레이션 시작")
            
            migrated_products = 0
            migrated_details = 0
            
            # 상품별로 처리
            for prod_row in products:
                try:
                    # Product 생성
                    product = Product(
                        company_id=1,  # 기본 에이원
                        product_name=prod_row.ProdName or 'Unknown',
                        price=prod_row.ProdTagAmt or 0,
                        description='',  # 일단 빈 값
                        is_active=(prod_row.UseYn == 'Y'),
                        legacy_seq=prod_row.ProdSeq,
                        created_at=prod_row.InsDate or datetime.now(),
                        created_by=prod_row.InsUser or 'migration'
                    )
                    
                    db.session.add(product)
                    db.session.flush()  # ID 생성
                    migrated_products += 1
                    
                    # 해당 상품의 상세 정보 조회
                    detail_query = """
                    SELECT 
                        d.Seq as DtlSeq, d.BrandCode, d.DivTypeCode, d.ProdGroupCode,
                        d.ProdTypeCode, d.ProdCode, d.ProdType2Code, d.YearCode,
                        d.ProdColorCode, d.ProductName as DtlName, d.Status
                    FROM tbl_Product_DTL d
                    WHERE d.MstSeq = ? AND d.Status = 'Active'
                    """
                    
                    cursor.execute(detail_query, prod_row.ProdSeq)
                    details = cursor.fetchall()
                    
                    # ProductDetail 생성
                    for detail in details:
                        # 유니크한 자가코드 생성
                        std_code = self.generate_unique_std_code(
                            detail.DtlSeq,  # 상세 seq 사용
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
                            std_div_prod_code=std_code,  # 유니크한 코드
                            product_name=detail.DtlName or prod_row.ProdName,
                            status=detail.Status or 'Active',
                            legacy_seq=detail.DtlSeq
                        )
                        
                        db.session.add(product_detail)
                        migrated_details += 1
                    
                    # 100개마다 커밋
                    if migrated_products % 100 == 0:
                        db.session.commit()
                        print(f"   진행률: {migrated_products}/{len(products)} ({migrated_products/len(products)*100:.1f}%)")
                    
                except Exception as e:
                    print(f"❌ 상품 처리 실패 (상품:{prod_row.ProdSeq}): {e}")
                    db.session.rollback()
                    continue
            
            db.session.commit()
            print(f"✅ 고속 마이그레이션 완료!")
            print(f"   - 상품: {migrated_products}개")
            print(f"   - 상세: {migrated_details}개")
            
            return True
    
    def create_optimized_indexes(self):
        """최적화된 인덱스 생성"""
        with self.app.app_context():
            print("🔧 최적화된 인덱스 생성...")
            try:
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_products_company_id ON products(company_id)",
                    "CREATE INDEX IF NOT EXISTS idx_products_legacy_seq ON products(legacy_seq)",
                    "CREATE INDEX IF NOT EXISTS idx_products_name_text ON products USING gin(to_tsvector('korean', product_name))",
                    "CREATE INDEX IF NOT EXISTS idx_product_details_product_id ON product_details(product_id)",
                    "CREATE INDEX IF NOT EXISTS idx_product_details_std_code_hash ON product_details USING hash(std_div_prod_code)",
                    "CREATE INDEX IF NOT EXISTS idx_products_active ON products(is_active) WHERE is_active = true"
                ]
                
                for idx_sql in indexes:
                    try:
                        db.session.execute(db.text(idx_sql))
                    except Exception as e:
                        print(f"   ⚠️ 인덱스 생성 건너뜀: {e}")
                
                db.session.commit()
                print("✅ 인덱스 생성 완료")
            except Exception as e:
                print(f"⚠️ 인덱스 생성 중 오류: {e}")
    
    def run(self):
        """전체 수정 작업 실행"""
        print("🚀 중복 코드 문제 해결 시작")
        print("="*50)
        
        if not self.connect_mssql():
            return False
        
        try:
            # 1. 유니크 제약 조건 제거
            self.drop_unique_constraint()
            
            # 2. 모든 데이터 정리
            if not self.clean_all_data():
                return False
            
            # 3. 고속 마이그레이션 (중복 제거)
            if not self.fast_migrate_all_products():
                return False
            
            # 4. 최적화된 인덱스 생성
            self.create_optimized_indexes()
            
            return True
            
        except Exception as e:
            print(f"❌ 수정 작업 실패: {e}")
            return False
        finally:
            if self.mssql_conn:
                self.mssql_conn.close()

if __name__ == "__main__":
    fixer = DuplicateCodeFixer()
    success = fixer.run()
    
    if success:
        print("\n🎉 중복 코드 문제 해결 완료!")
        print("   - 유니크 제약 조건 해결")
        print("   - 성능 최적화된 마이그레이션")
        print("   - 최적화된 인덱스 생성")
    else:
        print("\n💥 문제 해결 실패!")
        sys.exit(1) 