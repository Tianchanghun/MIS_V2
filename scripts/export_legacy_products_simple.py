#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
레거시 DB 상품 정보 엑셀 추출 스크립트 (간단 버전)
Windows 환경에서 안정적으로 작동하는 버전
"""

import os
import sys
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 로깅 설정 (이모티콘 제거)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('legacy_product_export.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LegacyProductExporter:
    def __init__(self):
        """레거시 상품 정보 추출기 초기화"""
        self.connection = None
        
    def connect_to_legacy_db(self):
        """레거시 MS-SQL 데이터베이스 연결"""
        try:
            import pyodbc
            
            # 여러 연결 방식 시도
            connection_configs = [
                # 1. Windows 인증 (SQL Express)
                {
                    "DRIVER": "{ODBC Driver 17 for SQL Server}",
                    "SERVER": "localhost\\SQLEXPRESS",
                    "DATABASE": "db_mis",
                    "Trusted_Connection": "yes"
                },
                # 2. Windows 인증 (기본 인스턴스)
                {
                    "DRIVER": "{ODBC Driver 17 for SQL Server}",
                    "SERVER": "localhost",
                    "DATABASE": "db_mis", 
                    "Trusted_Connection": "yes"
                },
                # 3. SQL Server 인증 (샘플)
                {
                    "DRIVER": "{ODBC Driver 17 for SQL Server}",
                    "SERVER": "localhost",
                    "DATABASE": "db_mis",
                    "UID": "sa",
                    "PWD": "password"  # 실제 비밀번호로 변경 필요
                }
            ]
            
            for i, config in enumerate(connection_configs, 1):
                try:
                    logger.info(f"연결 시도 {i}: {config['SERVER']}")
                    connection_string = ";".join([f"{k}={v}" for k, v in config.items()])
                    self.connection = pyodbc.connect(connection_string)
                    logger.info(f"성공: 레거시 MS-SQL 데이터베이스 연결 성공 (방식 {i})")
                    return True
                except Exception as e:
                    logger.warning(f"연결 방식 {i} 실패: {str(e)[:100]}...")
                    continue
                    
            logger.error("모든 연결 방식 실패")
            logger.info("해결 방법:")
            logger.info("1. SQL Server가 실행 중인지 확인")
            logger.info("2. SQL Server 서비스 시작: net start mssqlserver")
            logger.info("3. 스크립트의 연결 정보 수정")
            return False
            
        except ImportError:
            logger.error("pyodbc 모듈이 설치되지 않음: pip install pyodbc")
            return False
        except Exception as e:
            logger.error(f"예기치 않은 오류: {e}")
            return False
    
    def create_sample_data(self, output_file="sample_products.xlsx"):
        """샘플 상품 데이터 생성 (DB 연결 실패 시 대안)"""
        logger.info("샘플 상품 데이터를 생성합니다...")
        
        # 샘플 상품 데이터 생성
        sample_products = {
            '상품번호': [1, 2, 3, 4, 5],
            '회사코드': [581, 581, 582, 582, 581],
            '회사명': ['에이원', '에이원', '에이원월드', '에이원월드', '에이원'],
            '브랜드코드': [50, 51, 50, 52, 50],
            '브랜드명': ['에이원베이비', '베베원', '에이원베이비', '알집', '에이원베이비'],
            '품목코드': [50, 51, 50, 53, 52],
            '품목명': ['유모차', '카시트', '유모차', '젖병', '보행기'],
            '타입코드': [211, 212, 211, 214, 213],
            '타입명': ['프리미엄', '스탠다드', '프리미엄', '젖병', '보행기'],
            '제품년도': ['24', '24', '25', '24', '23'],
            '상품명': ['에이원 프리미엄 유모차', '베베원 스탠다드 카시트', '에이원월드 프리미엄 유모차', '알집 젖병', '에이원 보행기'],
            '상품가격': [500000, 300000, 450000, 15000, 120000],
            '매뉴얼경로': ['manual1.pdf', 'manual2.pdf', 'manual3.pdf', '', 'manual5.pdf'],
            '상품정보': ['프리미엄 유모차 상세 정보', '안전한 카시트', '신제품 유모차', '젖병 상세정보', '보행기 정보'],
            'FAQ연동': ['Y', 'N', 'Y', 'N', 'Y'],
            '노출여부': ['Y', 'Y', 'Y', 'Y', 'N'],
            '사용여부': ['Y', 'Y', 'Y', 'Y', 'N'],
            '등록일': ['2024-01-01', '2024-02-01', '2024-03-01', '2024-04-01', '2023-12-01'],
            '등록자': ['admin', 'admin', 'admin', 'admin', 'admin']
        }
        
        df_products = pd.DataFrame(sample_products)
        
        # 샘플 코드 데이터
        sample_codes = {
            '코드번호': [581, 582, 50, 51, 52, 53],
            '코드명': ['에이원', '에이원월드', '에이원베이비', '베베원', '알집', '젖병브랜드'],
            '코드': ['AONE', 'AONEWORLD', 'AONEBABY', 'BEBEONE', 'ALZIB', 'BOTTLE'],
            '사용여부': ['Y', 'Y', 'Y', 'Y', 'Y', 'Y']
        }
        
        df_codes = pd.DataFrame(sample_codes)
        
        # 엑셀 파일 저장
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df_products.to_excel(writer, sheet_name='상품목록_샘플', index=False)
            df_codes.to_excel(writer, sheet_name='코드정보_샘플', index=False)
            
            # 안내 정보
            info_data = {
                '항목': ['파일 성격', '생성 일시', '비고'],
                '내용': ['샘플 데이터', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'DB 연결 후 실제 데이터 추출 가능']
            }
            df_info = pd.DataFrame(info_data)
            df_info.to_excel(writer, sheet_name='안내사항', index=False)
        
        logger.info(f"샘플 파일 생성 완료: {output_file}")
        logger.info("실제 데이터를 추출하려면 DB 연결 정보를 설정해주세요.")
        return True
    
    def export_products_to_excel(self, output_file="legacy_products.xlsx"):
        """상품 정보를 엑셀로 추출"""
        if not self.connection:
            logger.error("데이터베이스 연결이 필요합니다.")
            return False
        
        try:
            logger.info("상품 정보 조회 시작...")
            
            # 상품 정보 조회 (간단 버전)
            query = """
            SELECT TOP 1000
                p.Seq AS 상품번호,
                p.Company AS 회사코드,
                ISNULL(c_comp.CodeName, '') AS 회사명,
                p.Brand AS 브랜드코드, 
                ISNULL(c_brand.CodeName, '') AS 브랜드명,
                p.ProdGroup AS 품목코드,
                ISNULL(c_group.CodeName, '') AS 품목명,
                p.ProdType AS 타입코드,
                ISNULL(c_type.CodeName, '') AS 타입명,
                p.ProdYear AS 제품년도,
                p.ProdName AS 상품명,
                p.ProdTagAmt AS 상품가격,
                ISNULL(p.UseYn, 'Y') AS 사용여부,
                p.InsDate AS 등록일,
                ISNULL(p.InsUser, '') AS 등록자
            FROM tbl_Product p
            LEFT JOIN tbl_Code c_comp ON p.Company = c_comp.Seq
            LEFT JOIN tbl_Code c_brand ON p.Brand = c_brand.Seq  
            LEFT JOIN tbl_Code c_group ON p.ProdGroup = c_group.Seq
            LEFT JOIN tbl_Code c_type ON p.ProdType = c_type.Seq
            ORDER BY p.Seq
            """
            
            df_products = pd.read_sql(query, self.connection)
            logger.info(f"총 {len(df_products)}개 상품 정보 조회 완료")
            
            # 엑셀 파일로 저장
            logger.info(f"엑셀 파일 저장 중: {output_file}")
            
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df_products.to_excel(writer, sheet_name='상품목록', index=False)
                
                # 요약 정보
                stats_data = {
                    '항목': ['총 상품 수', '사용 중인 상품', '추출 일시'],
                    '값': [
                        len(df_products),
                        len(df_products[df_products['사용여부'] == 'Y']),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ]
                }
                df_stats = pd.DataFrame(stats_data)
                df_stats.to_excel(writer, sheet_name='요약정보', index=False)
            
            logger.info(f"엑셀 파일 저장 완료: {output_file}")
            logger.info(f"총 상품 수: {len(df_products):,}개")
            
            return True
            
        except Exception as e:
            logger.error(f"상품 정보 추출 실패: {e}")
            return False
    
    def close_connection(self):
        """데이터베이스 연결 종료"""
        if self.connection:
            self.connection.close()
            logger.info("데이터베이스 연결 종료")

def main():
    """메인 실행 함수"""
    print("="*60)
    print("    레거시 MIS 상품 정보 엑셀 추출 스크립트")
    print("="*60)
    
    exporter = LegacyProductExporter()
    
    try:
        # 데이터베이스 연결 시도
        logger.info("레거시 DB 연결 시도 중...")
        
        if exporter.connect_to_legacy_db():
            # 실제 데이터 추출
            output_file = f"legacy_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            if exporter.export_products_to_excel(output_file):
                logger.info("상품 정보 추출 성공!")
                logger.info(f"파일 위치: {os.path.abspath(output_file)}")
            else:
                logger.error("상품 정보 추출 실패")
        else:
            # DB 연결 실패 시 샘플 데이터 생성
            logger.info("DB 연결 실패로 샘플 데이터를 생성합니다.")
            sample_file = f"sample_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            exporter.create_sample_data(sample_file)
            logger.info(f"샘플 파일 위치: {os.path.abspath(sample_file)}")
    
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단되었습니다.")
    
    except Exception as e:
        logger.error(f"예기치 않은 오류: {e}")
    
    finally:
        exporter.close_connection()
        print("="*60)
        print("    스크립트 실행 완료")
        print("="*60)

if __name__ == "__main__":
    main() 