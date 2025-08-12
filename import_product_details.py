import pandas as pd
from app import create_app, db
from app.common.models import Product, ProductDetail, Code
from sqlalchemy import text
import traceback

def main():
    print("🚀 제품 상세 정보 추가 시작")
    print("=" * 60)
    
    # Flask 앱 컨텍스트 생성
    app = create_app('development')
    
    with app.app_context():
        try:
            # Excel 파일 읽기
            print("📊 Excel 파일 읽는 중...")
            df = pd.read_excel('제픔코드용.xlsx')
            print(f"✅ {len(df)}개의 데이터를 읽었습니다.")
            
            # 기존 Product와 매칭을 위한 상품명 기준 처리
            success_count = 0
            error_count = 0
            skipped_count = 0
            
            print("\n🔍 상품 매칭 및 상세 정보 추가 중...")
            
            for index, row in df.iterrows():
                try:
                    product_name = row['상품명']
                    std_code = row['더존코드 변환값']  # 자사코드
                    
                    # 빈 값 체크
                    if pd.isna(std_code) or str(std_code).strip() == '':
                        print(f"⚠️  [{index+1}/{len(df)}] {product_name}: 자사코드가 없음")
                        skipped_count += 1
                        continue
                    
                    # 기존 상품 찾기 (상품명 기준)
                    existing_product = Product.query.filter_by(
                        product_name=product_name,
                        company_id=1  # 에이원 회사
                    ).first()
                    
                    if not existing_product:
                        print(f"⚠️  [{index+1}/{len(df)}] {product_name}: 기존 상품을 찾을 수 없음")
                        skipped_count += 1
                        continue
                    
                    # 이미 ProductDetail이 있는지 확인
                    existing_detail = ProductDetail.query.filter_by(
                        product_id=existing_product.id,
                        std_div_prod_code=std_code
                    ).first()
                    
                    if existing_detail:
                        print(f"⚠️  [{index+1}/{len(df)}] {product_name}: 이미 상세 정보가 존재함")
                        skipped_count += 1
                        continue
                    
                    # 자사코드가 16자리인지 확인
                    if len(str(std_code)) != 16:
                        print(f"⚠️  [{index+1}/{len(df)}] {product_name}: 자사코드 길이가 16자리가 아님 ({len(str(std_code))}자리)")
                        skipped_count += 1
                        continue
                    
                    # 자사코드 분해 (16자리)
                    std_code_str = str(std_code)
                    brand_code = std_code_str[:2]
                    div_type_code = std_code_str[2:3]
                    prod_group_code = std_code_str[3:5]
                    prod_type_code = std_code_str[5:7]
                    prod_code = std_code_str[7:9]
                    type2_code = std_code_str[9:11]
                    year_code = std_code_str[11:13]
                    color_code = std_code_str[13:15]
                    seq_code = std_code_str[15:16]
                    
                    # ProductDetail 생성 (기존 필드만 사용)
                    product_detail = ProductDetail(
                        product_id=existing_product.id,
                        brand_code=brand_code,
                        div_type_code=div_type_code,
                        prod_group_code=prod_group_code,
                        prod_type_code=prod_type_code,
                        prod_code=prod_code,
                        prod_type2_code=type2_code,  # 모델의 필드명에 맞춤
                        year_code=year_code,
                        color_code=color_code,
                        std_div_prod_code=std_code_str,
                        product_name=product_name,  # Excel의 상품명 사용
                        use_yn='Y',
                        created_by='system',
                        updated_by='system'
                    )
                    
                    db.session.add(product_detail)
                    
                    # 50개마다 커밋
                    if (index + 1) % 50 == 0:
                        db.session.commit()
                        print(f"✅ [{index+1}/{len(df)}] 중간 저장 완료")
                    
                    success_count += 1
                    print(f"✅ [{index+1}/{len(df)}] {product_name}: 상세 정보 추가 완료 (코드: {std_code_str})")
                    
                except Exception as e:
                    error_count += 1
                    print(f"❌ [{index+1}/{len(df)}] {row.get('상품명', 'Unknown')}: 오류 - {str(e)}")
                    db.session.rollback()
                    continue
            
            # 최종 커밋
            db.session.commit()
            
            print("\n" + "=" * 60)
            print("🎉 제품 상세 정보 추가 완료!")
            print(f"✅ 성공: {success_count}개")
            print(f"⚠️  건너뜀: {skipped_count}개")
            print(f"❌ 오류: {error_count}개")
            print(f"📊 총 처리: {success_count + skipped_count + error_count}개")
            
            # 결과 확인
            total_details = ProductDetail.query.count()
            print(f"🗄️  총 ProductDetail 개수: {total_details}개")
            
        except Exception as e:
            print(f"❌ 전체 프로세스 오류: {e}")
            traceback.print_exc()
            db.session.rollback()

if __name__ == "__main__":
    main() 