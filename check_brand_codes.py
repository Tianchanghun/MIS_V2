#!/usr/bin/env python3
"""
브랜드 코드 확인 스크립트
"""

from app import create_app
from app.common.models import Code

def check_brand_codes():
    """브랜드 코드 확인"""
    app = create_app()
    
    with app.app_context():
        print('🔍 브랜드 코드 목록:')
        brands = Code.get_codes_by_group_name('브랜드')
        
        for brand in brands:
            print(f'  - {brand.code}: {brand.code_name} (seq: {brand.seq})')
            if 'NU' in brand.code or 'NN' in brand.code or '뉴나' in brand.code_name:
                print(f'    ★ 뉴나 브랜드 발견!')
        
        print(f'\n총 브랜드 수: {len(brands)}개')
        
        # NU 코드가 있는지 직접 확인
        nu_brand = None
        for brand in brands:
            if brand.code == 'NU':
                nu_brand = brand
                break
        
        if nu_brand:
            print(f'\n✅ NU 브랜드 존재: {nu_brand.code_name} (seq: {nu_brand.seq})')
        else:
            print('\n❌ NU 브랜드 없음')
            
        # NN 코드가 있는지 확인
        nn_brand = None
        for brand in brands:
            if brand.code == 'NN':
                nn_brand = brand
                break
        
        if nn_brand:
            print(f'✅ NN 브랜드 존재: {nn_brand.code_name} (seq: {nn_brand.seq})')
        else:
            print('❌ NN 브랜드 없음')

if __name__ == '__main__':
    check_brand_codes() 