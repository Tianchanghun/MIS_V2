#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CompanyErpiaConfig 테이블에 동기화 상태 컬럼 추가
"""

import os
import sys

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.common.models import db
from sqlalchemy import text

def add_sync_columns():
    """동기화 상태 컬럼 추가"""
    app = create_app()
    
    with app.app_context():
        try:
            # 컬럼 존재 여부 확인 및 추가
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('company_erpia_configs')]
            
            if 'last_sync_date' not in columns:
                print("📅 last_sync_date 컬럼 추가 중...")
                db.session.execute(text("""
                    ALTER TABLE company_erpia_configs 
                    ADD COLUMN last_sync_date TIMESTAMP
                """))
                print("✅ last_sync_date 컬럼 추가 완료")
            else:
                print("✅ last_sync_date 컬럼이 이미 존재합니다")
            
            if 'sync_error_count' not in columns:
                print("📊 sync_error_count 컬럼 추가 중...")
                db.session.execute(text("""
                    ALTER TABLE company_erpia_configs 
                    ADD COLUMN sync_error_count INTEGER DEFAULT 0
                """))
                print("✅ sync_error_count 컬럼 추가 완료")
            else:
                print("✅ sync_error_count 컬럼이 이미 존재합니다")
            
            db.session.commit()
            print("🎉 동기화 상태 컬럼 추가 완료!")
            
            # 테이블 구조 확인
            print("\n📋 현재 company_erpia_configs 테이블 구조:")
            columns = inspector.get_columns('company_erpia_configs')
            for col in columns:
                print(f"  - {col['name']}: {col['type']}")
                
        except Exception as e:
            print(f"❌ 컬럼 추가 실패: {e}")
            db.session.rollback()
            return False
            
        return True

if __name__ == '__main__':
    success = add_sync_columns()
    if success:
        print("\n🚀 이제 ERPia 연결 테스트가 정상적으로 작동할 것입니다!")
    else:
        print("\n💥 컬럼 추가에 실패했습니다.")
        sys.exit(1) 