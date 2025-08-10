#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db
import pyodbc

def check_real_legacy_data():
    """실제 레거시 DB 연결하여 진짜 데이터 수 확인"""
    print("🔍 실제 레거시 DB 연결 및 데이터 수 확인")
    print("=" * 60)
    
    # 1. 레거시 MS SQL 연결 시도
    print("1️⃣ 레거시 MS SQL 연결 시도")
    
    # 다양한 연결 방법 시도
    connection_strings = [
        "DRIVER={ODBC Driver 17 for SQL Server};SERVER=127.0.0.1;DATABASE=mis;UID=sa;PWD=Dbwjd00*;",
        "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=mis;UID=sa;PWD=Dbwjd00*;",
        "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost,1433;DATABASE=mis;UID=sa;PWD=Dbwjd00*;",
        "DRIVER={SQL Server};SERVER=127.0.0.1;DATABASE=mis;UID=sa;PWD=Dbwjd00*;",
        "DRIVER={SQL Server};SERVER=localhost;DATABASE=mis;UID=sa;PWD=Dbwjd00*;",
        "DRIVER={ODBC Driver 17 for SQL Server};SERVER=.;DATABASE=mis;UID=sa;PWD=Dbwjd00*;",
        "DRIVER={ODBC Driver 17 for SQL Server};SERVER=(local);DATABASE=mis;UID=sa;PWD=Dbwjd00*;",
    ]
    
    legacy_conn = None
    for i, conn_str in enumerate(connection_strings, 1):
        try:
            print(f"   시도 {i}: {conn_str.split(';')[1]}")
            legacy_conn = pyodbc.connect(conn_str, timeout=10)
            print(f"   ✅ MS SQL 연결 성공!")
            break
        except Exception as e:
            print(f"   ❌ 연결 실패: {str(e)[:100]}...")
            continue
    
    if not legacy_conn:
        print("\n❌ 모든 연결 시도 실패!")
        print("💡 가능한 원인:")
        print("   1. SQL Server 서비스가 실행되지 않음")
        print("   2. 방화벽에서 1433 포트 차단")
        print("   3. SQL Server 인증 모드 문제")
        print("   4. 사용자 계정/비밀번호 문제")
        print("\n🔧 해결 방법:")
        print("   1. SQL Server Management Studio에서 연결 확인")
        print("   2. SQL Server Configuration Manager에서 TCP/IP 활성화 확인")
        print("   3. Windows 서비스에서 SQL Server 서비스 상태 확인")
        return
    
    try:
        legacy_cursor = legacy_conn.cursor()
        
        # 2. 실제 레거시 데이터 수 확인
        print("\n2️⃣ 실제 레거시 데이터 수 확인")
        
        # 제품 마스터 수 확인
        legacy_cursor.execute("SELECT COUNT(*) as count FROM tbl_Product WHERE UseYn = 'Y'")
        product_count = legacy_cursor.fetchone()[0]
        print(f"   📊 tbl_Product (활성 제품): {product_count}개")
        
        # 제품 상세 수 확인
        legacy_cursor.execute("SELECT COUNT(*) as count FROM tbl_Product_DTL WHERE Status = 'Active'")
        detail_count = legacy_cursor.fetchone()[0]
        print(f"   📊 tbl_Product_DTL (활성 상세): {detail_count}개")
        
        # 회사별 분포 확인
        legacy_cursor.execute("""
            SELECT c.CodeName, COUNT(*) as count
            FROM tbl_Product p
            LEFT JOIN tbl_Code c ON p.Company = c.Seq
            WHERE p.UseYn = 'Y'
            GROUP BY c.CodeName
            ORDER BY count DESC
        """)
        company_dist = legacy_cursor.fetchall()
        
        print(f"   📈 회사별 제품 분포:")
        for company in company_dist:
            print(f"      {company[0] or 'NULL'}: {company[1]}개")
        
        # 브랜드별 분포 확인
        legacy_cursor.execute("""
            SELECT c.CodeName, COUNT(*) as count
            FROM tbl_Product p
            LEFT JOIN tbl_Code c ON p.Brand = c.Seq
            WHERE p.UseYn = 'Y'
            GROUP BY c.CodeName
            ORDER BY count DESC
            LIMIT 10
        """)
        brand_dist = legacy_cursor.fetchall()
        
        print(f"   📈 브랜드별 제품 분포 (상위 10개):")
        for brand in brand_dist:
            print(f"      {brand[0] or 'NULL'}: {brand[1]}개")
        
        # 3. 현재 도커 DB와 비교
        print("\n3️⃣ 현재 도커 DB와 비교")
        
        app = create_app()
        with app.app_context():
            result = db.session.execute(db.text("""
                SELECT 
                    COUNT(DISTINCT p.id) as product_count,
                    COUNT(pd.id) as detail_count
                FROM products p
                LEFT JOIN product_details pd ON p.id = pd.product_id
                WHERE p.company_id = 1
            """))
            
            current = result.fetchone()
            print(f"   📊 현재 도커 DB:")
            print(f"      제품: {current.product_count}개")
            print(f"      상세: {current.detail_count}개")
            
            print(f"\n   📊 차이:")
            print(f"      제품: {product_count - current.product_count}개 부족")
            print(f"      상세: {detail_count - current.detail_count}개 부족")
        
        # 4. 샘플 데이터 확인
        print("\n4️⃣ 레거시 샘플 데이터 확인")
        
        legacy_cursor.execute("""
            SELECT TOP 10
                p.Seq,
                p.ProdName,
                p.ProdTagAmt,
                cb.CodeName as Company,
                bb.CodeName as Brand
            FROM tbl_Product p
            LEFT JOIN tbl_Code cb ON p.Company = cb.Seq
            LEFT JOIN tbl_Code bb ON p.Brand = bb.Seq
            WHERE p.UseYn = 'Y'
            ORDER BY p.Seq DESC
        """)
        
        samples = legacy_cursor.fetchall()
        print(f"   📋 최신 제품 10개:")
        for sample in samples:
            print(f"      {sample[0]}. {sample[1]}")
            print(f"         가격: {sample[2]:,}원" if sample[2] else "가격 없음")
            print(f"         회사: {sample[3] or 'NULL'} / 브랜드: {sample[4] or 'NULL'}")
        
        # 5. 상세 데이터 샘플
        legacy_cursor.execute("""
            SELECT TOP 10
                pd.Seq,
                pd.StdDivProdCode,
                pd.ProductName,
                LEN(pd.StdDivProdCode) as CodeLength
            FROM tbl_Product_DTL pd
            WHERE pd.Status = 'Active' AND pd.StdDivProdCode IS NOT NULL
            ORDER BY pd.Seq DESC
        """)
        
        detail_samples = legacy_cursor.fetchall()
        print(f"\n   📋 최신 상세 10개:")
        for detail in detail_samples:
            print(f"      {detail[0]}. {detail[2]}")
            print(f"         자가코드: {detail[1]} ({detail[3]}자리)")
        
        print(f"\n🚨 결론: 레거시 DB에 {product_count}개 제품, {detail_count}개 상세가 있지만")
        print(f"       현재 도커에는 {current.product_count}개 제품, {current.detail_count}개 상세만 있음!")
        print(f"🔧 전체 데이터를 다시 가져와야 합니다!")
        
    except Exception as e:
        print(f"❌ 쿼리 실행 오류: {e}")
    finally:
        if legacy_conn:
            legacy_conn.close()

if __name__ == "__main__":
    check_real_legacy_data() 