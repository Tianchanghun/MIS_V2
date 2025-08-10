#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
레거시 MS SQL 상품 데이터 완전 마이그레이션
- 올바른 DB 정보 사용
- 기존 마이그레이션된 코드 체계 활용
- 16자리 자가코드 생성 로직 구현
- 색상별 모델 관리 시스템 구축
"""

import os
import sys
import pyodbc
from datetime import datetime
from app import create_app
from app.common.models import db, Company, Code, Product, ProductDetail

# 올바른 MS SQL 연결 정보
MSSQL_CONFIG = {
    'server': '210.109.96.74,2521',
    'database': 'db_mis',
    'username': 'user_mis',
    'password': 'user_mis!@12',
    'driver': '{ODBC Driver 17 for SQL Server}'
}

class LegacyProductMigrator:
    """레거시 상품 데이터 마이그레이션"""
    
    def __init__(self):
        self.app = create_app()
        self.mssql_conn = None
        self.stats = {
            'total_legacy_products': 0,
            'migrated_products': 0,
            'migrated_models': 0,
            'skipped_products': 0,
            'errors': []
        }
        
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
    
    def generate_std_product_code(self, brand_code, div_type, prod_group, prod_type, prod_code, prod_type2, year, color):
        """16자리 자가코드 생성 (레거시 로직 기반)"""
        # 레거시 로직: BrandCode(2) + DivTypeCode(1) + ? + ProdGroupCode(2) + ProdTypeCode(2) + ProdCode(2) + ProdType2Code(2) + ??(2) + ProdColorCode(3)
        
        # 각 부분을 정규화
        brand_part = str(brand_code)[:2].ljust(2, '0')
        div_part = str(div_type)[:1]
        gap1 = '0'  # 고정값
        group_part = str(prod_group)[:2].ljust(2, '0')
        type_part = str(prod_type)[:2].ljust(2, '0')
        code_part = str(prod_code)[:2].ljust(2, '0')
        type2_part = str(prod_type2)[:2].ljust(2, '0')
        gap2 = '00'  # 고정값
        color_part = str(color)[:3].ljust(3, '0')
        
        std_code = f"{brand_part}{div_part}{gap1}{group_part}{type_part}{code_part}{type2_part}{gap2}{color_part}"
        return std_code[:16]  # 16자리로 제한
    
    def find_code_seq_by_legacy_mapping(self, legacy_seq, legacy_code):
        """레거시 seq/code를 현재 코드 체계로 매핑"""
        with self.app.app_context():
            # seq로 먼저 찾기
            code = Code.query.filter_by(seq=legacy_seq).first()
            if code:
                return code.seq
            
            # code로 찾기 (fallback)
            if legacy_code:
                code = Code.query.filter_by(code=legacy_code).first()
                if code:
                    return code.seq
            
            return None
    
    def migrate_legacy_products(self):
        """레거시 상품 데이터 마이그레이션"""
        if not self.mssql_conn:
            print("❌ MS SQL 연결이 필요합니다")
            return
            
        with self.app.app_context():
            # 기존 상품 데이터 안전하게 정리 (외래키 순서 고려)
            print("🗑️  기존 상품 데이터 정리...")
            try:
                # 1. ProductHistory 먼저 삭제 (외래키 참조)
                from app.common.models import ProductHistory
                ProductHistory.query.delete()
                
                # 2. ProductDetail 삭제
                ProductDetail.query.delete()
                
                # 3. Product 삭제 
                Product.query.delete()
                
                db.session.commit()
                print("✅ 기존 데이터 정리 완료")
            except Exception as e:
                print(f"⚠️ 기존 데이터 정리 중 오류: {e}")
                # 개별 삭제 시도
                try:
                    # 모든 데이터를 개별적으로 삭제
                    for product in Product.query.all():
                        # 연관된 이력 먼저 삭제
                        ProductHistory.query.filter_by(product_id=product.id).delete()
                        # 연관된 상세 삭제
                        ProductDetail.query.filter_by(product_id=product.id).delete()
                        # 상품 삭제
                        db.session.delete(product)
                    db.session.commit()
                    print("✅ 개별 삭제로 정리 완료")
                except Exception as e2:
                    print(f"❌ 개별 삭제도 실패: {e2}")
                    # 기존 데이터를 유지하고 업데이트 방식으로 변경
                    print("🔄 기존 데이터 유지하고 업데이트 방식으로 진행")
            
            cursor = self.mssql_conn.cursor()
            
            # 레거시 상품 마스터 조회
            master_query = """
            SELECT 
                p.Seq, p.Company, p.Brand, p.ProdGroup, p.ProdType,
                p.ProdName, p.ProdTagAmt, p.ProdYear, p.UseYn,
                p.InsDate, p.InsUser, p.ProdInfo, p.FaqYn, p.ShowYn,
                -- 코드명 조회
                c1.CodeName as CompanyName, c1.Code as CompanyCode,
                c2.CodeName as BrandName, c2.Code as BrandCode,
                c3.CodeName as ProdGroupName, c3.Code as ProdGroupCode,
                c4.CodeName as ProdTypeName, c4.Code as ProdTypeCode
            FROM tbl_Product p
            LEFT JOIN tbl_Code c1 ON p.Company = c1.Seq
            LEFT JOIN tbl_Code c2 ON p.Brand = c2.Seq  
            LEFT JOIN tbl_Code c3 ON p.ProdGroup = c3.Seq
            LEFT JOIN tbl_Code c4 ON p.ProdType = c4.Seq
            WHERE p.UseYn = 'Y'
            ORDER BY p.Seq
            """
            
            cursor.execute(master_query)
            legacy_products = cursor.fetchall()
            self.stats['total_legacy_products'] = len(legacy_products)
            
            print(f"📦 레거시 상품 {self.stats['total_legacy_products']}개 발견")
            
            for row in legacy_products:
                try:
                    # 기존 상품이 있는지 확인 (legacy_seq 기준)
                    existing_product = Product.query.filter_by(legacy_seq=row.Seq).first()
                    
                    # 회사 ID 매핑 (에이원=1, 에이원월드=2로 고정)
                    company_id = 1  # 기본적으로 에이원
                    if row.CompanyCode and 'A2' in row.CompanyCode:
                        company_id = 2  # 에이원 월드
                    
                    # 코드 seq 매핑
                    brand_code_seq = self.find_code_seq_by_legacy_mapping(row.Brand, row.BrandCode)
                    category_code_seq = self.find_code_seq_by_legacy_mapping(row.ProdGroup, row.ProdGroupCode)
                    type_code_seq = self.find_code_seq_by_legacy_mapping(row.ProdType, row.ProdTypeCode)
                    
                    if existing_product:
                        # 기존 상품 업데이트
                        existing_product.company_id = company_id
                        existing_product.brand_code_seq = brand_code_seq
                        existing_product.category_code_seq = category_code_seq
                        existing_product.type_code_seq = type_code_seq
                        existing_product.product_name = row.ProdName
                        existing_product.price = row.ProdTagAmt or 0
                        existing_product.description = row.ProdInfo
                        existing_product.is_active = (row.UseYn == 'Y')
                        existing_product.updated_by = 'legacy_migration'
                        product = existing_product
                    else:
                        # 새 상품 생성
                        product = Product(
                            company_id=company_id,
                            brand_code_seq=brand_code_seq,
                            category_code_seq=category_code_seq,
                            type_code_seq=type_code_seq,
                            product_name=row.ProdName,
                            price=row.ProdTagAmt or 0,
                            description=row.ProdInfo,
                            is_active=(row.UseYn == 'Y'),
                            legacy_seq=row.Seq,  # 레거시 연결
                            created_at=row.InsDate,
                            created_by=row.InsUser
                        )
                        
                        db.session.add(product)
                    
                    db.session.flush()  # ID 생성
                    
                    # 기존 상세 모델 삭제 (해당 상품의)
                    ProductDetail.query.filter_by(product_id=product.id).delete()
                    
                    # 상세 모델 조회 및 생성
                    detail_query = """
                    SELECT 
                        d.Seq, d.MstSeq, d.BrandCode, d.DivTypeCode,
                        d.ProdGroupCode, d.ProdTypeCode, d.ProdCode, d.ProdType2Code,
                        d.YearCode, d.ProdColorCode, d.StdDivProdCode, d.ProductName,
                        d.Status
                    FROM tbl_Product_DTL d
                    WHERE d.MstSeq = ? AND d.Status = 'Active'
                    """
                    
                    cursor.execute(detail_query, row.Seq)
                    details = cursor.fetchall()
                    
                    for detail in details:
                        # 16자리 자가코드 생성
                        std_code = self.generate_std_product_code(
                            detail.BrandCode, detail.DivTypeCode,
                            detail.ProdGroupCode, detail.ProdTypeCode,
                            detail.ProdCode, detail.ProdType2Code,
                            detail.YearCode, detail.ProdColorCode
                        )
                        
                        # ProductDetail 생성
                        product_detail = ProductDetail(
                            product_id=product.id,
                            brand_code=detail.BrandCode[:2] if detail.BrandCode else '',
                            div_type_code=detail.DivTypeCode[:1] if detail.DivTypeCode else '',
                            prod_group_code=detail.ProdGroupCode[:2] if detail.ProdGroupCode else '',
                            prod_type_code=detail.ProdTypeCode[:2] if detail.ProdTypeCode else '',
                            prod_code=detail.ProdCode[:2] if detail.ProdCode else '',
                            prod_type2_code=detail.ProdType2Code[:2] if detail.ProdType2Code else '',
                            year_code=str(detail.YearCode)[:1] if detail.YearCode else '',  # 1자리로 제한
                            color_code=detail.ProdColorCode[:3] if detail.ProdColorCode else '',
                            std_div_prod_code=std_code,  # 새 16자리 코드
                            product_name=detail.ProductName,
                            status=detail.Status,
                            legacy_seq=detail.Seq  # 레거시 연결
                        )
                        
                        db.session.add(product_detail)
                        self.stats['migrated_models'] += 1
                    
                    self.stats['migrated_products'] += 1
                    
                    if self.stats['migrated_products'] % 50 == 0:
                        db.session.commit()
                        print(f"   진행률: {self.stats['migrated_products']}/{self.stats['total_legacy_products']}")
                        
                except Exception as e:
                    self.stats['errors'].append(f"상품 {row.Seq}: {str(e)}")
                    self.stats['skipped_products'] += 1
                    db.session.rollback()
                    continue
            
            db.session.commit()
            print("✅ 레거시 상품 마이그레이션 완료")
    
    def migrate_code_mappings(self):
        """코드 매핑 테이블 마이그레이션 (현재는 로그만)"""
        if not self.mssql_conn:
            return
            
        with self.app.app_context():
            cursor = self.mssql_conn.cursor()
            
            try:
                # 레거시 코드 매핑 조회
                mapping_query = """
                SELECT 
                    cm.Seq, cm.BrandCode, cm.ProdCode, cm.ErpiaCode, 
                    cm.DouzoneCode, cm.ProdName, cm.InsUser, cm.InsDate
                FROM tbl_Product_CodeMatch cm
                ORDER BY cm.Seq
                """
                
                cursor.execute(mapping_query)
                mappings = cursor.fetchall()
                
                print(f"🔗 코드 매핑 {len(mappings)}개 발견:")
                
                # 처음 10개만 출력
                for mapping in mappings[:10]:
                    print(f"   매핑: {mapping.ProdCode} → ERPia: {mapping.ErpiaCode}, 더존: {mapping.DouzoneCode}")
                
                if len(mappings) > 10:
                    print(f"   ... 외 {len(mappings)-10}개 더")
                    
            except Exception as e:
                print(f"⚠️ 코드 매핑 조회 실패: {e}")
    
    def print_migration_summary(self):
        """마이그레이션 결과 요약"""
        print("\n" + "="*60)
        print("📊 레거시 상품 마이그레이션 완료 결과")
        print("="*60)
        print(f"📦 총 레거시 상품: {self.stats['total_legacy_products']:,}개")
        print(f"✅ 마이그레이션된 상품: {self.stats['migrated_products']:,}개")
        print(f"🎨 마이그레이션된 모델: {self.stats['migrated_models']:,}개")
        print(f"⏭️  건너뛴 상품: {self.stats['skipped_products']:,}개")
        
        if self.stats['errors']:
            print(f"❌ 오류 발생: {len(self.stats['errors'])}건")
            for error in self.stats['errors'][:3]:  # 최대 3개만 표시
                print(f"   - {error}")
            if len(self.stats['errors']) > 3:
                print(f"   ... 외 {len(self.stats['errors'])-3}건 더")
        
        print("="*60)
    
    def run(self):
        """전체 마이그레이션 실행"""
        print("🚀 레거시 상품 데이터 완전 마이그레이션 시작")
        print("="*60)
        
        if not self.connect_mssql():
            return False
        
        try:
            # 1단계: 상품 데이터 마이그레이션  
            self.migrate_legacy_products()
            
            # 2단계: 코드 매핑 마이그레이션
            self.migrate_code_mappings()
            
            # 3단계: 결과 출력
            self.print_migration_summary()
            
            return True
            
        except Exception as e:
            print(f"❌ 마이그레이션 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if self.mssql_conn:
                self.mssql_conn.close()

if __name__ == "__main__":
    migrator = LegacyProductMigrator()
    success = migrator.run()
    
    if success:
        print("\n🎉 레거시 상품 마이그레이션이 성공적으로 완료되었습니다!")
        print("   - 올바른 레거시 DB 연결 사용")
        print("   - 기존 코드 체계 활용")
        print("   - 16자리 자가코드 생성 로직 구현")
        print("   - 색상별 모델 관리 시스템 구축")
        print("   - 레거시 연결 정보 보존")
    else:
        print("\n💥 마이그레이션 실패!")
        sys.exit(1) 