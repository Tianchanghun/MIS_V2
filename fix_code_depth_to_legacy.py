#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
코드 관리 Depth 문제 해결
레거시 AdminController.cs 구조에 맞게 3단계로 제한
"""

from app.common.models import db, Code, Product
from app import create_app
from datetime import datetime

def main():
    app = create_app()
    with app.app_context():
        print("="*70)
        print("🔧 코드 관리 Depth 구조 개선 (레거시 호환)")
        print("="*70)
        
        # 1. 현재 4단계 이상 코드들 확인
        deep_codes = Code.query.filter(Code.depth >= 4).all()
        print(f"\n📋 4단계 이상 코드 확인: {len(deep_codes)}개")
        
        for code in deep_codes:
            parent = Code.query.filter_by(seq=code.parent_seq).first()
            parent_name = parent.code_name if parent else "부모 없음"
            print(f"  - Depth {code.depth}: {code.code} | {code.code_name} (부모: {parent_name})")
        
        # 2. 레거시 구조 분석 및 재구성 계획
        print(f"\n📊 레거시 구조 분석:")
        print(f"  - AdminController.cs: CodeManager() - OrderBy depth")
        print(f"  - 최대 권장 depth: 3 (Root > Group > Category > Item)")
        print(f"  - 현재 문제: {len(deep_codes)}개 코드가 4단계 이상")
        
        # 3. 해결 방안 제시
        print(f"\n🔧 해결 방안:")
        print(f"  1️⃣ 4단계 코드들을 3단계로 이동")
        print(f"  2️⃣ 불필요한 중간 단계 제거")
        print(f"  3️⃣ 상품 연결 유지 (데이터 무결성)")
        
        # 4. 자동 수정 시도
        try:
            print(f"\n🚀 자동 수정 시작...")
            
            # 4단계 이상 코드들을 3단계로 재배치
            fixed_count = 0
            
            for code in deep_codes:
                if code.depth == 4:
                    # 부모의 부모를 새로운 부모로 설정 (3단계로 이동)
                    parent = Code.query.filter_by(seq=code.parent_seq).first()
                    if parent and parent.parent_seq:
                        grandparent = Code.query.filter_by(seq=parent.parent_seq).first()
                        if grandparent:
                            print(f"    📦 {code.code_name}: Depth 4 → 3 (새 부모: {grandparent.code_name})")
                            code.parent_seq = grandparent.seq
                            code.depth = 3
                            code.upt_user = 'system_fix'
                            code.upt_date = datetime.now()
                            fixed_count += 1
                
                elif code.depth > 4:
                    # 5단계 이상은 3단계로 강제 이동
                    # 가장 가까운 1단계 부모 찾기
                    current = code
                    target_parent = None
                    
                    # 상위로 올라가면서 depth 1 찾기
                    while current.parent_seq:
                        current = Code.query.filter_by(seq=current.parent_seq).first()
                        if not current:
                            break
                        if current.depth == 1:
                            target_parent = current
                            break
                    
                    if target_parent:
                        print(f"    📦 {code.code_name}: Depth {code.depth} → 3 (부모: {target_parent.code_name})")
                        code.parent_seq = target_parent.seq
                        code.depth = 3
                        code.upt_user = 'system_fix'
                        code.upt_date = datetime.now()
                        fixed_count += 1
            
            # 변경사항 저장
            if fixed_count > 0:
                db.session.commit()
                print(f"\n✅ {fixed_count}개 코드 구조 수정 완료!")
            else:
                print(f"\n💡 수정할 코드가 없습니다.")
            
            # 5. 수정 후 검증
            print(f"\n🔍 수정 후 검증:")
            remaining_deep = Code.query.filter(Code.depth >= 4).count()
            print(f"  - 4단계 이상 코드: {remaining_deep}개")
            
            if remaining_deep == 0:
                print(f"  ✅ 모든 코드가 3단계 이하로 정리되었습니다!")
            else:
                print(f"  ⚠️  아직 {remaining_deep}개 코드가 4단계 이상입니다.")
            
            # 6. 코드 그룹별 최종 현황
            print(f"\n📈 최종 Depth 현황:")
            depth_stats = {}
            all_codes = Code.query.all()
            
            for code in all_codes:
                depth = code.depth
                if depth not in depth_stats:
                    depth_stats[depth] = 0
                depth_stats[depth] += 1
            
            for depth in sorted(depth_stats.keys()):
                print(f"  Depth {depth}: {depth_stats[depth]:3d}개")
            
            # 7. 상품 데이터 무결성 확인
            print(f"\n📦 상품 데이터 무결성 확인:")
            problem_products = Product.query.filter(
                db.or_(
                    Product.brand_code_seq.is_(None),
                    Product.category_code_seq.is_(None),
                    Product.type_code_seq.is_(None)
                )
            ).all()
            
            if problem_products:
                print(f"  ⚠️  문제 상품: {len(problem_products)}개")
                for product in problem_products:
                    print(f"    - ID {product.id}: {product.product_name or '이름없음'}")
            else:
                print(f"  ✅ 모든 상품 데이터 정상")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ 수정 중 오류 발생: {e}")
            
        print("\n" + "="*70)
        print("🎯 레거시 호환 코드 구조 개선 완료")
        print("="*70)

if __name__ == '__main__':
    main() 