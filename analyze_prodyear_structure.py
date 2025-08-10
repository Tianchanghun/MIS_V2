#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProdYear 구조 정확한 분석
"""

import sys
import os
import pyodbc
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def analyze_prodyear_structure():
    """레거시 ProdYear의 실제 구조 분석"""
    
    # 레거시 DB 연결
    legacy_conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=210.109.96.74,2521;"
        "DATABASE=db_mis;"
        "UID=user_mis;"
        "PWD=user_mis!@12;"
        "ApplicationIntent=ReadOnly;",
        timeout=30
    )
    
    try:
        print("=== ProdYear 구조 정확한 분석 ===\n")
        
        cursor = legacy_conn.cursor()
        
        # 1. tbl_code에서 년도 관련 모든 그룹 확인
        print("📅 tbl_code 년도 관련 그룹들:")
        cursor.execute("""
            SELECT DISTINCT Code, COUNT(*) as CodeCount
            FROM tbl_code 
            WHERE Code LIKE '%Y%' OR CodeName LIKE '%년%' OR CodeName LIKE '%20%'
            GROUP BY Code
            ORDER BY Code
        """)
        
        for row in cursor.fetchall():
            print(f"   {row.Code}: {row.CodeCount}개")
        
        # 2. YR 그룹의 모든 코드 확인
        print(f"\n📋 YR 그룹 상세:")
        cursor.execute("""
            SELECT Seq, CodeSeq, CodeName, CodeInfo
            FROM tbl_code 
            WHERE Code = 'YR'
            ORDER BY CodeSeq
        """)
        
        for row in cursor.fetchall():
            print(f"   Seq {row.Seq}: CodeSeq {row.CodeSeq}, Name '{row.CodeName}', Info '{row.CodeInfo}'")
        
        # 3. ProdYear 값들과 빈도 분석
        print(f"\n📊 ProdYear 값 분석:")
        cursor.execute("""
            SELECT ProdYear, COUNT(*) as ProductCount
            FROM tbl_Product 
            WHERE ProdYear IS NOT NULL AND ProdYear != ''
            GROUP BY ProdYear
            ORDER BY ProdYear
        """)
        
        prod_years = []
        for row in cursor.fetchall():
            prod_years.append((row.ProdYear, row.ProductCount))
            print(f"   ProdYear '{row.ProdYear}': {row.ProductCount}개 상품")
        
        # 4. ProdYear 값이 tbl_code에 있는지 확인
        print(f"\n🔍 ProdYear 값들이 tbl_code에 존재하는지 확인:")
        
        for prod_year, count in prod_years[:10]:  # 처음 10개만 확인
            cursor.execute("""
                SELECT TOP 1 Seq, Code, CodeSeq, CodeName
                FROM tbl_code 
                WHERE CodeSeq = ? OR Code = ? OR CodeName LIKE ?
            """, prod_year, prod_year, f'%{prod_year}%')
            
            result = cursor.fetchone()
            if result:
                print(f"   ProdYear '{prod_year}' 발견: Seq {result.Seq}, Code '{result.Code}', CodeSeq {result.CodeSeq}, Name '{result.CodeName}'")
            else:
                print(f"   ProdYear '{prod_year}' ❌ tbl_code에 없음")
        
        # 5. 실제 년도 문자열 패턴 확인
        print(f"\n🔍 년도 관련 코드들 (CodeName 기준):")
        cursor.execute("""
            SELECT TOP 20 Seq, Code, CodeSeq, CodeName
            FROM tbl_code 
            WHERE CodeName LIKE '%201%' OR CodeName LIKE '%202%'
               OR CodeName LIKE '%2018%' OR CodeName LIKE '%2014%'
               OR CodeName LIKE '%18%' OR CodeName LIKE '%14%'
            ORDER BY Code, CodeSeq
        """)
        
        for row in cursor.fetchall():
            print(f"   Seq {row.Seq}: Code '{row.Code}', CodeSeq {row.CodeSeq}, Name '{row.CodeName}'")
        
        # 6. 샘플 상품의 ProdYear와 매칭 시도
        print(f"\n🔍 샘플 상품 ProdYear 매칭 시도:")
        cursor.execute("""
            SELECT TOP 5 p.Seq, p.ProdName, p.ProdYear, p.Brand, p.ProdGroup, p.ProdType
            FROM tbl_Product p
            WHERE p.ProdYear IS NOT NULL AND p.ProdYear != ''
            ORDER BY p.Seq
        """)
        
        for row in cursor.fetchall():
            print(f"\n   상품: {row.ProdName}")
            print(f"   ProdYear: '{row.ProdYear}'")
            
            # 해당 ProdYear로 년도 코드 찾기 시도
            cursor.execute("""
                SELECT Seq, Code, CodeSeq, CodeName
                FROM tbl_code 
                WHERE (CodeName LIKE ? OR CodeName = ? OR 
                       (Code LIKE '%YR%' AND CodeSeq = ?) OR
                       (Code LIKE '%Y%' AND CodeName LIKE ?))
            """, f'%{row.ProdYear}%', f'20{row.ProdYear}', row.ProdYear, f'%20{row.ProdYear}%')
            
            matches = cursor.fetchall()
            if matches:
                for match in matches:
                    print(f"      매칭: Seq {match.Seq}, Code '{match.Code}', CodeSeq {match.CodeSeq}, Name '{match.CodeName}'")
            else:
                print(f"      ❌ 매칭되는 년도 코드 없음")
        
        legacy_conn.close()
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if legacy_conn:
            legacy_conn.close()

if __name__ == "__main__":
    analyze_prodyear_structure() 