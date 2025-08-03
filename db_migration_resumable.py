#!/usr/bin/env python3
"""
MIS v2 재개 가능한 데이터베이스 마이그레이션 도구
레거시 MS-SQL에서 PostgreSQL로 안전하게 복제
- 필드 구조 호환성 검증
- 대용량 데이터 배치 처리
- 중단된 지점에서 재개 기능
- 완전 자동화
- PostgreSQL 최적화
"""

import pyodbc
import psycopg2
import psycopg2.extras
import pandas as pd
from datetime import datetime
import logging
import os
import json
from typing import Dict, List, Any, Tuple
import time
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration_resumable.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ResumableDBMigrator:
    def __init__(self):
        # 레거시 MS-SQL 연결 정보 (READ ONLY)
        self.mssql_config = {
            'server': os.getenv('LEGACY_DB_SERVER', '210.109.96.74,2521'),
            'database': os.getenv('LEGACY_DB_NAME', 'db_mis'),
            'username': os.getenv('LEGACY_DB_USER', 'user_mis'),
            'password': os.getenv('LEGACY_DB_PASSWORD', 'user_mis!@12'),
            'driver': '{ODBC Driver 17 for SQL Server}'
        }
        
        # PostgreSQL 연결 정보
        self.postgres_config = {
            'host': 'localhost',
            'port': 5433,
            'database': 'db_mis',
            'user': 'mis_user',
            'password': 'mis123!@#'
        }
        
        # 배치 처리 설정
        self.batch_size = 500  # 안전한 배치 크기
        self.max_retries = 3
        self.retry_delay = 2
        
        # 진행 상태 파일
        self.progress_file = 'migration_progress.json'
        self.completed_tables = set()
        
        # 테이블 우선순위 (의존성 순서)
        self.table_priority = [
            'tbl_department',
            'tbl_member', 
            'tbl_category',
            'tbl_member_auth',
            'tbl_brand',
            'tbl_code_group',
            'tbl_code',
            'tbl_product',
            'tbl_shop',
            'tbl_customer',
            'tbl_as',
            'tbl_makeshop',
            'tbl_po',
            'tbl_serial',
            'tbl_demurrage',
            'tbl_container',
            'tbl_distribution',
            'tbl_pallet',
            'tbl_scheduler',
            'tbl_sales_report',
            'tbl_channel_analysis',
            'tbl_monitoring',
            'tbl_visit_log',
            'tbl_sms_log',
            'tbl_email_log',
            'tbl_inventory',
            'tbl_price_info',
            'tbl_targeting',
            'tbl_warehouse',
            'tbl_batch_job'
        ]

    def load_progress(self):
        """이전 진행 상태 로드"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                    self.completed_tables = set(progress_data.get('completed_tables', []))
                    logger.info(f"📋 이전 진행 상태 로드: {len(self.completed_tables)}개 테이블 완료")
                    if self.completed_tables:
                        logger.info(f"✅ 완료된 테이블: {', '.join(sorted(self.completed_tables))}")
                    return True
            else:
                logger.info("🆕 새로운 마이그레이션 시작")
                return False
        except Exception as e:
            logger.warning(f"진행 상태 로드 실패: {e}")
            return False

    def save_progress(self, completed_table: str = None):
        """진행 상태 저장"""
        try:
            if completed_table:
                self.completed_tables.add(completed_table)
            
            progress_data = {
                'completed_tables': list(self.completed_tables),
                'last_updated': datetime.now().isoformat(),
                'total_tables': len(self.table_priority),
                'remaining_tables': len(self.table_priority) - len(self.completed_tables)
            }
            
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.warning(f"진행 상태 저장 실패: {e}")

    def get_remaining_tables(self) -> List[str]:
        """남은 테이블 목록 반환"""
        return [table for table in self.table_priority if table not in self.completed_tables]

    def check_table_completion_status(self, postgres_conn) -> Dict[str, bool]:
        """PostgreSQL에서 각 테이블의 완료 상태 확인"""
        completion_status = {}
        
        for table_name in self.table_priority:
            try:
                count = self.get_table_record_count(postgres_conn, table_name.lower(), False)
                completion_status[table_name] = count > 0
                if count > 0:
                    logger.info(f"✅ {table_name}: {count:,}건 (완료됨)")
                else:
                    logger.info(f"⏳ {table_name}: 미완료")
            except Exception as e:
                completion_status[table_name] = False
                logger.warning(f"⚠️ {table_name}: 상태 확인 실패 - {e}")
        
        return completion_status

    def connect_mssql(self):
        """MS-SQL 연결 (READ ONLY)"""
        try:
            conn_str = (
                f"DRIVER={self.mssql_config['driver']};"
                f"SERVER={self.mssql_config['server']};"
                f"DATABASE={self.mssql_config['database']};"
                f"UID={self.mssql_config['username']};"
                f"PWD={self.mssql_config['password']};"
                f"ApplicationIntent=ReadOnly;"
                f"TrustServerCertificate=yes;"
            )
            conn = pyodbc.connect(conn_str)
            logger.info("MS-SQL 연결 성공 (읽기 전용)")
            return conn
        except Exception as e:
            logger.error(f"MS-SQL 연결 실패: {e}")
            return None

    def connect_postgres(self):
        """PostgreSQL 연결"""
        try:
            conn = psycopg2.connect(**self.postgres_config)
            conn.autocommit = False
            logger.info("PostgreSQL 연결 성공")
            return conn
        except Exception as e:
            logger.error(f"PostgreSQL 연결 실패: {e}")
            return None

    def get_table_schema(self, mssql_conn, table_name: str) -> List[Dict]:
        """테이블 스키마 정보 조회"""
        try:
            query = """
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                CHARACTER_MAXIMUM_LENGTH,
                NUMERIC_PRECISION,
                NUMERIC_SCALE,
                IS_NULLABLE,
                COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
            """
            cursor = mssql_conn.cursor()
            cursor.execute(query, table_name)
            columns = cursor.fetchall()
            
            schema_info = []
            for col in columns:
                schema_info.append({
                    'column_name': col[0],
                    'data_type': col[1],
                    'max_length': col[2],
                    'precision': col[3],
                    'scale': col[4],
                    'is_nullable': col[5],
                    'default_value': col[6]
                })
            
            return schema_info
        except Exception as e:
            logger.error(f"스키마 조회 실패 ({table_name}): {e}")
            return []

    def verify_table_compatibility(self, mssql_conn, postgres_conn, table_name: str) -> bool:
        """테이블 호환성 검증"""
        try:
            # MS-SQL 스키마 조회
            mssql_schema = self.get_table_schema(mssql_conn, table_name)
            if not mssql_schema:
                logger.warning(f"MS-SQL 테이블이 존재하지 않음: {table_name}")
                return False
                
            # PostgreSQL 테이블 존재 확인
            pg_cursor = postgres_conn.cursor()
            pg_cursor.execute("""
                SELECT column_name, data_type, character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table_name.lower(),))
            
            pg_columns = pg_cursor.fetchall()
            if not pg_columns:
                logger.warning(f"PostgreSQL 테이블이 존재하지 않음: {table_name}")
                return False
            
            logger.info(f"테이블 호환성 검증 완료: {table_name}")
            logger.info(f"MS-SQL 컬럼 수: {len(mssql_schema)}, PostgreSQL 컬럼 수: {len(pg_columns)}")
            
            return True
            
        except Exception as e:
            logger.error(f"호환성 검증 실패 ({table_name}): {e}")
            return False

    def get_table_record_count(self, conn, table_name: str, is_mssql: bool = True) -> int:
        """테이블 레코드 수 조회"""
        try:
            cursor = conn.cursor()
            query = f"SELECT COUNT(*) FROM {table_name}"
            cursor.execute(query)
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            db_type = "MS-SQL" if is_mssql else "PostgreSQL"
            logger.error(f"{db_type} 레코드 수 조회 실패 ({table_name}): {e}")
            return 0

    def migrate_table_data_batch(self, mssql_conn, postgres_conn, table_name: str) -> int:
        """배치 단위로 테이블 데이터 마이그레이션"""
        try:
            logger.info(f"🔄 테이블 마이그레이션 시작: {table_name}")
            
            # 호환성 검증
            if not self.verify_table_compatibility(mssql_conn, postgres_conn, table_name):
                logger.error(f"호환성 검증 실패: {table_name}")
                return 0
            
            # 전체 레코드 수 확인
            total_records = self.get_table_record_count(mssql_conn, table_name, True)
            if total_records == 0:
                logger.warning(f"빈 테이블: {table_name}")
                # 빈 테이블도 완료로 처리
                self.save_progress(table_name)
                return 0
                
            logger.info(f"📊 전체 레코드 수: {total_records:,}건")
            
            # PostgreSQL 기존 데이터 삭제
            pg_cursor = postgres_conn.cursor()
            pg_cursor.execute(f"TRUNCATE TABLE {table_name.lower()} RESTART IDENTITY CASCADE")
            postgres_conn.commit()
            logger.info(f"🗑️ 기존 데이터 삭제 완료: {table_name}")
            
            # 배치 단위로 데이터 처리
            total_migrated = 0
            offset = 0
            
            while offset < total_records:
                # MS-SQL에서 배치 데이터 조회
                query = f"""
                SELECT * FROM {table_name}
                ORDER BY (SELECT NULL)
                OFFSET {offset} ROWS
                FETCH NEXT {self.batch_size} ROWS ONLY
                """
                
                for retry in range(self.max_retries):
                    try:
                        df = pd.read_sql(query, mssql_conn)
                        break
                    except Exception as e:
                        if retry < self.max_retries - 1:
                            logger.warning(f"⚠️ 배치 조회 재시도 {retry + 1}/{self.max_retries}: {e}")
                            time.sleep(self.retry_delay)
                        else:
                            logger.error(f"❌ 배치 조회 최종 실패: {e}")
                            return total_migrated
                
                if df.empty:
                    break
                
                # 데이터 타입 변환 및 정제
                df = self.clean_data(df)
                
                # PostgreSQL에 배치 삽입
                success = self.insert_batch_data(postgres_conn, table_name.lower(), df)
                if success:
                    batch_count = len(df)
                    total_migrated += batch_count
                    progress = (total_migrated / total_records) * 100
                    logger.info(f"✅ 진행률: {total_migrated:,}/{total_records:,} ({progress:.1f}%)")
                else:
                    logger.error(f"❌ 배치 삽입 실패: offset {offset}")
                    break
                
                offset += self.batch_size
                
                # 메모리 정리
                del df
                
                # 잠시 대기 (DB 부하 방지)
                time.sleep(0.1)
            
            # 테이블 완료시 진행 상태 저장
            if total_migrated == total_records:
                self.save_progress(table_name)
                logger.info(f"✅ 테이블 마이그레이션 완료: {table_name} ({total_migrated:,}건)")
            else:
                logger.warning(f"⚠️ 테이블 마이그레이션 불완전: {table_name} ({total_migrated:,}/{total_records:,}건)")
            
            return total_migrated
            
        except Exception as e:
            logger.error(f"❌ 테이블 마이그레이션 실패 ({table_name}): {e}")
            return 0

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터 정제 및 타입 변환"""
        try:
            # NaN 값 처리
            df = df.where(pd.notnull(df), None)
            
            # 텍스트 컬럼의 공백 제거
            text_columns = df.select_dtypes(include=['object']).columns
            for col in text_columns:
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].replace('nan', None)
                df[col] = df[col].replace('', None)
            
            # 날짜 컬럼 처리
            date_columns = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
            for col in date_columns:
                if col in df.columns:
                    try:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                    except:
                        pass
            
            return df
        except Exception as e:
            logger.error(f"데이터 정제 실패: {e}")
            return df

    def insert_batch_data(self, postgres_conn, table_name: str, df: pd.DataFrame) -> bool:
        """PostgreSQL에 배치 데이터 삽입"""
        try:
            cursor = postgres_conn.cursor()
            
            # 컬럼명과 값 준비
            columns = list(df.columns)
            values_list = []
            
            for _, row in df.iterrows():
                values = []
                for col in columns:
                    value = row[col]
                    if pd.isna(value) or value is None:
                        values.append(None)
                    elif isinstance(value, pd.Timestamp):
                        values.append(value.to_pydatetime() if pd.notna(value) else None)
                    else:
                        values.append(value)
                values_list.append(tuple(values))
            
            # 동적 INSERT 쿼리 생성
            columns_str = ', '.join(columns)
            placeholders = ', '.join(['%s'] * len(columns))
            query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
            
            # 배치 실행
            psycopg2.extras.execute_batch(cursor, query, values_list, page_size=100)
            postgres_conn.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"배치 삽입 실패 ({table_name}): {e}")
            postgres_conn.rollback()
            return False

    def verify_migration_results(self, mssql_conn, postgres_conn, tables_to_verify: List[str] = None) -> Dict[str, Dict]:
        """마이그레이션 결과 검증"""
        logger.info("🔍 마이그레이션 결과 검증 시작")
        verification_results = {}
        
        tables = tables_to_verify if tables_to_verify else self.table_priority
        
        for table_name in tables:
            try:
                mssql_count = self.get_table_record_count(mssql_conn, table_name, True)
                pg_count = self.get_table_record_count(postgres_conn, table_name.lower(), False)
                
                is_match = mssql_count == pg_count
                verification_results[table_name] = {
                    'mssql_count': mssql_count,
                    'postgresql_count': pg_count,
                    'match': is_match,
                    'difference': abs(mssql_count - pg_count)
                }
                
                status = "✅" if is_match else "⚠️"
                logger.info(f"{status} {table_name}: MS-SQL({mssql_count:,}) -> PostgreSQL({pg_count:,})")
                
            except Exception as e:
                logger.error(f"검증 실패 ({table_name}): {e}")
                verification_results[table_name] = {
                    'mssql_count': 0,
                    'postgresql_count': 0,
                    'match': False,
                    'error': str(e)
                }
        
        return verification_results

    def run_migration(self, force_restart: bool = False) -> bool:
        """전체 마이그레이션 실행 (재개 가능)"""
        logger.info("🚀 재개 가능한 마이그레이션 시작")
        start_time = datetime.now()
        
        # 진행 상태 로드 (강제 재시작이 아닌 경우)
        if not force_restart:
            self.load_progress()
        else:
            logger.info("🔄 강제 재시작 - 모든 테이블 다시 처리")
            self.completed_tables.clear()
            if os.path.exists(self.progress_file):
                os.remove(self.progress_file)
        
        # 데이터베이스 연결
        mssql_conn = self.connect_mssql()
        postgres_conn = self.connect_postgres()
        
        if not mssql_conn or not postgres_conn:
            logger.error("❌ 데이터베이스 연결 실패")
            return False
        
        try:
            # 남은 테이블 목록 확인
            remaining_tables = self.get_remaining_tables()
            
            if not remaining_tables:
                logger.info("✅ 모든 테이블이 이미 완료되었습니다!")
                # 최종 검증만 수행
                verification_results = self.verify_migration_results(mssql_conn, postgres_conn)
                return True
            
            logger.info(f"📋 남은 테이블: {len(remaining_tables)}개")
            logger.info(f"⏳ 처리할 테이블: {', '.join(remaining_tables)}")
            
            # 현재 PostgreSQL 상태 확인
            logger.info("\n🔍 현재 PostgreSQL 상태 확인:")
            completion_status = self.check_table_completion_status(postgres_conn)
            
            migration_results = {}
            total_records = 0
            
            # 남은 테이블별 순차 마이그레이션
            for i, table_name in enumerate(remaining_tables, 1):
                logger.info(f"\n{'='*60}")
                logger.info(f"📋 처리 중 ({i}/{len(remaining_tables)}): {table_name}")
                logger.info(f"{'='*60}")
                
                count = self.migrate_table_data_batch(mssql_conn, postgres_conn, table_name)
                migration_results[table_name] = count
                total_records += count
                
                # 중간 진행상황 출력
                remaining_count = len(remaining_tables) - i
                if count > 0:
                    logger.info(f"✅ {table_name} 완료: {count:,}건 (남은 테이블: {remaining_count}개)")
                else:
                    logger.warning(f"⚠️ {table_name} 처리 없음: {count}건 (남은 테이블: {remaining_count}개)")
            
            # 최종 검증
            logger.info(f"\n{'='*60}")
            logger.info("🔍 최종 검증 시작")
            logger.info(f"{'='*60}")
            
            verification_results = self.verify_migration_results(mssql_conn, postgres_conn)
            
            # 결과 출력
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info(f"\n{'='*60}")
            logger.info("📊 마이그레이션 완료 보고서")
            logger.info(f"{'='*60}")
            logger.info(f"⏱️ 소요 시간: {duration}")
            logger.info(f"📦 이번 세션 처리 레코드: {total_records:,}건")
            
            # 전체 완료 확인
            all_completed = all(result.get('match', False) for result in verification_results.values())
            
            if all_completed:
                # 진행 상태 파일 삭제 (완료)
                if os.path.exists(self.progress_file):
                    os.remove(self.progress_file)
                logger.info("🎉 전체 마이그레이션이 성공적으로 완료되었습니다!")
            else:
                logger.warning("⚠️ 일부 테이블에 문제가 있습니다. 다시 실행하여 재시도하세요.")
            
            # 테이블별 상세 결과
            logger.info("\n📋 테이블별 결과:")
            for table_name, result in verification_results.items():
                if result.get('match', False):
                    logger.info(f"✅ {table_name}: {result['postgresql_count']:,}건")
                else:
                    logger.warning(f"⚠️ {table_name}: 불일치 (차이: {result.get('difference', 0)}건)")
            
            return all_completed
            
        except Exception as e:
            logger.error(f"❌ 마이그레이션 실행 중 오류: {e}")
            return False
            
        finally:
            if mssql_conn:
                mssql_conn.close()
                logger.info("MS-SQL 연결 종료")
            if postgres_conn:
                postgres_conn.close()
                logger.info("PostgreSQL 연결 종료")

if __name__ == "__main__":
    import sys
    
    # 명령행 인자 처리
    force_restart = '--restart' in sys.argv or '--force' in sys.argv
    
    migrator = ResumableDBMigrator()
    
    if force_restart:
        print("🔄 강제 재시작 모드")
    
    success = migrator.run_migration(force_restart=force_restart)
    
    if success:
        print("\n" + "="*60)
        print("✅ 마이그레이션이 성공적으로 완료되었습니다!")
        print("="*60)
        print("📝 상세 로그: migration_resumable.log")
        print("🔗 pgAdmin: http://localhost:5051")
        print("   - 계정: admin@mis.co.kr")
        print("   - 비밀번호: admin123!@#")
        print("="*60)
        print("\n💡 사용법:")
        print("   - 재개: python db_migration_resumable.py")
        print("   - 강제 재시작: python db_migration_resumable.py --restart")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ 마이그레이션이 중단되었습니다.")
        print("="*60)
        print("📝 오류 로그: migration_resumable.log")
        print("🔄 재시도: python db_migration_resumable.py")
        print("🔧 강제 재시작: python db_migration_resumable.py --restart")
        print("="*60) 