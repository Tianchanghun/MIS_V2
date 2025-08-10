#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db
import pyodbc
from datetime import datetime

def diagnose_missing_data():
    """914개 상세 중 누락된 80개 데이터 진단 및 UI 문제 분석"""
    print("🔍 누락된 80개 상세 데이터 진단")
    print("=" * 60)
    
    # 실제 레거시 DB 연결 정보
    LEGACY_CONNECTION = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=210.109.96.74,2521;DATABASE=db_mis;UID=user_mis;PWD=user_mis!@12;ApplicationIntent=ReadOnly;"
    
    try:
        # 1. 레거시 DB 연결 및 전체 데이터 확인
        print("1️⃣ 레거시 DB 전체 데이터 재확인")
        legacy_conn = pyodbc.connect(LEGACY_CONNECTION, timeout=30)
        legacy_cursor = legacy_conn.cursor()
        
        # 레거시 상세 데이터 전체 조회
        legacy_cursor.execute("""
            SELECT 
                pd.Seq, pd.MstSeq, pd.StdDivProdCode, pd.ProductName,
                pd.BrandCode, pd.DivTypeCode, pd.ProdGroupCode, pd.ProdTypeCode,
                pd.ProdCode, pd.ProdType2Code, pd.YearCode, pd.ProdColorCode,
                pd.Status, LEN(pd.StdDivProdCode) as CodeLength,
                p.ProdName, p.UseYn
            FROM tbl_Product_DTL pd
            LEFT JOIN tbl_Product p ON pd.MstSeq = p.Seq
            WHERE pd.Status = 'Active'
            ORDER BY pd.MstSeq, pd.Seq
        """)
        all_legacy_details = legacy_cursor.fetchall()
        print(f"   📊 레거시 전체 활성 상세: {len(all_legacy_details)}개")
        
        # 활성 제품과 연결된 상세만 확인
        legacy_cursor.execute("""
            SELECT 
                pd.Seq, pd.MstSeq, pd.StdDivProdCode, pd.ProductName,
                pd.Status, p.ProdName, p.UseYn
            FROM tbl_Product_DTL pd
            INNER JOIN tbl_Product p ON pd.MstSeq = p.Seq
            WHERE pd.Status = 'Active' AND p.UseYn = 'Y'
            ORDER BY pd.MstSeq, pd.Seq
        """)
        valid_legacy_details = legacy_cursor.fetchall()
        print(f"   📊 활성 제품 연결 상세: {len(valid_legacy_details)}개")
        
        # 2. 도커 DB 현재 상태 확인
        print("\n2️⃣ 도커 DB 현재 상태 확인")
        app = create_app()
        with app.app_context():
            result = db.session.execute(db.text("""
                SELECT 
                    COUNT(p.id) as product_count,
                    COUNT(pd.id) as detail_count,
                    COUNT(CASE WHEN pd.legacy_seq IS NOT NULL THEN 1 END) as with_legacy_seq,
                    COUNT(CASE WHEN LENGTH(pd.std_div_prod_code) = 16 THEN 1 END) as valid_16_count
                FROM products p
                LEFT JOIN product_details pd ON p.id = pd.product_id
                WHERE p.company_id = 1
            """))
            current_stats = result.fetchone()
            
            print(f"   📊 도커 현재 상태:")
            print(f"      제품: {current_stats.product_count}개")
            print(f"      상세: {current_stats.detail_count}개")
            print(f"      레거시 연결: {current_stats.with_legacy_seq}개")
            print(f"      16자리 코드: {current_stats.valid_16_count}개")
            
            # 3. 누락된 데이터 분석
            print(f"\n3️⃣ 누락 데이터 분석")
            
            # 도커에 있는 레거시 seq 목록
            result = db.session.execute(db.text("""
                SELECT DISTINCT legacy_seq
                FROM product_details
                WHERE legacy_seq IS NOT NULL
                ORDER BY legacy_seq
            """))
            docker_legacy_seqs = {row.legacy_seq for row in result.fetchall()}
            print(f"   📥 도커에 저장된 레거시 SEQ: {len(docker_legacy_seqs)}개")
            
            # 레거시에서 누락된 SEQ 찾기
            legacy_seqs = {detail[0] for detail in valid_legacy_details}  # pd.Seq
            missing_seqs = legacy_seqs - docker_legacy_seqs
            print(f"   ❌ 누락된 레거시 SEQ: {len(missing_seqs)}개")
            
            if missing_seqs:
                print(f"   🔍 누락된 SEQ 샘플 (최대 10개): {sorted(list(missing_seqs))[:10]}")
                
                # 누락된 데이터 상세 분석
                missing_details = [d for d in valid_legacy_details if d[0] in missing_seqs]
                print(f"\n   📋 누락된 상세 데이터 분석:")
                
                # MstSeq별 누락 통계
                missing_by_master = {}
                for detail in missing_details:
                    mst_seq = detail[1]  # MstSeq
                    if mst_seq not in missing_by_master:
                        missing_by_master[mst_seq] = []
                    missing_by_master[mst_seq].append(detail)
                
                print(f"      누락된 제품 마스터: {len(missing_by_master)}개")
                for mst_seq, details in list(missing_by_master.items())[:5]:
                    print(f"        MstSeq {mst_seq}: {len(details)}개 상세 누락")
                    for detail in details[:2]:  # 최대 2개만
                        print(f"          - {detail[3][:30]}... (SEQ: {detail[0]})")
        
        # 4. UI 문제 진단
        print(f"\n4️⃣ UI 문제 진단")
        with app.app_context():
            # 'undefined' 표시 원인 분석
            result = db.session.execute(db.text("""
                SELECT 
                    p.id, p.product_name, p.brand_code_seq, p.category_code_seq, p.type_code_seq,
                    b.code_name as brand_name,
                    c.code_name as category_name,
                    t.code_name as type_name,
                    pd.std_div_prod_code
                FROM products p
                LEFT JOIN tbl_code b ON p.brand_code_seq = b.seq
                LEFT JOIN tbl_code c ON p.category_code_seq = c.seq  
                LEFT JOIN tbl_code t ON p.type_code_seq = t.seq
                LEFT JOIN product_details pd ON p.id = pd.product_id
                WHERE p.company_id = 1
                AND (p.brand_code_seq IS NULL OR p.category_code_seq IS NULL OR p.type_code_seq IS NULL
                     OR b.code_name IS NULL OR c.code_name IS NULL OR t.code_name IS NULL
                     OR pd.std_div_prod_code IS NULL)
                LIMIT 10
            """))
            
            ui_issues = result.fetchall()
            print(f"   ❌ UI 문제 제품: {len(ui_issues)}개")
            
            for issue in ui_issues:
                problems = []
                if not issue.brand_code_seq or not issue.brand_name:
                    problems.append("브랜드 누락")
                if not issue.category_code_seq or not issue.category_name:
                    problems.append("품목 누락")
                if not issue.type_code_seq or not issue.type_name:
                    problems.append("타입 누락")
                if not issue.std_div_prod_code:
                    problems.append("자가코드 누락")
                
                print(f"      - {issue.product_name[:30]}: {', '.join(problems)}")
            
            # 페이징 데이터 확인
            result = db.session.execute(db.text("""
                SELECT COUNT(*) as total_count
                FROM products p
                WHERE p.company_id = 1 AND p.is_active = true
            """))
            total_products = result.fetchone().total_count
            
            pages_needed = (total_products + 19) // 20  # 20개씩 페이징
            print(f"\n   📄 페이징 정보:")
            print(f"      총 제품: {total_products}개")
            print(f"      필요한 페이지: {pages_needed}페이지 (20개씩)")
        
        print(f"\n🎯 해결 방안:")
        print(f"   1. 누락된 {len(missing_seqs)}개 상세 데이터 추가 마이그레이션")
        print(f"   2. NULL 브랜드/품목/타입 매핑 수정")
        print(f"   3. 'undefined' 자가코드 문제 해결")
        print(f"   4. 페이징/검색/정렬 기능 테스트")
        
        return missing_seqs, missing_details
        
    except Exception as e:
        print(f"❌ 진단 오류: {e}")
        import traceback
        traceback.print_exc()
        return set(), []
    
    finally:
        if 'legacy_conn' in locals() and legacy_conn:
            legacy_conn.close()
            print("🔒 레거시 DB 연결 안전 종료")

if __name__ == "__main__":
    diagnose_missing_data() 