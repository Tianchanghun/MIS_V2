#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
기존 상품에 샘플 제품모델 생성
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db, Product, ProductDetail, Code
from datetime import datetime

app = create_app()

def create_sample_product_models():
    """기존 상품에 샘플 제품모델 생성"""
    with app.app_context():
        
        # 1. 색상 코드 확인 (COLOR 그룹)
        color_codes = Code.query.filter_by(code_seq=5).limit(10).all()  # COLOR 그룹
        print(f"📊 사용 가능한 색상 코드: {len(color_codes)}개")
        for color in color_codes:
            print(f"  - {color.code}: {color.code_name}")
        
        if not color_codes:
            print("❌ 색상 코드가 없습니다. 먼저 코드를 생성해야 합니다.")
            return
        
        # 2. 기존 상품 중 몇 개 선택
        products = Product.query.limit(5).all()
        print(f"\n📦 처리할 상품: {len(products)}개")
        
        created_count = 0
        
        for product in products:
            print(f"\n🔧 상품 '{product.product_name}' 제품모델 생성...")
            
            # 해당 상품에 이미 제품모델이 있는지 확인
            existing_count = ProductDetail.query.filter_by(product_id=product.id).count()
            if existing_count > 0:
                print(f"  ⏭️  이미 {existing_count}개의 제품모델이 존재합니다.")
                continue
            
            # 상품별로 2-3개의 색상 제품모델 생성
            colors_to_use = color_codes[:3]  # 처음 3개 색상 사용
            
            for i, color_code in enumerate(colors_to_use):
                try:
                    # 자가코드 생성 (정확히 16자리)
                    brand_part = 'AA'  # 2자리
                    div_type_part = '1'  # 1자리  
                    prod_group_part = 'A0'  # 2자리
                    prod_type_part = 'A0'  # 2자리
                    prod_code_part = 'A0'  # 2자리
                    prod_type2_part = 'A0'  # 2자리
                    year_part = 'A'  # 1자리
                    color_part = color_code.code[:3]  # 3자리 (최대)
                    
                    # 색상 코드가 3자리 미만이면 패딩
                    if len(color_part) < 3:
                        color_part = color_part.ljust(3, '0')
                    elif len(color_part) > 3:
                        color_part = color_part[:3]
                    
                    # 16자리 조합: 2+1+2+2+2+2+1+3+1 = 16자리
                    sequence_part = str(i+1)  # 1자리 (순번)
                    
                    std_code = f"{brand_part}{div_type_part}{prod_group_part}{prod_type_part}{prod_code_part}{prod_type2_part}{year_part}{color_part}{sequence_part}"
                    
                    # 16자리 확인
                    if len(std_code) != 16:
                        std_code = std_code[:16].ljust(16, '0')
                    
                    # 중복 체크
                    existing_detail = ProductDetail.query.filter_by(std_div_prod_code=std_code).first()
                    if existing_detail:
                        # 마지막 자리를 변경하여 중복 해결
                        std_code = std_code[:15] + str((i+2) % 10)
                    
                    # 제품모델 생성
                    product_detail = ProductDetail(
                        product_id=product.id,
                        brand_code=brand_part,
                        div_type_code=div_type_part,
                        prod_group_code=prod_group_part,
                        prod_type_code=prod_type_part,
                        prod_code=prod_code_part,
                        prod_type2_code=prod_type2_part,
                        year_code=year_part,
                        color_code=color_part,
                        std_div_prod_code=std_code,
                        product_name=f"{product.product_name} ({color_code.code_name})",
                        additional_price=i * 5000,  # 색상별 추가 가격
                        stock_quantity=100 + i * 10,  # 재고 수량
                        status='Active',
                        created_by='sample_data',
                        updated_by='sample_data'
                    )
                    
                    db.session.add(product_detail)
                    created_count += 1
                    
                    print(f"  ✅ {color_code.code_name} 제품모델 생성: {std_code} (길이: {len(std_code)})")
                    
                except Exception as e:
                    print(f"  ❌ {color_code.code_name} 제품모델 생성 실패: {e}")
                    db.session.rollback()
        
        # 3. 커밋
        try:
            db.session.commit()
            print(f"\n🎉 샘플 제품모델 생성 완료: {created_count}개")
        except Exception as e:
            db.session.rollback()
            print(f"❌ 제품모델 저장 실패: {e}")

def create_sample_codes():
    """샘플 코드 생성 (색상, 구분타입, 제품코드)"""
    with app.app_context():
        
        # 색상 코드 생성 (COLOR 그룹, code_seq=5)
        sample_colors = [
            ('RED', '빨강'),
            ('BLU', '파랑'),
            ('GRN', '초록'),
            ('BLK', '검정'),
            ('WHT', '흰색'),
            ('YLW', '노랑'),
            ('PNK', '분홍'),
            ('GRY', '회색')
        ]
        
        color_group_seq = 5  # COLOR 그룹
        existing_colors = Code.query.filter_by(code_seq=color_group_seq).count()
        
        if existing_colors == 0:
            print("📝 색상 코드 생성 중...")
            for i, (code, name) in enumerate(sample_colors):
                color = Code(
                    code_seq=color_group_seq,
                    parent_seq=None,
                    depth=1,
                    sort=i + 1,
                    code=code,
                    code_name=name,
                    code_info=f'색상 - {name}',
                    ins_user='sample_data'
                )
                db.session.add(color)
            
            db.session.commit()
            print(f"✅ 색상 코드 {len(sample_colors)}개 생성 완료")
        else:
            print(f"⚠️  색상 코드가 이미 {existing_colors}개 존재합니다.")

if __name__ == '__main__':
    print("🚀 샘플 제품모델 생성 시작")
    print("=" * 50)
    
    # 1. 필요한 코드 먼저 생성
    create_sample_codes()
    
    # 2. 제품모델 생성
    create_sample_product_models()
    
    print("\n" + "=" * 50)
    print("🎊 샘플 데이터 생성 완료!")
    print("이제 상품 수정 페이지에서 제품모델을 확인할 수 있습니다.") 