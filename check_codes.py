import sys
sys.path.append('.')
from app import create_app
from app.common.models import db, Code

app = create_app()
with app.app_context():
    print('=== 브랜드 코드 ===')
    brand_codes = Code.get_codes_by_group_name('브랜드')
    if brand_codes:
        for code in brand_codes[:5]:
            print(f'  {code.seq}: {code.code} - {code.code_name}')
    else:
        print('  브랜드 코드 없음')
    
    print('\n=== PRD 코드 ===')  
    prd_codes = Code.get_codes_by_group_name('PRD')
    if prd_codes:
        for code in prd_codes[:10]:
            print(f'  {code.seq}: {code.code} - {code.code_name}')
    else:
        print('  PRD 코드 없음')
        
    print('\n=== CR(색상) 코드 ===')
    cr_codes = Code.get_codes_by_group_name('CR')
    if cr_codes:
        for code in cr_codes[:10]:
            print(f'  {code.seq}: {code.code} - {code.code_name}')
    else:
        print('  CR 코드 없음')
        
    print('\n=== 색상별 코드 ===')
    color_by_product_codes = Code.get_codes_by_group_name('색상별')
    if color_by_product_codes:
        for code in color_by_product_codes[:10]:
            print(f'  {code.seq}: {code.code} - {code.code_name}')
    else:
        print('  색상별 코드 없음') 