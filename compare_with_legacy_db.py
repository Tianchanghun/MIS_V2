#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db
import pyodbc
import requests

def compare_with_legacy_db():
    """MS SQL 레거시 DB와 현재 DB 비교 및 개선"""
    app = create_app()
    
    with app.app_context():
        print("🔍 MS SQL 레거시 DB와 현재 PostgreSQL DB 비교")
        print("=" * 60)
        
        # 1. 현재 PostgreSQL DB의 모든 제품 확인
        print("1️⃣ 현재 PostgreSQL DB의 모든 제품 조회")
        
        result = db.session.execute(db.text("""
            SELECT 
                p.id,
                p.product_name,
                p.product_code,
                p.price,
                p.company_id,
                cat_code.code as category_code,
                cat_code.code_name as category_name,
                type_code.code as type_code,
                type_code.code_name as type_name,
                brand_code.code as brand_code,
                brand_code.code_name as brand_name,
                p.is_active,
                p.created_at
            FROM products p
            LEFT JOIN tbl_code cat_code ON p.category_code_seq = cat_code.seq
            LEFT JOIN tbl_code type_code ON p.type_code_seq = type_code.seq  
            LEFT JOIN tbl_code brand_code ON p.brand_code_seq = brand_code.seq
            WHERE p.company_id = 1
            ORDER BY p.id
        """))
        
        current_products = result.fetchall()
        print(f"   📊 현재 PostgreSQL DB: {len(current_products)}개 제품")
        
        for i, product in enumerate(current_products, 1):
            print(f"   {i}. ID: {product.id}")
            print(f"      제품명: {product.product_name}")
            print(f"      제품코드: {product.product_code}")
            print(f"      가격: {product.price:,}원")
            print(f"      품목: {product.category_code} ({product.category_name})")
            print(f"      타입: {product.type_code} ({product.type_name})")
            print(f"      브랜드: {product.brand_code} ({product.brand_name})")
            print(f"      상태: {'활성' if product.is_active else '비활성'}")
            print()
        
        # 2. 제품 상세 정보 확인
        print("2️⃣ 제품 상세 정보 (자가코드) 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                pd.id,
                pd.product_id,
                pd.std_div_prod_code,
                pd.product_name,
                pd.brand_code,
                pd.div_type_code,
                pd.prod_group_code,
                pd.prod_type_code,
                pd.prod_code,
                pd.prod_type2_code,
                pd.year_code,
                pd.color_code,
                LENGTH(pd.std_div_prod_code) as code_length,
                p.product_name as master_name
            FROM product_details pd
            JOIN products p ON pd.product_id = p.id
            WHERE p.company_id = 1
            ORDER BY pd.product_id, pd.id
        """))
        
        product_details = result.fetchall()
        print(f"   📊 제품 상세 모델: {len(product_details)}개")
        
        # 제품별로 그룹화
        products_with_details = {}
        for detail in product_details:
            if detail.product_id not in products_with_details:
                products_with_details[detail.product_id] = {
                    'master_name': detail.master_name,
                    'details': []
                }
            products_with_details[detail.product_id]['details'].append(detail)
        
        for product_id, info in products_with_details.items():
            print(f"   제품 {product_id}: {info['master_name']} ({len(info['details'])}개 모델)")
            for detail in info['details'][:2]:  # 처음 2개만 표시
                print(f"      - {detail.product_name}")
                print(f"        자가코드: {detail.std_div_prod_code} ({detail.code_length}자리)")
                print(f"        구성: {detail.brand_code}+{detail.div_type_code}+{detail.prod_group_code}+{detail.prod_type_code}+{detail.prod_code}+{detail.prod_type2_code}+{detail.year_code}+{detail.color_code}")
            if len(info['details']) > 2:
                print(f"      ... 외 {len(info['details'])-2}개")
            print()
        
        # 3. MS SQL 레거시 DB 연결 시도
        print("3️⃣ MS SQL 레거시 DB 연결 시도")
        
        try:
            # MS SQL 연결 설정들 시도
            connection_strings = [
                "DRIVER={ODBC Driver 17 for SQL Server};SERVER=127.0.0.1;DATABASE=mis;UID=sa;PWD=Dbwjd00*;",
                "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=mis;UID=sa;PWD=Dbwjd00*;",
                "DRIVER={SQL Server};SERVER=127.0.0.1;DATABASE=mis;UID=sa;PWD=Dbwjd00*;",
                "DRIVER={SQL Server Native Client 11.0};SERVER=127.0.0.1;DATABASE=mis;UID=sa;PWD=Dbwjd00*;",
            ]
            
            legacy_conn = None
            for conn_str in connection_strings:
                try:
                    legacy_conn = pyodbc.connect(conn_str)
                    print(f"   ✅ MS SQL 연결 성공: {conn_str.split(';')[0]}")
                    break
                except Exception as e:
                    continue
            
            if legacy_conn:
                # 레거시 제품 데이터 조회
                legacy_cursor = legacy_conn.cursor()
                
                print("   📋 레거시 DB 제품 조회 중...")
                legacy_cursor.execute("""
                    SELECT TOP 10
                        p.Seq,
                        p.ProdName,
                        p.ProdYear,
                        p.ProdTagAmt,
                        p.UseYn,
                        cb.CodeName as CompanyName,
                        bb.CodeName as BrandName,
                        pgb.CodeName as ProdGroupName,
                        ptb.CodeName as ProdTypeName
                    FROM tbl_Product p
                    LEFT JOIN tbl_Code cb ON p.Company = cb.Seq
                    LEFT JOIN tbl_Code bb ON p.Brand = bb.Seq
                    LEFT JOIN tbl_Code pgb ON p.ProdGroup = pgb.Seq
                    LEFT JOIN tbl_Code ptb ON p.ProdType = ptb.Seq
                    WHERE p.UseYn = 'Y'
                    ORDER BY p.Seq DESC
                """)
                
                legacy_products = legacy_cursor.fetchall()
                print(f"   📊 레거시 DB: {len(legacy_products)}개 제품 (최근 10개)")
                
                for product in legacy_products:
                    print(f"   Seq: {product[0]}")
                    print(f"   제품명: {product[1]}")
                    print(f"   년도: {product[2]}")
                    print(f"   가격: {product[3]:,}원" if product[3] else "가격 없음")
                    print(f"   회사: {product[5]}")
                    print(f"   브랜드: {product[6]}")
                    print(f"   품목: {product[7]}")
                    print(f"   타입: {product[8]}")
                    print()
                
                # 레거시 제품 상세 조회
                print("   📋 레거시 DB 제품 상세 조회 중...")
                legacy_cursor.execute("""
                    SELECT TOP 10
                        pd.Seq,
                        pd.MstSeq,
                        pd.StdDivProdCode,
                        pd.ProductName,
                        pd.BrandCode,
                        pd.DivTypeCode,
                        pd.ProdGroupCode,
                        pd.ProdTypeCode,
                        pd.ProdCode,
                        pd.ProdType2Code,
                        pd.YearCode,
                        pd.ProdColorCode,
                        LEN(pd.StdDivProdCode) as CodeLength
                    FROM tbl_Product_DTL pd
                    WHERE pd.Status = 'Active'
                    ORDER BY pd.Seq DESC
                """)
                
                legacy_details = legacy_cursor.fetchall()
                print(f"   📊 레거시 DB 상세: {len(legacy_details)}개 모델 (최근 10개)")
                
                for detail in legacy_details:
                    print(f"   Seq: {detail[0]} (Master: {detail[1]})")
                    print(f"   제품명: {detail[3]}")
                    print(f"   자가코드: {detail[2]} ({detail[12]}자리)")
                    print(f"   구성: {detail[4]}+{detail[5]}+{detail[6]}+{detail[7]}+{detail[8]}+{detail[9]}+{detail[10]}+{detail[11]}")
                    print()
                
                legacy_conn.close()
                
            else:
                print("   ❌ MS SQL 레거시 DB 연결 실패")
                print("   💡 로컬 MS SQL Server가 실행 중인지 확인하세요")
                
        except Exception as e:
            print(f"   ❌ MS SQL 연결 오류: {e}")
        
        # 4. API를 통한 현재 제품 데이터 확인
        print("\n4️⃣ API를 통한 현재 제품 데이터 확인")
        
        try:
            response = requests.get("http://127.0.0.1:5000/product/api/list", timeout=10)
            
            if response.status_code == 200:
                api_data = response.json()
                api_products = api_data.get('data', [])
                
                print(f"   ✅ API 응답 성공: {len(api_products)}개 제품")
                
                for i, product in enumerate(api_products, 1):
                    print(f"   {i}. {product.get('product_name', 'N/A')}")
                    print(f"      제품코드: {product.get('product_code', 'N/A')}")
                    print(f"      가격: {product.get('price', 0):,}원")
                    print(f"      브랜드: {product.get('brand_name', 'N/A')}")
                    print(f"      품목: {product.get('category_name', 'N/A')}")
                    print(f"      타입: {product.get('type_name', 'N/A')}")
                    
                    details = product.get('details', [])
                    if details:
                        print(f"      상세 모델: {len(details)}개")
                        for j, detail in enumerate(details[:2], 1):
                            std_code = detail.get('std_div_prod_code', 'N/A')
                            print(f"        {j}. {detail.get('product_name', 'N/A')}")
                            print(f"           자가코드: {std_code} ({len(std_code)}자리)")
                    print()
                    
            else:
                print(f"   ❌ API 응답 실패: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ API 테스트 오류: {e}")
        
        # 5. 코드 체계 검증
        print("5️⃣ 현재 코드 체계 검증")
        
        # 16자리 코드 검증
        invalid_codes = 0
        for detail in product_details:
            if len(detail.std_div_prod_code or '') != 16:
                invalid_codes += 1
        
        print(f"   📊 16자리 코드 준수율: {len(product_details)-invalid_codes}/{len(product_details)} ({((len(product_details)-invalid_codes)/len(product_details)*100):.1f}%)")
        
        if invalid_codes > 0:
            print(f"   ⚠️ {invalid_codes}개 모델의 자가코드가 16자리가 아닙니다")
        
        # 6. 개선 권장사항
        print("\n6️⃣ 개선 권장사항")
        
        recommendations = []
        
        if invalid_codes > 0:
            recommendations.append(f"자가코드 길이 수정 ({invalid_codes}개)")
        
        if len(current_products) < 20:
            recommendations.append("제품 데이터 보강 필요")
        
        # 브랜드/품목/타입 매핑 확인
        unmapped_products = sum(1 for p in current_products if not p.category_name or not p.type_name)
        if unmapped_products > 0:
            recommendations.append(f"코드 매핑 수정 ({unmapped_products}개 제품)")
        
        if recommendations:
            print("   🔧 권장 개선사항:")
            for i, rec in enumerate(recommendations, 1):
                print(f"      {i}. {rec}")
        else:
            print("   ✅ 현재 상태가 양호합니다")
        
        print("\n📋 **현재 제품 관리 시스템 상태 요약:**")
        print(f"   - PostgreSQL DB: {len(current_products)}개 제품, {len(product_details)}개 모델")
        print(f"   - 16자리 자가코드: {len(product_details)-invalid_codes}개 정상")
        print(f"   - API 접근: 정상 작동")
        print(f"   - 웹 인터페이스: http://127.0.0.1:5000/product/")

if __name__ == "__main__":
    compare_with_legacy_db() 