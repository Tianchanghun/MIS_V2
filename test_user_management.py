#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사용자 관리 기능 테스트
간소화된 User 모델과 멀티테넌트 기능 테스트
"""

import sys
import os
sys.path.append('.')

from app import create_app
from app.common.models import db, User, UserCompany, Company, Department, UserDepartment
from werkzeug.security import generate_password_hash

def test_user_management():
    """사용자 관리 기능 테스트"""
    
    app = create_app()
    with app.app_context():
        print("🧪 사용자 관리 기능 테스트 시작")
        print("=" * 50)
        
        # 1. 기존 사용자 조회
        print("\n1️⃣ 기존 사용자 현황 확인")
        users = User.query.all()
        print(f"   총 사용자 수: {len(users)}명")
        
        for user in users[:3]:  # 처음 3명만 표시
            print(f"   - {user.login_id} ({user.name})")
            print(f"     이메일: {user.email or 'N/A'}")
            print(f"     핸드폰: {user.mobile or 'N/A'}")
            print(f"     상태: {user.member_status}, 슈퍼유저: {user.super_user}")
            
            # 회사 소속 확인
            companies = user.get_companies()
            if companies:
                print(f"     소속 회사: {[c.company_name for c in companies]}")
            
            # 부서 확인
            departments = user.get_departments()
            if departments:
                print(f"     소속 부서: {[d.dept_name for d in departments]}")
        
        # 2. 회사 및 부서 정보 확인
        print("\n2️⃣ 회사 및 부서 정보")
        companies = Company.query.filter_by(is_active=True).all()
        print(f"   활성 회사: {len(companies)}개")
        for company in companies:
            print(f"   - {company.company_name} ({company.company_code})")
        
        departments = Department.query.filter_by(use_yn='Y').all()
        print(f"   활성 부서: {len(departments)}개")
        for dept in departments[:5]:  # 처음 5개만 표시
            print(f"   - {dept.dept_name}")
        
        # 3. 새 사용자 생성 테스트
        print("\n3️⃣ 새 사용자 생성 테스트")
        test_user = User.query.filter_by(login_id='test_user_001').first()
        
        if test_user:
            print("   기존 테스트 사용자를 삭제합니다...")
            # 관련 데이터 정리
            UserCompany.query.filter_by(user_seq=test_user.seq).delete()
            UserDepartment.query.filter_by(user_seq=test_user.seq).delete()
            db.session.delete(test_user)
            db.session.commit()
        
        # 새 사용자 생성
        print("   새 테스트 사용자를 생성합니다...")
        new_user = User(
            login_id='test_user_001',
            name='테스트 사용자',
            password=generate_password_hash('test123'),
            id_number='E001',
            email='test@example.com',
            mobile='010-1234-5678',
            extension_number='1234',
            super_user='N',
            member_status='Y',
            ins_user='admin',
            ins_date=db.func.now(),
            upt_user='admin',
            upt_date=db.func.now()
        )
        
        db.session.add(new_user)
        db.session.flush()  # ID 생성
        
        # 회사 소속 설정 (에이원에 주소속)
        aone = Company.query.filter_by(company_code='AONE').first()
        if aone:
            user_company = UserCompany(
                user_seq=new_user.seq,
                company_id=aone.id,
                is_primary=True,
                role='user',
                is_active=True
            )
            db.session.add(user_company)
        
        # 부서 소속 설정 (첫 번째 부서)
        first_dept = Department.query.filter_by(use_yn='Y').first()
        if first_dept:
            user_dept = UserDepartment(
                user_seq=new_user.seq,
                dept_seq=first_dept.seq
            )
            db.session.add(user_dept)
        
        db.session.commit()
        print(f"   ✅ 사용자 생성 완료: {new_user.login_id} (ID: {new_user.seq})")
        
        # 4. 생성된 사용자 조회 테스트
        print("\n4️⃣ 생성된 사용자 조회 테스트")
        created_user = User.query.filter_by(login_id='test_user_001').first()
        
        if created_user:
            print(f"   사용자 정보: {created_user.to_dict()}")
            
            # 회사 소속 확인
            companies = created_user.get_companies()
            print(f"   소속 회사: {[c.company_name for c in companies]}")
            
            # 부서 확인
            departments = created_user.get_departments()
            print(f"   소속 부서: {[d.dept_name for d in departments]}")
            
            # 권한 확인
            has_aone_access = created_user.has_company_access(aone.id) if aone else False
            print(f"   에이원 접근 권한: {has_aone_access}")
        
        # 5. UserCompany 관계 테스트
        print("\n5️⃣ 멀티테넌트 관계 테스트")
        uc_count = UserCompany.query.count()
        print(f"   전체 사용자-회사 관계: {uc_count}개")
        
        recent_relations = UserCompany.query.limit(5).all()
        for relation in recent_relations:
            user = User.query.get(relation.user_seq)
            company = Company.query.get(relation.company_id)
            primary_text = " (주소속)" if relation.is_primary else ""
            print(f"   - {user.name} → {company.company_name} ({relation.role}){primary_text}")
        
        print("\n✅ 사용자 관리 기능 테스트 완료!")
        print("=" * 50)

if __name__ == '__main__':
    test_user_management() 