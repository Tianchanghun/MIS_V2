#!/usr/bin/env python3
"""
브랜드 매칭 테스트 - SEQ 582, 코드 RY 확인
"""

from app import create_app
from app.common.models import db, Code

def test_brand_matching():
    """브랜드 매칭 테스트"""
    app = create_app('development')
    
    with app.app_context():
        try:
            print("🔍 브랜드 매칭 테스트...")
            
            # SEQ 582 브랜드 확인
            brand_582 = db.session.query(Code).filter(Code.seq == 582).first()
            if brand_582:
                print(f"✅ SEQ 582 브랜드: {brand_582.code_name} (코드: {brand_582.code})")
            else:
                print("❌ SEQ 582 브랜드를 찾을 수 없습니다.")
            
            # RY 코드 브랜드 확인
            brand_ry = db.session.query(Code).filter(Code.code == 'RY').first()
            if brand_ry:
                print(f"✅ RY 코드 브랜드: SEQ {brand_ry.seq}, {brand_ry.code_name}")
            else:
                print("❌ RY 코드 브랜드를 찾을 수 없습니다.")
            
            # 브랜드 그룹의 모든 브랜드 확인
            brand_parent = db.session.query(Code).filter(
                Code.code_name == '브랜드',
                Code.depth == 1
            ).first()
            
            if brand_parent:
                brands = db.session.query(Code).filter(
                    Code.parent_seq == brand_parent.seq
                ).all()
                print(f"\n📋 브랜드 그룹 전체: {len(brands)}개")
                for brand in brands:
                    print(f"  - SEQ: {brand.seq}, 코드: '{brand.code}', 이름: '{brand.code_name}'")
            
        except Exception as e:
            print(f"❌ 오류: {e}")

if __name__ == '__main__':
    test_brand_matching() 