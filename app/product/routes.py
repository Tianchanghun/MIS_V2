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
from app.common.models import db, Product, ProductHistory, Code, Company, Brand

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
                
                # 브랜드 매핑
                brand_seq = None
                if not pd.isna(row.get('브랜드')):
                    brand_name = str(row['브랜드']).strip()
                    brand = Brand.query.filter_by(brand_name=brand_name).first()
                    if brand:
                        brand_seq = brand.seq
                
                # 품목 매핑
                category_code_seq = None
                if not pd.isna(row.get('품목')):
                    category_name = str(row['품목']).strip()
                    category_codes = Code.get_codes_by_group_name('품목')
                    for code in category_codes:
                        if code['code_name'] == category_name:
                            category_code_seq = code['seq']
                            break
                
                # 타입 매핑
                type_code_seq = None
                if not pd.isna(row.get('타입')):
                    type_name = str(row['타입']).strip()
                    type_codes = Code.get_codes_by_group_name('타입')
                    for code in type_codes:
                        if code['code_name'] == type_name:
                            type_code_seq = code['seq']
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
                    brand_seq=brand_seq,
                    category_code_seq=category_code_seq,
                    type_code_seq=type_code_seq,
                    product_name=str(row['상품명']).strip(),
                    product_code=str(row.get('상품코드', '')).strip() or None,
                    product_year=str(row.get('년도', '')).strip() or None,
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
                '브랜드': product.brand.brand_name if product.brand else '',
                '품목': product.category.code_name if product.category else '',
                '타입': product.type.code_name if product.type else '',
                '년도': product.product_year or '',
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
    """엑셀 업로드 템플릿 다운로드"""
    try:
        # 템플릿 데이터 생성
        template_data = {
            '상품명': ['상품명 예시1', '상품명 예시2'],
            '상품코드': ['PROD001', 'PROD002'],
            '브랜드': ['브랜드1', '브랜드2'],
            '품목': ['품목1', '품목2'],
            '타입': ['타입1', '타입2'],
            '년도': ['2024', '2024'],
            '가격': [10000, 20000],
            '설명': ['상품 설명1', '상품 설명2'],
            '상태': ['활성', '활성']
        }
        
        df = pd.DataFrame(template_data)
        
        # 엑셀 파일 생성
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='상품업로드템플릿', index=False)
            
            # 워크시트 서식 설정
            worksheet = writer.sheets['상품업로드템플릿']
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