#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
엑셀 임포트된 상품들의 코드 매핑 수정
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from app import create_app
from app.common.models import db, Product, Code

app = create_app()

def get_or_create_code(group_name, code_value, code_name):
    """코드 조회 또는 생성 (use_yn 제거)"""
    # 부모 그룹 찾기
    parent_group = Code.query.filter_by(code_name=group_name, depth=0).first()
    if not parent_group:
        print(f"⚠️ '{group_name}' 그룹을 찾을 수 없습니다.")
        return None
    
    # 기존 코드 찾기
    existing_code = Code.query.filter_by(
        parent_seq=parent_group.seq,
        code=str(code_value)
    ).first()
    
    if existing_code:
        return existing_code.seq
    
    # 새 코드 생성
    try:
        # 마지막 sort 번호 찾기
        last_code = Code.query.filter_by(parent_seq=parent_group.seq).order_by(Code.sort.desc()).first()
        next_sort = (last_code.sort + 1) if last_code else 1
        
        new_code = Code(
            parent_seq=parent_group.seq,
            code=str(code_value),
            code_name=str(code_name),
            depth=1,
            sort=next_sort
        )
        
        db.session.add(new_code)
        db.session.commit()
        
        print(f"✅ 새 코드 생성: {group_name} > {code_value} ({code_name})")
        return new_code.seq
        
    except Exception as e:
        print(f"❌ 코드 생성 실패: {e}")
        db.session.rollback()
        return None

def fix_excel_product_codes():
    """엑셀 임포트된 상품들의 코드 매핑 수정"""
    print("=== 엑셀 상품 코드 매핑 수정 ===")
    
    with app.app_context():
        # 엑셀 임포트된 상품들 조회
        excel_products = Product.query.filter_by(created_by='excel_import').all()
        print(f"엑셀 임포트 상품: {len(excel_products)}개")
        
        # 엑셀 파일 다시 읽기
        excel_path = r"c:\Users\splas\Documents\카카오톡 받은 파일\상품List.xlsx"
        df = pd.read_excel(excel_path)
        
        print(f"엑셀 파일 행 수: {len(df)}")
        print(f"엑셀 컬럼: {list(df.columns)}")
        
        # 1. 고유 값들로부터 코드 생성
        print("\n[1단계] 고유 값들로부터 코드 생성...")
        
        # 브랜드 코드 생성
        if '브랜드' in df.columns:
            unique_brands = df['브랜드'].dropna().unique()
            print(f"고유 브랜드: {len(unique_brands)}개")
            for brand in unique_brands:
                get_or_create_code('브랜드', str(brand), str(brand))
        
        # 품목 코드 생성
        if '품목' in df.columns:
            unique_categories = df['품목'].dropna().unique()
            print(f"고유 품목: {len(unique_categories)}개")
            for category in unique_categories:
                get_or_create_code('제품구분', str(category), str(category))
        
        # 타입 코드 생성
        if '타입' in df.columns:
            unique_types = df['타입'].dropna().unique()
            print(f"고유 타입: {len(unique_types)}개")
            for type_val in unique_types:
                get_or_create_code('타입', str(type_val), str(type_val))
        
        # 년도 코드 생성
        if '년도' in df.columns:
            unique_years = df['년도'].dropna().unique()
            print(f"고유 년도: {len(unique_years)}개")
            for year in unique_years:
                year_str = str(year).strip()
                if year_str:
                    get_or_create_code('년도', year_str, f"20{year_str}" if len(year_str) == 2 else year_str)
        
        # 2. 상품별 매핑 업데이트
        print(f"\n[2단계] 상품별 코드 매핑 업데이트...")
        
        updated_count = 0
        
        # 엑셀 데이터와 상품명으로 매칭
        for index, row in df.iterrows():
            try:
                product_name = row.get('상품명') or row.get(df.columns[0])
                if pd.isna(product_name):
                    continue
                
                # 해당 상품 찾기
                product = Product.query.filter(
                    Product.created_by == 'excel_import',
                    Product.product_name == str(product_name).strip()
                ).first()
                
                if not product:
                    continue
                
                updated = False
                
                # 브랜드 매핑
                if '브랜드' in row and not pd.isna(row['브랜드']):
                    brand_seq = get_or_create_code('브랜드', str(row['브랜드']), str(row['브랜드']))
                    if brand_seq and product.brand_code_seq != brand_seq:
                        product.brand_code_seq = brand_seq
                        updated = True
                
                # 품목 매핑
                if '품목' in row and not pd.isna(row['품목']):
                    category_seq = get_or_create_code('제품구분', str(row['품목']), str(row['품목']))
                    if category_seq and product.category_code_seq != category_seq:
                        product.category_code_seq = category_seq
                        updated = True
                
                # 타입 매핑
                if '타입' in row and not pd.isna(row['타입']):
                    type_seq = get_or_create_code('타입', str(row['타입']), str(row['타입']))
                    if type_seq and product.type_code_seq != type_seq:
                        product.type_code_seq = type_seq
                        updated = True
                
                # 년도 매핑
                if '년도' in row and not pd.isna(row['년도']):
                    year_str = str(row['년도']).strip()
                    if year_str:
                        year_seq = get_or_create_code('년도', year_str, f"20{year_str}" if len(year_str) == 2 else year_str)
                        if year_seq and product.year_code_seq != year_seq:
                            product.year_code_seq = year_seq
                            updated = True
                
                if updated:
                    product.updated_by = 'code_fix'
                    updated_count += 1
                    
                    if updated_count % 50 == 0:
                        db.session.commit()
                        print(f"  진행률: {updated_count}/{len(df)}")
                
            except Exception as e:
                print(f"❌ 행 {index+1} 처리 실패: {e}")
                continue
        
        db.session.commit()
        print(f"\n✅ 코드 매핑 업데이트 완료: {updated_count}개")

def verify_fixed_data():
    """수정된 데이터 검증"""
    with app.app_context():
        print("\n=== 수정 결과 검증 ===")
        
        # 전체 상품 통계
        excel_products = Product.query.filter_by(created_by='excel_import').count()
        
        # 매핑 상태 확인
        mapped_brand = Product.query.filter(
            Product.created_by == 'excel_import',
            Product.brand_code_seq.isnot(None)
        ).count()
        
        mapped_category = Product.query.filter(
            Product.created_by == 'excel_import',
            Product.category_code_seq.isnot(None)
        ).count()
        
        mapped_type = Product.query.filter(
            Product.created_by == 'excel_import',
            Product.type_code_seq.isnot(None)
        ).count()
        
        mapped_year = Product.query.filter(
            Product.created_by == 'excel_import',
            Product.year_code_seq.isnot(None)
        ).count()
        
        print(f"엑셀 임포트 상품: {excel_products}개")
        print(f"\n매핑 상태:")
        print(f"  - 브랜드: {mapped_brand}/{excel_products} ({mapped_brand/excel_products*100:.1f}%)")
        print(f"  - 품목: {mapped_category}/{excel_products} ({mapped_category/excel_products*100:.1f}%)")
        print(f"  - 타입: {mapped_type}/{excel_products} ({mapped_type/excel_products*100:.1f}%)")
        print(f"  - 년도: {mapped_year}/{excel_products} ({mapped_year/excel_products*100:.1f}%)")
        
        # 샘플 확인
        sample_products = Product.query.filter_by(created_by='excel_import').limit(5).all()
        print(f"\n수정된 샘플 5개:")
        for product in sample_products:
            print(f"  - {product.product_name}")
            print(f"    브랜드: {product.brand_code.code_name if product.brand_code else 'None'}")
            print(f"    품목: {product.category_code.code_name if product.category_code else 'None'}")
            print(f"    타입: {product.type_code.code_name if product.type_code else 'None'}")
            print(f"    년도: {product.year_code.code_name if product.year_code else 'None'}")

def main():
    """메인 실행 함수"""
    print("=== 엑셀 상품 코드 매핑 수정 도구 ===")
    
    # 1. 코드 매핑 수정
    fix_excel_product_codes()
    
    # 2. 결과 검증
    verify_fixed_data()
    
    print("\n✅ 코드 매핑 수정 완료! 웹 페이지를 새로고침하여 확인하세요.")

if __name__ == '__main__':
    with app.app_context():
        main() 