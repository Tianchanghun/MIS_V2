#!/usr/bin/env python3
"""
MIS v2 데이터베이스 마이그레이션 도구
레거시 MS-SQL에서 PostgreSQL로 안전하게 복제
"""

import pyodbc
import psycopg2
import pandas as pd
from datetime import datetime
import logging
from typing import Dict, List, Any

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DBMigrator:
    def __init__(self):
        # 레거시 MS-SQL 연결 정보 (READ ONLY)
        self.mssql_config = {
            'server': '210.109.96.74,2521',
            'database': 'db_mis',
            'username': 'user_mis',
            'password': 'user_mis!@12',
            'driver': '{ODBC Driver 17 for SQL Server}'
        }
        
        # PostgreSQL 연결 정보 (포트 변경됨: 5433)
        self.postgres_config = {
            'host': 'localhost',
            'port': 5433,
            'database': 'db_mis',
            'username': 'mis_user',
            'password': 'mis123!@#'
        }
        
        # 테이블 매핑 (MS-SQL -> PostgreSQL)
        self.table_mapping = {
            'tbl_category': 'tbl_category',
            'tbl_Member': 'tbl_member',
            'tbl_Department': 'tbl_department', 
            'tbl_MemberAuth': 'tbl_member_auth',
            'tbl_Code': 'tbl_code',
            'tbl_Brand': 'tbl_brand',
            'tbl_Product': 'tbl_product',
            'tbl_Product_Dtl': 'tbl_product_dtl',
            'tbl_TradeMakeShop_Mst': 'tbl_trade_makeshop_mst',
            'tbl_TradeMakeShop_Slv': 'tbl_trade_makeshop_slv',
            'tbl_TradeOrder_Mst': 'tbl_trade_order_mst',
            'tbl_TradeOrder_Slv': 'tbl_trade_order_slv',
            'tbl_Serial': 'tbl_serial',
            'tbl_Api': 'tbl_api',
            'tbl_Customer': 'tbl_customer',
            'tbl_Shop': 'tbl_shop',
            'tbl_AS': 'tbl_as',
            'em_tran': 'em_tran',
            'em_tran_mms': 'em_tran_mms'
        }
        
        # 컬럼 매핑 (CamelCase -> snake_case)
        self.column_mapping = {
            'Seq': 'seq',
            'MenuSeq': 'menu_seq',
            'ParentSeq': 'parent_seq',
            'Depth': 'depth',
            'Sort': 'sort',
            'Icon': 'icon',
            'Name': 'name',
            'Url': 'url',
            'UseWebYn': 'use_web_yn',
            'UseMobYn': 'use_mob_yn',
            'UseLogYn': 'use_log_yn',
            'InsUser': 'ins_user',
            'UptUser': 'upt_user',
            'InsDate': 'ins_date',
            'UptDate': 'upt_date',
            'Id': 'id',
            'Password': 'password',
            'DeptSeq': 'dept_seq',
            'SuperUser': 'super_user',
            'UseYn': 'use_yn',
            'DeptName': 'dept_name',
            'CreateYn': 'create_yn',
            'ReadYn': 'read_yn',
            'UpdateYn': 'update_yn',
            'DeleteYn': 'delete_yn',
            'MemberSeq': 'member_seq',
            'PrdSeq': 'prd_seq',
            'SerialNumber': 'serial_number',
            'SerialCreateYn': 'serial_create_yn',
            'SerialCreateCnt': 'serial_create_cnt'
        }

    def connect_mssql(self):
        """MS-SQL 연결 (읽기 전용)"""
        try:
            conn_string = (
                f"DRIVER={self.mssql_config['driver']};"
                f"SERVER={self.mssql_config['server']};"
                f"DATABASE={self.mssql_config['database']};"
                f"UID={self.mssql_config['username']};"
                f"PWD={self.mssql_config['password']};"
                f"ApplicationIntent=ReadOnly;"
            )
            conn = pyodbc.connect(conn_string)
            logger.info("MS-SQL 연결 성공 (읽기 전용)")
            return conn
        except Exception as e:
            logger.error(f"MS-SQL 연결 실패: {e}")
            return None

    def connect_postgres(self):
        """PostgreSQL 연결"""
        try:
            conn = psycopg2.connect(
                host=self.postgres_config['host'],
                port=self.postgres_config['port'],
                database=self.postgres_config['database'],
                user=self.postgres_config['username'],
                password=self.postgres_config['password']
            )
            logger.info("PostgreSQL 연결 성공")
            return conn
        except Exception as e:
            logger.error(f"PostgreSQL 연결 실패: {e}")
            return None

    def get_table_schema(self, mssql_conn, table_name: str) -> Dict:
        """MS-SQL 테이블 스키마 조회"""
        try:
            query = f"""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                CHARACTER_MAXIMUM_LENGTH,
                NUMERIC_PRECISION,
                NUMERIC_SCALE
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
            """
            df = pd.read_sql(query, mssql_conn)
            return df.to_dict('records')
        except Exception as e:
            logger.error(f"테이블 스키마 조회 실패 ({table_name}): {e}")
            return []

    def migrate_table_data(self, mssql_conn, postgres_conn, mssql_table: str, postgres_table: str):
        """테이블 데이터 마이그레이션"""
        try:
            logger.info(f"테이블 마이그레이션 시작: {mssql_table} -> {postgres_table}")
            
            # MS-SQL에서 데이터 조회
            query = f"SELECT * FROM {mssql_table}"
            df = pd.read_sql(query, mssql_conn)
            
            if df.empty:
                logger.warning(f"테이블이 비어있음: {mssql_table}")
                return 0
            
            # 컬럼명 변환 (CamelCase -> snake_case)
            for old_col, new_col in self.column_mapping.items():
                if old_col in df.columns:
                    df.rename(columns={old_col: new_col}, inplace=True)
            
            logger.info(f"조회된 레코드 수: {len(df)}")
            
            # PostgreSQL에 기존 데이터 삭제 (TRUNCATE)
            cursor = postgres_conn.cursor()
            cursor.execute(f"TRUNCATE TABLE {postgres_table} RESTART IDENTITY CASCADE")
            postgres_conn.commit()
            
            # 데이터 삽입 (배치 처리)
            batch_size = 1000
            total_inserted = 0
            
            for i in range(0, len(df), batch_size):
                batch_df = df.iloc[i:i+batch_size]
                
                # pandas to_sql 사용하여 삽입
                batch_df.to_sql(
                    postgres_table, 
                    postgres_conn, 
                    if_exists='append', 
                    index=False,
                    method='multi'
                )
                
                total_inserted += len(batch_df)
                logger.info(f"진행률: {total_inserted}/{len(df)} ({total_inserted/len(df)*100:.1f}%)")
            
            postgres_conn.commit()
            logger.info(f"테이블 마이그레이션 완료: {mssql_table} ({total_inserted}건)")
            return total_inserted
            
        except Exception as e:
            logger.error(f"테이블 마이그레이션 실패 ({mssql_table}): {e}")
            postgres_conn.rollback()
            return 0

    def verify_migration(self, postgres_conn):
        """마이그레이션 검증"""
        try:
            logger.info("마이그레이션 검증 시작")
            cursor = postgres_conn.cursor()
            
            # 각 테이블별 레코드 수 확인
            verification_results = {}
            
            for postgres_table in self.table_mapping.values():
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {postgres_table}")
                    count = cursor.fetchone()[0]
                    verification_results[postgres_table] = count
                    logger.info(f"{postgres_table}: {count}건")
                except Exception as e:
                    logger.warning(f"테이블 검증 실패 ({postgres_table}): {e}")
                    verification_results[postgres_table] = -1
            
            # 시리얼 번호 샘플 확인
            try:
                cursor.execute("SELECT serial_number FROM tbl_serial LIMIT 5")
                serials = cursor.fetchall()
                logger.info("시리얼 번호 샘플:")
                for serial in serials:
                    logger.info(f"  - {serial[0]}")
            except Exception as e:
                logger.warning(f"시리얼 번호 샘플 확인 실패: {e}")
            
            return verification_results
            
        except Exception as e:
            logger.error(f"마이그레이션 검증 실패: {e}")
            return {}

    def run_migration(self):
        """마이그레이션 실행"""
        logger.info("=== MIS v2 데이터베이스 마이그레이션 시작 ===")
        
        # 연결 설정
        mssql_conn = self.connect_mssql()
        postgres_conn = self.connect_postgres()
        
        if not mssql_conn or not postgres_conn:
            logger.error("데이터베이스 연결 실패")
            return False
        
        try:
            # 테이블별 마이그레이션 실행
            migration_results = {}
            
            for mssql_table, postgres_table in self.table_mapping.items():
                count = self.migrate_table_data(mssql_conn, postgres_conn, mssql_table, postgres_table)
                migration_results[postgres_table] = count
            
            # 검증
            verification_results = self.verify_migration(postgres_conn)
            
            # 결과 출력
            logger.info("\n=== 마이그레이션 결과 ===")
            total_records = 0
            for table, count in migration_results.items():
                if count > 0:
                    total_records += count
                logger.info(f"{table}: {count}건")
            
            logger.info(f"\n총 마이그레이션 레코드 수: {total_records}건")
            logger.info("=== 마이그레이션 완료 ===")
            
            return True
            
        except Exception as e:
            logger.error(f"마이그레이션 실행 중 오류: {e}")
            return False
            
        finally:
            if mssql_conn:
                mssql_conn.close()
            if postgres_conn:
                postgres_conn.close()

if __name__ == "__main__":
    migrator = DBMigrator()
    success = migrator.run_migration()
    
    if success:
        print("\n✅ 마이그레이션이 성공적으로 완료되었습니다!")
        print("📝 로그 파일 'migration.log'에서 상세 내용을 확인할 수 있습니다.")
        print("🔗 pgAdmin: http://localhost:5051 (admin@mis.co.kr / admin123!@#)")
    else:
        print("\n❌ 마이그레이션이 실패했습니다.")
        print("📝 'migration.log' 파일에서 오류 내용을 확인하세요.") 