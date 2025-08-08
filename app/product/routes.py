"""
상품관리 라우트
"""
import os
from datetime import datetime
from flask import render_template, request, jsonify, session, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import and_, or_

from app.product import bp
from app.common.models import db, Product, ProductHistory, Code, Company, Brand

# 파일 업로드 설정
ALLOWED_EXTENSIONS = {'pdf'}
UPLOAD_FOLDER = 'static/uploads/manuals'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def require_login():
    """로그인 체크 함수"""
    if not session.get('member_seq'):
        return redirect(url_for('auth.login'))
    return None

@bp.route('/')
@login_required
def index():
    """상품 목록 페이지"""
    # 로그인 체크
    login_check = require_login()
    if login_check:
        return login_check
        
    try:
        current_company_id = session.get('current_company_id', 1)
        
        # 검색 파라미터
        search_term = request.args.get('search', '')
        brand_seq = request.args.get('brand_seq', type=int)
        category_code_seq = request.args.get('category_code_seq', type=int)
        type_code_seq = request.args.get('type_code_seq', type=int)
        show_inactive = request.args.get('show_inactive', 'false') == 'true'
        
        # 상품 목록 조회
        products = Product.search_products(
            company_id=current_company_id,
            search_term=search_term,
            brand_seq=brand_seq,
            category_code_seq=category_code_seq,
            type_code_seq=type_code_seq,
            active_only=not show_inactive
        )
        
        # 코드 정보 조회 (드롭다운용)
        brand_codes = Brand.get_brands_by_company(current_company_id)
        category_codes = Code.get_codes_by_group_name('품목', company_id=current_company_id)
        type_codes = Code.get_codes_by_group_name('타입', company_id=current_company_id)
        year_codes = Code.get_codes_by_group_name('년도', company_id=current_company_id)
        
        # 년도 코드가 없으면 기본 년도 생성
        if not year_codes:
            current_year = datetime.now().year
            year_codes = [
                {'seq': None, 'code': str(current_year), 'code_name': f'{current_year}년'},
                {'seq': None, 'code': str(current_year-1), 'code_name': f'{current_year-1}년'},
                {'seq': None, 'code': str(current_year+1), 'code_name': f'{current_year+1}년'}
            ]
        
        return render_template('product/index.html',
                             products=products,
                             brand_codes=brand_codes,
                             category_codes=category_codes,
                             type_codes=type_codes,
                             year_codes=year_codes,
                             search_term=search_term,
                             current_brand=brand_seq,
                             current_category=category_code_seq,
                             current_type=type_code_seq,
                             show_inactive=show_inactive)
        
    except Exception as e:
        current_app.logger.error(f"❌ 상품 목록 조회 실패: {e}")
        flash('상품 목록을 불러오는 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('index'))

@bp.route('/api/list')
@login_required
def api_list():
    """상품 목록 API"""
    # 로그인 체크
    if not session.get('member_seq'):
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        
    try:
        current_company_id = session.get('current_company_id', 1)
        
        # 페이징 파라미터
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # 검색 파라미터
        search_term = request.args.get('search', '')
        brand_seq = request.args.get('brand_seq', type=int)
        category_code_seq = request.args.get('category_code_seq', type=int)
        type_code_seq = request.args.get('type_code_seq', type=int)
        show_inactive = request.args.get('show_inactive', 'false') == 'true'
        
        # 쿼리 빌드
        query = Product.query.filter_by(company_id=current_company_id)
        
        if not show_inactive:
            query = query.filter_by(is_active=True)
        
        if search_term:
            search_pattern = f'%{search_term}%'
            query = query.filter(
                or_(
                    Product.product_name.ilike(search_pattern),
                    Product.product_code.ilike(search_pattern),
                    Product.description.ilike(search_pattern)
                )
            )
        
        if brand_seq:
            query = query.filter_by(brand_seq=brand_seq)
            
        if category_code_seq:
            query = query.filter_by(category_code_seq=category_code_seq)
            
        if type_code_seq:
            query = query.filter_by(type_code_seq=type_code_seq)
        
        # 페이징
        pagination = query.order_by(Product.product_name).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        products = [product.to_dict() for product in pagination.items]
        
        return jsonify({
            'success': True,
            'products': products,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ 상품 목록 API 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    """상품 등록 API"""
    # 로그인 체크
    if not session.get('member_seq'):
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        
    try:
        current_company_id = session.get('current_company_id', 1)
        
        # 폼 데이터 받기
        data = request.form.to_dict()
        
        # 필수 필드 검증
        required_fields = ['product_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field}는 필수 항목입니다.'}), 400
        
        # 중복 검사 (상품명 + 회사)
        existing_product = Product.query.filter_by(
            company_id=current_company_id,
            product_name=data['product_name']
        ).first()
        
        if existing_product:
            return jsonify({'success': False, 'message': '동일한 상품명이 이미 존재합니다.'}), 400
        
        # 파일 업로드 처리
        manual_file_path = None
        if 'manual_file' in request.files:
            file = request.files['manual_file']
            if file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # 타임스탬프 추가로 중복 방지
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                
                # 업로드 폴더 생성
                upload_dir = os.path.join(current_app.root_path, UPLOAD_FOLDER)
                os.makedirs(upload_dir, exist_ok=True)
                
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                manual_file_path = f"{UPLOAD_FOLDER}/{filename}"
        
        # 새 상품 생성
        product = Product(
            company_id=current_company_id,
            brand_seq=data.get('brand_seq') or None,
            category_code_seq=data.get('category_code_seq') or None,
            type_code_seq=data.get('type_code_seq') or None,
            product_name=data['product_name'],
            product_code=data.get('product_code', ''),
            product_year=data.get('product_year', ''),
            price=int(data.get('price', 0)) if data.get('price') else 0,
            description=data.get('description', ''),
            manual_file_path=manual_file_path,
            is_active=data.get('is_active', 'true') == 'true',
            created_by=session.get('member_id', 'admin'),
            updated_by=session.get('member_id', 'admin')
        )
        
        db.session.add(product)
        db.session.commit()
        
        # 히스토리 기록
        history = ProductHistory(
            product_id=product.id,
            action='CREATE',
            new_values=product.to_dict(),
            created_by=session.get('member_id', 'admin')
        )
        db.session.add(history)
        db.session.commit()
        
        current_app.logger.info(f"✅ 상품 등록 성공: {product.product_name} (ID: {product.id})")
        
        return jsonify({
            'success': True,
            'message': '상품이 성공적으로 등록되었습니다.',
            'product': product.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ 상품 등록 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/api/update/<int:product_id>', methods=['PUT'])
@login_required
def api_update(product_id):
    """상품 수정 API"""
    # 로그인 체크
    if not session.get('member_seq'):
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        
    try:
        current_company_id = session.get('current_company_id', 1)
        
        # 상품 조회
        product = Product.query.filter_by(
            id=product_id,
            company_id=current_company_id
        ).first()
        
        if not product:
            return jsonify({'success': False, 'message': '상품을 찾을 수 없습니다.'}), 404
        
        # 이전 값 저장
        old_values = product.to_dict()
        
        # 폼 데이터 받기
        data = request.form.to_dict()
        
        # 필수 필드 검증
        if not data.get('product_name'):
            return jsonify({'success': False, 'message': '상품명은 필수 항목입니다.'}), 400
        
        # 중복 검사 (상품명 + 회사, 자기 제외)
        existing_product = Product.query.filter(
            and_(
                Product.company_id == current_company_id,
                Product.product_name == data['product_name'],
                Product.id != product_id
            )
        ).first()
        
        if existing_product:
            return jsonify({'success': False, 'message': '동일한 상품명이 이미 존재합니다.'}), 400
        
        # 파일 업로드 처리
        if 'manual_file' in request.files:
            file = request.files['manual_file']
            if file.filename and allowed_file(file.filename):
                # 기존 파일 삭제
                if product.manual_file_path:
                    old_file_path = os.path.join(current_app.root_path, product.manual_file_path)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                
                # 새 파일 저장
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                
                upload_dir = os.path.join(current_app.root_path, UPLOAD_FOLDER)
                os.makedirs(upload_dir, exist_ok=True)
                
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                product.manual_file_path = f"{UPLOAD_FOLDER}/{filename}"
        
        # 상품 정보 업데이트
        product.brand_seq = data.get('brand_seq') or None
        product.category_code_seq = data.get('category_code_seq') or None
        product.type_code_seq = data.get('type_code_seq') or None
        product.product_name = data['product_name']
        product.product_code = data.get('product_code', '')
        product.product_year = data.get('product_year', '')
        product.price = int(data.get('price', 0)) if data.get('price') else 0
        product.description = data.get('description', '')
        product.is_active = data.get('is_active', 'true') == 'true'
        product.updated_by = session.get('member_id', 'admin')
        product.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # 히스토리 기록
        new_values = product.to_dict()
        changed_fields = []
        for key in new_values:
            if old_values.get(key) != new_values.get(key):
                changed_fields.append(key)
        
        if changed_fields:
            history = ProductHistory(
                product_id=product.id,
                action='UPDATE',
                changed_fields=changed_fields,
                old_values={k: old_values.get(k) for k in changed_fields},
                new_values={k: new_values.get(k) for k in changed_fields},
                created_by=session.get('member_id', 'admin')
            )
            db.session.add(history)
            db.session.commit()
        
        current_app.logger.info(f"✅ 상품 수정 성공: {product.product_name} (ID: {product.id})")
        
        return jsonify({
            'success': True,
            'message': '상품이 성공적으로 수정되었습니다.',
            'product': product.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ 상품 수정 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/api/delete/<int:product_id>', methods=['DELETE'])
@login_required
def api_delete(product_id):
    """상품 삭제 API"""
    # 로그인 체크
    if not session.get('member_seq'):
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        
    try:
        current_company_id = session.get('current_company_id', 1)
        
        # 상품 조회
        product = Product.query.filter_by(
            id=product_id,
            company_id=current_company_id
        ).first()
        
        if not product:
            return jsonify({'success': False, 'message': '상품을 찾을 수 없습니다.'}), 404
        
        # 히스토리 기록
        old_values = product.to_dict()
        history = ProductHistory(
            product_id=product.id,
            action='DELETE',
            old_values=old_values,
            created_by=session.get('member_id', 'admin')
        )
        db.session.add(history)
        
        # 파일 삭제
        if product.manual_file_path:
            file_path = os.path.join(current_app.root_path, product.manual_file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # 상품 삭제
        product_name = product.product_name
        db.session.delete(product)
        db.session.commit()
        
        current_app.logger.info(f"✅ 상품 삭제 성공: {product_name} (ID: {product_id})")
        
        return jsonify({
            'success': True,
            'message': '상품이 성공적으로 삭제되었습니다.'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ 상품 삭제 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/api/get/<int:product_id>')
@login_required
def api_get(product_id):
    """상품 상세 조회 API"""
    # 로그인 체크
    if not session.get('member_seq'):
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        
    try:
        current_company_id = session.get('current_company_id', 1)
        
        product = Product.query.filter_by(
            id=product_id,
            company_id=current_company_id
        ).first()
        
        if not product:
            return jsonify({'success': False, 'message': '상품을 찾을 수 없습니다.'}), 404
        
        return jsonify({
            'success': True,
            'product': product.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ 상품 조회 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/api/codes/<code_type>')
@login_required
def api_get_codes(code_type):
    """코드 목록 조회 API (계층형 선택용)"""
    # 로그인 체크
    if not session.get('member_seq'):
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        
    try:
        current_company_id = session.get('current_company_id', 1)
        parent_seq = request.args.get('parent_seq', type=int)
        
        # 코드 타입별 조회
        if code_type == 'brands':
            codes = Brand.get_brands_by_company(current_company_id)
        elif code_type == 'categories':
            codes = Code.get_codes_by_group_name('품목', company_id=current_company_id)
        elif code_type == 'types':
            codes = Code.get_codes_by_group_name('타입', company_id=current_company_id)
        elif code_type == 'years':
            codes = Code.get_codes_by_group_name('년도', company_id=current_company_id)
            if not codes:
                # 기본 년도 생성
                current_year = datetime.now().year
                codes = [
                    {'seq': None, 'code': str(current_year), 'code_name': f'{current_year}년'},
                    {'seq': None, 'code': str(current_year-1), 'code_name': f'{current_year-1}년'},
                    {'seq': None, 'code': str(current_year+1), 'code_name': f'{current_year+1}년'}
                ]
        elif parent_seq:
            # 상위 코드 기준 하위 코드 조회
            codes = Code.get_child_codes(parent_seq)
        else:
            codes = []
        
        return jsonify({
            'success': True,
            'codes': codes
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ 코드 조회 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500 