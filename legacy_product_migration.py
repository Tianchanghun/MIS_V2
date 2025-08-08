#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
레거시 상품 데이터 마이그레이션 스크립트
- tbl_Product (마스터) → products 테이블
- tbl_Product_DTL (상세) → 코드 매핑으로 처리
- 안전한 UPSERT 방식 사용
"""
import pyodbc
import logging
from datetime import datetime
from app import create_app
from app.common.models import db, Product, ProductHistory, Code, Company, Brand

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('legacy_product_migration.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LegacyProductMigration:
    def __init__(self):
        self.app = create_app()
        self.legacy_conn = None
        self.migrated_count = 0
        self.error_count = 0
        self.skipped_count = 0
        
    def connect_to_legacy_db(self):
        """레거시 MS-SQL 데이터베이스 연결"""
        connection_strings = [
            # 실제 레거시 DB 서버 (.env_fixed 정보 기반)
            "DRIVER={ODBC Driver 17 for SQL Server};SERVER=210.109.96.74,2521;DATABASE=db_mis;UID=user_mis;PWD=user_mis!@12;ApplicationIntent=ReadOnly;",
            # Docker MS-SQL (백업)
            "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost,1433;DATABASE=db_mis;UID=sa;PWD=YourStrong@Passw0rd;",
            # 로컬 SQL Server Express (통합 인증)
            "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=db_mis;Trusted_Connection=yes;",
            # 로컬 SQL Server 기본 인스턴스 (통합 인증)
            "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=db_mis;Trusted_Connection=yes;",
        ]
        
        for i, conn_str in enumerate(connection_strings, 1):
            try:
                logger.info(f"레거시 DB 연결 시도 {i}")
                self.legacy_conn = pyodbc.connect(conn_str, timeout=10)
                logger.info(f"✅ 레거시 DB 연결 성공: 방식 {i}")
                return True
            except Exception as e:
                logger.warning(f"연결 방식 {i} 실패: {str(e)[:100]}...")
                continue
        
        logger.error("❌ 모든 레거시 DB 연결 방식 실패")
        return False
    
    def fetch_legacy_products(self):
        """레거시 상품 데이터 조회"""
        if not self.legacy_conn:
            logger.error("레거시 DB 연결이 없습니다.")
            return []
        
        try:
            cursor = self.legacy_conn.cursor()
            
            # 레거시 상품 마스터 조회 (회사, 브랜드, 분류 정보 포함)
            query = """
            SELECT 
                p.Seq,
                p.Company,
                p.Brand,
                p.ProdGroup,
                p.ProdType,
                p.ProdYear,
                p.ProdName,
                p.ProdTagAmt,
                p.ProdManual,
                p.ProdInfo,
                p.UseYn,
                p.InsDate,
                p.InsUser,
                p.UptDate,
                p.UptUser,
                -- 회사명
                c_comp.CodeName as CompanyName,
                -- 브랜드명  
                c_brand.CodeName as BrandName,
                c_brand.Code as BrandCode,
                -- 품목명
                c_group.CodeName as ProdGroupName,
                c_group.Code as ProdGroupCode,
                -- 타입명
                c_type.CodeName as ProdTypeName,
                c_type.Code as ProdTypeCode
            FROM tbl_Product p
            LEFT JOIN tbl_Code c_comp ON p.Company = c_comp.Seq
            LEFT JOIN tbl_Code c_brand ON p.Brand = c_brand.Seq  
            LEFT JOIN tbl_Code c_group ON p.ProdGroup = c_group.Seq
            LEFT JOIN tbl_Code c_type ON p.ProdType = c_type.Seq
            WHERE p.UseYn = 'Y'
            ORDER BY p.Company, p.InsDate DESC
            """
            
            cursor.execute(query)
            products = cursor.fetchall()
            
            logger.info(f"📊 레거시에서 {len(products)}개 상품 조회 완료")
            
            # 딕셔너리 형태로 변환
            columns = [desc[0] for desc in cursor.description]
            product_list = []
            
            for row in products:
                product_dict = dict(zip(columns, row))
                product_list.append(product_dict)
            
            return product_list
            
        except Exception as e:
            logger.error(f"❌ 레거시 상품 조회 실패: {e}")
            return []
    
    def map_company_id(self, legacy_company_seq, company_name):
        """레거시 회사 코드 → MIS v2 company_id 매핑"""
        company_mapping = {
            # 레거시 회사 시퀀스 → MIS v2 ID
            580: 1,  # 에이원 → 1
            581: 2,  # 에이원월드 → 2 (예상)
        }
        
        # 시퀀스 기반 매핑 우선
        if legacy_company_seq in company_mapping:
            return company_mapping[legacy_company_seq]
        
        # 회사명 기반 매핑
        if company_name:
            if '에이원' in company_name and '월드' not in company_name:
                return 1  # 에이원
            elif '월드' in company_name or 'world' in company_name.lower():
                return 2  # 에이원월드
        
        # 기본값: 에이원
        return 1
    
    def find_brand_seq(self, legacy_brand_code, brand_name):
        """레거시 브랜드 → MIS v2 brand_seq 매핑"""
        try:
            # 브랜드 코드로 매핑
            if legacy_brand_code:
                brand = Brand.query.filter_by(brand_code=legacy_brand_code).first()
                if brand:
                    return brand.seq
            
            # 브랜드명으로 매핑
            if brand_name:
                brand = Brand.query.filter_by(brand_name=brand_name).first()
                if brand:
                    return brand.seq
                
                # 부분 매칭
                brand = Brand.query.filter(Brand.brand_name.like(f'%{brand_name}%')).first()
                if brand:
                    return brand.seq
            
            return None
            
        except Exception as e:
            logger.warning(f"브랜드 매핑 실패: {e}")
            return None
    
    def find_code_seq(self, legacy_code, code_name, group_name):
        """레거시 코드 → MIS v2 code_seq 매핑"""
        try:
            # 그룹별 코드 매핑
            if group_name == '품목':
                codes = Code.get_codes_by_group_name('품목')
            elif group_name == '타입':
                codes = Code.get_codes_by_group_name('타입')
            else:
                return None
            
            # 코드로 매핑
            for code in codes:
                if code['code'] == legacy_code:
                    return code['seq']
            
            # 코드명으로 매핑
            for code in codes:
                if code['code_name'] == code_name:
                    return code['seq']
            
            return None
            
        except Exception as e:
            logger.warning(f"코드 매핑 실패 ({group_name}): {e}")
            return None
    
    def migrate_product(self, legacy_product):
        """개별 상품 마이그레이션"""
        try:
            with self.app.app_context():
                # 회사 매핑
                company_id = self.map_company_id(
                    legacy_product['Company'], 
                    legacy_product['CompanyName']
                )
                
                # 브랜드 매핑
                brand_seq = self.find_brand_seq(
                    legacy_product['BrandCode'],
                    legacy_product['BrandName']
                )
                
                # 품목 매핑
                category_code_seq = self.find_code_seq(
                    legacy_product['ProdGroupCode'],
                    legacy_product['ProdGroupName'],
                    '품목'
                )
                
                # 타입 매핑
                type_code_seq = self.find_code_seq(
                    legacy_product['ProdTypeCode'],
                    legacy_product['ProdTypeName'],
                    '타입'
                )
                
                # 상품코드 생성 (레거시 Seq 기반)
                product_code = f"LEG_{legacy_product['Seq']:06d}"
                
                # 기존 상품 확인 (상품명 + 회사 기준)
                existing_product = Product.query.filter_by(
                    company_id=company_id,
                    product_name=legacy_product['ProdName']
                ).first()
                
                if existing_product:
                    # 기존 상품 업데이트
                    existing_product.brand_seq = brand_seq
                    existing_product.category_code_seq = category_code_seq
                    existing_product.type_code_seq = type_code_seq
                    existing_product.product_code = product_code
                    existing_product.product_year = legacy_product['ProdYear']
                    existing_product.price = legacy_product['ProdTagAmt'] or 0
                    existing_product.description = legacy_product['ProdInfo']
                    existing_product.manual_file_path = legacy_product['ProdManual']
                    existing_product.is_active = legacy_product['UseYn'] == 'Y'
                    existing_product.updated_by = 'legacy_migration'
                    existing_product.updated_at = datetime.utcnow()
                    
                    action = 'UPDATE'
                    product = existing_product
                    
                else:
                    # 신규 상품 생성
                    product = Product(
                        company_id=company_id,
                        brand_seq=brand_seq,
                        category_code_seq=category_code_seq,
                        type_code_seq=type_code_seq,
                        product_name=legacy_product['ProdName'],
                        product_code=product_code,
                        product_year=legacy_product['ProdYear'],
                        price=legacy_product['ProdTagAmt'] or 0,
                        description=legacy_product['ProdInfo'],
                        manual_file_path=legacy_product['ProdManual'],
                        is_active=legacy_product['UseYn'] == 'Y',
                        created_by='legacy_migration',
                        updated_by='legacy_migration'
                    )
                    
                    db.session.add(product)
                    action = 'INSERT'
                
                db.session.commit()
                
                # 히스토리 기록
                history = ProductHistory(
                    product_id=product.id,
                    action=f'LEGACY_{action}',
                    new_values={
                        'legacy_seq': legacy_product['Seq'],
                        'legacy_company': legacy_product['CompanyName'],
                        'legacy_brand': legacy_product['BrandName'],
                        'migrated_at': datetime.utcnow().isoformat()
                    },
                    created_by='legacy_migration'
                )
                db.session.add(history)
                db.session.commit()
                
                self.migrated_count += 1
                logger.info(f"✅ {action}: {legacy_product['ProdName']} (레거시 seq: {legacy_product['Seq']})")
                
        except Exception as e:
            db.session.rollback()
            self.error_count += 1
            logger.error(f"❌ 상품 마이그레이션 실패: {legacy_product.get('ProdName', 'Unknown')} - {e}")
    
    def run_migration(self):
        """마이그레이션 실행"""
        logger.info("🚀 레거시 상품 데이터 마이그레이션 시작")
        
        # 레거시 DB 연결
        if not self.connect_to_legacy_db():
            logger.error("❌ 레거시 DB 연결 실패로 마이그레이션 중단")
            return False
        
        # 레거시 상품 데이터 조회
        legacy_products = self.fetch_legacy_products()
        if not legacy_products:
            logger.warning("⚠️ 마이그레이션할 레거시 상품이 없습니다.")
            return False
        
        logger.info(f"📊 총 {len(legacy_products)}개 상품 마이그레이션 시작")
        
        # 상품별 마이그레이션
        for i, product in enumerate(legacy_products, 1):
            logger.info(f"🔄 진행률: {i}/{len(legacy_products)} ({i/len(legacy_products)*100:.1f}%)")
            self.migrate_product(product)
        
        # 마이그레이션 완료
        logger.info("=" * 60)
        logger.info("🎉 레거시 상품 데이터 마이그레이션 완료!")
        logger.info(f"✅ 성공: {self.migrated_count}개")
        logger.info(f"❌ 실패: {self.error_count}개")
        logger.info(f"⏭️ 건너뜀: {self.skipped_count}개")
        logger.info("=" * 60)
        
        # 연결 종료
        if self.legacy_conn:
            self.legacy_conn.close()
        
        return True

if __name__ == "__main__":
    migration = LegacyProductMigration()
    migration.run_migration() 