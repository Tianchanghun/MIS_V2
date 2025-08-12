#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
새로운 분류 코드들을 데이터베이스에 추가하는 스크립트
1. 색상별(상세) - 엑셀에서 가져오기
2. 제품군 (PD) 
3. 아이템 상세 (ITD)
4. 아이템별 (IT)
5. 제품타입 (PT) - 기존 것 활용
"""

import pandas as pd
from app import create_app
from app.common.models import db, Code
from datetime import datetime

def import_new_classification_codes():
    """새로운 분류 코드들을 데이터베이스에 추가"""
    
    app = create_app()
    with app.app_context():
        
        # 1. 색상별(상세) 코드 그룹 생성 및 데이터 가져오기
        print("📊 1. 색상별(상세) 코드 그룹 생성 중...")
        create_color_detail_codes()
        
        # 2. 제품군 (PD) 코드 그룹 생성
        print("📊 2. 제품군 (PD) 코드 그룹 생성 중...")
        create_product_division_codes()
        
        # 3. 아이템 상세 (ITD) 코드 그룹 생성
        print("📊 3. 아이템 상세 (ITD) 코드 그룹 생성 중...")
        create_item_detail_codes()
        
        # 4. 아이템별 (IT) 코드 그룹 생성
        print("📊 4. 아이템별 (IT) 코드 그룹 생성 중...")
        create_item_codes()
        
        print("✅ 모든 새로운 분류 코드 추가 완료!")

def create_color_detail_codes():
    """색상별(상세) 코드 그룹 생성 및 엑셀 데이터 가져오기"""
    
    # 1. 색상별(상세) 부모 그룹 생성
    parent_code = Code.query.filter_by(code='CLD', depth=0).first()
    if not parent_code:
        parent_code = Code(
            code='CLD',
            code_name='색상별(상세)',
            depth=0,
            parent_seq=None,
            sort=950,
            use_yn='Y',
            created_by='admin',
            updated_by='admin'
        )
        db.session.add(parent_code)
        db.session.flush()  # ID 생성
        print(f"✅ 색상별(상세) 부모 그룹 생성: {parent_code.code} - {parent_code.code_name}")
    
    # 2. 엑셀에서 색상별(상세) 데이터 가져오기
    try:
        excel_file = "분류 코드 추가1.xlsx"
        df = pd.read_excel(excel_file, sheet_name='Sheet3')
        
        color_details = df['색상별(상세)'].dropna().unique()
        print(f"📄 엑셀에서 {len(color_details)}개 색상별(상세) 데이터 발견")
        
        # 3. 각 색상별(상세) 데이터를 코드로 추가
        for idx, color_detail in enumerate(color_details):
            if pd.isna(color_detail) or str(color_detail).strip() == '':
                continue
                
            color_name = str(color_detail).strip()
            color_code = f"CLD{idx+1:03d}"  # CLD001, CLD002, ...
            
            # 중복 확인
            existing = Code.query.filter_by(
                code=color_code, 
                parent_seq=parent_code.seq
            ).first()
            
            if not existing:
                new_color = Code(
                    code=color_code,
                    code_name=color_name,
                    depth=1,
                    parent_seq=parent_code.seq,
                    sort=idx + 1,
                    use_yn='Y',
                    created_by='admin',
                    updated_by='admin'
                )
                db.session.add(new_color)
                print(f"  + {color_code}: {color_name}")
            else:
                print(f"  = {color_code}: {color_name} (이미 존재)")
        
        db.session.commit()
        print(f"✅ 색상별(상세) 코드 추가 완료")
        
    except Exception as e:
        print(f"❌ 색상별(상세) 코드 추가 실패: {e}")
        db.session.rollback()

def create_product_division_codes():
    """제품군 (PD) 코드 그룹 생성"""
    
    # 1. 제품군 부모 그룹 생성
    parent_code = Code.query.filter_by(code='PD', depth=0).first()
    if not parent_code:
        parent_code = Code(
            code='PD',
            code_name='제품군',
            depth=0,
            parent_seq=None,
            sort=960,
            use_yn='Y',
            created_by='admin',
            updated_by='admin'
        )
        db.session.add(parent_code)
        db.session.flush()
        print(f"✅ 제품군 부모 그룹 생성: {parent_code.code} - {parent_code.code_name}")
    
    # 2. 제품군 하위 코드들 생성
    product_divisions = [
        ('PD001', '자동차용품'),
        ('PD002', '펫용품'),
        ('PD003', '라이프스타일'),
        ('PD004', '피트니스'),
        ('PD005', '전자제품'),
        ('PD006', '주방용품'),
        ('PD007', '홈데코'),
        ('PD008', '기타')
    ]
    
    for idx, (code, name) in enumerate(product_divisions):
        existing = Code.query.filter_by(
            code=code, 
            parent_seq=parent_code.seq
        ).first()
        
        if not existing:
            new_division = Code(
                code=code,
                code_name=name,
                depth=1,
                parent_seq=parent_code.seq,
                sort=idx + 1,
                use_yn='Y',
                created_by='admin',
                updated_by='admin'
            )
            db.session.add(new_division)
            print(f"  + {code}: {name}")
        else:
            print(f"  = {code}: {name} (이미 존재)")
    
    db.session.commit()
    print(f"✅ 제품군 (PD) 코드 추가 완료")

def create_item_detail_codes():
    """아이템 상세 (ITD) 코드 그룹 생성"""
    
    # 1. 아이템 상세 부모 그룹 생성
    parent_code = Code.query.filter_by(code='ITD', depth=0).first()
    if not parent_code:
        parent_code = Code(
            code='ITD',
            code_name='아이템상세',
            depth=0,
            parent_seq=None,
            sort=970,
            use_yn='Y',
            created_by='admin',
            updated_by='admin'
        )
        db.session.add(parent_code)
        db.session.flush()
        print(f"✅ 아이템상세 부모 그룹 생성: {parent_code.code} - {parent_code.code_name}")
    
    # 2. 아이템 상세 하위 코드들 생성
    item_details = [
        ('ITD001', '실버'),
        ('ITD002', '블랙'),
        ('ITD003', '화이트'),
        ('ITD004', '베이지'),
        ('ITD005', '그레이'),
        ('ITD006', '브라운'),
        ('ITD007', '네이비'),
        ('ITD008', '레드'),
        ('ITD009', '블루'),
        ('ITD010', '그린'),
        ('ITD011', '옐로우'),
        ('ITD012', '핑크'),
        ('ITD013', '퍼플'),
        ('ITD014', '오렌지'),
        ('ITD015', '기타색상')
    ]
    
    for idx, (code, name) in enumerate(item_details):
        existing = Code.query.filter_by(
            code=code, 
            parent_seq=parent_code.seq
        ).first()
        
        if not existing:
            new_item_detail = Code(
                code=code,
                code_name=name,
                depth=1,
                parent_seq=parent_code.seq,
                sort=idx + 1,
                use_yn='Y',
                created_by='admin',
                updated_by='admin'
            )
            db.session.add(new_item_detail)
            print(f"  + {code}: {name}")
        else:
            print(f"  = {code}: {name} (이미 존재)")
    
    db.session.commit()
    print(f"✅ 아이템 상세 (ITD) 코드 추가 완료")

def create_item_codes():
    """아이템별 (IT) 코드 그룹 생성"""
    
    # 1. 아이템별 부모 그룹 생성
    parent_code = Code.query.filter_by(code='IT', depth=0).first()
    if not parent_code:
        parent_code = Code(
            code='IT',
            code_name='아이템별',
            depth=0,
            parent_seq=None,
            sort=980,
            use_yn='Y',
            created_by='admin',
            updated_by='admin'
        )
        db.session.add(parent_code)
        db.session.flush()
        print(f"✅ 아이템별 부모 그룹 생성: {parent_code.code} - {parent_code.code_name}")
    
    # 2. 아이템별 하위 코드들 생성
    items = [
        ('IT001', '시트커버'),
        ('IT002', '매트'),
        ('IT003', '쿠션'),
        ('IT004', '액세서리'),
        ('IT005', '청소용품'),
        ('IT006', '보호필름'),
        ('IT007', '케이스'),
        ('IT008', '스탠드'),
        ('IT009', '충전기'),
        ('IT010', '케이블'),
        ('IT011', '어댑터'),
        ('IT012', '홀더'),
        ('IT013', '받침대'),
        ('IT014', '덮개'),
        ('IT015', '기타아이템')
    ]
    
    for idx, (code, name) in enumerate(items):
        existing = Code.query.filter_by(
            code=code, 
            parent_seq=parent_code.seq
        ).first()
        
        if not existing:
            new_item = Code(
                code=code,
                code_name=name,
                depth=1,
                parent_seq=parent_code.seq,
                sort=idx + 1,
                use_yn='Y',
                created_by='admin',
                updated_by='admin'
            )
            db.session.add(new_item)
            print(f"  + {code}: {name}")
        else:
            print(f"  = {code}: {name} (이미 존재)")
    
    db.session.commit()
    print(f"✅ 아이템별 (IT) 코드 추가 완료")

if __name__ == "__main__":
    import_new_classification_codes() 