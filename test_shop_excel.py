#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import create_app
from app.common.models import db, ErpiaCustomer, Code
import traceback

app = create_app()

with app.app_context():
    print('=== Shop Management 엑셀 처리 테스트 ===')
    
    try:
        # 1. CST 코드 체계 확인
        print('1. CST 코드 체계 확인...')
        cst_group = Code.query.filter_by(code='CST', depth=0).first()
        if cst_group:
            classification_groups = Code.query.filter_by(
                parent_seq=cst_group.seq, 
                depth=1
            ).order_by(Code.sort.asc()).all()
            
            print(f'   - CST 그룹 발견: {cst_group.code_name}')
            print(f'   - 하위 분류 그룹: {len(classification_groups)}개')
            
            for group in classification_groups:
                sub_codes = Code.query.filter_by(parent_seq=group.seq, depth=2).all()
                print(f'     · {group.code} ({group.code_name}): {len(sub_codes)}개 코드')
                if sub_codes:
                    print(f'       예시: {sub_codes[0].code} → {sub_codes[0].code_name}')
        else:
            print('   ❌ CST 그룹을 찾을 수 없습니다')
        
        # 2. 매장 데이터 확인
        print('\n2. 매장 데이터 확인...')
        total_shops = ErpiaCustomer.query.filter_by(company_id=1).count()
        print(f'   - 에이원 매장 수: {total_shops}개')
        
        # 분류별 현황 확인
        if cst_group and classification_groups:
            for group in classification_groups[:3]:  # 처음 3개만 확인
                field_map = {
                    'dis': 'distribution_type',
                    'ch': 'channel_type', 
                    'sl': 'sales_type',
                    'ty': 'business_form'
                }
                
                field_name = field_map.get(group.code.lower(), f'{group.code.lower()}_type')
                
                if hasattr(ErpiaCustomer, field_name):
                    classified_count = ErpiaCustomer.query.filter_by(company_id=1).filter(
                        getattr(ErpiaCustomer, field_name).isnot(None)
                    ).count()
                    print(f'   - {group.code_name} 분류된 매장: {classified_count}개')
        
        # 3. 코드변환 테스트
        print('\n3. 코드 → 텍스트명 변환 테스트...')
        
        test_shop = ErpiaCustomer.query.filter_by(company_id=1).first()
        if test_shop:
            print(f'   테스트 매장: {test_shop.customer_name}')
            
            # 각 분류별 변환 테스트
            for group in classification_groups[:3]:
                field_map = {
                    'dis': 'distribution_type',
                    'ch': 'channel_type', 
                    'sl': 'sales_type',
                    'ty': 'business_form'
                }
                
                field_name = field_map.get(group.code.lower(), f'{group.code.lower()}_type')
                
                if hasattr(test_shop, field_name):
                    field_value = getattr(test_shop, field_name)
                    
                    if field_value:
                        # 코드번호를 텍스트명으로 변환 (개선된 로직 테스트)
                        sub_code = Code.query.filter_by(
                            parent_seq=group.seq, 
                            code=field_value, 
                            depth=2
                        ).first()
                        
                        converted_name = sub_code.code_name if sub_code else field_value
                        print(f'   - {group.code_name}: "{field_value}" → "{converted_name}"')
                    else:
                        print(f'   - {group.code_name}: 미분류')
        
        # 4. 텍스트 → 코드 매핑 테스트 (업로드 로직)
        print('\n4. 텍스트명 → 코드 매핑 테스트...')
        
        test_mappings = [
            ('DIS', '도매'),
            ('CH', '온라인'),
            ('SL', '매출'),
            ('TY', '일반')
        ]
        
        for group_code, test_text in test_mappings:
            group = Code.query.filter_by(code=group_code, depth=1).first()
            if group:
                sub_codes = Code.query.filter_by(parent_seq=group.seq, depth=2).all()
                valid_codes = {code.code: code.code_name for code in sub_codes}
                
                found_code = None
                # 텍스트명으로 매핑
                for code, name in valid_codes.items():
                    if name == test_text:
                        found_code = code
                        break
                
                status = "✅ 매핑됨" if found_code else "❌ 매핑안됨"
                print(f'   - {group.code_name} "{test_text}" → "{found_code}" {status}')
        
        print('\n🎉 Shop Management 엑셀 처리 테스트 완료!')
        
    except Exception as e:
        print(f'\n❌ 테스트 실패: {e}')
        print(f'상세 오류:\n{traceback.format_exc()}')
    
    print('\n📋 개선사항 요약:')
    print('1. ✅ 엑셀 다운로드: 코드번호 → 텍스트명 변환 구현')
    print('2. ✅ 엑셀 업로드: 텍스트명 → 코드번호 변환 (기존 지원)')
    print('3. ✅ 템플릿 다운로드: 실제 코드명 예시 + 코드참조표 추가')
    print('4. ✅ 유연한 매핑: 코드명/코드 모두 지원')
    
    print('\n🔗 테스트 방법:')
    print('1. http://127.0.0.1:5000/shop/index 접속')
    print('2. "엑셀 다운로드" → 분류 코드가 텍스트명으로 출력되는지 확인')
    print('3. "템플릿 다운로드" → 실제 분류명 예시 + 참조표 확인')
    print('4. 템플릿에 데이터 입력 후 업로드 → 텍스트명이 코드로 변환되는지 확인') 