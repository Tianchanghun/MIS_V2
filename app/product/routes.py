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
import time # 레거시 자가코드 생성 함수에 사용

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
        
        # 코드 정보 조회 (드롭다운용) - 요구사항에 맞게 수정
        # 1. 회사 정보 (하드코딩 - 에이원, 에이원월드만)
        company_codes = [
            {'id': 1, 'name': '에이원'},
            {'id': 2, 'name': '에이원월드'}
        ]
        
        # 2. 브랜드 코드 (브랜드 그룹에서)
        brand_codes_raw = Code.get_codes_by_group_name('브랜드')
        brand_codes = [{'seq': code.seq, 'code': code.code, 'code_name': code.code_name} for code in brand_codes_raw]
        
        # 3. 품목 코드 (PRD 그룹에서 가져오기)
        product_codes_raw = Code.get_codes_by_group_name('PRD')
        product_codes = [{'seq': code.seq, 'code': code.code, 'code_name': code.code_name} for code in product_codes_raw]
        
        # 4. 타입 코드 (초기에는 빈 리스트, 품목 선택 시 동적 로드)
        type_codes = []
        
        # 5. 색상 코드 (CR 그룹에서 가져오기)
        color_codes_raw = Code.get_codes_by_group_name('CR')
        color_codes = [{'seq': code.seq, 'code': code.code, 'code_name': code.code_name} for code in color_codes_raw]
        
        # 6. 년도 코드 (YR 그룹에서 가져오기)
        year_codes_raw = Code.get_codes_by_group_name('YR')
        year_codes = [{'seq': code.seq, 'code': code.code, 'code_name': code.code_name} for code in year_codes_raw]
        
        # 년도 코드가 없으면 기본 년도 생성
        if not year_codes:
            current_year = datetime.now().year
            year_codes = [
                {'seq': None, 'code': str(current_year), 'code_name': f'{current_year}년'},
                {'seq': None, 'code': str(current_year-1), 'code_name': f'{current_year-1}년'},
                {'seq': None, 'code': str(current_year+1), 'code_name': f'{current_year+1}년'}
            ]
        
        # 7. 상태 코드 (하드코딩)
        status_codes = [
            {'value': 'true', 'name': '활성'},
            {'value': 'false', 'name': '비활성'}
        ]
        
        # 레거시 호환 코드들 (기존 기능 유지)
        category_codes_raw = Code.get_codes_by_group_name('제품구분')  # 제품구분 (PRT)
        category_codes = [{'seq': code.seq, 'code': code.code, 'code_name': code.code_name} for code in category_codes_raw]
        
        div_type_codes_raw = Code.get_codes_by_group_name('구분타입')
        div_type_codes = [{'seq': code.seq, 'code': code.code, 'code_name': code.code_name} for code in div_type_codes_raw]
        
        prod_group_codes_raw = Code.get_codes_by_group_name('품목그룹')  # 레거시 호환
        prod_group_codes = [{'seq': code.seq, 'code': code.code, 'code_name': code.code_name} for code in prod_group_codes_raw]
        
        prod_type_codes_raw = Code.get_codes_by_group_name('제품타입')  # 레거시 호환
        prod_type_codes = [{'seq': code.seq, 'code': code.code, 'code_name': code.code_name} for code in prod_type_codes_raw]
        
        type2_codes_raw = Code.get_codes_by_group_name('타입2')
        type2_codes = [{'seq': code.seq, 'code': code.code, 'code_name': code.code_name} for code in type2_codes_raw]
        
        # 🔥 새로운 분류 체계들 로드 (Excel에서 가져온 실제 분류)
        try:
            product_group_codes_raw = Code.get_codes_by_group_name('제품군')
            product_group_codes = [{'seq': code.seq, 'code': code.code, 'code_name': code.code_name} for code in product_group_codes_raw]
            
            item_codes_raw = Code.get_codes_by_group_name('아이템별')
            item_codes = [{'seq': code.seq, 'code': code.code, 'code_name': code.code_name} for code in item_codes_raw]
            
            item_detail_codes_raw = Code.get_codes_by_group_name('아이템상세')
            item_detail_codes = [{'seq': code.seq, 'code': code.code, 'code_name': code.code_name} for code in item_detail_codes_raw]
            
            color_by_product_codes_raw = Code.get_codes_by_group_name('색상별')
            color_by_product_codes = [{'seq': code.seq, 'code': code.code, 'code_name': code.code_name} for code in color_by_product_codes_raw]
            
            product_type_category_codes_raw = Code.get_codes_by_group_name('제품타입')
            product_type_category_codes = [{'seq': code.seq, 'code': code.code, 'code_name': code.code_name} for code in product_type_category_codes_raw]
            
        except Exception as e:
            current_app.logger.error(f"❌ 새로운 분류 체계 로딩 실패: {e}")
            product_group_codes = []
            item_codes = []
            item_detail_codes = []
            color_by_product_codes = []
            product_type_category_codes = []
        
        return render_template('product/index.html',
                             products=products,
                             # 새로운 코드 체계 (요구사항)
                             company_codes=company_codes,        # 회사 (에이원, 에이원월드)
                             brand_codes=brand_codes,            # 브랜드 그룹
                             product_codes=product_codes,        # PRD 그룹 (품목)
                             type_codes=type_codes,              # 동적 로드 (품목 선택 시)
                             color_codes=color_codes,            # CR 그룹 (색상)
                             year_codes=year_codes,              # YR 그룹 (년도)
                             status_codes=status_codes,          # 상태 (활성/비활성)
                             # 레거시 호환 코드들
                             category_codes=category_codes,
                             div_type_codes=div_type_codes,
                             prod_group_codes=prod_group_codes,
                             prod_type_codes=prod_type_codes,
                             type2_codes=type2_codes,
                             # 🔥 새로운 분류 체계들 추가
                             product_group_codes=product_group_codes,
                             item_codes=item_codes,
                             item_detail_codes=item_detail_codes,
                             color_by_product_codes=color_by_product_codes,
                             product_type_category_codes=product_type_category_codes,
                             search_term=search_term,
                             brand_code_seq=brand_code_seq,
                             category_code_seq=category_code_seq,
                             type_code_seq=type_code_seq,
                             year_code_seq=year_code_seq,
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
        
        # 검색어 처리 (상품명, 상품코드, 설명, 자가코드 포함)
        if search_term:
            search_pattern = f'%{search_term}%'
            # 서브쿼리로 자가코드 검색 포함
            subquery = db.session.query(ProductDetail.product_id).filter(
                ProductDetail.std_div_prod_code.ilike(search_pattern)
            ).subquery()
            
            query = query.filter(
                db.or_(
                    Product.product_name.ilike(search_pattern),
                    Product.product_code.ilike(search_pattern),
                    Product.description.ilike(search_pattern),
                    Product.id.in_(subquery)  # 자가코드로 검색
                )
            )
        
        # 필터 조건들
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
            'data': products,  # products -> data로 변경
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
        
        # 새 상품 생성 (tbl_Product - 기본 정보)
        product = Product(
            company_id=current_company_id,
            brand_code_seq=int(data['brand_code_seq']),
            category_code_seq=int(data['prod_group_code_seq']),  # 제품구분 → category로 매핑
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
        
        # tbl_Product_DTL 생성 (16자리 자사코드와 함께)
        product_models_data = data.get('product_models')
        if product_models_data:
            try:
                import json
                product_models = json.loads(product_models_data)
                
                for model_data in product_models:
                    # 16자리 자사코드로 ProductDetail 생성
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
                            additional_price=int(model_data.get('additional_price', 0)),
                            stock_quantity=int(model_data.get('stock_quantity', 0)),
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

@bp.route('/api/generate-code', methods=['POST'])
def api_generate_code():
    """레거시 방식에 따른 자사코드 자동 생성 (16자리)"""
    # 개발 환경에서는 로그인 체크 우회 (임시)
    if not session.get('member_seq'):
        session['member_seq'] = 1
        session['member_id'] = 'admin'
        session['current_company_id'] = 1
    
    try:
        # JSON과 FormData 모두 처리
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        # 필수 파라미터 확인
        required_fields = ['brandSeq', 'prodGroupSeq', 'prodCodeSeq', 'prodTypeSeq', 'yearSeq', 'colorSeq']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field}는 필수 항목입니다.'}), 400
        
        # 코드 정보 조회
        brand_code = Code.query.get(data['brandSeq'])
        prod_group_code = Code.query.get(data['prodGroupSeq'])
        prod_code = Code.query.get(data['prodCodeSeq'])
        prod_type_code = Code.query.get(data['prodTypeSeq'])
        year_code = Code.query.get(data['yearSeq'])
        color_code = Code.query.get(data['colorSeq'])
        
        if not all([brand_code, prod_group_code, prod_code, prod_type_code, year_code, color_code]):
            return jsonify({'success': False, 'message': '선택된 코드 중 일부를 찾을 수 없습니다.'}), 400
        
        # 레거시 자사코드 생성 로직 (16자리) - tbl_Product_DTL 기준
        # 브랜드(2) + 구분타입(1) + 제품군(2) + 제품타입(2) + 제품(2) + 타입2(2) + 년도(2) + 색상(3)
        generated_code = generate_legacy_std_code_16digit(
            brand_code.code,
            '1',  # 구분타입 고정 (일반)
            prod_group_code.code,
            prod_type_code.code,
            prod_code.code,
            '00',  # 타입2 기본값
            year_code.code,
            color_code.code
        )
        
        # 중복 확인
        existing_code = ProductDetail.query.filter_by(std_div_prod_code=generated_code).first()
        if existing_code:
            # 중복 시 시퀀스 번호 추가하여 유니크하게 만들기
            sequence = 1
            while True:
                new_code = generated_code[:-3] + f'{sequence:03d}'
                if not ProductDetail.query.filter_by(std_div_prod_code=new_code).first():
                    generated_code = new_code
                    break
                sequence += 1
                if sequence > 999:  # 무한루프 방지
                    generated_code = generated_code[:-6] + f'{int(time.time()) % 1000000:06d}'
                    break
        
        current_app.logger.info(f"자사코드 생성 완료: {generated_code}")
        
        return jsonify({
            'success': True,
            'generated_code': generated_code,
            'components': {
                'brand': brand_code.code,
                'div_type': '1',
                'prod_group': prod_group_code.code,
                'prod_type': prod_type_code.code,
                'prod': prod_code.code,
                'type2': '00',
                'year': year_code.code,
                'color': color_code.code
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"자사코드 생성 실패: {e}")
        return jsonify({'success': False, 'message': f'자사코드 생성 중 오류가 발생했습니다: {str(e)}'}), 500

def generate_legacy_std_code_16digit(brand, div_type, prod_group, prod_type, prod, type2, year, color):
    """
    레거시 방식 자사코드 생성 (16자리) - tbl_Product_DTL 기준
    총 16자리: 브랜드(2) + 구분타입(1) + 제품군(2) + 제품타입(2) + 제품(2) + 타입2(2) + 년도(2) + 색상(3)
    예시: JI1SGZ1CT0018STN
    """
    # 각 구성요소를 정해진 길이로 맞추기
    brand_part = (brand or 'AA')[:2].ljust(2, 'A').upper()          # 2자리 (JI)
    div_type_part = (div_type or '1')[:1]                           # 1자리 (1)
    prod_group_part = (prod_group or 'AA')[:2].ljust(2, 'A').upper() # 2자리 (SG)
    prod_type_part = (prod_type or 'AA')[:2].ljust(2, 'A').upper()  # 2자리 (Z1)  
    prod_part = (prod or 'AA')[:2].ljust(2, 'A').upper()           # 2자리 (CT)
    type2_part = (type2 or '00')[:2].ljust(2, '0')                  # 2자리 (00)
    year_part = (year or '00')[-2:].ljust(2, '0')                   # 2자리 년도 (18)
    color_part = (color or 'AAA')[:3].ljust(3, 'A').upper()        # 3자리 색상 (STN)
    
    std_code = brand_part + div_type_part + prod_group_part + prod_type_part + prod_part + type2_part + year_part + color_part
    
    return std_code.upper()

@bp.route('/api/generate-std-code', methods=['POST'])
@login_required
def api_generate_std_code():
    """자사코드 자동 생성 API"""
    try:
        if not session.get('member_seq'):
            return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        
        # JSON과 FormData 둘 다 처리
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        # 필수 파라미터 확인 (더 안전한 체크)
        required_fields = ['brand_code', 'prod_group_code', 'prod_type_code', 'prod_code', 'year_code', 'color_code']
        
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False, 
                    'message': f'{field} 파라미터가 필요합니다.'
                }), 400
        
        # 코드 SEQ를 통해 실제 코드값 조회
        def get_code_by_seq(seq):
            if not seq or seq == '':
                return None
            try:
                code = Code.query.get(int(seq))
                return code.code if code else None
            except:
                return str(seq)  # SEQ가 아닌 경우 그대로 사용
        
        # 실제 코드값들 조회 (SEQ → 코드값 변환)
        brand_code = get_code_by_seq(data.get('brand_code')) or 'RY'  # 기본값: RY
        div_type_code = str(data.get('div_type_code', '3'))[:1]  # 기본값: 3
        prod_group_code = get_code_by_seq(data.get('prod_group_code')) or 'SG'  # 기본값: SG
        prod_type_code = get_code_by_seq(data.get('prod_type_code')) or 'TR'  # 기본값: TR
        prod_code = get_code_by_seq(data.get('prod_code')) or 'TJ'  # 기본값: TJ
        prod_type2_code = str(data.get('prod_type2_code', '00'))[:2].ljust(2, '0')  # 기본값: 00
        year_code = get_code_by_seq(data.get('year_code')) or '25'  # 기본값: 25
        color_code = str(data.get('color_code', 'BLK')).upper()  # 색상은 직접 입력값 사용
        
        # 16자리 자사코드 조합 (RY3SGTRTJ0025BLK 형태)
        # 브랜드(2) + 구분타입(1) + 제품구분(2) + 타입(2) + 품목(2) + 타입2(2) + 년도(2) + 색상(3)
        
        # 각 구성요소를 정확한 길이로 맞춤
        brand_part = str(brand_code)[:2].ljust(2, '0')           # 2자리 (RY)
        div_type_part = str(div_type_code)[:1].ljust(1, '0')     # 1자리 (3)  
        prod_group_part = str(prod_group_code)[:2].ljust(2, '0') # 2자리 (SG)
        prod_type_part = str(prod_type_code)[:2].ljust(2, '0')   # 2자리 (TR)
        prod_code_part = str(prod_code)[:2].ljust(2, '0')        # 2자리 (TJ)
        prod_type2_part = str(prod_type2_code)[:2].ljust(2, '0') # 2자리 (00)
        year_part = str(year_code)[-2:].ljust(2, '0')            # 2자리 (25)
        color_part = str(color_code)[:3].ljust(3, '0')           # 3자리 (BLK)
        
        std_code = (brand_part + div_type_part + prod_group_part + 
                   prod_type_part + prod_code_part + prod_type2_part + 
                   year_part + color_part)
        
        # 16자리 확인
        if len(std_code) != 16:
            std_code = std_code[:16].ljust(16, '0')  # 강제로 16자리 맞춤
        
        current_app.logger.info(f"✅ 자사코드 생성 성공: {std_code}")
        current_app.logger.info(f"🔧 구성: {brand_code}+{div_type_code}+{prod_group_code}+{prod_type_code}+{prod_code}+{prod_type2_code}+{year_code}+{color_code}")
        
        return jsonify({
            'success': True,
            'std_code': std_code,
            'message': '자사코드가 성공적으로 생성되었습니다.',
            'breakdown': {
                'brand': brand_code,
                'div_type': div_type_code,
                'prod_group': prod_group_code,
                'prod_type': prod_type_code,
                'prod_code': prod_code,
                'prod_type2': prod_type2_code,
                'year': year_code,
                'color': color_code
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ 자사코드 생성 실패: {e}")
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
            codes = Code.get_codes_by_group_name(group_name)
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
        brands = Code.get_codes_by_group_name('브랜드')
        categories = Code.get_codes_by_group_name('품목')
        colors = Code.get_codes_by_group_name('색상')
        div_types = Code.get_codes_by_group_name('구분타입')
        
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
    """품목에 따른 타입 목록 조회 API"""
    try:
        # 개발 환경에서 임시 세션 설정
        if not session.get('member_seq'):
            session['member_seq'] = 1
            session['member_id'] = 'admin'
            session['current_company_id'] = 1
            
        # 해당 품목에 연결된 타입들 조회 (실제로는 모든 타입 반환)
        # 추후 더 정교한 연동 로직 구현 가능
        types = Code.get_codes_by_group_name('타입')
        
        types_data = []
        for type_code in types:
            if hasattr(type_code, 'seq'):
                types_data.append({
                    'seq': type_code.seq,
                    'code': type_code.code,
                    'code_name': type_code.code_name
                })
            else:
                types_data.append(type_code)
        
        return jsonify({
            'success': True,
            'types': types_data
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ 타입 목록 조회 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/api/get-types-by-product-code/<product_code>')
# @login_required  # 개발 환경에서 임시 제거
def api_get_types_by_product_code(product_code):
    """품목 코드별 타입 목록 조회 API"""
    # 개발 환경에서 임시 세션 설정
    if not session.get('member_seq'):
        session['member_seq'] = 1
        session['member_id'] = 'admin'
        session['current_company_id'] = 1
        
    try:
        current_company_id = session.get('current_company_id', 1)
        
        # 품목 코드로 해당 품목의 seq 찾기
        product_code_obj = Code.query.filter_by(
            code=product_code,
            company_id=current_company_id
        ).first()  # CodeGroup 조인 제거
        
        if not product_code_obj:
            return jsonify({'success': False, 'message': '품목을 찾을 수 없습니다'}), 404
        
        # 해당 품목의 하위 타입들을 정렬 순서대로 조회
        types = Code.query.filter_by(
            parent_seq=product_code_obj.seq,
            company_id=current_company_id,
            use_yn='Y'
        ).order_by(Code.sort_order, Code.code).all()
        
        types_list = []
        for type_code in types:
            types_list.append({
                'seq': type_code.seq,
                'code': type_code.code,
                'code_name': type_code.code_name,
                'sort_order': type_code.sort_order
            })
        
        return jsonify({
            'success': True,
            'types': types_list
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ 품목별 타입 조회 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/api/get-types-by-product-seq/<int:product_seq>')
# @login_required  # 개발 환경에서 임시 제거
def api_get_types_by_product_seq(product_seq):
    """품목 SEQ별 타입 목록 조회 API"""
    # 개발 환경에서 임시 세션 설정
    if not session.get('member_seq'):
        session['member_seq'] = 1
        session['member_id'] = 'admin'
        session['current_company_id'] = 1
        
    try:
        # 해당 품목의 하위 타입들을 정렬 순서대로 조회 (use_yn 필터 제거)
        types = Code.query.filter_by(
            parent_seq=product_seq
        ).order_by(Code.sort, Code.code).all()
        
        types_list = []
        for type_code in types:
            types_list.append({
                'seq': type_code.seq,
                'code': type_code.code,
                'code_name': type_code.code_name,
                'sort_order': type_code.sort
            })
        
        return jsonify({
            'success': True,
            'types': types_list
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ 품목별 타입 조회 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/api/get-product-models/<int:product_id>')
def api_get_product_models(product_id):
    """상품의 제품 모델 목록 조회 API"""
    # 개발 환경에서 임시 세션 설정
    if not session.get('member_seq'):
        session['member_seq'] = 1
        session['member_id'] = 'admin'
        session['current_company_id'] = 1
        
    try:
        current_company_id = session.get('current_company_id', 1)
        
        # 상품 존재 확인
        product = Product.query.filter_by(
            id=product_id,
            company_id=current_company_id
        ).first()
        
        if not product:
            return jsonify({'success': False, 'message': '상품을 찾을 수 없습니다'}), 404
        
        # 제품 모델 목록 조회
        product_details = ProductDetail.query.filter_by(
            product_id=product_id
        ).all()
        
        models_list = []
        for detail in product_details:
            # 색상 코드 정보 조회
            color_info = None
            if detail.color_code:
                color_info = Code.query.filter_by(
                    code=detail.color_code
                ).first()  # company_id 필터 제거
            
            models_list.append({
                'id': detail.id,
                'product_id': detail.product_id,
                'color_code': detail.color_code,
                'color_name': color_info.code_name if color_info else detail.color_code,
                'product_model_name': detail.product_name,  # ProductDetail.product_name 사용
                'std_product_code': detail.std_div_prod_code,
                'created_at': detail.created_at.isoformat() if detail.created_at else None
            })
        
        return jsonify({
            'success': True,
            'models': models_list,
            'count': len(models_list)
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ 제품 모델 목록 조회 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500 

@bp.route('/api/get/<int:product_id>')
# @login_required  # 개발 환경에서 임시 제거
def api_get(product_id):
    """상품 상세 조회 API (tbl_Product + tbl_Product_DTL 연동)"""
    # 개발 환경에서 임시 세션 설정
    if not session.get('member_seq'):
        session['member_seq'] = 1
        session['member_id'] = 'admin'
        session['current_company_id'] = 1
        
    try:
        current_company_id = session.get('current_company_id', 1)
        
        # tbl_Product 기본 정보 조회
        product = Product.query.filter_by(
            id=product_id,
            company_id=current_company_id
        ).first()
        
        if not product:
            return jsonify({'success': False, 'message': '상품을 찾을 수 없습니다.'}), 404
        
        # tbl_Product_DTL에서 연결된 제품 모델들 조회 (product_id 기준)
        product_details = ProductDetail.query.filter_by(
            product_id=product_id
        ).order_by(ProductDetail.id).all()
        
        # 기본 상품 정보 (tbl_Product)
        product_data = product.to_dict()
        
        # 제품 모델 정보 (tbl_Product_DTL - 색상별)
        product_models = []
        for detail in product_details:
            # 색상 코드 정보 조회 (code 기준)
            color_code = None
            if detail.color_code:
                # 색상 코드 3자리를 기준으로 CR 그룹에서 찾기 (company_id 제거)
                color_codes = Code.get_codes_by_group_name('CR')
                for code in color_codes:
                    if code.code == detail.color_code:
                        color_code = {
                            'seq': code.seq,
                            'code': code.code,
                            'code_name': code.code_name
                        }
                        break
            
            product_models.append({
                'id': detail.id,  # seq 대신 id 사용
                'std_div_prod_code': detail.std_div_prod_code,
                'product_name': detail.product_name,
                'color_code': detail.color_code,
                'color_code_info': color_code,
                'status': detail.status,
                'use_yn': detail.use_yn,  # 직접 사용
                'brand_code': detail.brand_code,
                'div_type_code': detail.div_type_code,
                'prod_group_code': detail.prod_group_code,
                'prod_type_code': detail.prod_type_code,
                'prod_code': detail.prod_code,
                'prod_type2_code': detail.prod_type2_code,
                'year_code': detail.year_code,
                'additional_price': detail.additional_price,
                'stock_quantity': detail.stock_quantity
            })
        
        # 선택된 코드 정보 (셀렉트박스 selected 처리용)
        selected_codes = {
            'brand_code_seq': product.brand_code_seq,
            'category_code_seq': product.category_code_seq,  # prod_group_code_seq와 매핑
            'type_code_seq': product.type_code_seq,         # prod_type_code_seq와 매핑
            'year_code_seq': product.year_code_seq,
            'div_type_code_seq': product.div_type_code_seq,
        }
        
        # PRD 품목 코드 찾기 (category_code_seq로부터 역추적)
        if product.category_code_seq:
            category_code = Code.query.get(product.category_code_seq)
            if category_code and category_code.parent_seq:
                # 카테고리의 상위가 PRD 그룹인지 확인
                parent_code = Code.query.get(category_code.parent_seq)
                if parent_code and parent_code.code == 'PRD':
                    selected_codes['prod_code_seq'] = product.category_code_seq
        
        # 타입 코드 찾기 (type_code_seq로부터)
        if product.type_code_seq:
            selected_codes['prod_type_code_seq'] = product.type_code_seq
        
        current_app.logger.info(f"✅ 상품 조회 완료: {product.product_name} (모델 {len(product_models)}개)")
        
        return jsonify({
            'success': True,
            'product': product_data,
            'product_models': product_models,
            'selected_codes': selected_codes,
            'total_models': len(product_models)
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ 상품 조회 실패: {e}")
        return jsonify({'success': False, 'message': f'상품 조회 중 오류가 발생했습니다: {str(e)}'}), 500 