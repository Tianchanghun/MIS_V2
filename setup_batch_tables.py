#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERPia 배치 시스템 데이터베이스 초기화 스크립트
- 새로운 테이블 생성
- 기본 설정 데이터 삽입
- 에이원 ERPia 계정 설정
"""

import os
import sys
from datetime import datetime

def setup_batch_system():
    """배치 시스템 초기화"""
    try:
        # Flask 앱 생성
        from app import create_app
        from app.common.models import db, create_default_data
        
        app = create_app()
        
        with app.app_context():
            print("🔧 ERPia 배치 시스템 초기화 시작...")
            
            # 1. 테이블 생성
            print("📋 데이터베이스 테이블 생성 중...")
            db.create_all()
            print("✅ 테이블 생성 완료!")
            
            # 2. 기본 데이터 생성 (회사, ERPia 설정, 배치 설정)
            print("🏢 기본 데이터 생성 중...")
            create_default_data()
            print("✅ 기본 데이터 생성 완료!")
            
            # 3. 테이블 확인
            print("\n📊 생성된 테이블 확인:")
            
            # 새로 생성된 테이블들 확인
            new_tables = [
                'companies',
                'user_companies', 
                'company_erpia_configs',
                'erpia_batch_settings',
                'erpia_batch_logs',
                'sales_analysis_master'
            ]
            
            for table_name in new_tables:
                try:
                    # SQLAlchemy 2.0 호환 방식
                    from sqlalchemy import text
                    result = db.session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                    print(f"  ✓ {table_name}: {result}건")
                except Exception as e:
                    print(f"  ❌ {table_name}: 오류 - {str(e)[:50]}...")
            
            # 4. ERPia 설정 확인
            print("\n🔌 ERPia 설정 확인:")
            from app.common.models import CompanyErpiaConfig, ErpiaBatchSettings
            
            configs = CompanyErpiaConfig.query.all()
            for config in configs:
                print(f"  ✓ 회사 ID {config.company_id}: {config.admin_code} (활성: {config.is_active})")
            
            settings_count = ErpiaBatchSettings.query.count()
            print(f"  ✓ 배치 설정: {settings_count}개")
            
            print("\n🎉 ERPia 배치 시스템 초기화 완료!")
            print("\n📝 다음 단계:")
            print("  1. 웹 브라우저에서 http://127.0.0.1:5000/batch/settings 접속")
            print("  2. 회사별 ERPia 계정 설정 확인/수정")
            print("  3. 배치 스케줄 설정")
            print("  4. ERPia 연결 테스트 실행")
            print("  5. 수동 배치 실행으로 테스트")
            
    except Exception as e:
        print(f"❌ 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def check_current_status():
    """현재 시스템 상태 확인"""
    try:
        from app import create_app
        from app.common.models import db, Company, CompanyErpiaConfig, ErpiaBatchSettings
        
        app = create_app()
        
        with app.app_context():
            print("🔍 현재 시스템 상태 확인...")
            
            # 회사 정보
            companies = Company.query.all()
            print(f"\n🏢 등록된 회사: {len(companies)}개")
            for company in companies:
                print(f"  - {company.company_name} (코드: {company.company_code}, 활성: {company.is_active})")
            
            # ERPia 설정
            erpia_configs = CompanyErpiaConfig.query.all()
            print(f"\n🔌 ERPia 연동 설정: {len(erpia_configs)}개")
            for config in erpia_configs:
                company = Company.query.get(config.company_id)
                status = "활성" if config.is_active else "비활성"
                last_sync = config.last_sync_date.strftime('%Y-%m-%d %H:%M') if config.last_sync_date else "없음"
                print(f"  - {company.company_name}: {config.admin_code} ({status}, 마지막동기: {last_sync})")
            
            # 배치 설정
            batch_settings = ErpiaBatchSettings.query.count()
            print(f"\n⚙️ 배치 설정: {batch_settings}개")
            
            # 각 회사별 설정 요약
            for company in companies:
                settings = ErpiaBatchSettings.query.filter_by(company_id=company.id).all()
                setting_dict = {s.setting_key: s.setting_value for s in settings}
                
                schedule_time = setting_dict.get('schedule_time', '설정안됨')
                schedule_type = setting_dict.get('schedule_type', '설정안됨')
                auto_classify = setting_dict.get('auto_gift_classify', 'true')
                
                print(f"  - {company.company_name}: {schedule_type} {schedule_time}, 자동분류: {auto_classify}")
            
    except Exception as e:
        print(f"❌ 상태 확인 실패: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ERPia 배치 시스템 초기화 도구")
    print("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        check_current_status()
    else:
        if setup_batch_system():
            print("\n" + "=" * 60)
            print("✅ 초기화가 성공적으로 완료되었습니다!")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ 초기화 중 오류가 발생했습니다.")
            print("=" * 60)
            sys.exit(1) 