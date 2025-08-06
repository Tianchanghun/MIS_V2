#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
관리자 모듈 초기화
메뉴관리, 코드관리, 부서관리, 사용자관리, 권한관리, 브랜드관리
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, session
from flask_login import login_required, current_user
from app.common.models import Menu, User, Department, Code, Brand, MemberAuth, DeptAuth, db
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
def index():
    """관리자 대시보드"""
    return render_template('admin/dashboard.html')

@admin_bp.route('/menu')
@admin_bp.route('/menu_management')
@login_required
def menu_management():
    """메뉴 관리"""
    try:
        # 모든 메뉴 조회 (계층 구조)
        menus = Menu.query.order_by(Menu.menu_seq, Menu.sort, Menu.depth).all()
        
        return render_template('admin/menu_management.html', menus=menus)
    except Exception as e:
        flash(f'메뉴 목록 조회 중 오류가 발생했습니다: {str(e)}', 'error')
        return render_template('admin/menu_management.html', menus=[])

@admin_bp.route('/users')
@admin_bp.route('/user_management')
@login_required
def user_management():
    """사용자 관리"""
    try:
        users = User.query.order_by(User.name).all()
        return render_template('admin/user_management.html', users=users)
    except Exception as e:
        flash(f'사용자 목록 조회 중 오류가 발생했습니다: {e}', 'error')
        return redirect(url_for('admin.index'))

@admin_bp.route('/departments')
@admin_bp.route('/department_management')
@login_required
def department_management():
    """부서 관리"""
    try:
        departments = Department.query.order_by(Department.sort.asc()).all()
        return render_template('admin/department_management.html', departments=departments)
    except Exception as e:
        flash(f'부서 목록 조회 중 오류가 발생했습니다: {e}', 'error')
        return redirect(url_for('admin.index'))

@admin_bp.route('/code_management')
@login_required
def code_management():
    """코드 관리"""
    try:
        # 모든 코드 조회 (계층 구조)
        codes = Code.query.order_by(Code.code_seq, Code.sort, Code.depth).all()
        
        return render_template('admin/code_management.html', codes=codes)
    except Exception as e:
        flash(f'코드 목록 조회 중 오류가 발생했습니다: {str(e)}', 'error')
        return render_template('admin/code_management.html', codes=[])

@admin_bp.route('/brands')
@admin_bp.route('/brand_management')
@login_required
def brand_management():
    """브랜드 관리"""
    try:
        brands = Brand.query.order_by(Brand.sort.asc()).all()
        return render_template('admin/brand_management.html', brands=brands)
    except Exception as e:
        flash(f'브랜드 목록 조회 중 오류가 발생했습니다: {e}', 'error')
        return redirect(url_for('admin.index'))

@admin_bp.route('/permissions')
@login_required
def permissions():
    """권한 관리"""
    try:
        users = User.query.order_by(User.name).all()
        menus = Menu.query.order_by(Menu.depth.asc(), Menu.sort.asc()).all()
        return render_template('admin/permissions.html', users=users, menus=menus)
    except Exception as e:
        flash(f'권한 관리 조회 중 오류가 발생했습니다: {e}', 'error')
        return redirect(url_for('admin.index'))

# ==================== 메뉴 관리 API ====================

@admin_bp.route('/api/menus/get', methods=['POST'])
@login_required
def get_menu():
    """메뉴 정보 조회"""
    try:
        seq = request.form.get('seq')
        if not seq:
            return jsonify({'success': False, 'message': 'seq가 필요합니다.'})
        
        menu = Menu.query.filter_by(seq=seq).first()
        if not menu:
            return jsonify({'success': False, 'message': '메뉴를 찾을 수 없습니다.'})
        
        return jsonify({'success': True, 'data': menu.to_dict()})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/menus/create', methods=['POST'])
@login_required
def create_menu():
    """메뉴 생성"""
    try:
        data = request.form
        
        if not data.get('name'):
            return jsonify({'success': False, 'message': '메뉴명은 필수입니다.'})
        
        # 메뉴 시퀀스 생성
        parent_seq = int(data.get('parent_seq', 0))
        depth = int(data.get('depth', 0))
        
        if depth == 0:
            menu_seq = Menu.query.filter_by(parent_seq=parent_seq).count() + 1
        else:
            parent_menu = Menu.query.filter_by(seq=parent_seq).first()
            menu_seq = parent_menu.menu_seq if parent_menu else 1
        
        new_menu = Menu(
            parent_seq=parent_seq,
            depth=depth,
            menu_seq=menu_seq,
            name=data.get('name'),
            icon=data.get('icon', ''),
            url=data.get('url', ''),
            use_web_yn=data.get('use_web_yn', 'Y'),
            use_mob_yn=data.get('use_mob_yn', 'Y'),
            use_log_yn=data.get('use_log_yn', 'Y'),
            sort=int(data.get('sort', 1)),
            ins_user='admin',
            ins_date=db.func.now()
        )
        
        db.session.add(new_menu)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '메뉴가 생성되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/menus/update', methods=['POST'])
@login_required
def update_menu():
    """메뉴 수정"""
    try:
        data = request.form
        seq = data.get('seq')
        
        if not seq:
            return jsonify({'success': False, 'message': 'seq가 필요합니다.'})
        
        menu = Menu.query.filter_by(seq=seq).first()
        if not menu:
            return jsonify({'success': False, 'message': '메뉴를 찾을 수 없습니다.'})
        
        # 수정
        menu.name = data.get('name')
        menu.icon = data.get('icon', '')
        menu.url = data.get('url', '')
        menu.use_web_yn = data.get('use_web_yn', 'Y')
        menu.use_mob_yn = data.get('use_mob_yn', 'Y')
        menu.use_log_yn = data.get('use_log_yn', 'Y')
        menu.sort = int(data.get('sort', 1))
        menu.upt_user = 'admin'
        menu.upt_date = db.func.now()
        
        db.session.commit()
        return jsonify({'success': True, 'message': '메뉴가 수정되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/menus/delete', methods=['POST'])
@login_required
def delete_menu():
    """메뉴 삭제"""
    try:
        seq = request.form.get('seq')
        if not seq:
            return jsonify({'success': False, 'message': 'seq가 필요합니다.'})
        
        menu = Menu.query.filter_by(seq=seq).first()
        if not menu:
            return jsonify({'success': False, 'message': '메뉴를 찾을 수 없습니다.'})
        
        # 하위 메뉴도 함께 삭제
        child_menus = Menu.query.filter_by(parent_seq=seq).all()
        for child in child_menus:
            # 관련 권한 데이터도 삭제
            MemberAuth.query.filter_by(menu_seq=child.seq).delete()
            DeptAuth.query.filter_by(menu_seq=child.seq).delete()
            db.session.delete(child)
        
        # 관련 권한 데이터 삭제
        MemberAuth.query.filter_by(menu_seq=seq).delete()
        DeptAuth.query.filter_by(menu_seq=seq).delete()
        
        db.session.delete(menu)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '메뉴가 삭제되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# ==================== 코드 관리 API ====================

@admin_bp.route('/api/codes/get', methods=['POST'])
@login_required
def get_code():
    """코드 정보 조회"""
    try:
        seq = request.form.get('seq')
        if not seq:
            return jsonify({'success': False, 'message': 'seq가 필요합니다.'})
        
        code = Code.query.filter_by(seq=seq).first()
        if not code:
            return jsonify({'success': False, 'message': '코드를 찾을 수 없습니다.'})
        
        return jsonify({'success': True, 'data': code.to_dict()})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/codes/children', methods=['POST'])
@login_required  
def get_child_codes():
    """하위 코드 목록 조회"""
    try:
        parent_seq = request.form.get('parent_seq', 0)
        codes = Code.query.filter_by(parent_seq=parent_seq).order_by(Code.sort, Code.seq).all()
        
        return jsonify({
            'success': True,
            'data': [code.to_dict() for code in codes]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/codes/update', methods=['POST'])
@login_required
def update_code():
    """코드 수정"""
    try:
        data = request.form
        seq = data.get('seq')
        
        if not seq:
            return jsonify({'success': False, 'message': 'seq가 필요합니다.'})
        
        code = Code.query.filter_by(seq=seq).first()
        if not code:
            return jsonify({'success': False, 'message': '코드를 찾을 수 없습니다.'})
        
        # 중복 체크 (본인 제외)
        existing = Code.query.filter(
            Code.code == data.get('code'),
            Code.parent_seq == data.get('parent_seq', 0),
            Code.seq != seq
        ).first()
        
        if existing:
            return jsonify({'success': False, 'message': '이미 존재하는 코드입니다.'})
        
        # 수정
        code.code = data.get('code')
        code.code_name = data.get('code_name')
        code.code_info = data.get('code_info', '')
        code.sort = int(data.get('sort', 1))
        code.upt_user = 'admin'
        code.upt_date = db.func.now()
        
        db.session.commit()
        return jsonify({'success': True, 'message': '코드가 수정되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/codes/delete', methods=['POST'])
@login_required
def delete_code():
    """코드 삭제"""
    try:
        seq = request.form.get('seq')
        if not seq:
            return jsonify({'success': False, 'message': 'seq가 필요합니다.'})
        
        code = Code.query.filter_by(seq=seq).first()
        if not code:
            return jsonify({'success': False, 'message': '코드를 찾을 수 없습니다.'})
        
        # 하위 코드도 함께 삭제
        child_codes = Code.query.filter_by(parent_seq=seq).all()
        for child in child_codes:
            db.session.delete(child)
        
        db.session.delete(code)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '코드가 삭제되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}) 

# ==================== 부서 관리 API ====================

@admin_bp.route('/api/departments/get', methods=['POST'])
@login_required
def get_department():
    """부서 정보 조회"""
    try:
        seq = request.form.get('seq')
        if not seq:
            return jsonify({'success': False, 'message': 'seq가 필요합니다.'})
        
        dept = Department.query.filter_by(seq=seq).first()
        if not dept:
            return jsonify({'success': False, 'message': '부서를 찾을 수 없습니다.'})
        
        return jsonify({'success': True, 'data': {
            'seq': dept.seq,
            'dept_name': dept.dept_name,
            'sort': dept.sort,
            'report_yn': dept.report_yn,
            'use_yn': dept.use_yn,
            'font_color': dept.font_color,
            'bg_color': dept.bg_color
        }})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/departments/create', methods=['POST'])
@login_required
def create_department():
    """부서 생성"""
    try:
        data = request.form
        
        if not data.get('dept_name'):
            return jsonify({'success': False, 'message': '부서명은 필수입니다.'})
        
        new_dept = Department(
            dept_name=data.get('dept_name'),
            sort=int(data.get('sort', 1)),
            report_yn=data.get('report_yn', 'Y'),
            use_yn=data.get('use_yn', 'Y'),
            font_color=data.get('font_color', '#000000'),
            bg_color=data.get('bg_color', '#ffffff'),
            ins_user='admin',
            ins_date=db.func.now()
        )
        
        db.session.add(new_dept)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '부서가 생성되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/departments/update', methods=['POST'])
@login_required
def update_department():
    """부서 수정"""
    try:
        data = request.form
        seq = data.get('seq')
        
        if not seq:
            return jsonify({'success': False, 'message': 'seq가 필요합니다.'})
        
        dept = Department.query.filter_by(seq=seq).first()
        if not dept:
            return jsonify({'success': False, 'message': '부서를 찾을 수 없습니다.'})
        
        dept.dept_name = data.get('dept_name')
        dept.sort = int(data.get('sort', 1))
        dept.report_yn = data.get('report_yn', 'Y')
        dept.use_yn = data.get('use_yn', 'Y')
        dept.font_color = data.get('font_color', '#000000')
        dept.bg_color = data.get('bg_color', '#ffffff')
        dept.upt_user = 'admin'
        dept.upt_date = db.func.now()
        
        db.session.commit()
        return jsonify({'success': True, 'message': '부서가 수정되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/departments/delete', methods=['POST'])
@login_required
def delete_department():
    """부서 삭제"""
    try:
        seq = request.form.get('seq')
        if not seq:
            return jsonify({'success': False, 'message': 'seq가 필요합니다.'})
        
        dept = Department.query.filter_by(seq=seq).first()
        if not dept:
            return jsonify({'success': False, 'message': '부서를 찾을 수 없습니다.'})
        
        # 부서 사용 중지로 변경 (실제 삭제하지 않음)
        dept.use_yn = 'N'
        dept.upt_user = 'admin'
        dept.upt_date = db.func.now()
        
        db.session.commit()
        return jsonify({'success': True, 'message': '부서가 삭제되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/departments/auth', methods=['POST'])
@login_required
def get_department_auth():
    """부서 권한 조회"""
    try:
        dept_seq = request.form.get('dept_seq')
        if not dept_seq:
            return jsonify({'success': False, 'message': 'dept_seq가 필요합니다.'})
        
        # 모든 메뉴와 부서 권한을 조회
        menus = Menu.query.order_by(Menu.depth.asc(), Menu.sort.asc()).all()
        dept_auths = DeptAuth.query.filter_by(dept_seq=dept_seq).all()
        
        # 권한 데이터를 딕셔너리로 변환
        auth_dict = {auth.menu_seq: auth for auth in dept_auths}
        
        result = []
        for menu in menus:
            auth = auth_dict.get(menu.seq)
            result.append({
                'menu': menu.to_dict(),
                'auth': {
                    'auth_read': auth.auth_read if auth else 'N',
                    'auth_create': auth.auth_create if auth else 'N',
                    'auth_update': auth.auth_update if auth else 'N',
                    'auth_delete': auth.auth_delete if auth else 'N'
                } if auth else None
            })
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/departments/auth/save', methods=['POST'])
@login_required
def save_department_auth():
    """부서 권한 저장"""
    try:
        dept_seq = request.form.get('dept_seq')
        auth_data = request.form.get('auth_data')
        
        if not dept_seq or not auth_data:
            return jsonify({'success': False, 'message': '필수 데이터가 누락되었습니다.'})
        
        import json
        auth_list = json.loads(auth_data)
        
        # 기존 권한 삭제
        DeptAuth.query.filter_by(dept_seq=dept_seq).delete()
        
        # 새 권한 추가
        for auth_item in auth_list:
            if (auth_item['AuthRead'] == 'Y' or auth_item['AuthCreate'] == 'Y' or 
                auth_item['AuthUpdate'] == 'Y' or auth_item['AuthDelete'] == 'Y'):
                
                new_auth = DeptAuth(
                    dept_seq=dept_seq,
                    menu_seq=auth_item['Seq'],
                    auth_read=auth_item['AuthRead'],
                    auth_create=auth_item['AuthCreate'],
                    auth_update=auth_item['AuthUpdate'],
                    auth_delete=auth_item['AuthDelete'],
                    ins_user='admin',
                    ins_date=db.func.now()
                )
                db.session.add(new_auth)
        
        db.session.commit()
        return jsonify({'success': True, 'message': '부서 권한이 저장되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# ==================== 사용자 관리 API ====================

@admin_bp.route('/api/users/get', methods=['POST'])
@login_required
def get_user():
    """사용자 정보 조회"""
    try:
        seq = request.form.get('seq')
        if not seq:
            return jsonify({'success': False, 'message': 'seq가 필요합니다.'})
        
        user = User.query.filter_by(seq=seq).first()
        if not user:
            return jsonify({'success': False, 'message': '사용자를 찾을 수 없습니다.'})
        
        return jsonify({'success': True, 'data': user.to_dict()})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/users/create', methods=['POST'])
@login_required
def create_user():
    """사용자 생성"""
    try:
        data = request.form
        
        if not data.get('id') or not data.get('name'):
            return jsonify({'success': False, 'message': 'ID와 이름은 필수입니다.'})
        
        # ID 중복 체크
        existing = User.query.filter_by(id=data.get('id')).first()
        if existing:
            return jsonify({'success': False, 'message': '이미 존재하는 ID입니다.'})
        
        from werkzeug.security import generate_password_hash
        
        new_user = User(
            id=data.get('id'),
            password=data.get('password', 'temp123'),  # 임시 비밀번호
            name=data.get('name'),
            member_status=data.get('member_status', 'A'),
            super_user=data.get('super_user', 'N'),
            work_group=data.get('work_group', ''),
            biz_card_num=data.get('biz_card_num', ''),
            ins_user='admin',
            ins_date=db.func.now()
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '사용자가 생성되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/users/update', methods=['POST'])
@login_required
def update_user():
    """사용자 수정"""
    try:
        data = request.form
        seq = data.get('seq')
        
        if not seq:
            return jsonify({'success': False, 'message': 'seq가 필요합니다.'})
        
        user = User.query.filter_by(seq=seq).first()
        if not user:
            return jsonify({'success': False, 'message': '사용자를 찾을 수 없습니다.'})
        
        user.name = data.get('name')
        user.member_status = data.get('member_status', 'A')
        user.super_user = data.get('super_user', 'N')
        user.work_group = data.get('work_group', '')
        user.biz_card_num = data.get('biz_card_num', '')
        user.upt_user = 'admin'
        user.upt_date = db.func.now()
        
        # 비밀번호 변경 시
        if data.get('password'):
            user.password = data.get('password')
        
        db.session.commit()
        return jsonify({'success': True, 'message': '사용자가 수정되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/users/delete', methods=['POST'])
@login_required
def delete_user():
    """사용자 삭제"""
    try:
        seq = request.form.get('seq')
        if not seq:
            return jsonify({'success': False, 'message': 'seq가 필요합니다.'})
        
        user = User.query.filter_by(seq=seq).first()
        if not user:
            return jsonify({'success': False, 'message': '사용자를 찾을 수 없습니다.'})
        
        # 사용자 상태를 비활성화로 변경
        user.member_status = 'D'
        user.upt_user = 'admin'
        user.upt_date = db.func.now()
        
        db.session.commit()
        return jsonify({'success': True, 'message': '사용자가 삭제되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# ==================== 브랜드 관리 API ====================

@admin_bp.route('/api/brands/get', methods=['POST'])
@login_required
def get_brand():
    """브랜드 정보 조회"""
    try:
        seq = request.form.get('seq')
        if not seq:
            return jsonify({'success': False, 'message': 'seq가 필요합니다.'})
        
        brand = Brand.query.filter_by(seq=seq).first()
        if not brand:
            return jsonify({'success': False, 'message': '브랜드를 찾을 수 없습니다.'})
        
        return jsonify({'success': True, 'data': {
            'seq': brand.seq,
            'brand_name': brand.brand_name,
            'brand_code': brand.brand_code,
            'sort': brand.sort,
            'use_yn': brand.use_yn,
            'memo': brand.memo
        }})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/brands/create', methods=['POST'])
@login_required
def create_brand():
    """브랜드 생성"""
    try:
        data = request.get_json()
        
        if not data.get('brand_name') or not data.get('brand_code') or not data.get('brand_eng_name'):
            return jsonify({'success': False, 'message': '브랜드명, 브랜드 코드, 영문명은 필수입니다.'})
        
        # 코드 중복 체크
        existing = Brand.query.filter_by(brand_code=data.get('brand_code')).first()
        if existing:
            return jsonify({'success': False, 'message': '이미 존재하는 브랜드 코드입니다.'})
        
        new_brand = Brand(
            brand_name=data.get('brand_name'),
            brand_code=data.get('brand_code'),
            brand_eng_name=data.get('brand_eng_name'),
            brand_info=data.get('brand_info', ''),
            sort=int(data.get('sort', 1)),
            use_yn=data.get('use_yn', 'Y'),
            company_id=session.get('current_company_id'),
            ins_user=current_user.id,
            ins_date=datetime.utcnow()
        )
        
        db.session.add(new_brand)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '브랜드가 생성되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/brands/update', methods=['POST'])
@login_required
def update_brand():
    """브랜드 수정"""
    try:
        data = request.get_json()
        seq = data.get('seq')
        
        if not seq:
            return jsonify({'success': False, 'message': 'seq가 필요합니다.'})
        
        brand = Brand.query.filter_by(seq=seq).first()
        if not brand:
            return jsonify({'success': False, 'message': '브랜드를 찾을 수 없습니다.'})
        
        # 코드 중복 체크 (본인 제외)
        existing = Brand.query.filter(
            Brand.brand_code == data.get('brand_code'),
            Brand.seq != seq
        ).first()
        if existing:
            return jsonify({'success': False, 'message': '이미 존재하는 브랜드 코드입니다.'})
        
        brand.brand_name = data.get('brand_name')
        brand.brand_code = data.get('brand_code')
        brand.brand_eng_name = data.get('brand_eng_name')
        brand.brand_info = data.get('brand_info', '')
        brand.sort = int(data.get('sort', 1))
        brand.use_yn = data.get('use_yn', 'Y')
        brand.upt_user = current_user.id
        brand.upt_date = datetime.utcnow()
        
        db.session.commit()
        return jsonify({'success': True, 'message': '브랜드가 수정되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/brands/delete', methods=['POST'])
@login_required
def delete_brand():
    """브랜드 삭제"""
    try:
        data = request.get_json()
        seq = data.get('seq')
        if not seq:
            return jsonify({'success': False, 'message': 'seq가 필요합니다.'})
        
        brand = Brand.query.filter_by(seq=seq).first()
        if not brand:
            return jsonify({'success': False, 'message': '브랜드를 찾을 수 없습니다.'})
        
        db.session.delete(brand)
        db.session.commit()
        return jsonify({'success': True, 'message': '브랜드가 삭제되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}) 