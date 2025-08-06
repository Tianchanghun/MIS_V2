"""
인증 관련 라우트
실제 tbl_member 테이블 기반 로그인
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app.common.models import User, db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """로그인 처리"""
    if request.method == 'POST':
        try:
            user_id = request.form.get('user_id')
            password = request.form.get('password')
            
            if not user_id or not password:
                flash('아이디와 비밀번호를 입력해주세요.', 'error')
                return render_template('auth/login.html')
            
            # 실제 tbl_member 테이블에서 사용자 검색
            user = User.query.filter_by(id=user_id, member_status='A').first()
            
            if user and user.verify_password(password):
                # 로그인 성공
                login_user(user, remember=True)
                
                # 세션 설정 (레거시 호환)
                session['member_seq'] = user.seq
                session['member_id'] = user.id
                session['member_name'] = user.name
                session['dept_seq'] = user.work_group if user.work_group else 1
                session['super_user'] = 'Y' if user.is_super_user else 'N'
                session['company_id'] = user.company_id if user.company_id else 1
                
                flash(f'{user.name}님, 환영합니다!', 'success')
                
                # next 파라미터 확인
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('index'))
            else:
                flash('아이디 또는 비밀번호가 올바르지 않습니다.', 'error')
                
        except Exception as e:
            flash(f'로그인 처리 중 오류가 발생했습니다: {e}', 'error')
            print(f"로그인 오류: {e}")
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """로그아웃 처리"""
    logout_user()
    
    # 세션 정리
    session.clear()
    
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('auth.login'))

# Flask-Login 사용자 로더
from flask_login import LoginManager

def init_login_manager(app):
    """LoginManager 초기화"""
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '로그인이 필요합니다.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        """사용자 로더 함수"""
        try:
            return User.query.filter_by(seq=int(user_id)).first()
        except (ValueError, TypeError):
            return None
    
    return login_manager

def load_user_permissions(user):
    """사용자 권한 로드 (추후 구현)"""
    # 추후 tbl_menu_auth 등에서 권한 로드
    return {}

def has_permission(user, menu_code, action='read'):
    """권한 확인 (추후 구현)"""
    if user.is_super_user:
        return True
    
    # 추후 세부 권한 체크 로직 구현
    return True 