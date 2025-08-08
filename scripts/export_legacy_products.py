#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
레거시 DB 상품 정보 엑셀 추출 스크립트
mis.aone.co.kr의 tbl_Product 테이블에서 모든 상품 정보를 엑셀 파일로 추출합니다.
"""

import os
import sys
import logging
import pandas as pd
import pyodbc
from datetime import datetime
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('legacy_product_export.log'),
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
            # 레거시 DB 연결 정보 (실제 환경에 맞게 수정 필요)
            connection_string = (
                "DRIVER={ODBC Driver 17 for SQL Server};"
                "SERVER=localhost\\SQLEXPRESS;"  # 또는 실제 서버 주소
                "DATABASE=db_mis;"
                "Trusted_Connection=yes;"
            )
            
            # 만약 사용자명/비밀번호가 필요한 경우 아래 방식 사용
            # connection_string = (
            #     "DRIVER={ODBC Driver 17 for SQL Server};"
            #     "SERVER=서버주소;"
            #     "DATABASE=db_mis;"
            #     "UID=사용자명;"
            #     "PWD=비밀번호;"
            # )
            
            self.connection = pyodbc.connect(connection_string)
            logger.info("✅ 레거시 MS-SQL 데이터베이스 연결 성공")
            return True
            
        except Exception as e:
            logger.error(f"❌ 레거시 DB 연결 실패: {e}")
            logger.info("💡 연결 정보를 확인하고 다시 시도해주세요.")
            return False
    
    def export_products_to_excel(self, output_file="legacy_products.xlsx"):
        """상품 정보를 엑셀로 추출"""
        if not self.connection:
            logger.error("❌ 데이터베이스 연결이 필요합니다.")
            return False
        
        try:
            logger.info("🔍 상품 정보 조회 시작...")
            
            # 상품 정보와 관련 코드 정보를 JOIN하여 조회
            query = """
            SELECT 
                p.Seq AS '상품번호',
                p.Company AS '회사코드',
                c_comp.CodeName AS '회사명',
                p.Brand AS '브랜드코드', 
                c_brand.CodeName AS '브랜드명',
                p.ProdGroup AS '품목코드',
                c_group.CodeName AS '품목명',
                p.ProdType AS '타입코드',
                c_type.CodeName AS '타입명',
                p.ProdYear AS '제품년도',
                p.ProdName AS '상품명',
                p.ProdTagAmt AS '상품가격',
                p.ProdManual AS '매뉴얼경로',
                p.ProdInfo AS '상품정보',
                p.FaqYn AS 'FAQ연동',
                p.ShowYn AS '노출여부',
                p.UseYn AS '사용여부',
                p.InsDate AS '등록일',
                p.InsUser AS '등록자',
                p.UptDate AS '수정일',
                p.UptUser AS '수정자'
            FROM tbl_Product p
            LEFT JOIN tbl_Code c_comp ON p.Company = c_comp.Seq
            LEFT JOIN tbl_Code c_brand ON p.Brand = c_brand.Seq  
            LEFT JOIN tbl_Code c_group ON p.ProdGroup = c_group.Seq
            LEFT JOIN tbl_Code c_type ON p.ProdType = c_type.Seq
            ORDER BY p.Company, p.Brand, p.ProdGroup, p.ProdType, p.Seq
            """
            
            # 데이터 조회
            df_products = pd.read_sql(query, self.connection)
            
            logger.info(f"📊 총 {len(df_products)}개 상품 정보 조회 완료")
            
            # 상품 상세 정보도 조회 (별도 시트)
            detail_query = """
            SELECT 
                pd.Seq AS '상세번호',
                pd.ProdSeq AS '상품번호',
                p.ProdName AS '상품명',
                pd.ProdDivCode AS '상품구분코드',
                pd.ProdDtlName AS '상세명',
                pd.UseYn AS '사용여부',
                pd.InsDate AS '등록일',
                pd.InsUser AS '등록자'
            FROM tbl_Product_DTL pd
            INNER JOIN tbl_Product p ON pd.ProdSeq = p.Seq
            ORDER BY pd.ProdSeq, pd.Seq
            """
            
            try:
                df_details = pd.read_sql(detail_query, self.connection)
                logger.info(f"📊 총 {len(df_details)}개 상품 상세 정보 조회 완료")
            except Exception as e:
                logger.warning(f"⚠️ 상품 상세 정보 조회 실패: {e}")
                df_details = pd.DataFrame()
            
            # 코드 정보도 조회 (참고용)
            code_query = """
            SELECT 
                c.Seq AS '코드번호',
                c.CodeSeq AS '코드그룹',
                c.ParentSeq AS '상위코드',
                c.Code AS '코드',
                c.CodeName AS '코드명',
                c.Depth AS '깊이',
                c.Sort AS '정렬순서',
                c.UseYn AS '사용여부'
            FROM tbl_Code c
            WHERE c.CodeSeq IN (5, 39, 49, 210, 219, 230, 580)  -- 상품 관련 코드들
                OR c.ParentSeq IN (39, 49, 210, 219, 230, 580)
            ORDER BY c.CodeSeq, c.ParentSeq, c.Sort, c.Seq
            """
            
            try:
                df_codes = pd.read_sql(code_query, self.connection)
                logger.info(f"📊 총 {len(df_codes)}개 코드 정보 조회 완료")
            except Exception as e:
                logger.warning(f"⚠️ 코드 정보 조회 실패: {e}")
                df_codes = pd.DataFrame()
            
            # 엑셀 파일로 저장 (다중 시트)
            logger.info(f"💾 엑셀 파일 저장 중: {output_file}")
            
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # 상품 마스터 정보
                df_products.to_excel(writer, sheet_name='상품목록', index=False)
                
                # 상품 상세 정보
                if not df_details.empty:
                    df_details.to_excel(writer, sheet_name='상품상세', index=False)
                
                # 코드 정보 (참고용)
                if not df_codes.empty:
                    df_codes.to_excel(writer, sheet_name='코드정보', index=False)
                
                # 통계 정보
                stats_data = {
                    '항목': [
                        '총 상품 수', 
                        '사용 중인 상품', 
                        '미사용 상품',
                        '회사별 상품 수',
                        '브랜드별 상품 수',
                        '추출 일시'
                    ],
                    '값': [
                        len(df_products),
                        len(df_products[df_products['사용여부'] == 'Y']),
                        len(df_products[df_products['사용여부'] == 'N']),
                        df_products['회사명'].nunique(),
                        df_products['브랜드명'].nunique(),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ]
                }
                df_stats = pd.DataFrame(stats_data)
                df_stats.to_excel(writer, sheet_name='통계정보', index=False)
            
            logger.info(f"✅ 엑셀 파일 저장 완료: {output_file}")
            
            # 요약 정보 출력
            logger.info("📊 상품 정보 요약:")
            logger.info(f"   - 총 상품 수: {len(df_products):,}개")
            logger.info(f"   - 사용 중인 상품: {len(df_products[df_products['사용여부'] == 'Y']):,}개")
            logger.info(f"   - 미사용 상품: {len(df_products[df_products['사용여부'] == 'N']):,}개")
            logger.info(f"   - 회사 수: {df_products['회사명'].nunique()}개")
            logger.info(f"   - 브랜드 수: {df_products['브랜드명'].nunique()}개")
            
            # 회사별 상품 수 출력
            if '회사명' in df_products.columns:
                company_stats = df_products['회사명'].value_counts()
                logger.info("📋 회사별 상품 수:")
                for company, count in company_stats.items():
                    logger.info(f"   - {company}: {count:,}개")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 상품 정보 추출 실패: {e}")
            import traceback
            logger.error(f"상세 오류: {traceback.format_exc()}")
            return False
    
    def close_connection(self):
        """데이터베이스 연결 종료"""
        if self.connection:
            self.connection.close()
            logger.info("🔌 데이터베이스 연결 종료")

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='레거시 DB 상품 정보 엑셀 추출')
    parser.add_argument('--output', '-o', type=str, default='legacy_products.xlsx',
                      help='출력 엑셀 파일명 (기본값: legacy_products.xlsx)')
    
    args = parser.parse_args()
    
    logger.info("🚀 레거시 상품 정보 추출 시작")
    logger.info(f"📁 출력 파일: {args.output}")
    
    exporter = LegacyProductExporter()
    
    try:
        # 데이터베이스 연결
        if not exporter.connect_to_legacy_db():
            logger.error("❌ 데이터베이스 연결 실패로 종료합니다.")
            return
        
        # 상품 정보 추출
        if exporter.export_products_to_excel(args.output):
            logger.info("✅ 상품 정보 추출이 성공적으로 완료되었습니다.")
            logger.info(f"📂 파일 위치: {os.path.abspath(args.output)}")
        else:
            logger.error("❌ 상품 정보 추출에 실패했습니다.")
    
    except KeyboardInterrupt:
        logger.info("⚠️ 사용자에 의해 중단되었습니다.")
    
    except Exception as e:
        logger.error(f"❌ 예기치 않은 오류 발생: {e}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
    
    finally:
        exporter.close_connection()

if __name__ == "__main__":
    main() 