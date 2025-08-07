from flask import Blueprint, render_template, request, redirect, session, flash
from werkzeug.security import check_password_hash
from app.common.models import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'member_seq' in session:
        return redirect('/')
    
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
        password = request.form.get('password', '').strip()
        
        if user_id and password:
            # member_status가 'Y' 또는 'A'인 사용자 모두 허용
            user = User.query.filter_by(login_id=user_id).filter(
                User.member_status.in_(['Y', 'A'])
            ).first()
            
            if user and check_password_hash(user.password, password):
                session['member_seq'] = user.seq
                session['member_id'] = user.login_id
                session['member_name'] = user.name
                session['company_id'] = user.company_id or 1
                session['current_company_id'] = user.company_id or 1
                flash('로그인 성공', 'success')
                return redirect('/')
        
        flash('아이디 또는 비밀번호가 올바르지 않습니다.', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('로그아웃되었습니다.', 'info')
    return redirect('/auth/login')
