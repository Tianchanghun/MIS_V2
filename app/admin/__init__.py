#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
관리자 모듈 초기화
메뉴관리, 코드관리, 부서관리, 사용자관리, 권한관리, 브랜드관리
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, session, current_app
from flask_login import login_required, current_user
from app.common.models import Menu, User, Department, Code, Brand, MemberAuth, DeptAuth, db
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
def index():
    """관리자 대시보드"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    """관리자 대시보드"""
    return render_template('admin/dashboard.html')

@admin_bp.route('/menu')
@admin_bp.route('/menu_management')
def menu_management():
    """메뉴 관리"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def user_management():
    """사용자 관리"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    """사용자 관리"""
    try:
        users = User.query.order_by(User.name).all()
        return render_template('admin/user_management.html', users=users)
    except Exception as e:
        flash(f'사용자 목록 조회 중 오류가 발생했습니다: {e}', 'error')
        return redirect(url_for('admin.index'))

@admin_bp.route('/departments')
@admin_bp.route('/department_management')
def department_management():
    """부서 관리"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    """부서 관리"""
    try:
        departments = Department.query.order_by(Department.sort.asc()).all()
        return render_template('admin/department_management.html', departments=departments)
    except Exception as e:
        flash(f'부서 목록 조회 중 오류가 발생했습니다: {e}', 'error')
        return redirect(url_for('admin.index'))

@admin_bp.route('/code_management')
def code_management():
    """코드 관리"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    
    try:
        # 분석 결과를 바탕으로 개선된 정렬: CodeSeq → parent_seq → Sort → Seq
        # 이렇게 하면 같은 CodeSeq 그룹 내에서 부모-자식 관계가 더 명확하게 표현됩니다
        codes_query = Code.query.order_by(
            Code.code_seq.asc().nulls_last(),    # CodeSeq 먼저 (그룹별)
            Code.parent_seq.asc().nulls_first(), # 부모 관계 (NULL이 Root)
            Code.sort.asc(),                     # 정렬 순서
            Code.seq.asc()                       # 시퀀스 순서 (최종)
        ).all()
        
        # Code 객체를 딕셔너리로 변환
        codes = [code.to_dict() for code in codes_query]
        
        current_app.logger.info(f"코드 관리 페이지: {len(codes)}개 코드 조회 완료")
        
        # 디버깅: 개선된 계층 구조 확인
        if codes:
            depth_counts = {}
            codeseq_counts = {}
            for code in codes[:15]:  # 첫 15개만 로깅
                depth = code['depth']
                code_seq = code['code_seq']
                depth_counts[depth] = depth_counts.get(depth, 0) + 1
                codeseq_counts[code_seq] = codeseq_counts.get(code_seq, 0) + 1
                current_app.logger.info(f"📋 코드: {code['seq']} | {code['code']} | {code['code_name']} | CodeSeq: {code_seq} | Parent: {code['parent_seq']} | Sort: {code['sort']}")
            
            current_app.logger.info(f"📊 깊이별 코드 수: {depth_counts}")
            current_app.logger.info(f"📁 CodeSeq별 코드 수: {list(codeseq_counts.items())[:10]}")
            current_app.logger.info(f"🌳 정렬 방식: CodeSeq → parent_seq → Sort → Seq (트리 구조 최적화)")
        else:
            current_app.logger.warning("⚠️ 조회된 코드가 없습니다!")
        
        return render_template('admin/code_management.html', codes=codes)
        
    except Exception as e:
        current_app.logger.error(f"코드 관리 페이지 오류: {e}")
        flash(f'코드 목록 조회 중 오류가 발생했습니다: {str(e)}', 'error')
        return render_template('admin/code_management.html', codes=[])

@admin_bp.route('/brands')
@admin_bp.route('/brand_management')
def brand_management():
    """브랜드 관리"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    """브랜드 관리"""
    try:
        brands = Brand.query.order_by(Brand.sort.asc()).all()
        return render_template('admin/brand_management.html', brands=brands)
    except Exception as e:
        flash(f'브랜드 목록 조회 중 오류가 발생했습니다: {e}', 'error')
        return redirect(url_for('admin.index'))

@admin_bp.route('/permissions')
def permissions():
    """권한 관리"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def get_menu():
    """메뉴 정보 조회"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def create_menu():
    """메뉴 생성"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def update_menu():
    """메뉴 수정"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def delete_menu():
    """메뉴 삭제"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def get_code():
    """코드 정보 조회"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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

@admin_bp.route('/api/codes/create', methods=['POST'])
def create_code():
    """코드 추가"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    
    try:
        parent_seq = request.form.get('parent_seq', 0)
        depth = request.form.get('depth', 0)
        code = request.form.get('code', '').strip()
        code_name = request.form.get('code_name', '').strip()
        code_info = request.form.get('code_info', '').strip()
        sort = request.form.get('sort', 1)
        
        # 유효성 검사
        if not code or not code_name:
            return jsonify({'success': False, 'message': '코드와 코드명은 필수입니다.'})
        
        if int(depth) > 4:
            return jsonify({'success': False, 'message': '최대 깊이는 4까지입니다.'})
        
        # 중복 코드 체크 (같은 부모 하위에서)
        existing_code = Code.query.filter_by(
            parent_seq=int(parent_seq) if parent_seq != '0' else None,
            code=code
        ).first()
        
        if existing_code:
            return jsonify({'success': False, 'message': '같은 레벨에서 중복된 코드입니다.'})
        
        # 새 코드 생성
        new_code = Code(
            parent_seq=int(parent_seq) if parent_seq != '0' else None,
            depth=int(depth),
            code=code,
            code_name=code_name,
            code_info=code_info if code_info else None,
            sort=int(sort),
            ins_user=session.get('member_seq'),
            ins_date=datetime.now()
        )
        
        db.session.add(new_code)
        db.session.commit()
        
        current_app.logger.info(f"코드 추가 성공: {code} - {code_name} (사용자: {session.get('member_seq')})")
        
        return jsonify({
            'success': True,
            'message': '코드가 성공적으로 추가되었습니다.',
            'data': {
                'seq': new_code.seq,
                'code': new_code.code,
                'code_name': new_code.code_name
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"코드 추가 실패: {e}")
        return jsonify({'success': False, 'message': f'코드 추가 중 오류가 발생했습니다: {str(e)}'}), 500

@admin_bp.route('/api/codes/children', methods=['POST'])
  
def get_child_codes():
    """하위 코드 목록 조회"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def update_code():
    """코드 수정"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    
    try:
        seq = request.form.get('edit_seq')
        code = request.form.get('code', '').strip()
        code_name = request.form.get('code_name', '').strip()
        code_info = request.form.get('code_info', '').strip()
        sort = request.form.get('sort', 1)
        
        # 유효성 검사
        if not seq or not code or not code_name:
            return jsonify({'success': False, 'message': 'seq, 코드, 코드명은 필수입니다.'})
        
        # 기존 코드 조회
        existing_code = Code.query.filter_by(seq=int(seq)).first()
        if not existing_code:
            return jsonify({'success': False, 'message': '해당 코드를 찾을 수 없습니다.'})
        
        # 중복 코드 체크 (자신 제외, 같은 부모 하위에서)
        duplicate_code = Code.query.filter(
            Code.seq != int(seq),
            Code.parent_seq == existing_code.parent_seq,
            Code.code == code
        ).first()
        
        if duplicate_code:
            return jsonify({'success': False, 'message': '같은 레벨에서 중복된 코드입니다.'})
        
        # 코드 수정
        existing_code.code = code
        existing_code.code_name = code_name
        existing_code.code_info = code_info if code_info else None
        existing_code.sort = int(sort)
        existing_code.upt_user = session.get('member_seq')
        existing_code.upt_date = datetime.now()
        
        db.session.commit()
        
        current_app.logger.info(f"코드 수정 성공: {code} - {code_name} (사용자: {session.get('member_seq')})")
        
        return jsonify({
            'success': True,
            'message': '코드가 성공적으로 수정되었습니다.',
            'data': {
                'seq': existing_code.seq,
                'code': existing_code.code,
                'code_name': existing_code.code_name
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"코드 수정 실패: {e}")
        return jsonify({'success': False, 'message': f'코드 수정 중 오류가 발생했습니다: {str(e)}'}), 500

@admin_bp.route('/api/codes/delete', methods=['POST'])
def delete_code():
    """코드 삭제 (하위 코드 포함)"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    
    try:
        seq = request.form.get('seq')
        if not seq:
            return jsonify({'success': False, 'message': 'seq가 필요합니다.'})
        
        # 기존 코드 조회
        target_code = Code.query.filter_by(seq=int(seq)).first()
        if not target_code:
            return jsonify({'success': False, 'message': '해당 코드를 찾을 수 없습니다.'})
        
        # 하위 코드들을 재귀적으로 찾기
        def find_all_children(parent_seq):
            children = Code.query.filter_by(parent_seq=parent_seq).all()
            all_children = children.copy()
            for child in children:
                all_children.extend(find_all_children(child.seq))
            return all_children
        
        # 삭제할 모든 코드 (자신 + 하위 코드들)
        all_codes_to_delete = [target_code] + find_all_children(target_code.seq)
        
        # 삭제 확인 로그
        deleted_codes = []
        for code in all_codes_to_delete:
            deleted_codes.append(f"{code.code} - {code.code_name}")
            db.session.delete(code)
        
        db.session.commit()
        
        current_app.logger.info(f"코드 삭제 성공: {len(deleted_codes)}개 코드 삭제 - {', '.join(deleted_codes)} (사용자: {session.get('member_seq')})")
        
        return jsonify({
            'success': True,
            'message': f'코드가 성공적으로 삭제되었습니다. (총 {len(deleted_codes)}개)',
            'data': {
                'deleted_count': len(deleted_codes),
                'deleted_codes': deleted_codes
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"코드 삭제 실패: {e}")
        return jsonify({'success': False, 'message': f'코드 삭제 중 오류가 발생했습니다: {str(e)}'}), 500

@admin_bp.route('/api/codes/update-sort', methods=['POST'])
def update_code_sort():
    """코드 순서 변경 (레거시 AdminController.cs CodeSeqChange와 동일)"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    
    try:
        seq = request.form.get('seq')
        new_sort = request.form.get('sort')
        
        if not seq or not new_sort:
            return jsonify({'success': False, 'message': 'seq와 sort가 필요합니다.'})
        
        # 코드 조회
        target_code = Code.query.filter_by(seq=int(seq)).first()
        if not target_code:
            return jsonify({'success': False, 'message': '해당 코드를 찾을 수 없습니다.'})
        
        # 같은 부모의 형제 코드들 조회
        siblings = Code.query.filter_by(
            parent_seq=target_code.parent_seq,
            depth=target_code.depth
        ).filter(Code.seq != target_code.seq).all()
        
        # 새로운 정렬 순서 적용
        new_sort_value = int(new_sort)
        
        # 같은 순서나 그 이후의 코드들을 한 칸씩 밀어내기
        for sibling in siblings:
            if (sibling.sort or 999) >= new_sort_value:
                sibling.sort = (sibling.sort or 0) + 1
                sibling.upt_user = session.get('member_seq')
                sibling.upt_date = datetime.now()
        
        # 대상 코드의 순서 변경
        target_code.sort = new_sort_value
        target_code.upt_user = session.get('member_seq')
        target_code.upt_date = datetime.now()
        
        db.session.commit()
        
        current_app.logger.info(f"코드 순서 변경 성공: {target_code.code} → Sort {new_sort_value} (사용자: {session.get('member_seq')})")
        
        return jsonify({
            'success': True,
            'message': '순서가 성공적으로 변경되었습니다.',
            'data': {
                'seq': target_code.seq,
                'new_sort': new_sort_value
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"코드 순서 변경 실패: {e}")
        return jsonify({'success': False, 'message': f'순서 변경 중 오류가 발생했습니다: {str(e)}'}), 500

@admin_bp.route('/api/codes/paginated', methods=['GET'])
def get_codes_paginated():
    """페이징된 코드 목록 조회"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        depth = request.args.get('depth', type=int)
        parent_seq = request.args.get('parent_seq', type=int)
        
        # 기본 쿼리
        query = Code.query
        
        # 필터링
        if depth is not None:
            query = query.filter(Code.depth == depth)
        if parent_seq is not None:
            query = query.filter(Code.parent_seq == parent_seq)
        
        # 정렬 및 페이징
        codes = query.order_by(
            Code.depth.asc(),
            Code.parent_seq.asc().nullsfirst(),
            Code.sort.asc(),
            Code.seq.asc()
        ).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        result = []
        for code in codes.items:
            result.append({
                'seq': code.seq,
                'parent_seq': code.parent_seq,
                'depth': code.depth,
                'sort': code.sort,
                'code': code.code,
                'code_name': code.code_name,
                'code_info': code.code_info
            })
        
        return jsonify({
            'success': True,
            'data': result,
            'pagination': {
                'page': codes.page,
                'pages': codes.pages,
                'per_page': codes.per_page,
                'total': codes.total,
                'has_next': codes.has_next,
                'has_prev': codes.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"페이징된 코드 조회 실패: {e}")
        return jsonify({'success': False, 'message': f'코드 조회 중 오류가 발생했습니다: {str(e)}'}), 500

@admin_bp.route('/api/codes/update-order', methods=['POST'])
def update_code_order():
    """코드 정렬 순서 업데이트 (드래그 앤 드롭용)"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    
    try:
        # POST 데이터 처리 (form과 JSON 모두 지원)
        if request.is_json:
            data = request.get_json()
            parent_seq = data.get('parent_seq')
            depth = data.get('depth')
            order_json = data.get('order')
        else:
            parent_seq = request.form.get('parent_seq')
            depth = request.form.get('depth')
            order_json = request.form.get('order')
        
        if not parent_seq or not depth or not order_json:
            return jsonify({'success': False, 'message': '필수 데이터가 누락되었습니다.'})
        
        # JSON 파싱
        import json
        try:
            order_list = json.loads(order_json)
        except:
            return jsonify({'success': False, 'message': '순서 데이터 형식이 잘못되었습니다.'})
        
        parent_seq = int(parent_seq)
        depth = int(depth)
        
        # 해당 부모의 같은 깊이 코드들 조회
        codes = Code.query.filter_by(parent_seq=parent_seq, depth=depth).all()
        code_dict = {code.seq: code for code in codes}
        
        # 새로운 순서로 sort 값 업데이트
        for index, seq in enumerate(order_list):
            if seq in code_dict:
                code_dict[seq].sort = index + 1
                code_dict[seq].upt_user = session.get('member_seq')
                code_dict[seq].upt_date = datetime.now()
        
        db.session.commit()
        
        current_app.logger.info(f"드래그 앤 드롭 순서 변경 완료: parent={parent_seq}, depth={depth}, order={order_list}")
        
        return jsonify({
            'success': True,
            'message': '정렬 순서가 성공적으로 업데이트되었습니다.',
            'data': {
                'parent_seq': parent_seq,
                'depth': depth,
                'updated_count': len(order_list)
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"드래그 앤 드롭 순서 변경 실패: {e}")
        return jsonify({'success': False, 'message': f'순서 변경 중 오류가 발생했습니다: {str(e)}'}), 500

# ==================== 부서 관리 API ====================

@admin_bp.route('/api/departments/get', methods=['POST'])
def get_department():
    """부서 정보 조회"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def create_department():
    """부서 생성"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    """부서 생성"""
    try:
        data = request.form
        
        if not data.get('dept_name'):
            return jsonify({'success': False, 'message': '부서명은 필수입니다.'})
        
        new_dept = Department(
            dept_name=data.get('dept_name'),
            sort=int(data.get('sort', 1)),
            use_yn=data.get('use_yn', 'Y'),
            company_id=int(data.get('company_id', 1)),
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
def update_department():
    """부서 수정"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
        dept.use_yn = data.get('use_yn', 'Y')
        dept.company_id = int(data.get('company_id', dept.company_id or 1))
        dept.upt_user = 'admin'
        dept.upt_date = db.func.now()
        
        db.session.commit()
        return jsonify({'success': True, 'message': '부서가 수정되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/departments/delete', methods=['POST'])
def delete_department():
    """부서 삭제"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def get_department_auth():
    """부서 권한 조회"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def save_department_auth():
    """부서 권한 저장"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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

@admin_bp.route('/api/users', methods=['GET'])
def get_users():
    """사용자 목록 조회 (멀티테넌트 지원)"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    """사용자 목록 조회 (멀티테넌트 지원)"""
    try:
        company_id = session.get('current_company_id', 1)
        
        # 페이징 파라미터
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        
        # 기본 쿼리 (해당 회사에 소속된 사용자만)
        from app.common.models import UserCompany
        query = db.session.query(User).join(
            UserCompany, User.seq == UserCompany.user_seq
        ).filter(
            UserCompany.company_id == company_id,
            UserCompany.is_active == True,
            User.member_status == 'Y'
        )
        
        # 검색 조건
        if search:
            query = query.filter(
                db.or_(
                    User.name.contains(search),
                    User.login_id.contains(search),
                    User.id_number.contains(search),
                    User.email.contains(search)
                )
            )
        
        # 페이징 실행
        users = query.order_by(User.name.asc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 결과 변환
        result = []
        for user in users.items:
            user_data = user.to_dict()
            result.append(user_data)
        
        return jsonify({
            'success': True,
            'data': result,
            'pagination': {
                'page': users.page,
                'pages': users.pages,
                'per_page': users.per_page,
                'total': users.total
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/api/users', methods=['POST'])
def create_user():
    """사용자 생성 (멀티테넌트 지원)"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    """사용자 생성 (멀티테넌트 지원)"""
    try:
        data = request.get_json()
        
        # 필수 필드 검증
        required_fields = ['login_id', 'name', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field}는 필수입니다.'}), 400
        
        # ID 중복 검사 (전체 시스템에서 중복 불가)
        existing_user = User.query.filter_by(login_id=data['login_id']).first()
        if existing_user:
            return jsonify({'success': False, 'message': '이미 존재하는 ID입니다.'}), 400
        
        # 사번 중복 검사 (회사별로 중복 불가)
        if data.get('id_number'):
            company_id = session.get('current_company_id', 1)
            from app.common.models import UserCompany
            existing_id_number = db.session.query(User).join(
                UserCompany, User.seq == UserCompany.user_seq
            ).filter(
                UserCompany.company_id == company_id,
                User.id_number == data['id_number']
            ).first()
            if existing_id_number:
                return jsonify({'success': False, 'message': '해당 회사에 이미 존재하는 사번입니다.'}), 400
        
        # 새 사용자 생성
        from werkzeug.security import generate_password_hash
        from datetime import datetime
        
        new_user = User(
            login_id=data['login_id'],
            name=data['name'],
            password=generate_password_hash(data['password']),
            id_number=data.get('id_number'),
            email=data.get('email'),
            mobile=data.get('mobile'),
            extension_number=data.get('extension_number'),
            super_user=data.get('super_user', 'N'),
            member_status=data.get('member_status', 'Y'),
            ins_user=session.get('member_id', 'admin'),
            ins_date=datetime.utcnow(),
            upt_user=session.get('member_id', 'admin'),
            upt_date=datetime.utcnow()
        )
        
        db.session.add(new_user)
        db.session.flush()  # seq 값 얻기 위해
        
        # 회사 소속 설정
        company_settings = data.get('companies', [])
        if not company_settings:
            # 기본값: 현재 회사에 일반 사용자로 소속
            current_company_id = session.get('current_company_id', 1)
            company_settings = [{'company_id': current_company_id, 'is_primary': True, 'role': 'user'}]
        
        from app.common.models import UserCompany
        for company_setting in company_settings:
            user_company = UserCompany(
                user_seq=new_user.seq,
                company_id=company_setting['company_id'],
                is_primary=company_setting.get('is_primary', False),
                role=company_setting.get('role', 'user'),
                is_active=True
            )
            db.session.add(user_company)
        
        # 부서 연결 처리
        if data.get('department_ids'):
            from app.common.models import UserDepartment
            for dept_id in data['department_ids']:
                user_dept = UserDepartment(
                    user_seq=new_user.seq,
                    dept_seq=dept_id
                )
                db.session.add(user_dept)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '사용자가 성공적으로 생성되었습니다.',
            'data': {'seq': new_user.seq}
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/api/users/<int:user_seq>', methods=['GET'])
def get_user(user_seq):
    """사용자 상세 조회"""
    try:
        user = User.query.filter_by(seq=user_seq).first()
        
        if not user:
            return jsonify({'success': False, 'message': '사용자를 찾을 수 없습니다.'}), 404
        
        # 현재 회사에 접근 권한이 있는지 확인
        current_company_id = session.get('current_company_id', 1)
        current_user_super = session.get('super_user') == 'Y'
        if not user.has_company_access(current_company_id) and not current_user_super:
            return jsonify({'success': False, 'message': '해당 사용자에 대한 접근 권한이 없습니다.'}), 403
        
        user_data = user.to_dict()
        
        return jsonify({
            'success': True,
            'data': user_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/api/users/<int:user_seq>', methods=['PUT'])
def update_user(user_seq):
    """사용자 수정"""
    try:
        data = request.get_json()
        
        user = User.query.filter_by(seq=user_seq).first()
        if not user:
            return jsonify({'success': False, 'message': '사용자를 찾을 수 없습니다.'}), 404
        
        # 접근 권한 확인
        current_company_id = session.get('current_company_id', 1)
        current_user_super = session.get('super_user') == 'Y'
        if not user.has_company_access(current_company_id) and not current_user_super:
            return jsonify({'success': False, 'message': '해당 사용자에 대한 접근 권한이 없습니다.'}), 403
        
        # ID 중복 검사 (자신 제외)
        if data.get('login_id') and data['login_id'] != user.login_id:
            existing_user = User.query.filter_by(login_id=data['login_id']).filter(User.seq != user_seq).first()
            if existing_user:
                return jsonify({'success': False, 'message': '이미 존재하는 ID입니다.'}), 400
        
        # 사번 중복 검사 (회사별, 자신 제외)
        if data.get('id_number') and data['id_number'] != user.id_number:
            from app.common.models import UserCompany
            existing_id_number = db.session.query(User).join(
                UserCompany, User.seq == UserCompany.user_seq
            ).filter(
                UserCompany.company_id == current_company_id,
                User.id_number == data['id_number'],
                User.seq != user_seq
            ).first()
            if existing_id_number:
                return jsonify({'success': False, 'message': '해당 회사에 이미 존재하는 사번입니다.'}), 400
        
        # 사용자 정보 업데이트
        if data.get('login_id'):
            user.login_id = data['login_id']
        if data.get('name'):
            user.name = data['name']
        if data.get('password'):
            from werkzeug.security import generate_password_hash
            user.password = generate_password_hash(data['password'])
        
        # 기타 필드 업데이트
        simple_fields = ['id_number', 'email', 'mobile', 'extension_number', 'super_user', 'member_status']
        for field in simple_fields:
            if field in data:
                setattr(user, field, data[field])
        
        user.upt_user = session.get('member_id', 'admin')
        user.upt_date = datetime.utcnow()
        
        # 회사 소속 업데이트 (슈퍼유저만 가능)
        current_user_super = session.get('super_user') == 'Y'
        if current_user_super and 'companies' in data:
            # 기존 회사 관계 삭제
            from app.common.models import UserCompany
            UserCompany.query.filter_by(user_seq=user_seq).delete()
            
            # 새 회사 관계 추가
            for company_setting in data['companies']:
                user_company = UserCompany(
                    user_seq=user_seq,
                    company_id=company_setting['company_id'],
                    is_primary=company_setting.get('is_primary', False),
                    role=company_setting.get('role', 'user'),
                    is_active=True
                )
                db.session.add(user_company)
        
        # 부서 연결 업데이트
        if 'department_ids' in data:
            # 기존 부서 연결 삭제
            from app.common.models import UserDepartment
            UserDepartment.query.filter_by(user_seq=user_seq).delete()
            
            # 새 부서 연결 추가
            for dept_id in data['department_ids']:
                user_dept = UserDepartment(
                    user_seq=user_seq,
                    dept_seq=dept_id
                )
                db.session.add(user_dept)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '사용자 정보가 성공적으로 수정되었습니다.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/api/users/<int:user_seq>', methods=['DELETE'])
def delete_user(user_seq):
    """사용자 삭제 (소프트 삭제)"""
    try:
        user = User.query.filter_by(seq=user_seq).first()
        
        if not user:
            return jsonify({'success': False, 'message': '사용자를 찾을 수 없습니다.'}), 404
        
        # 접근 권한 확인
        current_company_id = session.get('current_company_id', 1)
        current_user_super = session.get('super_user') == 'Y'
        if not user.has_company_access(current_company_id) and not current_user_super:
            return jsonify({'success': False, 'message': '해당 사용자에 대한 접근 권한이 없습니다.'}), 403
        
        # 소프트 삭제 (상태 변경)
        user.member_status = 'D'  # Deleted
        user.upt_user = session.get('member_id', 'admin')
        user.upt_date = datetime.utcnow()
        
        # 회사 소속도 비활성화
        from app.common.models import UserCompany
        UserCompany.query.filter_by(user_seq=user_seq).update({'is_active': False})
        
        # 관련 권한 정보도 정리
        MemberAuth.query.filter_by(member_seq=user_seq).delete()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '사용자가 성공적으로 삭제되었습니다.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/api/users/<int:user_seq>/password', methods=['POST'])
def change_user_password(user_seq):
    """사용자 비밀번호 변경"""
    try:
        data = request.get_json()
        
        if not data.get('new_password'):
            return jsonify({'success': False, 'message': '새 비밀번호를 입력해주세요.'}), 400
        
        user = User.query.filter_by(seq=user_seq).first()
        if not user:
            return jsonify({'success': False, 'message': '사용자를 찾을 수 없습니다.'}), 404
        
        # 접근 권한 확인
        current_company_id = session.get('current_company_id', 1)
        current_user_super = session.get('super_user') == 'Y'
        if not user.has_company_access(current_company_id) and not current_user_super:
            return jsonify({'success': False, 'message': '해당 사용자에 대한 접근 권한이 없습니다.'}), 403
        
        # 비밀번호 업데이트
        from werkzeug.security import generate_password_hash
        user.password = generate_password_hash(data['new_password'])
        user.upt_user = session.get('member_id', 'admin')
        user.upt_date = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '비밀번호가 성공적으로 변경되었습니다.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== 권한 관리 API ====================

@admin_bp.route('/api/permissions', methods=['GET'])
def get_permissions():
    """권한 매트릭스 조회"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    """권한 매트릭스 조회"""
    try:
        company_id = session.get('current_company_id', 1)
        
        # 모든 메뉴 조회 (계층 구조)
        menus = Menu.query.order_by(Menu.depth.asc(), Menu.sort.asc()).all()
        
        # 사용자 목록 조회
        users = User.query.filter_by(member_status='Y').order_by(User.name.asc()).all()
        
        # 부서 목록 조회
        departments = Department.query.filter_by(use_yn='Y').order_by(Department.sort.asc()).all()
        
        return jsonify({
            'success': True,
            'data': {
                'menus': [menu.to_dict() for menu in menus],
                'users': [{'seq': u.seq, 'name': u.name, 'login_id': u.login_id} for u in users],
                'departments': [{'seq': d.seq, 'name': d.dept_name} for d in departments]
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/api/permissions/user/<int:user_seq>', methods=['GET'])
def get_user_permissions(user_seq):
    """사용자별 권한 조회"""
    try:
        company_id = session.get('current_company_id', 1)
        
        # 사용자 확인
        user = User.query.filter_by(seq=user_seq, company_id=company_id).first()
        if not user:
            return jsonify({'success': False, 'message': '사용자를 찾을 수 없습니다.'}), 404
        
        # 사용자 권한 조회
        user_auths = MemberAuth.query.filter_by(member_seq=user_seq).all()
        
        # 메뉴별 권한 정리
        permissions = {}
        for auth in user_auths:
            permissions[auth.menu_seq] = {
                'auth_create': auth.auth_create,
                'auth_read': auth.auth_read,
                'auth_update': auth.auth_update,
                'auth_delete': auth.auth_delete
            }
        
        return jsonify({
            'success': True,
            'data': {
                'user_seq': user_seq,
                'user_name': user.name,
                'permissions': permissions
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/api/permissions/user/<int:user_seq>', methods=['POST'])
def set_user_permissions(user_seq):
    """사용자별 권한 설정"""
    try:
        data = request.get_json()
        company_id = session.get('current_company_id', 1)
        
        # 사용자 확인
        user = User.query.filter_by(seq=user_seq, company_id=company_id).first()
        if not user:
            return jsonify({'success': False, 'message': '사용자를 찾을 수 없습니다.'}), 404
        
        # 슈퍼유저는 권한 설정 제외
        if user.super_user == 'Y':
            return jsonify({'success': False, 'message': '슈퍼유저는 권한을 설정할 수 없습니다.'}), 400
        
        # 기존 권한 삭제
        MemberAuth.query.filter_by(member_seq=user_seq).delete()
        
        # 새 권한 추가
        permissions = data.get('permissions', [])
        for perm in permissions:
            new_auth = MemberAuth(
                member_seq=user_seq,
                menu_seq=perm['menu_seq'],
                auth_create=perm.get('auth_create', 'N'),
                auth_read=perm.get('auth_read', 'N'),
                auth_update=perm.get('auth_update', 'N'),
                auth_delete=perm.get('auth_delete', 'N'),
                ins_user=session.get('member_id', 'admin'),
                ins_date=datetime.utcnow(),
                upt_user=session.get('member_id', 'admin'),
                upt_date=datetime.utcnow()
            )
            db.session.add(new_auth)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '사용자 권한이 성공적으로 설정되었습니다.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/api/permissions/department/<int:dept_seq>', methods=['GET'])
def get_department_permissions(dept_seq):
    """부서별 권한 조회"""
    try:
        # 부서 확인
        department = Department.query.filter_by(seq=dept_seq).first()
        if not department:
            return jsonify({'success': False, 'message': '부서를 찾을 수 없습니다.'}), 404
        
        # 부서 권한 조회
        dept_auths = DeptAuth.query.filter_by(dept_seq=dept_seq).all()
        
        # 메뉴별 권한 정리
        permissions = {}
        for auth in dept_auths:
            permissions[auth.menu_seq] = {
                'auth_create': auth.auth_create,
                'auth_read': auth.auth_read,
                'auth_update': auth.auth_update,
                'auth_delete': auth.auth_delete
            }
        
        return jsonify({
            'success': True,
            'data': {
                'dept_seq': dept_seq,
                'dept_name': department.dept_name,
                'permissions': permissions
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/api/permissions/department/<int:dept_seq>', methods=['POST'])
def set_department_permissions(dept_seq):
    """부서별 권한 설정"""
    try:
        data = request.get_json()
        
        # 부서 확인
        department = Department.query.filter_by(seq=dept_seq).first()
        if not department:
            return jsonify({'success': False, 'message': '부서를 찾을 수 없습니다.'}), 404
        
        # 기존 부서 권한 삭제
        DeptAuth.query.filter_by(dept_seq=dept_seq).delete()
        
        # 새 부서 권한 추가
        permissions = data.get('permissions', [])
        for perm in permissions:
            new_auth = DeptAuth(
                dept_seq=dept_seq,
                menu_seq=perm['menu_seq'],
                auth_create=perm.get('auth_create', 'N'),
                auth_read=perm.get('auth_read', 'N'),
                auth_update=perm.get('auth_update', 'N'),
                auth_delete=perm.get('auth_delete', 'N'),
                ins_user=session.get('member_id', 'admin'),
                ins_date=datetime.utcnow(),
                upt_user=session.get('member_id', 'admin'),
                upt_date=datetime.utcnow()
            )
            db.session.add(new_auth)
        
        # 해당 부서 소속 사용자들의 권한도 업데이트 (레거시 호환)
        from app.common.models import UserDepartment
        user_dept_list = UserDepartment.query.filter_by(dept_seq=dept_seq).all()
        
        for user_dept in user_dept_list:
            # 슈퍼유저는 제외
            user = User.query.filter_by(seq=user_dept.user_seq).first()
            if user and user.super_user != 'Y':
                # 기존 사용자 권한 삭제
                MemberAuth.query.filter_by(member_seq=user_dept.user_seq).delete()
                
                # 부서 권한을 사용자 권한으로 복사
                for perm in permissions:
                    new_user_auth = MemberAuth(
                        member_seq=user_dept.user_seq,
                        menu_seq=perm['menu_seq'],
                        auth_create=perm.get('auth_create', 'N'),
                        auth_read=perm.get('auth_read', 'N'),
                        auth_update=perm.get('auth_update', 'N'),
                        auth_delete=perm.get('auth_delete', 'N'),
                        ins_user=session.get('member_id', 'admin'),
                        ins_date=datetime.utcnow(),
                        upt_user=session.get('member_id', 'admin'),
                        upt_date=datetime.utcnow()
                    )
                    db.session.add(new_user_auth)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '부서 권한이 성공적으로 설정되었습니다.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/api/permissions/matrix', methods=['GET'])
def get_permissions_matrix():
    """권한 매트릭스 전체 조회 (UI용)"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    """권한 매트릭스 전체 조회 (UI용)"""
    try:
        company_id = session.get('current_company_id', 1)
        view_type = request.args.get('type', 'user')  # user 또는 department
        
        if view_type == 'user':
            # 사용자별 권한 매트릭스
            users = User.query.filter_by(member_status='Y').order_by(User.name.asc()).all()
            menus = Menu.query.order_by(Menu.depth.asc(), Menu.sort.asc()).all()
            
            matrix = []
            for user in users:
                user_auths = MemberAuth.query.filter_by(member_seq=user.seq).all()
                auth_dict = {auth.menu_seq: auth for auth in user_auths}
                
                user_permissions = []
                for menu in menus:
                    auth = auth_dict.get(menu.seq)
                    if auth:
                        user_permissions.append({
                            'menu_seq': menu.seq,
                            'menu_name': menu.name,
                            'auth_create': auth.auth_create,
                            'auth_read': auth.auth_read,
                            'auth_update': auth.auth_update,
                            'auth_delete': auth.auth_delete
                        })
                    else:
                        user_permissions.append({
                            'menu_seq': menu.seq,
                            'menu_name': menu.name,
                            'auth_create': 'N',
                            'auth_read': 'N',
                            'auth_update': 'N',
                            'auth_delete': 'N'
                        })
                
                matrix.append({
                    'user_seq': user.seq,
                    'user_name': user.name,
                    'super_user': user.super_user,
                    'permissions': user_permissions
                })
            
            return jsonify({
                'success': True,
                'data': {
                    'type': 'user',
                    'menus': [menu.to_dict() for menu in menus],
                    'matrix': matrix
                }
            })
            
        else:  # department
            # 부서별 권한 매트릭스
            departments = Department.query.filter_by(use_yn='Y').order_by(Department.sort.asc()).all()
            menus = Menu.query.order_by(Menu.depth.asc(), Menu.sort.asc()).all()
            
            matrix = []
            for dept in departments:
                dept_auths = DeptAuth.query.filter_by(dept_seq=dept.seq).all()
                auth_dict = {auth.menu_seq: auth for auth in dept_auths}
                
                dept_permissions = []
                for menu in menus:
                    auth = auth_dict.get(menu.seq)
                    if auth:
                        dept_permissions.append({
                            'menu_seq': menu.seq,
                            'menu_name': menu.name,
                            'auth_create': auth.auth_create,
                            'auth_read': auth.auth_read,
                            'auth_update': auth.auth_update,
                            'auth_delete': auth.auth_delete
                        })
                    else:
                        dept_permissions.append({
                            'menu_seq': menu.seq,
                            'menu_name': menu.name,
                            'auth_create': 'N',
                            'auth_read': 'N',
                            'auth_update': 'N',
                            'auth_delete': 'N'
                        })
                
                matrix.append({
                    'dept_seq': dept.seq,
                    'dept_name': dept.dept_name,
                    'permissions': dept_permissions
                })
            
            return jsonify({
                'success': True,
                'data': {
                    'type': 'department',
                    'menus': [menu.to_dict() for menu in menus],
                    'matrix': matrix
                }
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== 헬퍼 API ====================

@admin_bp.route('/api/companies', methods=['GET'])
def get_companies():
    """회사 목록 조회 (멀티테넌트)"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    """회사 목록 조회 (멀티테넌트)"""
    try:
        # 슈퍼유저는 모든 회사, 일반 사용자는 접근 가능한 회사만
        current_user_super = session.get('super_user') == 'Y'
        if current_user_super:
            from app.common.models import Company
            companies = Company.query.filter_by(is_active=True).order_by(Company.company_name.asc()).all()
        else:
            # 일반 사용자는 접근 가능한 회사만
            from app.common.models import UserCompany, Company
            user_seq = session.get('member_seq')
            companies = db.session.query(Company).join(
                UserCompany, Company.id == UserCompany.company_id
            ).filter(
                UserCompany.user_seq == user_seq,
                UserCompany.is_active == True,
                Company.is_active == True
            ).order_by(Company.company_name.asc()).all()
        
        result = []
        for company in companies:
            result.append({
                'id': company.id,
                'company_code': company.company_code,
                'company_name': company.company_name,
                'is_active': company.is_active
            })
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== 부서 관리 REST API ====================

@admin_bp.route('/api/departments', methods=['GET'])
def get_all_departments():
    """부서 관리 - 전체 부서 목록 조회 (관리자용)"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    try:
        # 회사별 부서 조회
        company_id = session.get('current_company_id', 1)
        departments = Department.query.filter_by(company_id=company_id).order_by(Department.sort.asc()).all()
        
        result = []
        for dept in departments:
            # 회사명 매핑
            company_usage = "에이원"
            if dept.company_id == 1:
                company_usage = "에이원"
            elif dept.company_id == 2:
                company_usage = "에이원 월드"
            else:
                company_usage = "모두"
            
            result.append({
                'seq': dept.seq,
                'dept_name': dept.dept_name,
                'sort': dept.sort,
                'use_yn': dept.use_yn,
                'company_id': dept.company_id,
                'company_usage': company_usage,
                'ins_date': dept.ins_date.strftime('%Y-%m-%d %H:%M') if dept.ins_date else '',
                'upt_date': dept.upt_date.strftime('%Y-%m-%d %H:%M') if dept.upt_date else ''
            })
        
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/api/departments', methods=['POST'])
def create_department_rest():
    """부서 생성 (REST API)"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    try:
        # JSON 데이터 처리
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        if not data.get('dept_name'):
            return jsonify({'success': False, 'message': '부서명은 필수입니다.'})
        
        new_dept = Department(
            dept_name=data.get('dept_name'),
            sort=int(data.get('sort', 1)),
            use_yn=data.get('use_yn', 'Y'),
            company_id=int(data.get('company_id', session.get('current_company_id', 1))),
            ins_user=session.get('member_id', 'admin'),
            ins_date=db.func.now()
        )
        
        db.session.add(new_dept)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '부서가 생성되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/api/departments/<int:dept_id>', methods=['GET'])
def get_department_rest(dept_id):
    """부서 상세 조회 (REST API)"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    try:
        dept = Department.query.filter_by(seq=dept_id).first()
        if not dept:
            return jsonify({'success': False, 'message': '부서를 찾을 수 없습니다.'}), 404
        
        return jsonify({
            'success': True,
            'data': {
                'seq': dept.seq,
                'dept_name': dept.dept_name,
                'sort': dept.sort,
                'use_yn': dept.use_yn,
                'company_id': dept.company_id
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/api/departments/<int:dept_id>', methods=['PUT'])
def update_department_rest(dept_id):
    """부서 수정 (REST API)"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    try:
        # JSON 데이터 처리
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        dept = Department.query.filter_by(seq=dept_id).first()
        if not dept:
            return jsonify({'success': False, 'message': '부서를 찾을 수 없습니다.'}), 404
        
        dept.dept_name = data.get('dept_name', dept.dept_name)
        dept.sort = int(data.get('sort', dept.sort))
        dept.use_yn = data.get('use_yn', dept.use_yn)
        dept.company_id = int(data.get('company_id', dept.company_id))
        dept.upt_user = session.get('member_id', 'admin')
        dept.upt_date = db.func.now()
        
        db.session.commit()
        return jsonify({'success': True, 'message': '부서가 수정되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/api/departments/<int:dept_id>', methods=['DELETE'])
def delete_department_rest(dept_id):
    """부서 삭제 (REST API)"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    try:
        dept = Department.query.filter_by(seq=dept_id).first()
        if not dept:
            return jsonify({'success': False, 'message': '부서를 찾을 수 없습니다.'}), 404
        
        # 부서 사용 중지로 변경 (실제 삭제하지 않음)
        dept.use_yn = 'N'
        dept.upt_user = session.get('member_id', 'admin')
        dept.upt_date = db.func.now()
        
        db.session.commit()
        return jsonify({'success': True, 'message': '부서가 삭제되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/api/departments/dropdown', methods=['GET'])
def get_departments_for_dropdown():
    """사용자 관리용 부서 목록 조회 (드롭다운용) - 사용자 회사별 필터링"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    try:
        # 현재 사용자의 회사 ID 가져오기
        current_company_id = session.get('current_company_id', 1)
        
        # 해당 회사의 부서만 조회 (사용 중인 부서만)
        departments = Department.query.filter_by(
            company_id=current_company_id,
            use_yn='Y'
        ).order_by(Department.sort.asc()).all()
        
        result = []
        for dept in departments:
            result.append({
                'seq': dept.seq,
                'dept_name': dept.dept_name,
                'sort': dept.sort,
                'company_id': dept.company_id
            })
        
        return jsonify({
            'success': True,
            'data': result,
            'current_company_id': current_company_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/api/codes/positions', methods=['GET'])
def get_positions():
    """직책/직급 코드 조회"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    """직책/직급 코드 조회"""
    try:
        # 직책 (JPT)
        job_positions = Code.query.filter_by(parent_seq=1).order_by(Code.sort.asc()).all()
        
        # 직급 (RPT)  
        rank_positions = Code.query.filter_by(parent_seq=2).order_by(Code.sort.asc()).all()
        
        return jsonify({
            'success': True,
            'data': {
                'job_positions': [{'seq': c.seq, 'code_name': c.code_name} for c in job_positions],
                'rank_positions': [{'seq': c.seq, 'code_name': c.code_name} for c in rank_positions]
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
