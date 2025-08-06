#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기본 메뉴 데이터 및 권한 설정 스크립트
"""

import sys
import os
from datetime import datetime

# Flask 앱 컨텍스트 필요
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.common.models import Menu, Department, MenuAuth

def setup_basic_data():
    """기본 메뉴와 권한 데이터 설정"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔧 기본 데이터 설정을 시작합니다...")
            
            # 1. 기본 메뉴 생성
            setup_menus()
            
            # 2. 관리자 부서 생성/확인
            setup_admin_department()
            
            # 3. 관리자 권한 설정
            setup_admin_permissions()
            
            print("✅ 기본 데이터 설정이 완료되었습니다!")
            
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            db.session.rollback()

def setup_menus():
    """기본 메뉴 구조 생성"""
    print("📝 메뉴 구조를 설정합니다...")
    
    # Phase 1: 관리자 시스템 메뉴
    menus_data = [
        # 1차 메뉴
        {'menu_name': '관리자', 'menu_url': '/admin', 'icon': 'bi-gear', 'sort': 1, 'depth': 1},
        {'menu_name': '고객 관리', 'menu_url': '/customer', 'icon': 'bi-people', 'sort': 2, 'depth': 1},
        {'menu_name': '통계 관리', 'menu_url': '/stats', 'icon': 'bi-bar-chart', 'sort': 3, 'depth': 1},
        {'menu_name': '영업 관리', 'menu_url': '/sales', 'icon': 'bi-briefcase', 'sort': 4, 'depth': 1},
        {'menu_name': '무역', 'menu_url': '/trade', 'icon': 'bi-ship', 'sort': 5, 'depth': 1},
        {'menu_name': '물류', 'menu_url': '/logistics', 'icon': 'bi-truck', 'sort': 6, 'depth': 1},
    ]
    
    # 1차 메뉴 생성
    for menu_data in menus_data:
        existing = Menu.query.filter_by(menu_name=menu_data['menu_name'], depth=1).first()
        if not existing:
            menu = Menu(
                menu_name=menu_data['menu_name'],
                menu_url=menu_data['menu_url'],
                icon=menu_data['icon'],
                sort=menu_data['sort'],
                depth=menu_data['depth'],
                use_yn='Y',
                company_id=1
            )
            db.session.add(menu)
            print(f"   ✅ {menu_data['menu_name']} 메뉴 생성")
    
    db.session.commit()
    
    # 관리자 하위 메뉴 생성
    admin_menu = Menu.query.filter_by(menu_name='관리자', depth=1).first()
    if admin_menu:
        admin_submenus = [
            {'menu_name': '메뉴 관리', 'menu_url': '/admin/menu', 'icon': 'bi-list-ul', 'sort': 1},
            {'menu_name': '사용자 관리', 'menu_url': '/admin/users', 'icon': 'bi-people', 'sort': 2},
            {'menu_name': '부서 관리', 'menu_url': '/admin/departments', 'icon': 'bi-building', 'sort': 3},
            {'menu_name': '코드 관리', 'menu_url': '/admin/codes', 'icon': 'bi-code-square', 'sort': 4},
            {'menu_name': 'ERPia 배치 관리', 'menu_url': '/batch', 'icon': 'bi-clock', 'sort': 5},
            {'menu_name': '사은품 설정 관리', 'menu_url': '/gift', 'icon': 'bi-gift', 'sort': 6},
        ]
        
        for submenu_data in admin_submenus:
            existing = Menu.query.filter_by(
                menu_name=submenu_data['menu_name'], 
                parent_seq=admin_menu.seq
            ).first()
            if not existing:
                submenu = Menu(
                    menu_name=submenu_data['menu_name'],
                    menu_url=submenu_data['menu_url'],
                    parent_seq=admin_menu.seq,
                    icon=submenu_data['icon'],
                    sort=submenu_data['sort'],
                    depth=2,
                    use_yn='Y',
                    company_id=1
                )
                db.session.add(submenu)
                print(f"   ✅ {submenu_data['menu_name']} 하위메뉴 생성")
    
    db.session.commit()
    print("📝 메뉴 구조 설정 완료")

def setup_admin_department():
    """관리자 부서 설정"""
    print("🏢 관리자 부서를 설정합니다...")
    
    admin_dept = Department.query.filter_by(dept_name='관리자').first()
    if not admin_dept:
        admin_dept = Department(
            dept_name='관리자',
            dept_code='ADMIN',
            use_yn='Y',
            report_yn='Y',
            sort=1,
            company_id=1
        )
        db.session.add(admin_dept)
        db.session.commit()
        print("   ✅ 관리자 부서 생성 완료")
    else:
        print("   ✅ 관리자 부서 이미 존재")
    
    return admin_dept

def setup_admin_permissions():
    """관리자 권한 설정"""
    print("🔐 관리자 권한을 설정합니다...")
    
    admin_dept = Department.query.filter_by(dept_name='관리자').first()
    if not admin_dept:
        print("   ❌ 관리자 부서를 찾을 수 없습니다.")
        return
    
    # 모든 메뉴에 대해 관리자 부서에 전체 권한 부여
    menus = Menu.query.filter_by(use_yn='Y').all()
    
    for menu in menus:
        existing_auth = MenuAuth.query.filter_by(
            dept_seq=admin_dept.seq,
            menu_seq=menu.seq
        ).first()
        
        if not existing_auth:
            menu_auth = MenuAuth(
                dept_seq=admin_dept.seq,
                menu_seq=menu.seq,
                auth_c='Y',  # Create
                auth_r='Y',  # Read
                auth_u='Y',  # Update
                auth_d='Y'   # Delete
            )
            db.session.add(menu_auth)
            print(f"   ✅ {menu.menu_name} 권한 설정")
    
    db.session.commit()
    print("🔐 관리자 권한 설정 완료")

if __name__ == '__main__':
    setup_basic_data() 