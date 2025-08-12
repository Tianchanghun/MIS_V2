#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
색상별(상세) 코드만 엑셀에서 가져와서 추가하는 스크립트
"""

import pandas as pd
from app import create_app
from app.common.models import db, Code
from datetime import datetime

def add_color_detail_codes():
    """색상별(상세) 코드를 엑셀에서 가져와서 데이터베이스에 추가"""
    
    app = create_app()
    with app.app_context():
        
        print("📊 색상별(상세) 코드 추가 시작...")
        
        # 1. 색상별(상세) 부모 그룹 생성
        parent_code = Code.query.filter_by(code='CLD', depth=0).first()
        if not parent_code:
            parent_code = Code(
                code='CLD',
                code_name='색상별(상세)',
                depth=0,
                parent_seq=None,
                sort=950,
                ins_user='admin',
                ins_date=datetime.now(),
                upt_user='admin',
                upt_date=datetime.now()
            )
            db.session.add(parent_code)
            db.session.flush()  # ID 생성
            print(f"✅ 색상별(상세) 부모 그룹 생성: {parent_code.code} - {parent_code.code_name}")
        else:
            print(f"✅ 색상별(상세) 부모 그룹 이미 존재: {parent_code.code} - {parent_code.code_name}")
        
        # 2. 엑셀에서 색상별(상세) 데이터 가져오기
        try:
            excel_file = "분류 코드 추가1.xlsx"
            df = pd.read_excel(excel_file, sheet_name='Sheet3')
            
            color_details = df['색상별(상세)'].dropna().unique()
            print(f"📄 엑셀에서 {len(color_details)}개 색상별(상세) 데이터 발견")
            
            # 3. 각 색상별(상세) 데이터를 코드로 추가
            added_count = 0
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
                        ins_user='admin',
                        ins_date=datetime.now(),
                        upt_user='admin',
                        upt_date=datetime.now()
                    )
                    db.session.add(new_color)
                    print(f"  + {color_code}: {color_name}")
                    added_count += 1
                else:
                    print(f"  = {color_code}: {color_name} (이미 존재)")
            
            db.session.commit()
            print(f"✅ 색상별(상세) 코드 추가 완료: {added_count}개 신규 추가")
            
        except Exception as e:
            print(f"❌ 색상별(상세) 코드 추가 실패: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    add_color_detail_codes() 