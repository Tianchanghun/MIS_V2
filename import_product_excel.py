#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
상품List.xlsx 파일 임포트
기존 코드 체계를 활용하여 엑셀 데이터를 상품으로 등록
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from app import create_app
from app.common.models import db, Product, ProductDetail, Code

app = create_app()

def analyze_excel_file():
    """엑셀 파일 구조 분석"""
    excel_path = r"c:\Users\splas\Documents\카카오톡 받은 파일\상품List.xlsx"
    
    try:
        # 엑셀 파일 읽기
        print("=== 상품List.xlsx 파일 분석 ===")
        
        # 시트 목록 확인
        excel_file = pd.ExcelFile(excel_path)
        print(f"시트 목록: {excel_file.sheet_names}")
        
        # 각 시트별 데이터 확인
        for sheet_name in excel_file.sheet_names:
            print(f"\n[시트: {sheet_name}]")
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            
            print(f"  - 행 수: {len(df)}")
            print(f"  - 열 수: {len(df.columns)}")
            print(f"  - 컬럼명: {list(df.columns)}")
            
            # 첫 5행 데이터 미리보기
            print(f"  - 첫 5행 미리보기:")
            print(df.head().to_string(index=False))
            
            # 빈 값 확인
            print(f"  - 빈 값 개수:")
            null_counts = df.isnull().sum()
            for col, null_count in null_counts.items():
                if null_count > 0:
                    print(f"    {col}: {null_count}개")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {excel_path}")
        print("파일 경로를 확인해주세요.")
        return False
    except Exception as e:
        print(f"❌ 엑셀 파일 분석 실패: {e}")
        return False

def get_or_create_code(group_name, code_value, code_name):
    """코드 조회 또는 생성"""
    with app.app_context():
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
                sort=next_sort,
                use_yn='Y',
                created_by='excel_import',
                updated_by='excel_import'
            )
            
            db.session.add(new_code)
            db.session.commit()
            
            print(f"✅ 새 코드 생성: {group_name} > {code_value} ({code_name})")
            return new_code.seq
            
        except Exception as e:
            print(f"❌ 코드 생성 실패: {e}")
            db.session.rollback()
            return None

def import_products_from_excel():
    """엑셀에서 상품 데이터 임포트"""
    excel_path = r"c:\Users\splas\Documents\카카오톡 받은 파일\상품List.xlsx"
    
    try:
        print("\n=== 상품 데이터 임포트 시작 ===")
        
        # 엑셀 읽기 (첫 번째 시트 사용)
        df = pd.read_excel(excel_path)
        
        print(f"총 {len(df)}개 상품 데이터 발견")
        
        imported_count = 0
        skipped_count = 0
        
        with app.app_context():
            # 기존 레거시 상품 정리 (선택사항)
            print("\n기존 레거시 상품 정리를 하시겠습니까? (y/n): ", end="")
            clear_legacy = input().lower().strip() == 'y'
            
            if clear_legacy:
                Product.query.filter(Product.legacy_seq.isnot(None)).delete()
                db.session.commit()
                print("✅ 기존 레거시 상품 정리 완료")
            
            # 컬럼 매핑 (실제 엑셀 구조에 맞게 수정 필요)
            column_mapping = {
                '상품명': 'product_name',
                '브랜드': 'brand',
                '품목': 'category', 
                '타입': 'type',
                '년도': 'year',
                '가격': 'price',
                '설명': 'description'
            }
            
            for index, row in df.iterrows():
                try:
                    # 필수 필드 확인
                    product_name = row.get('상품명') or row.get(df.columns[0])  # 첫 번째 컬럼을 상품명으로 가정
                    
                    if pd.isna(product_name) or not str(product_name).strip():
                        skipped_count += 1
                        continue
                    
                    # 코드 값들 처리
                    brand_name = row.get('브랜드', '')
                    category_name = row.get('품목', '')
                    type_name = row.get('타입', '') 
                    year_value = row.get('년도', '')
                    price_value = row.get('가격', 0)
                    description = row.get('설명', '')
                    
                    # 코드 SEQ 가져오기 또는 생성
                    brand_seq = None
                    category_seq = None
                    type_seq = None
                    year_seq = None
                    
                    if brand_name and not pd.isna(brand_name):
                        brand_seq = get_or_create_code('브랜드', brand_name, brand_name)
                    
                    if category_name and not pd.isna(category_name):
                        category_seq = get_or_create_code('제품구분', category_name, category_name)
                    
                    if type_name and not pd.isna(type_name):
                        type_seq = get_or_create_code('타입', type_name, type_name)
                    
                    if year_value and not pd.isna(year_value):
                        year_str = str(year_value).strip()
                        if year_str:
                            year_seq = get_or_create_code('년도', year_str, f"20{year_str}" if len(year_str) == 2 else year_str)
                    
                    # 가격 처리
                    try:
                        price = float(price_value) if not pd.isna(price_value) else 0
                    except:
                        price = 0
                    
                    # 상품 생성
                    new_product = Product(
                        company_id=1,  # 에이원으로 고정
                        brand_code_seq=brand_seq,
                        category_code_seq=category_seq,
                        type_code_seq=type_seq,
                        year_code_seq=year_seq,
                        product_name=str(product_name).strip(),
                        price=price,
                        description=str(description) if not pd.isna(description) else '',
                        is_active=True,
                        created_by='excel_import',
                        updated_by='excel_import'
                    )
                    
                    db.session.add(new_product)
                    imported_count += 1
                    
                    if imported_count % 50 == 0:
                        db.session.commit()
                        print(f"  진행률: {imported_count}/{len(df)}")
                
                except Exception as e:
                    print(f"❌ 행 {index+1} 처리 실패: {e}")
                    skipped_count += 1
                    db.session.rollback()
                    continue
            
            db.session.commit()
            
            print(f"\n=== 임포트 완료 ===")
            print(f"✅ 성공: {imported_count}개")
            print(f"⚠️ 실패: {skipped_count}개")
            
        return imported_count > 0
        
    except Exception as e:
        print(f"❌ 임포트 실패: {e}")
        return False

def verify_imported_data():
    """임포트된 데이터 검증"""
    with app.app_context():
        print("\n=== 임포트 결과 검증 ===")
        
        # 전체 상품 통계
        total_products = Product.query.count()
        excel_products = Product.query.filter_by(created_by='excel_import').count()
        
        print(f"총 상품: {total_products}개")
        print(f"엑셀 임포트: {excel_products}개")
        
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
        
        print(f"\n매핑 상태:")
        print(f"  - 브랜드: {mapped_brand}/{excel_products}")
        print(f"  - 품목: {mapped_category}/{excel_products}")
        print(f"  - 타입: {mapped_type}/{excel_products}")
        print(f"  - 년도: {mapped_year}/{excel_products}")
        
        # 샘플 확인
        sample_products = Product.query.filter_by(created_by='excel_import').limit(5).all()
        print(f"\n샘플 상품 5개:")
        for product in sample_products:
            print(f"  - {product.product_name}")
            print(f"    브랜드: {product.brand_code.code_name if product.brand_code else 'None'}")
            print(f"    품목: {product.category_code.code_name if product.category_code else 'None'}")
            print(f"    타입: {product.type_code.code_name if product.type_code else 'None'}")
            print(f"    년도: {product.year_code.code_name if product.year_code else 'None'}")

def main():
    """메인 실행 함수"""
    print("=== 상품 엑셀 임포트 도구 ===")
    
    # 1. 엑셀 파일 분석
    if not analyze_excel_file():
        return
    
    # 2. 임포트 진행 여부 확인
    print(f"\n엑셀 파일 분석이 완료되었습니다.")
    print(f"상품 데이터를 임포트하시겠습니까? (y/n): ", end="")
    
    proceed = input().lower().strip() == 'y'
    if not proceed:
        print("임포트를 취소했습니다.")
        return
    
    # 3. 상품 임포트
    if import_products_from_excel():
        # 4. 결과 검증
        verify_imported_data()
        print(f"\n✅ 엑셀 임포트 완료! 웹 페이지를 새로고침하여 확인하세요.")
    else:
        print(f"\n❌ 엑셀 임포트 실패")

if __name__ == '__main__':
    main() 