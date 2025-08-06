#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DB 상태 및 레거시 데이터 확인 스크립트
"""

from app import create_app
from app.common.models import db, Company, UserCompany, User, Menu, Code, Brand, Department
from sqlalchemy import text

def check_db_status():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("🔍 DB 상태 및 레거시 데이터 확인")
        print("=" * 60)
        
        # 1. 멀티테넌트 테이블 확인
        print("\n📊 멀티테넌트 테이블:")
        try:
            companies = Company.query.all()
            print(f"  - companies: {len(companies)}개")
            for company in companies:
                print(f"    • {company.company_name} ({company.company_code})")
            
            user_companies = UserCompany.query.all()
            print(f"  - user_companies: {len(user_companies)}개")
            
        except Exception as e:
            print(f"  ❌ 멀티테넌트 테이블 오류: {e}")
        
        # 2. 레거시 테이블 데이터 확인
        print("\n🗄️ 레거시 테이블 데이터:")
        try:
            # tbl_member
            result = db.session.execute(text("SELECT COUNT(*) FROM tbl_member"))
            member_count = result.scalar()
            print(f"  - tbl_member: {member_count}명")
            
            # 활성 사용자만
            result = db.session.execute(text("SELECT COUNT(*) FROM tbl_member WHERE member_status = 'A'"))
            active_count = result.scalar()
            print(f"    └ 활성 사용자: {active_count}명")
            
            # chjeon 확인
            result = db.session.execute(text("SELECT seq, id, name, super_user FROM tbl_member WHERE id = 'chjeon'"))
            chjeon_data = result.fetchone()
            if chjeon_data:
                print(f"    └ chjeon: SEQ={chjeon_data[0]}, 이름={chjeon_data[2]}, 관리자={chjeon_data[3]}")
            
            # tbl_category (메뉴)
            result = db.session.execute(text("SELECT COUNT(*) FROM tbl_category"))
            menu_count = result.scalar()
            print(f"  - tbl_category (메뉴): {menu_count}개")
            
            # tbl_code
            result = db.session.execute(text("SELECT COUNT(*) FROM tbl_code"))
            code_count = result.scalar()
            print(f"  - tbl_code: {code_count}개")
            
            # 코드 그룹 확인
            result = db.session.execute(text("SELECT COUNT(*) FROM tbl_code WHERE depth = 0"))
            group_count = result.scalar()
            print(f"    └ 코드 그룹: {group_count}개")
            
            # tbl_department
            result = db.session.execute(text("SELECT COUNT(*) FROM tbl_department"))
            dept_count = result.scalar()
            print(f"  - tbl_department: {dept_count}개")
            
            # tbl_brand
            result = db.session.execute(text("SELECT COUNT(*) FROM tbl_brand"))
            brand_count = result.scalar()
            print(f"  - tbl_brand: {brand_count}개")
            
        except Exception as e:
            print(f"  ❌ 레거시 테이블 확인 오류: {e}")
        
        # 3. 사용자-회사 관계 확인 (chjeon 중심)
        print("\n👤 chjeon 멀티테넌트 상태:")
        try:
            chjeon = User.query.filter_by(id='chjeon').first()
            if chjeon:
                print(f"  - SEQ: {chjeon.seq}")
                print(f"  - 회사ID: {chjeon.company_id}")
                print(f"  - 관리자: {chjeon.is_super_user}")
                
                # 접근 가능한 회사들
                user_companies = UserCompany.query.filter_by(user_seq=chjeon.seq, is_active=True).all()
                print(f"  - 접근 가능 회사: {len(user_companies)}개")
                for uc in user_companies:
                    print(f"    • {uc.company.company_name} (주소속: {uc.is_primary})")
            else:
                print("  ❌ chjeon 사용자를 찾을 수 없음")
        except Exception as e:
            print(f"  ❌ chjeon 멀티테넌트 확인 오류: {e}")
        
        # 4. 테이블 스키마 확인
        print("\n🔧 테이블 스키마 확인:")
        try:
            # tbl_member 컬럼 확인
            result = db.session.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'tbl_member' 
                ORDER BY ordinal_position
            """))
            columns = result.fetchall()
            print(f"  - tbl_member: {len(columns)}개 컬럼")
            
            # 중요 컬럼들 확인
            important_cols = ['seq', 'id', 'name', 'super_user', 'member_status']
            for col_name, col_type in columns:
                if col_name in important_cols:
                    print(f"    • {col_name}: {col_type}")
            
        except Exception as e:
            print(f"  ❌ 스키마 확인 오류: {e}")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    check_db_status() 