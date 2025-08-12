#!/usr/bin/env python3
"""
자사코드 파싱 확인 스크립트
"""

from app import create_app
from app.common.models import ProductDetail

def check_std_codes():
    """자사코드 파싱 확인"""
    app = create_app()
    
    with app.app_context():
        print('🔍 자사코드 파싱 분석:')
        
        # 처음 10개 ProductDetail 조회
        details = ProductDetail.query.limit(10).all()
        
        for detail in details:
            if detail.std_div_prod_code and len(detail.std_div_prod_code) >= 16:
                std_code = detail.std_div_prod_code
                
                parsed = {
                    'brand': std_code[0:2],      # 브랜드 (2자리)
                    'divType': std_code[2:3],    # 구분타입 (1자리)
                    'prodGroup': std_code[3:5],  # 제품구분 (2자리)
                    'prodType': std_code[5:7],   # 제품타입 (2자리)
                    'prod': std_code[7:9],       # 품목 (2자리)
                    'type2': std_code[9:11],     # 타입2 (2자리)
                    'year': std_code[11:13],     # 년도 (2자리)
                    'color': std_code[13:16]     # 색상 (3자리)
                }
                
                print(f'\n📦 ProductDetail ID: {detail.id}')
                print(f'   자사코드: {std_code}')
                print(f'   파싱결과:')
                for key, value in parsed.items():
                    print(f'     - {key}: {value}')

if __name__ == '__main__':
    check_std_codes() 