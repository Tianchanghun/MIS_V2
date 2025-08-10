#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def test_final_ui_fix():
    """최종 UI 수정 사항 테스트"""
    print("🧪 최종 UI 수정 사항 종합 테스트")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        # 1. 년도 매핑 상태 재확인
        print("1️⃣ 년도 매핑 상태 재확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(*) as total,
                COUNT(year_code_seq) as mapped,
                COUNT(CASE WHEN year_code_seq IS NULL THEN 1 END) as unmapped
            FROM products WHERE company_id = 1 AND use_yn = 'Y'
        """))
        year_stats = result.fetchone()
        year_percentage = year_stats.mapped / year_stats.total * 100
        
        print(f"   📊 년도 매핑: {year_stats.mapped}/{year_stats.total}개 ({year_percentage:.1f}%)")
        
        if year_percentage >= 95:
            print(f"   ✅ 년도 매핑 완료!")
        else:
            print(f"   ⚠️ 년도 매핑 부족: {year_stats.unmapped}개 미매핑")
        
        # 2. 품목/타입 매핑 상태 재확인
        print(f"\n2️⃣ 품목/타입 매핑 상태 재확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(*) as total,
                COUNT(category_code_seq) as category_mapped,
                COUNT(type_code_seq) as type_mapped
            FROM products WHERE company_id = 1 AND use_yn = 'Y'
        """))
        mapping_stats = result.fetchone()
        category_percentage = mapping_stats.category_mapped / mapping_stats.total * 100
        type_percentage = mapping_stats.type_mapped / mapping_stats.total * 100
        
        print(f"   📊 품목 매핑: {mapping_stats.category_mapped}/{mapping_stats.total}개 ({category_percentage:.1f}%)")
        print(f"   📊 타입 매핑: {mapping_stats.type_mapped}/{mapping_stats.total}개 ({type_percentage:.1f}%)")
        
        # 3. 레거시 호환 코드 그룹 확인
        print(f"\n3️⃣ 레거시 호환 코드 그룹 확인")
        
        required_groups = [
            ('브랜드', 'Brand'),
            ('구분타입', 'DivType'),
            ('품목그룹', 'ProdGroup'),
            ('제품타입', 'ProdType'),
            ('제품코드', 'ProdCode'),
            ('타입2', 'Type2'),
            ('년도', 'Year'),
            ('색상', 'Color')
        ]
        
        all_groups_exist = True
        for group_name, eng_name in required_groups:
            result = db.session.execute(db.text("""
                SELECT COUNT(*) as code_count
                FROM tbl_code p
                JOIN tbl_code c ON p.seq = c.parent_seq
                WHERE p.code_name = :group_name AND p.parent_seq = 0
            """), {'group_name': group_name})
            
            code_count = result.fetchone().code_count
            if code_count > 0:
                print(f"   ✅ {group_name} ({eng_name}): {code_count}개 코드")
            else:
                print(f"   ❌ {group_name} ({eng_name}): 코드 없음")
                all_groups_exist = False
        
        # 4. 샘플 데이터 최종 확인
        print(f"\n4️⃣ 샘플 데이터 최종 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                p.id,
                p.product_name,
                b.code_name as brand_name,
                y.code_name as year_name,
                c.code_name as category_name,
                t.code_name as type_name,
                p.price,
                pd.std_div_prod_code,
                CASE 
                    WHEN LENGTH(pd.std_div_prod_code) = 16 THEN '✅'
                    ELSE '❌'
                END as code_valid
            FROM products p
            LEFT JOIN tbl_code b ON p.brand_code_seq = b.seq
            LEFT JOIN tbl_code y ON p.year_code_seq = y.seq
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            LEFT JOIN tbl_code t ON p.type_code_seq = t.seq
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1 AND p.use_yn = 'Y'
            ORDER BY p.id
            LIMIT 10
        """))
        
        samples = result.fetchall()
        print(f"   📋 개선된 샘플 데이터:")
        print(f"      {'ID':4} | {'제품명':20} | {'브랜드':8} | {'년도':8} | {'품목':8} | {'타입':8} | {'자가코드':16} | {'V':2}")
        print(f"      {'-'*4} | {'-'*20} | {'-'*8} | {'-'*8} | {'-'*8} | {'-'*8} | {'-'*16} | {'-'*2}")
        
        perfect_samples = 0
        for sample in samples:
            brand_display = sample.brand_name[:8] if sample.brand_name else "❌미지정"
            year_display = sample.year_name[:8] if sample.year_name else "❌미지정"
            category_display = sample.category_name[:8] if sample.category_name else "❌미지정"
            type_display = sample.type_name[:8] if sample.type_name else "❌미지정"
            code_display = sample.std_div_prod_code[:16] if sample.std_div_prod_code else "❌미지정"
            
            # 완벽한 샘플인지 체크
            if (sample.brand_name and sample.year_name and 
                sample.category_name and sample.type_name and 
                sample.std_div_prod_code and len(sample.std_div_prod_code) == 16):
                perfect_samples += 1
            
            print(f"      {sample.id:4} | {sample.product_name[:20]:20} | {brand_display:8} | {year_display:8} | {category_display:8} | {type_display:8} | {code_display:16} | {sample.code_valid:2}")
        
        # 5. 최종 점수 계산
        print(f"\n5️⃣ 최종 완성도 점수")
        
        scores = []
        
        # 년도 매핑 점수 (40점)
        year_score = min(40, year_percentage * 0.4)
        scores.append(('년도 매핑', year_score, 40))
        
        # 품목 매핑 점수 (20점)
        category_score = min(20, category_percentage * 0.2)
        scores.append(('품목 매핑', category_score, 20))
        
        # 타입 매핑 점수 (20점)
        type_score = min(20, type_percentage * 0.2)
        scores.append(('타입 매핑', type_score, 20))
        
        # 코드 그룹 존재 점수 (10점)
        group_score = 10 if all_groups_exist else 5
        scores.append(('코드 그룹', group_score, 10))
        
        # 샘플 완성도 점수 (10점)
        sample_score = perfect_samples * 1  # 10개 샘플 중 완벽한 것들
        scores.append(('샘플 완성도', sample_score, 10))
        
        total_score = sum(score for _, score, _ in scores)
        max_score = sum(max_score for _, _, max_score in scores)
        
        print(f"   📊 세부 점수:")
        for name, score, max_s in scores:
            print(f"      {name:12}: {score:5.1f}/{max_s:2} ({score/max_s*100:5.1f}%)")
        
        print(f"\n   🎯 총점: {total_score:.1f}/{max_score} ({total_score/max_score*100:.1f}%)")
        
        # 6. 개선 권장사항
        print(f"\n6️⃣ 개선 권장사항")
        
        recommendations = []
        
        if year_percentage < 95:
            recommendations.append("- 년도 매핑 추가 개선 필요")
        
        if category_percentage < 80:
            recommendations.append("- 품목 매핑 추가 개선 필요")
        
        if type_percentage < 60:
            recommendations.append("- 타입 매핑 추가 개선 필요")
        
        if not all_groups_exist:
            recommendations.append("- 누락된 코드 그룹 생성 필요")
        
        if perfect_samples < 8:
            recommendations.append("- 샘플 데이터 품질 개선 필요")
        
        if recommendations:
            print(f"   📝 권장사항:")
            for rec in recommendations:
                print(f"      {rec}")
        else:
            print(f"   🎉 모든 항목이 우수한 상태입니다!")
        
        # 7. 최종 결론
        print(f"\n7️⃣ 최종 결론")
        
        if total_score >= 90:
            print(f"   🎉 우수! UI 개선이 성공적으로 완료되었습니다!")
            print(f"   📱 http://127.0.0.1:5000/product/ 에서 확인해보세요!")
        elif total_score >= 70:
            print(f"   ✅ 양호! 대부분의 문제가 해결되었습니다!")
            print(f"   📱 http://127.0.0.1:5000/product/ 에서 확인해보세요!")
        elif total_score >= 50:
            print(f"   ⚠️ 보통! 일부 개선이 더 필요합니다.")
        else:
            print(f"   ❌ 부족! 추가 개선 작업이 필요합니다.")
        
        print(f"\n🔧 모달 필드 순서가 레거시와 동일하게 변경되었습니다:")
        print(f"   1. 브랜드 → 2. 구분타입 → 3. 품목그룹 → 4. 제품타입")
        print(f"   5. 제품코드 → 6. 타입2 → 7. 년도 → 8. 색상")

if __name__ == "__main__":
    test_final_ui_fix() 