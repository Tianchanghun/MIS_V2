#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
현재 시스템 이슈 확인 스크립트
코드 관리 depth와 상품관리 상태 점검
"""

from app.common.models import db, Code, Product
from app import create_app

def main():
    app = create_app()
    with app.app_context():
        print("="*60)
        print("🔍 현재 시스템 이슈 분석")
        print("="*60)
        
        # 1. 코드 깊이 현황 확인
        print("\n📊 코드 깊이(Depth) 현황:")
        codes = Code.query.all()
        depth_stats = {}
        max_depth = 0
        
        for code in codes:
            depth = code.depth
            if depth not in depth_stats:
                depth_stats[depth] = 0
            depth_stats[depth] += 1
            max_depth = max(max_depth, depth)
        
        for depth in sorted(depth_stats.keys()):
            print(f"  Depth {depth}: {depth_stats[depth]:3d}개")
        
        print(f"\n⚠️  현재 최대 깊이: {max_depth} (레거시는 최대 2-3 권장)")
        
        # 2. 깊이별 샘플 코드 확인
        print(f"\n📋 깊이별 샘플 코드:")
        for depth in range(min(6, max_depth + 1)):
            samples = Code.query.filter_by(depth=depth).limit(3).all()
            if samples:
                print(f"  Depth {depth}:")
                for sample in samples:
                    parent_info = f" (부모: {sample.parent_seq})" if sample.parent_seq else ""
                    print(f"    - {sample.code} | {sample.code_name}{parent_info}")
        
        # 3. 상품 데이터 현황
        print(f"\n📦 상품 데이터 현황:")
        total_products = Product.query.count()
        print(f"  총 상품 수: {total_products}개")
        
        # 문제 상품 확인 (null 필드들)
        products_with_issues = Product.query.filter(
            db.or_(
                Product.brand_code_seq.is_(None),
                Product.category_code_seq.is_(None),
                Product.type_code_seq.is_(None)
            )
        ).limit(10).all()
        
        if products_with_issues:
            print(f"  ⚠️  문제 상품 {len(products_with_issues)}개 발견:")
            for product in products_with_issues:
                issues = []
                if not product.brand_code_seq: issues.append("브랜드 없음")
                if not product.category_code_seq: issues.append("품목 없음") 
                if not product.type_code_seq: issues.append("타입 없음")
                print(f"    - {product.product_name}: {', '.join(issues)}")
        else:
            print("  ✅ 상품 데이터 무결성 양호")
        
        # 4. 코드 그룹별 현황
        print(f"\n📁 주요 코드 그룹 현황:")
        main_groups = Code.query.filter_by(depth=0).all()
        for group in main_groups[:10]:  # 상위 10개만
            child_count = Code.query.filter_by(parent_seq=group.seq).count()
            print(f"  - {group.code} ({group.code_name}): {child_count}개 하위코드")
        
        # 5. 레거시와 비교 분석
        print(f"\n🔍 레거시 비교 분석:")
        print(f"  레거시 구조: Parent-Child 2-3단계 (AdminController.cs 기준)")
        print(f"  현재 구조: {max_depth}단계")
        
        if max_depth > 3:
            print(f"  ⚠️  권장사항: 3단계로 단순화 필요")
            print(f"  📋 4단계 이상 코드들:")
            deep_codes = Code.query.filter(Code.depth >= 4).limit(5).all()
            for code in deep_codes:
                print(f"    - Depth {code.depth}: {code.code} | {code.code_name}")
        
        print("\n" + "="*60)
        print("분석 완료")
        print("="*60)

if __name__ == '__main__':
    main() 