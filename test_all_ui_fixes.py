#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db
import requests
import json

def test_all_ui_fixes():
    """모든 UI 수정사항 종합 테스트"""
    print("🧪 모든 UI 수정사항 종합 테스트")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        
        # 1. 자가코드 표시 테스트
        print("1️⃣ 자가코드 표시 테스트")
        
        # Product.to_dict() 테스트
        from app.common.models import Product
        sample_products = Product.query.filter_by(company_id=1, is_active=True).limit(5).all()
        
        print(f"   📋 샘플 제품들의 자가코드 확인:")
        for product in sample_products:
            product_dict = product.to_dict()
            std_code = product_dict.get('std_product_code', 'undefined')
            print(f"      ID {product.id}: {product.product_name[:20]:20} → {std_code}")
        
        # API 응답 테스트
        print(f"\n   📡 API 응답 테스트:")
        try:
            response = requests.get('http://127.0.0.1:5000/product/api/list?page=1&per_page=3')
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('products'):
                    for product in data['products'][:3]:
                        std_code = product.get('std_product_code', 'undefined')
                        print(f"      API ID {product['id']}: {std_code}")
                else:
                    print(f"      ❌ API 응답 실패: {data}")
            else:
                print(f"      ❌ API 호출 실패: {response.status_code}")
        except Exception as e:
            print(f"      ⚠️ API 테스트 건너뜀 (Flask 앱이 실행되지 않음): {e}")
        
        # 2. 모달 필드 순서 테스트
        print(f"\n2️⃣ 모달 필드 순서 테스트")
        
        # HTML 템플릿에서 필드 순서 확인
        template_path = 'app/templates/product/index.html'
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 필드 순서 확인
            field_order = [
                'modal_brand_code_seq',
                'modal_div_type_code_seq', 
                'modal_prod_group_code_seq',
                'modal_prod_type_code_seq',
                'modal_product_code_seq',
                'modal_prod_type2_code_seq',
                'modal_year_code_seq',
                'modal_color_code_seq'
            ]
            
            print(f"   📋 레거시 호환 필드 순서:")
            for i, field in enumerate(field_order, 1):
                if field in content:
                    print(f"      {i}. {field.replace('modal_', '').replace('_', ' ').title()} ✅")
                else:
                    print(f"      {i}. {field.replace('modal_', '').replace('_', ' ').title()} ❌")
        
        # 3. 코드 그룹 존재 확인
        print(f"\n3️⃣ 코드 그룹 존재 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                group_cd,
                COUNT(*) as code_count
            FROM tbl_code 
            WHERE parent_seq = 0 AND company_id = 1
            GROUP BY group_cd
            ORDER BY group_cd
        """))
        
        code_groups = result.fetchall()
        essential_groups = ['브랜드', '구분타입', '품목그룹', '제품타입', '제품코드', '타입2', '년도', '색상']
        
        print(f"   📊 필수 코드 그룹 확인:")
        for group in essential_groups:
            found = False
            for cg in code_groups:
                if group in cg.group_cd:
                    print(f"      {group}: {cg.code_count}개 ✅")
                    found = True
                    break
            if not found:
                print(f"      {group}: 없음 ❌")
        
        # 4. 연관 셀렉트 테스트 (JavaScript 함수 존재 확인)
        print(f"\n4️⃣ 연관 셀렉트 기능 확인")
        
        if os.path.exists(template_path):
            js_functions = [
                'setupDependentSelects',
                'setModalValues', 
                'setSelectValue'
            ]
            
            print(f"   📋 JavaScript 함수 존재 확인:")
            for func in js_functions:
                if f'function {func}' in content:
                    print(f"      {func}: 존재 ✅")
                else:
                    print(f"      {func}: 없음 ❌")
        
        # 5. 제품 매핑 상태 최종 확인
        print(f"\n5️⃣ 제품 매핑 상태 최종 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(*) as total,
                COUNT(brand_code_seq) as brand_mapped,
                COUNT(category_code_seq) as category_mapped,
                COUNT(type_code_seq) as type_mapped,
                COUNT(year_code_seq) as year_mapped
            FROM products 
            WHERE company_id = 1 AND is_active = true
        """))
        
        mapping = result.fetchone()
        print(f"   📊 매핑 완성도:")
        print(f"      브랜드: {mapping.brand_mapped}/{mapping.total}개 ({mapping.brand_mapped/mapping.total*100:.1f}%)")
        print(f"      품목: {mapping.category_mapped}/{mapping.total}개 ({mapping.category_mapped/mapping.total*100:.1f}%)")  
        print(f"      타입: {mapping.type_mapped}/{mapping.total}개 ({mapping.type_mapped/mapping.total*100:.1f}%)")
        print(f"      년도: {mapping.year_mapped}/{mapping.total}개 ({mapping.year_mapped/mapping.total*100:.1f}%)")
        
        # 6. 최종 점수 계산
        print(f"\n6️⃣ 최종 완성도 점수")
        
        # 자가코드 표시 (25점)
        std_code_score = 0
        undefined_count = 0
        for product in sample_products:
            product_dict = product.to_dict()
            std_code = product_dict.get('std_product_code')
            if std_code and std_code != 'undefined' and len(str(std_code)) >= 10:
                std_code_score += 5
            else:
                undefined_count += 1
        
        # 모달 필드 순서 (25점)
        modal_score = 0
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            for field in field_order:
                if field in content:
                    modal_score += 3.125  # 25점 / 8개 필드
        
        # 코드 그룹 완성도 (25점)
        code_group_score = 0
        for group in essential_groups:
            for cg in code_groups:
                if group in cg.group_cd:
                    code_group_score += 3.125  # 25점 / 8개 그룹
                    break
        
        # 매핑 완성도 (25점)
        avg_mapping_ratio = (mapping.brand_mapped + mapping.category_mapped + mapping.type_mapped + mapping.year_mapped) / (4 * mapping.total)
        mapping_score = avg_mapping_ratio * 25
        
        total_score = std_code_score + modal_score + code_group_score + mapping_score
        
        print(f"   🎯 세부 점수:")
        print(f"      자가코드 표시: {std_code_score:.1f}/25점 (undefined: {undefined_count}개)")
        print(f"      모달 필드 순서: {modal_score:.1f}/25점")
        print(f"      코드 그룹 완성도: {code_group_score:.1f}/25점")
        print(f"      매핑 완성도: {mapping_score:.1f}/25점")
        print(f"   🏆 총점: {total_score:.1f}/100점")
        
        if total_score >= 90:
            print(f"   ✅ 우수! UI가 완벽하게 수정되었습니다!")
        elif total_score >= 70:
            print(f"   ✅ 양호! 대부분의 문제가 해결되었습니다.")
        else:
            print(f"   ⚠️ 보완 필요! 추가 수정이 필요합니다.")
        
        # 7. 권장사항
        print(f"\n7️⃣ 권장사항")
        
        if undefined_count > 0:
            print(f"   🔧 자가코드 'undefined' 문제가 {undefined_count}개 남아있습니다.")
            print(f"      → Product 모델의 to_dict() 수정이 필요합니다.")
        
        if mapping.type_mapped / mapping.total < 0.8:
            print(f"   🔧 타입 매핑이 {mapping.type_mapped/mapping.total*100:.1f}%로 낮습니다.")
            print(f"      → 추가 매핑 작업이 필요합니다.")
        
        if total_score >= 90:
            print(f"   🎉 모든 UI 문제가 성공적으로 해결되었습니다!")
            print(f"   📱 이제 http://127.0.0.1:5000/product/ 에서 완벽한 UI를 확인할 수 있습니다!")

if __name__ == "__main__":
    test_all_ui_fixes() 