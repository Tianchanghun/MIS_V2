#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
현재 MIS v2 PostgreSQL DB 데이터 추출 스크립트
상품관리 구현을 위한 참고 데이터 추출
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

# Flask 앱 컨텍스트 설정
from app import create_app
from app.common.models import db, Code, Company, User, UserCompany

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('current_data_export.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CurrentDataExporter:
    def __init__(self):
        """현재 MIS v2 데이터 추출기 초기화"""
        self.app = create_app()
        
    def export_reference_data(self, output_file="current_reference_data.xlsx"):
        """상품관리 구현 참고용 데이터 추출"""
        try:
            with self.app.app_context():
                logger.info("현재 MIS v2 참고 데이터 추출 시작...")
                
                # 1. 회사 정보
                companies_query = db.session.query(Company).all()
                companies_data = []
                for company in companies_query:
                    companies_data.append({
                        'ID': company.id,
                        '회사코드': company.company_code,
                        '회사명': company.company_name,
                        '회사명(영문)': company.company_name_en,
                        '사업자번호': company.business_number,
                        'CEO': company.ceo_name,
                        '주소': company.address,
                        '전화번호': company.phone,
                        '이메일': company.email,
                        '상태': '활성' if company.is_active else '비활성',
                        '테마색상': company.theme_color,
                        '생성일': company.created_at
                    })
                df_companies = pd.DataFrame(companies_data)
                logger.info(f"회사 정보: {len(df_companies)}개")
                
                # 2. 코드 정보 (상품 관련)
                codes_query = db.session.query(Code).all()
                codes_data = []
                for code in codes_query:
                    codes_data.append({
                        'ID': code.seq,
                        '코드그룹': code.code_seq,
                        '상위코드': code.parent_seq,
                        '코드': code.code,
                        '코드명': code.code_name,
                        '깊이': code.depth,
                        '정렬': code.sort,
                        '코드정보': code.code_info,
                        '등록자': code.ins_user,
                        '등록일': code.ins_date
                    })
                df_codes = pd.DataFrame(codes_data)
                logger.info(f"코드 정보: {len(df_codes)}개")
                
                # 3. 사용자 정보
                users_query = db.session.query(User).limit(10).all()  # 상위 10명만
                users_data = []
                for user in users_query:
                    users_data.append({
                        'ID': user.seq,
                        '로그인ID': user.login_id,
                        '이름': user.name,
                        '주민번호': user.id_number,
                        '이메일': user.email,
                        '휴대폰': user.mobile,
                        '내선번호': user.extension_number,
                        '회사ID': user.company_id,
                        '상태': user.member_status,
                        '슈퍼유저': user.super_user,
                        '등록일': user.ins_date
                    })
                df_users = pd.DataFrame(users_data)
                logger.info(f"사용자 정보: {len(df_users)}개")
                
                # 4. 사용자-회사 매핑
                user_companies_query = db.session.query(UserCompany).all()
                user_companies_data = []
                for uc in user_companies_query:
                    user_companies_data.append({
                        'ID': uc.id,
                        '사용자ID': uc.user_seq,
                        '회사ID': uc.company_id,
                        '역할': uc.role,
                        '주속여부': uc.is_primary,
                        '활성상태': uc.is_active,
                        '접근시작일': uc.access_start_date,
                        '접근종료일': uc.access_end_date,
                        '마지막접근': uc.last_access_at,
                        '할당일': uc.created_at
                    })
                df_user_companies = pd.DataFrame(user_companies_data)
                logger.info(f"사용자-회사 매핑: {len(df_user_companies)}개")
                
                # 5. 상품 관련 코드 분석
                product_related_codes = []
                for code in codes_query:
                    code_name_lower = (code.code_name or '').lower()
                    if any(keyword in code_name_lower for keyword in 
                           ['상품', '제품', '브랜드', '품목', '타입', '분류', '카테고리']):
                        product_related_codes.append({
                            'ID': code.seq,
                            '코드그룹': code.code_seq,
                            '코드': code.code,
                            '코드명': code.code_name,
                            '깊이': code.depth,
                            '상위코드': code.parent_seq,
                            '정렬': code.sort
                        })
                df_product_codes = pd.DataFrame(product_related_codes)
                logger.info(f"상품 관련 코드: {len(df_product_codes)}개")
                
                # 6. 코드 그룹별 분석
                code_groups = {}
                for code in codes_query:
                    if code.code_seq not in code_groups:
                        code_groups[code.code_seq] = []
                    code_groups[code.code_seq].append(code)
                
                code_group_analysis = []
                for group_id, codes in code_groups.items():
                    root_codes = [c for c in codes if c.depth == 0]
                    group_name = root_codes[0].code_name if root_codes else f"그룹{group_id}"
                    
                    code_group_analysis.append({
                        '그룹ID': group_id,
                        '그룹명': group_name,
                        '총코드수': len(codes),
                        '최대깊이': max([c.depth for c in codes] + [0]),
                        '루트코드': root_codes[0].code if root_codes else ''
                    })
                
                df_code_groups = pd.DataFrame(code_group_analysis)
                logger.info(f"코드 그룹: {len(df_code_groups)}개")
                
                # 엑셀 파일로 저장
                logger.info(f"엑셀 파일 저장 중: {output_file}")
                
                with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                    # 각 시트별 저장
                    df_companies.to_excel(writer, sheet_name='01_회사정보', index=False)
                    df_codes.to_excel(writer, sheet_name='02_전체코드', index=False)
                    df_code_groups.to_excel(writer, sheet_name='03_코드그룹분석', index=False)
                    df_product_codes.to_excel(writer, sheet_name='04_상품관련코드', index=False)
                    df_users.to_excel(writer, sheet_name='05_사용자정보', index=False)
                    df_user_companies.to_excel(writer, sheet_name='06_사용자회사매핑', index=False)
                    
                    # 요약 정보
                    summary_data = {
                        '항목': [
                            '회사 수',
                            '전체 코드 수', 
                            '코드 그룹 수',
                            '상품 관련 코드 수',
                            '사용자 수 (샘플)',
                            '사용자-회사 매핑 수',
                            '추출 일시'
                        ],
                        '값': [
                            len(df_companies),
                            len(df_codes),
                            len(df_code_groups),
                            len(df_product_codes),
                            len(df_users),
                            len(df_user_companies),
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        ]
                    }
                    df_summary = pd.DataFrame(summary_data)
                    df_summary.to_excel(writer, sheet_name='00_요약정보', index=False)
                
                logger.info(f"엑셀 파일 저장 완료: {output_file}")
                
                # 요약 출력
                logger.info("현재 MIS v2 데이터 요약:")
                logger.info(f"  - 회사 수: {len(df_companies)}개")
                logger.info(f"  - 전체 코드 수: {len(df_codes)}개")
                logger.info(f"  - 코드 그룹 수: {len(df_code_groups)}개")
                logger.info(f"  - 상품 관련 코드: {len(df_product_codes)}개")
                logger.info(f"  - 사용자-회사 매핑: {len(df_user_companies)}개")
                
                return True
                
        except Exception as e:
            logger.error(f"데이터 추출 실패: {e}")
            import traceback
            logger.error(f"상세 오류: {traceback.format_exc()}")
            return False

def main():
    """메인 실행 함수"""
    print("="*60)
    print("    현재 MIS v2 참고 데이터 추출 스크립트")
    print("="*60)
    
    exporter = CurrentDataExporter()
    
    try:
        output_file = f"current_reference_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        if exporter.export_reference_data(output_file):
            logger.info("참고 데이터 추출 성공!")
            logger.info(f"파일 위치: {os.path.abspath(output_file)}")
            logger.info("")
            logger.info("이 데이터는 상품관리 구현 시 다음과 같이 활용할 수 있습니다:")
            logger.info("1. 회사별 멀티테넌트 구조 참고")
            logger.info("2. 코드 체계 및 계층 구조 분석")
            logger.info("3. 사용자 권한 및 회사 매핑 방식 이해")
            logger.info("4. 기존 코드 재활용 방안 검토")
        else:
            logger.error("참고 데이터 추출 실패")
    
    except Exception as e:
        logger.error(f"예기치 않은 오류: {e}")
    
    finally:
        print("="*60)
        print("    스크립트 실행 완료")
        print("="*60)

if __name__ == "__main__":
    main() 