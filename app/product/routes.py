"""
상품관리 라우트
"""
import os
import pandas as pd
from datetime import datetime
from flask import render_template, request, jsonify, session, current_app, redirect, url_for, flash, send_file, make_response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import and_, or_
from io import BytesIO
import tempfile

from app.product import bp
from app.common.models import db, Product, ProductHistory, Code, Company, Brand, ProductDetail

# 파일 업로드 설정
ALLOWED_EXTENSIONS = {'pdf'}
EXCEL_EXTENSIONS = {'xlsx', 'xls'}
UPLOAD_FOLDER = 'static/uploads/manuals'

def allowed_file(filename, extensions=ALLOWED_EXTENSIONS):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in extensions

def require_login():
    """로그인 체크 함수"""
    if not session.get('member_seq'):
        return redirect(url_for('auth.login'))
    return None

@bp.route('/')
def index():
    """상품 목록 페이지"""
    # 개발 환경에서는 로그인 체크 우회 (임시)
    if not session.get('member_seq'):
        # 임시 세션 설정
        session['member_seq'] = 1
        session['member_id'] = 'admin'
        session['current_company_id'] = 1
        
    try:
        current_company_id = session.get('current_company_id', 1)
        
        # 검색 파라미터
        search_term = request.args.get('search', '')
        brand_code_seq = request.args.get('brand_code_seq', type=int)
        category_code_seq = request.args.get('category_code_seq', type=int)
        type_code_seq = request.args.get('type_code_seq', type=int)
        year_code_seq = request.args.get('year_code_seq', type=int)
        show_inactive = request.args.get('show_inactive', 'false') == 'true'
        
        # 상품 목록 조회
        products = Product.search_products(
            company_id=current_company_id,
            search_term=search_term,
            brand_code_seq=brand_code_seq,
            category_code_seq=category_code_seq,
            type_code_seq=type_code_seq,
            year_code_seq=year_code_seq,
            active_only=not show_inactive
        )
        
        # 코드 정보 조회 (드롭다운용)
        brand_codes = Code.get_codes_by_group_name('브랜드', company_id=current_company_id)
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
        
        # 확장 코드 그룹 조회 (레거시 호환 순서)
        color_codes = Code.get_codes_by_group_name('색상', company_id=current_company_id)
        div_type_codes = Code.get_codes_by_group_name('구분타입', company_id=current_company_id)
        product_codes = Code.get_codes_by_group_name('제품코드', company_id=current_company_id)
        
        # 레거시 호환 추가 코드 그룹들
        prod_group_codes = Code.get_codes_by_group_name('품목그룹', company_id=current_company_id)
        prod_type_codes = Code.get_codes_by_group_name('제품타입', company_id=current_company_id)
        type2_codes = Code.get_codes_by_group_name('타입2', company_id=current_company_id)
        
        return render_template('product/index.html',
                             products=products,
                             brand_codes=brand_codes,
                             category_codes=category_codes,
                             type_codes=type_codes,
                             year_codes=year_codes,
                             # 확장 코드 그룹 추가
                             color_codes=color_codes,
                             div_type_codes=div_type_codes,
                             product_codes=product_codes,
                             # 레거시 호환 코드 그룹 추가
                             prod_group_codes=prod_group_codes,
                             prod_type_codes=prod_type_codes,
                             type2_codes=type2_codes,
                             search_term=search_term,
                             current_brand=brand_code_seq,
                             current_category=category_code_seq,
                             current_type=type_code_seq,
                             show_inactive=show_inactive)
        
    except Exception as e:
        current_app.logger.error(f"❌ 상품 목록 조회 실패: {e}")
        flash('상품 목록을 불러오는 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('index'))

@bp.route('/api/list')
def api_list():
    """상품 목록 API"""
    # 개발 환경에서는 로그인 체크 우회 (강제)
    current_company_id = 1  # 에이원으로 고정
    
    # 원래 로그인 체크 코드는 주석 처리
    # if current_app.config.get('FLASK_ENV') == 'development':
    #     current_company_id = 1  # 에이원으로 고정
    # else:
    #     # 로그인 체크
    #     if not session.get('member_seq'):
    #         return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
    #     current_company_id = session.get('current_company_id', 1)
        
    try:
        # 페이징 파라미터
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        
        # 정렬 파라미터 (새로 추가)
        sort_by = request.args.get('sort_by', 'created_at')
        sort_direction = request.args.get('sort_direction', 'desc')
        
        # 검색 파라미터
        search_term = request.args.get('search', '')
        brand_code_seq = request.args.get('brand_code_seq', type=int)
        category_code_seq = request.args.get('category_code_seq', type=int)
        type_code_seq = request.args.get('type_code_seq', type=int)
        year_code_seq = request.args.get('year_code_seq', type=int)
        show_inactive = request.args.get('show_inactive', 'false') == 'true'
        
        # 쿼리 빌드
        query = Product.query.filter_by(company_id=current_company_id)
        
        if not show_inactive:
            query = query.filter_by(is_active=True)
        
        if search_term:
            search_pattern = f'%{search_term}%'
            query = query.filter(
                or_(
                    Product.product_name.like(search_pattern),
                    Product.product_code.like(search_pattern),
                    Product.description.like(search_pattern)
                )
            )
        
        if brand_code_seq:
            query = query.filter_by(brand_code_seq=brand_code_seq)
            
        if category_code_seq:
            query = query.filter_by(category_code_seq=category_code_seq)
            
        if type_code_seq:
            query = query.filter_by(type_code_seq=type_code_seq)
        
        if year_code_seq:
            query = query.filter_by(year_code_seq=year_code_seq)
        
        # 정렬 적용 (새로 추가)
        if sort_by and hasattr(Product, sort_by):
            sort_column = getattr(Product, sort_by)
            if sort_direction.lower() == 'desc':
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            # 기본 정렬: 생성일 내림차순
            query = query.order_by(Product.created_at.desc())
        
        # 페이징
        pagination = query.paginate(
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
def api_create():
    """상품 등록 API (레거시 방식)"""
    # 개발 환경에서는 로그인 체크 우회 (임시)
    if not session.get('member_seq'):
        # 임시 세션 설정
        session['member_seq'] = 1
        session['member_id'] = 'admin'
        session['current_company_id'] = 1
        
    try:
        current_company_id = session.get('current_company_id', 1)
        
        # 폼 데이터 받기
        data = request.form.to_dict()
        
        # 필수 필드 검증
        required_fields = ['product_name', 'brand_code_seq', 'prod_group_code_seq', 'prod_type_code_seq', 'year_code_seq', 'price']
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
        
        # 새 상품 생성 (레거시 방식)
        product = Product(
            company_id=current_company_id,
            brand_code_seq=int(data['brand_code_seq']),
            category_code_seq=int(data['prod_group_code_seq']),  # 품목 → category로 매핑
            type_code_seq=int(data['prod_type_code_seq']),       # 타입 → type으로 매핑
            year_code_seq=int(data['year_code_seq']),
            
            # 레거시 호환 필드들
            div_type_code_seq=int(data.get('div_type_code_seq', 0)) if data.get('div_type_code_seq') else None,
            
            product_name=data['product_name'],
            product_code='',  # 레거시에서는 제품코드가 별도로 없음
            price=int(data.get('price', 0)),
            description=data.get('description', ''),
            
            # use_yn을 is_active로 변환
            is_active=data.get('use_yn', 'Y') == 'Y',
            use_yn=data.get('use_yn', 'Y'),  # 레거시 호환용
            
            created_by=session.get('member_id', 'admin'),
            updated_by=session.get('member_id', 'admin')
        )
        
        db.session.add(product)
        db.session.flush()  # ID 생성을 위해
        
        # 제품모델 정보 처리
        product_models_data = data.get('product_models')
        if product_models_data:
            try:
                import json
                product_models = json.loads(product_models_data)
                
                for model_data in product_models:
                    # 자가코드로 ProductDetail 생성
                    std_code = model_data['std_code']
                    if len(std_code) == 16:
                        product_detail = ProductDetail(
                            product_id=product.id,
                            brand_code=std_code[:2],
                            div_type_code=std_code[2:3],
                            prod_group_code=std_code[3:5],
                            prod_type_code=std_code[5:7],
                            prod_code=std_code[7:9],
                            prod_type2_code=std_code[9:11],
                            year_code=std_code[11:13],
                            color_code=std_code[13:16],
                            std_div_prod_code=std_code,
                            product_name=model_data['name'],
                            status='Active',
                            use_yn='Y',
                            created_by=session.get('member_id', 'admin'),
                            updated_by=session.get('member_id', 'admin')
                        )
                        db.session.add(product_detail)
                        
            except json.JSONDecodeError:
                current_app.logger.warning('제품모델 데이터 파싱 실패')
        
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
        product.brand_code_seq = data.get('brand_code_seq') or None
        product.category_code_seq = data.get('category_code_seq') or None
        product.type_code_seq = data.get('type_code_seq') or None
        product.year_code_seq = data.get('year_code_seq') or None
        
        # 확장 분류 정보 업데이트 (새로 추가)
        product.color_code_seq = data.get('color_code_seq') or None
        product.div_type_code_seq = data.get('div_type_code_seq') or None
        product.product_code_seq = data.get('product_code_seq') or None
        
        product.product_name = data['product_name']
        product.product_code = data.get('product_code', '')
        product.std_product_code = data.get('std_product_code', '')  # 자가코드 업데이트
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

@bp.route('/api/generate-std-code', methods=['POST'])
@login_required
def api_generate_std_code():
    """자가코드 자동생성 API"""
    # 로그인 체크
    if not session.get('member_seq'):
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        
    try:
        data = request.get_json()
        
        # 필수 매개변수 확인
        required_params = ['brand_code_seq', 'div_type_code_seq', 'category_code_seq', 
                          'type_code_seq', 'product_code_seq', 'year_code_seq', 'color_code_seq']
        
        for param in required_params:
            if not data.get(param):
                return jsonify({'success': False, 'message': f'{param}는 필수 항목입니다.'}), 400
        
        # 코드 정보 조회
        brand_code = Code.query.get(data['brand_code_seq'])
        div_type_code = Code.query.get(data['div_type_code_seq'])
        category_code = Code.query.get(data['category_code_seq'])  # 제품그룹으로 사용
        type_code = Code.query.get(data['type_code_seq'])
        product_code = Code.query.get(data['product_code_seq'])
        year_code = Code.query.get(data['year_code_seq'])
        color_code = Code.query.get(data['color_code_seq'])
        
        # 코드 검증
        codes = {
            '브랜드': brand_code,
            '구분타입': div_type_code, 
            '제품그룹': category_code,
            '제품타입': type_code,
            '제품코드': product_code,
            '년도': year_code,
            '색상': color_code
        }
        
        for name, code_obj in codes.items():
            if not code_obj:
                return jsonify({'success': False, 'message': f'{name} 코드를 찾을 수 없습니다.'}), 400
        
        # 16자리 자가코드 생성 (레거시 호환)
        brand_part = brand_code.code[:2].ljust(2, '0')        # 브랜드 (2자리)
        div_type_part = div_type_code.code[:1]                # 구분타입 (1자리)
        prod_group_part = category_code.code[:2].ljust(2, '0') # 제품그룹 (2자리)
        prod_type_part = type_code.code[:2].ljust(2, '0')     # 제품타입 (2자리)
        prod_code_part = product_code.code[:2].ljust(2, '0')  # 제품코드 (2자리)
        
        # 제품타입2는 타입에서 다른 코드가 있으면 사용, 없으면 기본값
        type2_codes = Code.get_codes_by_group_name('타입')
        prod_type2_part = '00'  # 기본값
        if len(type2_codes) > 1:
            # 현재 선택된 타입과 다른 첫 번째 타입 사용
            for code_info in type2_codes:
                if code_info['seq'] != data['type_code_seq']:
                    prod_type2_part = code_info['code'][:2].ljust(2, '0')
                    break
        
        year_part = year_code.code[:1]                        # 년도 (1자리)
        color_part = color_code.code[:3].ljust(3, '0')       # 색상 (3자리)
        
        # 자가코드 조합 (총 16자리)
        std_code = f"{brand_part}{div_type_part}{prod_group_part}{prod_type_part}{prod_code_part}{prod_type2_part}{year_part}{color_part}"
        
        # 중복 검증
        existing_detail = ProductDetail.find_by_std_code(std_code)
        if existing_detail:
            return jsonify({
                'success': False, 
                'message': f'자가코드 {std_code}는 이미 사용 중입니다.',
                'existing_product': existing_detail.product.product_name if existing_detail.product else None
            }), 400
        
        # 생성 정보 반환
        return jsonify({
            'success': True,
            'std_code': std_code,
            'breakdown': {
                'brand': {'code': brand_part, 'name': brand_code.code_name},
                'div_type': {'code': div_type_part, 'name': div_type_code.code_name},
                'prod_group': {'code': prod_group_part, 'name': category_code.code_name},
                'prod_type': {'code': prod_type_part, 'name': type_code.code_name},
                'prod_code': {'code': prod_code_part, 'name': product_code.code_name},
                'prod_type2': {'code': prod_type2_part, 'name': '기본타입2'},
                'year': {'code': year_part, 'name': year_code.code_name},
                'color': {'code': color_part, 'name': color_code.code_name}
            },
            'message': f'자가코드가 생성되었습니다: {std_code}'
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ 자가코드 생성 실패: {e}")
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
            codes = Code.get_codes_by_group_name('브랜드', company_id=current_company_id)
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
        # 확장 코드 그룹 (새로 추가)
        elif code_type == 'colors':
            codes = Code.get_codes_by_group_name('색상', company_id=current_company_id)
        elif code_type == 'div_types':
            codes = Code.get_codes_by_group_name('구분타입', company_id=current_company_id)
        elif code_type == 'product_codes':
            codes = Code.get_codes_by_group_name('제품코드', company_id=current_company_id)
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

@bp.route('/api/upload-excel', methods=['POST'])
@login_required
def api_upload_excel():
    """엑셀 파일 일괄 업로드"""
    try:
        if not session.get('member_seq'):
            return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '파일이 선택되지 않았습니다.'}), 400
        
        file = request.files['file']
        if not file.filename:
            return jsonify({'success': False, 'message': '파일이 선택되지 않았습니다.'}), 400
        
        if not allowed_file(file.filename, EXCEL_EXTENSIONS):
            return jsonify({'success': False, 'message': '엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.'}), 400
        
        current_company_id = session.get('current_company_id', 1)
        created_by = session.get('member_id', 'admin')
        
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            file.save(tmp_file.name)
            
            # 엑셀 파일 읽기
            df = pd.read_excel(tmp_file.name)
            
        os.unlink(tmp_file.name)  # 임시 파일 삭제
        
        success_count = 0
        error_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # 필수 필드 체크
                if pd.isna(row.get('상품명')) or not str(row['상품명']).strip():
                    errors.append(f"행 {index + 2}: 상품명이 없습니다")
                    error_count += 1
                    continue
                
                # 브랜드 매핑 (코드 체계 사용 - 텍스트 → 코드번호)
                brand_code_seq = None
                if not pd.isna(row.get('브랜드')):
                    brand_name = str(row['브랜드']).strip()
                    if brand_name:
                        brand_codes = Code.get_codes_by_group_name('브랜드')
                        for code in brand_codes:
                            if code['code_name'] == brand_name or code['code'] == brand_name:
                                brand_code_seq = code['seq']
                                break

                # 품목 매핑 (텍스트 → 코드번호)
                category_code_seq = None
                if not pd.isna(row.get('품목')):
                    category_name = str(row['품목']).strip()
                    if category_name:
                        category_codes = Code.get_codes_by_group_name('품목')
                        for code in category_codes:
                            if code['code_name'] == category_name or code['code'] == category_name:
                                category_code_seq = code['seq']
                                break

                # 타입 매핑 (텍스트 → 코드번호)
                type_code_seq = None
                if not pd.isna(row.get('타입')):
                    type_name = str(row['타입']).strip()
                    if type_name:
                        type_codes = Code.get_codes_by_group_name('타입')
                        for code in type_codes:
                            if code['code_name'] == type_name or code['code'] == type_name:
                                type_code_seq = code['seq']
                                break

                # 년도 매핑 (텍스트 → 코드번호)
                year_code_seq = None
                if not pd.isna(row.get('년도')):
                    year_value = str(row['년도']).strip()
                    if year_value:
                        year_codes = Code.get_codes_by_group_name('년도')
                        for code in year_codes:
                            # 년도는 다양한 형식으로 매칭 (2024, 24, 2024년 등)
                            if (code['code_name'] == year_value or 
                                code['code'] == year_value or
                                year_value in code['code_name'] or
                                year_value.replace('년', '') in code['code_name'] or
                                code['code_name'].replace('년', '') == year_value.replace('년', '')):
                                year_code_seq = code['seq']
                                break
                
                # 가격 처리
                price = 0
                if not pd.isna(row.get('가격')):
                    try:
                        price = int(float(row['가격']))
                    except:
                        price = 0
                
                # 상품 생성
                product = Product(
                    company_id=current_company_id,
                    brand_code_seq=brand_code_seq,
                    category_code_seq=category_code_seq,
                    type_code_seq=type_code_seq,
                    year_code_seq=year_code_seq,
                    product_name=str(row['상품명']).strip(),
                    product_code=str(row.get('상품코드', '')).strip() or None,
                    price=price,
                    description=str(row.get('설명', '')).strip() or None,
                    is_active=str(row.get('상태', '활성')).strip() == '활성',
                    created_by=created_by,
                    updated_by=created_by
                )
                
                db.session.add(product)
                db.session.flush()  # ID 생성을 위해
                
                # 히스토리 기록
                history = ProductHistory(
                    product_id=product.id,
                    action='EXCEL_UPLOAD',
                    new_values=product.to_dict(),
                    created_by=created_by
                )
                db.session.add(history)
                
                success_count += 1
                
            except Exception as e:
                db.session.rollback()
                errors.append(f"행 {index + 2}: {str(e)}")
                error_count += 1
                continue
        
        if success_count > 0:
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'업로드 완료: 성공 {success_count}개, 실패 {error_count}개',
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors[:10]  # 최대 10개 오류만 반환
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ 엑셀 업로드 실패: {e}")
        return jsonify({'success': False, 'message': f'업로드 중 오류가 발생했습니다: {str(e)}'}), 500

@bp.route('/api/download-excel')
@login_required
def api_download_excel():
    """상품 목록 엑셀 다운로드"""
    try:
        if not session.get('member_seq'):
            return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        
        current_company_id = session.get('current_company_id', 1)
        
        # 상품 목록 조회
        products = Product.query.filter_by(company_id=current_company_id).all()
        
        # 데이터 준비
        data = []
        for product in products:
            data.append({
                'ID': product.id,
                '상품명': product.product_name,
                '상품코드': product.product_code or '',
                '브랜드': product.brand_code.code_name if product.brand_code else '',
                '품목': product.category_code.code_name if product.category_code else '',
                '타입': product.type_code.code_name if product.type_code else '',
                '년도': product.year_code.code_name if product.year_code else '',
                '가격': product.price or 0,
                '설명': product.description or '',
                '상태': '활성' if product.is_active else '비활성',
                '등록일': product.created_at.strftime('%Y-%m-%d') if product.created_at else '',
                '등록자': product.created_by or ''
            })
        
        # DataFrame 생성
        df = pd.DataFrame(data)
        
        # 엑셀 파일 생성
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='상품목록', index=False)
            
            # 워크시트 서식 설정
            worksheet = writer.sheets['상품목록']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # 파일명 생성
        filename = f"상품목록_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"❌ 엑셀 다운로드 실패: {e}")
        return jsonify({'success': False, 'message': f'다운로드 중 오류가 발생했습니다: {str(e)}'}), 500

@bp.route('/api/download-template')
@login_required
def api_download_template():
    """엑셀 업로드 템플릿 다운로드 (실제 코드명 예시 포함)"""
    try:
        current_company_id = session.get('current_company_id', 1)
        
        # 실제 코드명 예시 수집
        brand_codes = Code.get_codes_by_group_name('브랜드', company_id=current_company_id)
        category_codes = Code.get_codes_by_group_name('품목', company_id=current_company_id)
        type_codes = Code.get_codes_by_group_name('타입', company_id=current_company_id)
        year_codes = Code.get_codes_by_group_name('년도', company_id=current_company_id)
        
        # 예시 데이터 (실제 코드명 사용)
        brand_example = brand_codes[0]['code_name'] if brand_codes else '브랜드 예시'
        category_example = category_codes[0]['code_name'] if category_codes else '품목 예시'
        type_example = type_codes[0]['code_name'] if type_codes else '타입 예시'
        year_example = year_codes[0]['code_name'] if year_codes else '2024'
        
        # 코드 정보 조회 (드롭다운용)
        brand_codes = Code.get_codes_by_group_name('브랜드', company_id=current_company_id)
        category_codes = Code.get_codes_by_group_name('품목', company_id=current_company_id)
        type_codes = Code.get_codes_by_group_name('타입', company_id=current_company_id)
        year_codes = Code.get_codes_by_group_name('년도', company_id=current_company_id)
        
        # 확장 코드 그룹 조회 (새로 추가)
        color_codes = Code.get_codes_by_group_name('색상', company_id=current_company_id)
        div_type_codes = Code.get_codes_by_group_name('구분타입', company_id=current_company_id)
        product_codes = Code.get_codes_by_group_name('제품코드', company_id=current_company_id)
        
        # 레거시 호환 추가 코드 그룹들
        prod_group_codes = Code.get_codes_by_group_name('품목그룹', company_id=current_company_id)
        prod_type_codes = Code.get_codes_by_group_name('제품타입', company_id=current_company_id)
        type2_codes = Code.get_codes_by_group_name('타입2', company_id=current_company_id)
        
        template_data = {
            '상품명': ['상품명 예시1', '상품명 예시2'],
            '상품코드': ['PROD001', 'PROD002'],
            '브랜드': [brand_example, brand_example],
            '품목': [category_example, category_example],
            '타입': [type_example, type_example],
            '년도': [year_example, year_example],
            '가격': [10000, 20000],
            '설명': ['상품 설명1', '상품 설명2'],
            '상태': ['활성', '활성']
        }
        
        df = pd.DataFrame(template_data)
        
        # 엑셀 파일 생성
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='상품업로드템플릿', index=False)
            
            # 코드 정보 시트 추가
            if brand_codes or category_codes or type_codes or year_codes:
                code_data = []
                
                # 브랜드 코드 정보
                for code in brand_codes:
                    code_data.append(['브랜드', code['code'], code['code_name']])
                
                # 품목 코드 정보  
                for code in category_codes:
                    code_data.append(['품목', code['code'], code['code_name']])
                
                # 타입 코드 정보
                for code in type_codes:
                    code_data.append(['타입', code['code'], code['code_name']])
                
                # 년도 코드 정보
                for code in year_codes:
                    code_data.append(['년도', code['code'], code['code_name']])
                
                codes_df = pd.DataFrame(code_data, columns=['분류', '코드', '코드명'])
                codes_df.to_excel(writer, sheet_name='코드참조표', index=False)
            
            # 워크시트 서식 설정
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 30)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename="상품업로드템플릿.xlsx"'
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"❌ 템플릿 다운로드 실패: {e}")
        return jsonify({'success': False, 'message': f'템플릿 다운로드 중 오류가 발생했습니다: {str(e)}'}), 500

@bp.route('/api/sync-erpia', methods=['POST'])
@login_required
def api_sync_erpia():
    """ERPia와 상품 동기화"""
    try:
        if not session.get('member_seq'):
            return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        
        # ERPia 동기화 로직 구현
        # 여기서는 간단한 예시로 성공 반환
        # 실제로는 ERPia API를 호출하여 상품 정보를 가져와야 함
        
        current_app.logger.info(f"ERPia 상품 동기화 시작 - 사용자: {session.get('member_id')}")
        
        # TODO: 실제 ERPia API 연동 구현
        # 1. ERPia에서 상품 목록 가져오기
        # 2. 기존 상품과 비교하여 UPSERT
        # 3. 동기화 결과 반환
        
        return jsonify({
            'success': True,
            'message': 'ERPia 동기화가 완료되었습니다',
            'sync_count': 0,
            'new_count': 0,
            'updated_count': 0
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ ERPia 동기화 실패: {e}")
        return jsonify({'success': False, 'message': f'동기화 중 오류가 발생했습니다: {str(e)}'}), 500 

@bp.route('/api/create-product-model', methods=['POST'])
@login_required
def api_create_product_model():
    """제품모델(색상별 상품) 생성 API"""
    try:
        if not session.get('member_seq'):
            return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        
        data = request.get_json()
        current_company_id = session.get('current_company_id', 1)
        
        # 필수 필드 검증
        required_fields = ['product_name', 'color_code_seq', 'div_type_code_seq', 'type_code_seq', 'std_product_code']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field}는 필수 항목입니다.'}), 400
        
        # 중복 자가코드 검증
        existing_model = ProductDetail.find_by_std_code(data['std_product_code'])
        if existing_model:
            return jsonify({'success': False, 'message': f'자가코드 {data["std_product_code"]}는 이미 사용 중입니다.'}), 400
        
        # 코드 정보 조회
        color_code = Code.query.get(data['color_code_seq'])
        div_type_code = Code.query.get(data['div_type_code_seq'])
        type_code = Code.query.get(data['type_code_seq'])
        
        if not all([color_code, div_type_code, type_code]):
            return jsonify({'success': False, 'message': '선택된 코드 정보를 찾을 수 없습니다.'}), 400
        
        # 자가코드 분해 (16자리)
        std_code = data['std_product_code']
        if len(std_code) != 16:
            return jsonify({'success': False, 'message': '자가코드는 16자리여야 합니다.'}), 400
        
        # 제품모델 생성
        product_detail = ProductDetail(
            product_id=None,  # 임시로 None, 나중에 상품 저장 시 연결
            brand_code=std_code[:2],
            div_type_code=std_code[2:3],
            prod_group_code=std_code[3:5],
            prod_type_code=std_code[5:7],
            prod_code=std_code[7:9],
            prod_type2_code=std_code[9:11],
            year_code=std_code[11:12],
            color_code=std_code[12:15],
            std_div_prod_code=std_code,
            product_name=data['product_name'],
            additional_price=int(data.get('additional_price', 0)),
            stock_quantity=int(data.get('stock_quantity', 0)),
            status='Active',
            created_by=session.get('member_id', 'admin'),
            updated_by=session.get('member_id', 'admin')
        )
        
        db.session.add(product_detail)
        db.session.commit()
        
        current_app.logger.info(f"✅ 제품모델 생성 성공: {product_detail.product_name} ({product_detail.std_div_prod_code})")
        
        return jsonify({
            'success': True,
            'message': '제품모델이 성공적으로 생성되었습니다.',
            'product_model': product_detail.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ 제품모델 생성 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/api/list-product-models')
@login_required
def api_list_product_models():
    """제품모델 목록 조회 API"""
    try:
        if not session.get('member_seq'):
            return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        
        current_company_id = session.get('current_company_id', 1)
        
        # 제품모델 목록 조회 (최신순)
        product_models = ProductDetail.query.order_by(ProductDetail.created_at.desc()).all()
        
        # 코드 정보와 함께 반환
        models_data = []
        for model in product_models:
            model_dict = model.to_dict()
            
            # 색상 정보 추가
            if model.color_code:
                color = Code.query.filter_by(code=model.color_code).first()
                model_dict['color_name'] = color.code_name if color else model.color_code
            
            # 구분타입 정보 추가
            if model.div_type_code:
                div_type = Code.query.filter_by(code=model.div_type_code).first()
                model_dict['div_type_name'] = div_type.code_name if div_type else model.div_type_code
            
            # 타입 정보 추가
            if model.prod_type_code:
                type_code = Code.query.filter_by(code=model.prod_type_code).first()
                model_dict['type_name'] = type_code.code_name if type_code else model.prod_type_code
                
            models_data.append(model_dict)
        
        return jsonify({
            'success': True,
            'product_models': models_data
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ 제품모델 목록 조회 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/api/list-product-models/<int:product_id>')
@login_required
def api_list_product_models_by_product(product_id):
    """특정 상품의 제품모델 목록 조회 API"""
    try:
        if not session.get('member_seq'):
            return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        
        # 제품모델 목록 조회 (특정 상품 기준)
        product_models = ProductDetail.query.filter_by(product_id=product_id).order_by(ProductDetail.created_at.desc()).all()
        
        # 코드 정보와 함께 반환
        models_data = []
        for model in product_models:
            model_dict = model.to_dict()
            
            # 색상 정보 추가
            if model.color_code:
                color = Code.query.filter_by(code=model.color_code).first()
                model_dict['color_name'] = color.code_name if color else model.color_code
            
            # 구분타입 정보 추가
            if model.div_type_code:
                div_type = Code.query.filter_by(code=model.div_type_code).first()
                model_dict['div_type_name'] = div_type.code_name if div_type else model.div_type_code
            
            # 타입 정보 추가
            if model.prod_type_code:
                type_code = Code.query.filter_by(code=model.prod_type_code).first()
                model_dict['type_name'] = type_code.code_name if type_code else model.prod_type_code
                
            models_data.append(model_dict)
        
        return jsonify({
            'success': True,
            'product_models': models_data
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ 상품별 제품모델 목록 조회 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500 

@bp.route('/api/delete-product-model/<int:model_id>', methods=['DELETE'])
@login_required
def api_delete_product_model(model_id):
    """제품모델 삭제 API"""
    try:
        if not session.get('member_seq'):
            return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        
        # 제품모델 조회
        product_model = ProductDetail.query.get(model_id)
        if not product_model:
            return jsonify({'success': False, 'message': '제품모델을 찾을 수 없습니다.'}), 404
        
        # 제품모델 삭제
        model_name = product_model.product_name
        std_code = product_model.std_div_prod_code
        
        db.session.delete(product_model)
        db.session.commit()
        
        current_app.logger.info(f"✅ 제품모델 삭제 성공: {model_name} ({std_code})")
        
        return jsonify({
            'success': True,
            'message': '제품모델이 성공적으로 삭제되었습니다.'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ 제품모델 삭제 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500 

@bp.route('/api/debug/mapping-status')
@login_required
def debug_mapping_status():
    """상품 매핑 상태 확인 (디버그용)"""
    try:
        current_company_id = session.get('current_company_id', 1)
        
        # 전체 상품 개수
        total_count = Product.query.filter_by(company_id=current_company_id).count()
        
        # 매핑 상태별 개수
        brand_mapped = Product.query.filter_by(company_id=current_company_id).filter(Product.brand_code_seq.isnot(None)).count()
        category_mapped = Product.query.filter_by(company_id=current_company_id).filter(Product.category_code_seq.isnot(None)).count()
        type_mapped = Product.query.filter_by(company_id=current_company_id).filter(Product.type_code_seq.isnot(None)).count()
        year_mapped = Product.query.filter_by(company_id=current_company_id).filter(Product.year_code_seq.isnot(None)).count()
        
        # 샘플 데이터
        sample_products = Product.query.filter_by(company_id=current_company_id).limit(5).all()
        samples = []
        for product in sample_products:
            samples.append({
                'id': product.id,
                'name': product.product_name,
                'legacy_seq': product.legacy_seq,
                'brand_seq': product.brand_code_seq,
                'brand_name': product.brand_code.code_name if product.brand_code else None,
                'category_seq': product.category_code_seq,
                'category_name': product.category_code.code_name if product.category_code else None,
                'type_seq': product.type_code_seq,
                'type_name': product.type_code.code_name if product.type_code else None,
                'year_seq': product.year_code_seq,
                'year_name': product.year_code.code_name if product.year_code else None
            })
        
        # 사용 가능한 코드들
        available_codes = {}
        code_groups = [
            ('브랜드', 'brand'),
            ('품목', 'category'),
            ('타입', 'type'),
            ('년도', 'year')
        ]
        
        for group_name, key in code_groups:
            codes = Code.get_codes_by_group_name(group_name, current_company_id)
            available_codes[key] = [{'seq': c.seq, 'code': c.code, 'name': c.code_name} for c in codes[:5]]
        
        return jsonify({
            'success': True,
            'mapping_status': {
                'total': total_count,
                'brand_mapped': brand_mapped,
                'category_mapped': category_mapped,
                'type_mapped': type_mapped,
                'year_mapped': year_mapped,
                'brand_percentage': round(brand_mapped/total_count*100, 1) if total_count > 0 else 0,
                'category_percentage': round(category_mapped/total_count*100, 1) if total_count > 0 else 0,
                'type_percentage': round(type_mapped/total_count*100, 1) if total_count > 0 else 0,
                'year_percentage': round(year_mapped/total_count*100, 1) if total_count > 0 else 0
            },
            'sample_products': samples,
            'available_codes': available_codes
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ 매핑 상태 확인 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500 

@bp.route('/api/get-codes')
def api_get_all_codes():
    """모든 코드 정보 조회 API (개발용)"""
    try:
        # 개발 환경에서는 로그인 체크 우회 (강제)
        current_company_id = 1  # 에이원으로 고정
        
        # 원래 로그인 체크 코드는 주석 처리
        # if current_app.config.get('FLASK_ENV') == 'development':
        #     current_company_id = 1  # 에이원으로 고정
        # else:
        #     # 로그인 체크
        #     if not session.get('member_seq'):
        #         return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        #     current_company_id = session.get('current_company_id', 1)
        
        # 모든 코드 그룹 조회
        brands = Code.get_codes_by_group_name('브랜드', company_id=current_company_id)
        categories = Code.get_codes_by_group_name('품목', company_id=current_company_id)
        colors = Code.get_codes_by_group_name('색상', company_id=current_company_id)
        div_types = Code.get_codes_by_group_name('구분타입', company_id=current_company_id)
        
        # JSON 형태로 변환
        result = {
            'brands': [{'seq': code.seq, 'code': code.code, 'name': code.code_name} for code in brands],
            'categories': [{'seq': code.seq, 'code': code.code, 'name': code.code_name} for code in categories],
            'colors': [{'seq': code.seq, 'code': code.code, 'name': code.code_name} for code in colors],
            'div_types': [{'seq': code.seq, 'code': code.code, 'name': code.code_name} for code in div_types]
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'오류 발생: {str(e)}'}), 500 

@bp.route('/api/get-types-by-category/<int:category_seq>')
def api_get_types_by_category(category_seq):
    """품목에 해당하는 타입 목록 조회 API"""
    try:
        # 개발 환경에서는 로그인 체크 우회
        current_company_id = 1
        
        # 해당 품목에 맞는 타입들을 찾기
        # 실제로는 코드 체계의 parent_seq 관계를 이용해야 하지만
        # 임시로 모든 타입을 반환 (추후 개선 필요)
        types_list = Code.get_codes_by_group_name('타입', company_id=current_company_id)
        
        # Code 객체를 딕셔너리로 변환
        types = []
        for type_obj in types_list:
            types.append({
                'seq': type_obj.seq,
                'code': type_obj.code,
                'code_name': type_obj.code_name
            })
        
        return jsonify({
            'success': True,
            'types': types
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ 타입 조회 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500 