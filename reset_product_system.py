#!/usr/bin/env python3
"""
상품 시스템 완전 초기화 및 재구축
- 기존 상품 DB 완전 삭제
- 코드 체계 기반 정확한 매핑
- 레거시 시스템 정확한 분석
"""
from app.common.models import db, Product, ProductDetail, ProductHistory, Code
from app import create_app
import pyodbc
import traceback

def reset_and_rebuild_product_system():
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 상품 시스템 완전 초기화 및 재구축")
            print("=" * 60)
            
            # 1. 기존 상품 데이터 완전 삭제
            print("🗑️ **1단계: 기존 데이터 완전 삭제**")
            
            # 외래키 순서대로 삭제
            deleted_history = ProductHistory.query.delete()
            deleted_details = ProductDetail.query.delete()
            deleted_products = Product.query.delete()
            
            db.session.commit()
            
            print(f"  ✅ ProductHistory 삭제: {deleted_history}개")
            print(f"  ✅ ProductDetail 삭제: {deleted_details}개")
            print(f"  ✅ Product 삭제: {deleted_products}개")
            
            # 2. 코드 체계 정확한 분석
            print(f"\n🗂️ **2단계: 코드 체계 정확한 분석**")
            
            # 브랜드 코드 그룹 분석
            brand_parent = Code.query.filter_by(code_name='브랜드', depth=0).first()
            if brand_parent:
                brand_codes = Code.query.filter_by(parent_seq=brand_parent.seq).all()
                print(f"  📦 브랜드 코드: {len(brand_codes)}개")
                for brand in brand_codes[:5]:
                    print(f"    - seq={brand.seq}, code='{brand.code}', name='{brand.code_name}'")
            
            # 제품구분(품목) 코드 그룹 분석
            category_parent = Code.query.filter_by(code_name='제품구분', depth=0).first()
            if category_parent:
                category_codes = Code.query.filter_by(parent_seq=category_parent.seq).all()
                print(f"  📂 품목 코드: {len(category_codes)}개")
                for category in category_codes[:5]:
                    print(f"    - seq={category.seq}, code='{category.code}', name='{category.code_name}'")
            
            # 타입 코드 그룹 분석
            type_parent = Code.query.filter_by(code_name='타입', depth=0).first()
            if type_parent:
                type_codes = Code.query.filter_by(parent_seq=type_parent.seq).all()
                print(f"  🔧 타입 코드: {len(type_codes)}개")
                for type_code in type_codes[:5]:
                    print(f"    - seq={type_code.seq}, code='{type_code.code}', name='{type_code.code_name}'")
            
            # 년도 코드 그룹 분석
            year_parent = Code.query.filter_by(code_name='년도', depth=0).first()
            if year_parent:
                year_codes = Code.query.filter_by(parent_seq=year_parent.seq).all()
                print(f"  📅 년도 코드: {len(year_codes)}개")
                for year in year_codes[:5]:
                    print(f"    - seq={year.seq}, code='{year.code}', name='{year.code_name}'")
            
            # 색상 코드 그룹 분석
            color_parent = Code.query.filter_by(code_name='색상', depth=0).first()
            if color_parent:
                color_codes = Code.query.filter_by(parent_seq=color_parent.seq).all()
                print(f"  🎨 색상 코드: {len(color_codes)}개")
            
            # 구분타입 코드 그룹 분석
            divtype_parent = Code.query.filter_by(code='DIVTYPE', depth=0).first()
            if divtype_parent:
                divtype_codes = Code.query.filter_by(parent_seq=divtype_parent.seq).all()
                print(f"  🔖 구분타입 코드: {len(divtype_codes)}개")
            
            # 제품코드 그룹 분석
            prodcode_parent = Code.query.filter_by(code_name='제품', depth=0).first()
            if prodcode_parent:
                prodcode_codes = Code.query.filter_by(parent_seq=prodcode_parent.seq).all()
                print(f"  🏷️ 제품코드: {len(prodcode_codes)}개")
            
            # 3. 레거시 DB 연결 및 정확한 분석
            print(f"\n🔗 **3단계: 레거시 DB 정확한 분석**")
            
            # MS SQL 연결
            connection_string = (
                "DRIVER={ODBC Driver 17 for SQL Server};"
                "SERVER=210.109.96.74,2521;"
                "DATABASE=db_mis;"
                "UID=user_mis;"
                "PWD=user_mis!@12;"
                "ApplicationIntent=ReadOnly;"
            )
            
            try:
                legacy_conn = pyodbc.connect(connection_string)
                legacy_cursor = legacy_conn.cursor()
                
                # 레거시 상품 구조 분석
                legacy_cursor.execute("""
                    SELECT TOP 5 
                        p.Seq, p.ProdName, p.ProdTagAmt, p.ProdYear,
                        p.Company, p.Brand, p.ProdGroup, p.ProdType, p.UseYn,
                        p.InsDate
                    FROM tbl_Product p
                    ORDER BY p.Seq DESC
                """)
                
                products = legacy_cursor.fetchall()
                print(f"  📦 레거시 상품 구조 분석 (최신 5개):")
                for product in products:
                    print(f"    - Seq={product.Seq}, Name='{product.ProdName}', Brand={product.Brand}")
                
                # 레거시 상품 상세 구조 분석
                legacy_cursor.execute("""
                    SELECT TOP 5
                        d.Seq, d.MstSeq, d.BrandCode, d.DivTypeCode, d.ProdGroupCode,
                        d.ProdTypeCode, d.ProdCode, d.ProdType2Code, d.YearCode, 
                        d.ProdColorCode, d.StdDivProdCode, d.ProductName
                    FROM tbl_Product_DTL d
                    ORDER BY d.Seq DESC
                """)
                
                details = legacy_cursor.fetchall()
                print(f"  🎨 레거시 상품 상세 구조 분석 (최신 5개):")
                for detail in details:
                    print(f"    - MstSeq={detail.MstSeq}, StdCode='{detail.StdDivProdCode}', Name='{detail.ProductName}'")
                
                # 4. 코드 매핑 테이블 생성
                print(f"\n🗺️ **4단계: 코드 매핑 테이블 생성**")
                
                # 브랜드 매핑 테이블
                brand_mapping = {}
                if brand_codes:
                    for brand in brand_codes:
                        # 레거시 브랜드 코드와 매칭
                        brand_mapping[brand.code] = brand.seq
                        brand_mapping[brand.code_name] = brand.seq
                
                print(f"  📦 브랜드 매핑: {len(brand_mapping)}개 항목")
                
                # 품목 매핑 테이블
                category_mapping = {}
                if category_codes:
                    for category in category_codes:
                        category_mapping[category.code] = category.seq
                        category_mapping[category.code_name] = category.seq
                
                print(f"  📂 품목 매핑: {len(category_mapping)}개 항목")
                
                # 5. 정확한 상품 데이터 마이그레이션
                print(f"\n📥 **5단계: 정확한 상품 데이터 마이그레이션**")
                
                # 레거시 상품 전체 조회 (정확한 매핑 포함)
                legacy_cursor.execute("""
                    SELECT 
                        p.Seq, p.ProdName, p.ProdTagAmt, p.ProdYear,
                        p.Company, p.Brand, p.ProdGroup, p.ProdType, p.UseYn,
                        p.InsDate, p.ProdInfo, p.ProdManual
                    FROM tbl_Product p
                    WHERE p.UseYn = 'Y'
                    ORDER BY p.Seq
                """)
                
                migrated_count = 0
                
                for row in legacy_cursor.fetchall():
                    # 브랜드 코드 정확한 매핑
                    brand_code_seq = None
                    if row.Brand:
                        # 브랜드 코드로 먼저 찾기
                        brand_match = next((b for b in brand_codes if b.code == str(row.Brand)), None)
                        if brand_match:
                            brand_code_seq = brand_match.seq
                        else:
                            # 브랜드명으로 찾기
                            brand_match = next((b for b in brand_codes if str(row.Brand) in b.code_name), None)
                            if brand_match:
                                brand_code_seq = brand_match.seq
                    
                    # 품목 코드 정확한 매핑
                    category_code_seq = None
                    if row.ProdGroup:
                        category_match = next((c for c in category_codes if c.code == str(row.ProdGroup)), None)
                        if category_match:
                            category_code_seq = category_match.seq
                    
                    # 타입 코드 정확한 매핑
                    type_code_seq = None
                    if row.ProdType:
                        type_match = next((t for t in type_codes if t.code == str(row.ProdType)), None)
                        if type_match:
                            type_code_seq = type_match.seq
                    
                    # 년도 코드 정확한 매핑
                    year_code_seq = None
                    if row.ProdYear:
                        year_match = next((y for y in year_codes if y.code == str(row.ProdYear)), None)
                        if year_match:
                            year_code_seq = year_match.seq
                    
                    # 상품 생성
                    product = Product(
                        legacy_seq=row.Seq,
                        company_id=row.Company or 1,
                        brand_code_seq=brand_code_seq,
                        category_code_seq=category_code_seq,
                        type_code_seq=type_code_seq,
                        year_code_seq=year_code_seq,
                        product_name=row.ProdName,
                        product_code=None,  # ProdCode 컬럼이 없으므로 None
                        price=row.ProdTagAmt,
                        description=row.ProdInfo,
                        manual_file_path=row.ProdManual,  # ProdManual 사용
                        is_active=(row.UseYn == 'Y'),
                        created_at=row.InsDate
                    )
                    
                    db.session.add(product)
                    migrated_count += 1
                    
                    if migrated_count % 100 == 0:
                        print(f"    📝 {migrated_count}개 상품 마이그레이션 진행 중...")
                        db.session.commit()
                
                db.session.commit()
                print(f"  ✅ 상품 마이그레이션 완료: {migrated_count}개")
                
                # 6. 상품 상세 (제품모델) 정확한 마이그레이션
                print(f"\n🎨 **6단계: 제품모델 정확한 마이그레이션**")
                
                legacy_cursor.execute("""
                    SELECT 
                        d.Seq, d.MstSeq, d.BrandCode, d.DivTypeCode, d.ProdGroupCode,
                        d.ProdTypeCode, d.ProdCode, d.ProdType2Code, d.YearCode, 
                        d.ProdColorCode, d.StdDivProdCode, d.ProductName, d.Status
                    FROM tbl_Product_DTL d
                    INNER JOIN tbl_Product p ON d.MstSeq = p.Seq
                    WHERE p.UseYn = 'Y' AND d.Status = 'Active'
                    ORDER BY d.Seq
                """)
                
                detail_count = 0
                
                for detail_row in legacy_cursor.fetchall():
                    # 상품 찾기
                    product = Product.query.filter_by(legacy_seq=detail_row.MstSeq).first()
                    if not product:
                        continue
                    
                    # 제품모델 생성
                    product_detail = ProductDetail(
                        product_id=product.id,
                        brand_code=detail_row.BrandCode,
                        div_type_code=detail_row.DivTypeCode,
                        prod_group_code=detail_row.ProdGroupCode,
                        prod_type_code=detail_row.ProdTypeCode,
                        prod_code=detail_row.ProdCode,
                        prod_type2_code=detail_row.ProdType2Code,
                        year_code=detail_row.YearCode[:1] if detail_row.YearCode else None,
                        color_code=detail_row.ProdColorCode,
                        std_div_prod_code=detail_row.StdDivProdCode,
                        product_name=detail_row.ProductName,
                        status=detail_row.Status,
                        legacy_seq=detail_row.Seq
                    )
                    
                    db.session.add(product_detail)
                    detail_count += 1
                    
                    if detail_count % 100 == 0:
                        print(f"    🎨 {detail_count}개 제품모델 마이그레이션 진행 중...")
                        db.session.commit()
                
                db.session.commit()
                print(f"  ✅ 제품모델 마이그레이션 완료: {detail_count}개")
                
                # 7. 최종 검증
                print(f"\n✅ **7단계: 최종 검증**")
                
                final_product_count = Product.query.count()
                final_detail_count = ProductDetail.query.count()
                
                products_with_brand = Product.query.filter(Product.brand_code_seq.isnot(None)).count()
                products_with_category = Product.query.filter(Product.category_code_seq.isnot(None)).count()
                products_with_type = Product.query.filter(Product.type_code_seq.isnot(None)).count()
                products_with_year = Product.query.filter(Product.year_code_seq.isnot(None)).count()
                
                print(f"  📦 최종 상품 수: {final_product_count}개")
                print(f"  🎨 최종 제품모델 수: {final_detail_count}개")
                print(f"  ✅ 브랜드 매핑: {products_with_brand}개 ({products_with_brand/final_product_count*100:.1f}%)")
                print(f"  ✅ 품목 매핑: {products_with_category}개 ({products_with_category/final_product_count*100:.1f}%)")
                print(f"  ✅ 타입 매핑: {products_with_type}개 ({products_with_type/final_product_count*100:.1f}%)")
                print(f"  ✅ 년도 매핑: {products_with_year}개 ({products_with_year/final_product_count*100:.1f}%)")
                
                # 샘플 확인
                print(f"\n🔍 **샘플 확인 (처음 3개)**")
                sample_products = Product.query.limit(3).all()
                
                for i, product in enumerate(sample_products, 1):
                    brand_name = "미지정"
                    category_name = "미지정"
                    type_name = "미지정"
                    year_name = "미지정"
                    
                    if product.brand_code_seq:
                        brand = Code.query.filter_by(seq=product.brand_code_seq).first()
                        if brand:
                            brand_name = brand.code_name
                    
                    if product.category_code_seq:
                        category = Code.query.filter_by(seq=product.category_code_seq).first()
                        if category:
                            category_name = category.code_name
                    
                    if product.type_code_seq:
                        type_code = Code.query.filter_by(seq=product.type_code_seq).first()
                        if type_code:
                            type_name = type_code.code_name
                    
                    if product.year_code_seq:
                        year = Code.query.filter_by(seq=product.year_code_seq).first()
                        if year:
                            year_name = year.code_name
                    
                    print(f"  {i}. {product.product_name}")
                    print(f"     브랜드: {brand_name} | 품목: {category_name} | 타입: {type_name} | 년도: {year_name}")
                
                legacy_conn.close()
                print(f"\n🎉 **상품 시스템 완전 재구축 완료!**")
                
            except Exception as e:
                print(f"❌ 레거시 DB 연결 실패: {e}")
                return False
                
        except Exception as e:
            print(f"❌ 전체 프로세스 실패: {e}")
            traceback.print_exc()
            db.session.rollback()
            return False
        
        return True

if __name__ == "__main__":
    success = reset_and_rebuild_product_system()
    if success:
        print("✅ 성공적으로 완료되었습니다!")
    else:
        print("❌ 실패했습니다.") 