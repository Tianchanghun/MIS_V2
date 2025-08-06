#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask 애플리케이션 팩토리
멀티테넌트 시스템 통합
"""

import os
import urllib.parse
from datetime import datetime
from flask import Flask, render_template_string, session, redirect, url_for, g, request, jsonify
from flask_login import LoginManager, login_required, current_user
from flask_session import Session
from redis import Redis
from sqlalchemy import text

# 설정 클래스
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'mis-v2-secret-key-2025'
    
    # 데이터베이스 설정
    DB_PASSWORD = 'mis123!@#'
    DB_PASSWORD_ENCODED = urllib.parse.quote_plus(DB_PASSWORD)
    SQLALCHEMY_DATABASE_URI = f'postgresql://mis_user:{DB_PASSWORD_ENCODED}@localhost:5433/db_mis'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 세션 설정 (Redis 문제로 임시 파일시스템 사용)
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = './flask_session'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'mis_v2_session:'
    
    # Redis 설정 (캐시용)
    REDIS_URL = 'redis://:redis123!@#@localhost:6380/0'  # 암호 포함

# 확장 모듈들
from app.common.models import db, init_db

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '로그인이 필요합니다.'
login_manager.login_message_category = 'info'

def create_app(config_name='development'):
    """Flask 애플리케이션 팩토리"""
    app = Flask(__name__)
    
    # 설정 로드
    app.config.from_object(Config)
    
    # 확장 모듈 초기화
    init_db(app)  # 데이터베이스 초기화
    login_manager.init_app(app)
    
    # 세션 초기화
    Session(app)
    
    # Redis 연결 확인
    redis_client = None
    try:
        # 먼저 암호 없이 시도
        redis_client = Redis(host='localhost', port=6380, db=0)
        redis_client.ping()
        print("✅ Redis 캐시 연결 성공 (포트 6380, 암호 없음)")
    except Exception as e1:
        try:
            # 암호와 함께 시도
            redis_client = Redis(host='localhost', port=6380, db=0, password='redis123!@#')
            redis_client.ping()
            print("✅ Redis 캐시 연결 성공 (포트 6380, 암호 있음)")
        except Exception as e2:
            print(f"⚠️ Redis 연결 실패: {e2}")
            redis_client = None
        
    with app.app_context():
        # 데이터베이스 연결 확인
        try:
            db.session.execute(text('SELECT 1'))
            print("✅ PostgreSQL 데이터베이스 연결 성공")
        except Exception as e:
            print(f"❌ 데이터베이스 연결 실패: {e}")
    
    # 블루프린트 등록
    from app.auth.routes import auth_bp
    from app.batch.routes import batch_bp  # 새로운 배치 모듈
    # 관리자 블루프린트 등록
    from app.admin import admin_bp
    # 고객 관리 블루프린트 등록 (임시)
    from app.customer import customer_bp
    # 사은품 관리 블루프린트 등록 (임시)
    from app.gift import gift_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(batch_bp)  # /batch 프리픽스는 Blueprint에서 설정됨
    app.register_blueprint(admin_bp)  # /admin 프리픽스는 Blueprint에서 설정됨
    app.register_blueprint(customer_bp)
    app.register_blueprint(gift_bp)
    
    # 멀티테넌트 미들웨어 초기화 (블루프린트 등록 후)
    try:
        from app.common.middleware import multi_tenant
        multi_tenant.init_app(app)
        print("🏢 멀티테넌트 미들웨어 초기화 완료")
    except Exception as e:
        print(f"⚠️ 멀티테넌트 미들웨어 초기화 실패: {e}")
        import traceback
        print(f"   상세 오류: {traceback.format_exc()}")
    
    # 배치 스케줄러 초기화
    try:
        from app.services.batch_scheduler import batch_scheduler
        batch_scheduler.init_app(app)
        print("🔧 배치 스케줄러 초기화 완료")
        
        # 개발 환경에서는 수동 시작으로 변경 (안정성을 위해)
        if config_name == 'development':
            print("💡 개발 환경: 배치 스케줄러 수동 시작 모드")
            print("   - /batch 페이지에서 수동으로 시작할 수 있습니다.")
            
    except Exception as e:
        print(f"⚠️ 배치 스케줄러 초기화 실패: {e}")
        import traceback
        print(f"   상세 오류: {traceback.format_exc()}")
    
    # 컨텍스트 프로세서
    @app.context_processor
    def inject_template_vars():
        """템플릿에 전역 변수 주입"""
        context_vars = {
            'app_name': 'MIS v2',
            'app_version': '2.0.0',
            'current_year': datetime.now().year,
        }
        
        # 멀티테넌트 정보 (강화된 방식)
        try:
            from app.common.models import Company, UserCompany
            
            # 현재 활성 회사 (강화된 방식)
            current_company = getattr(g, 'current_company', None)
            user_seq = session.get('member_seq')
            current_company_id = session.get('current_company_id')
            
            print(f"🔍 템플릿 컨텍스트 디버그: user_seq={user_seq}, current_company_id={current_company_id}")
            
            if not current_company and user_seq:
                if current_company_id:
                    # 세션에 저장된 회사 ID로 조회
                    company = Company.query.filter_by(id=current_company_id).first()
                    if company:
                        current_company = {
                            'id': company.id,
                            'company_name': company.company_name,
                            'company_code': company.company_code,
                            'name': company.company_name  # 호환성을 위해 추가
                        }
                        print(f"🏢 세션 회사 조회 성공: {company.company_name}")
                
                if not current_company:
                    # 사용자의 주소속 회사로 설정
                    primary_uc = UserCompany.query.filter_by(
                        user_seq=user_seq, 
                        is_primary=True, 
                        is_active=True
                    ).join(Company).first()
                    
                    if primary_uc:
                        current_company = {
                            'id': primary_uc.company.id,
                            'company_name': primary_uc.company.company_name,
                            'company_code': primary_uc.company.company_code,
                            'name': primary_uc.company.company_name  # 호환성을 위해 추가
                        }
                        # 세션에도 저장
                        session['current_company_id'] = primary_uc.company.id
                        print(f"🏢 주소속 회사 설정: {primary_uc.company.company_name}")
            
            # 기본값 설정
            if not current_company:
                # 기본 회사 설정 (에이원)
                default_company = Company.query.filter_by(company_code='AONE').first()
                if default_company:
                    current_company = {
                        'id': default_company.id,
                        'company_name': default_company.company_name,
                        'company_code': default_company.company_code,
                        'name': default_company.company_name  # 호환성을 위해 추가
                    }
                    print(f"🏢 기본 회사 설정: {default_company.company_name}")
                else:
                    current_company = {
                        'id': 1, 
                        'company_name': '에이원', 
                        'company_code': 'AONE',
                        'name': '에이원'  # 호환성을 위해 추가
                    }
                    print("🏢 하드코딩 기본 회사 설정: 에이원")
            
            context_vars['current_company'] = current_company
            
            # 사용자가 접근 가능한 회사 목록 (강화된 방식)
            if user_seq:
                # 사용자-회사 관계 조회
                user_companies = UserCompany.query.filter_by(
                    user_seq=user_seq, 
                    is_active=True
                ).join(Company).all()
                
                context_vars['user_companies'] = user_companies
                print(f"🏢 멀티테넌트: user_companies 개수: {len(user_companies)}")
                
                for uc in user_companies:
                    print(f"  - {uc.company.company_name} (ID: {uc.company_id}, 주속: {uc.is_primary})")
                
                # 회사 전환 UI 표시 여부 결정
                context_vars['show_company_switcher'] = len(user_companies) > 1
                print(f"🔄 회사 전환 UI 표시: {len(user_companies) > 1}")
                
            else:
                context_vars['user_companies'] = []
                context_vars['show_company_switcher'] = False
                print("⚠️ 로그인되지 않은 사용자 - 멀티테넌트 정보 없음")
                
        except Exception as e:
            print(f"❌ 템플릿 컨텍스트 프로세서 오류: {e}")
            import traceback
            print(f"   상세 오류: {traceback.format_exc()}")
            
            # 오류 시 기본값 설정
            context_vars['current_company'] = {'id': 1, 'company_name': '에이원', 'company_code': 'AONE'}
            context_vars['user_companies'] = []
            context_vars['show_company_switcher'] = False
        
        return context_vars
    
    # 에러 핸들러
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>페이지를 찾을 수 없습니다</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-5">
                <div class="text-center">
                    <h1 class="display-1">404</h1>
                    <p class="fs-3"><span class="text-danger">죄송합니다!</span> 페이지를 찾을 수 없습니다.</p>
                    <p class="lead">요청하신 페이지가 존재하지 않습니다.</p>
                    <a href="{{ url_for('index') }}" class="btn btn-primary">홈으로 돌아가기</a>
                </div>
            </div>
        </body>
        </html>
        """), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>서버 오류</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-5">
                <div class="text-center">
                    <h1 class="display-1">500</h1>
                    <p class="fs-3"><span class="text-danger">죄송합니다!</span> 서버 내부 오류가 발생했습니다.</p>
                    <p class="lead">잠시 후 다시 시도해 주세요.</p>
                    <a href="{{ url_for('index') }}" class="btn btn-primary">홈으로 돌아가기</a>
                </div>
            </div>
        </body>
        </html>
        """), 500
    
    # 메인 대시보드
    @app.route('/')
    @login_required
    def index():
        """메인 대시보드"""
        try:
            # 시스템 상태 확인
            redis_client = None
            try:
                # 먼저 암호 없이 시도
                redis_client = Redis(host='localhost', port=6380, db=0)
                redis_client.ping()
            except Exception as e1:
                try:
                    # 암호와 함께 시도
                    redis_client = Redis(host='localhost', port=6380, db=0, password='redis123!@#')
                    redis_client.ping()
                except Exception as e2:
                    redis_client = None
            
            # 배치 스케줄러 상태 확인
            batch_status = "준비중"
            batch_jobs_count = 0
            try:
                from app.services.batch_scheduler import batch_scheduler
                if batch_scheduler.is_running:
                    batch_status = "실행중"
                    batch_jobs_count = len(batch_scheduler.get_jobs())
                else:
                    batch_status = "중지됨"
            except:
                pass
            
            # 사은품 분류 상태 확인
            gift_status = "준비중"
            try:
                from app.services.gift_classifier import GiftClassifier
                gift_status = "활성"
            except:
                pass
            
            return render_template_string("""
            {% extends "base.html" %}
            
            {% block title %}MIS v2 대시보드{% endblock %}
            
            {% block content %}
            <div class="container-fluid">
                <!-- 회사 정보 표시 -->
                <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
                    <h1 class="h2">📊 {{ current_company.company_name }} MIS v2 대시보드</h1>
                    <div class="btn-toolbar mb-2 mb-md-0">
                        {% if user_companies|length > 1 %}
                            <div class="dropdown me-2">
                                <button class="btn btn-outline-primary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                                    <i class="bi bi-building"></i> {{ current_company.company_name }}
                                </button>
                                <ul class="dropdown-menu">
                                    {% for uc in user_companies %}
                                        <li><a class="dropdown-item" href="#" onclick="switchCompany({{ uc.company_id }})">
                                            {{ uc.company.company_name }}
                                        </a></li>
                                    {% endfor %}
                                </ul>
                            </div>
                        {% endif %}
                        <div class="btn-group me-2">
                            <small class="text-muted">{{ current_time }}</small>
                        </div>
                    </div>
                </div>
                
                <!-- 핵심 메뉴 카드 -->
                <div class="row mb-4">
                    <div class="col-md-4">
                        <div class="card h-100">
                            <div class="card-header bg-primary text-white">
                                <h5><i class="bi bi-clock-history"></i> 배치 관리</h5>
                            </div>
                            <div class="card-body">
                                <p class="card-text">ERPia 자동 데이터 수집 및 배치 작업 관리</p>
                                <div class="list-group list-group-flush">
                                    <a href="/batch" class="list-group-item list-group-item-action">
                                        <i class="bi bi-speedometer2"></i> 배치 대시보드
                                    </a>
                                    <a href="/batch/jobs" class="list-group-item list-group-item-action">
                                        <i class="bi bi-list-task"></i> 배치 작업 관리
                                    </a>
                                    <a href="/batch/settings" class="list-group-item list-group-item-action">
                                        <i class="bi bi-gear"></i> 배치 설정
                                    </a>
                                </div>
                                <div class="mt-3">
                                    <small class="text-muted">상태: <span class="badge bg-{{ 'success' if batch_status == '실행중' else 'warning' }}">{{ batch_status }}</span></small><br>
                                    <small class="text-muted">등록된 작업: {{ batch_jobs_count }}개</small>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-4">
                        <div class="card h-100">
                            <div class="card-header bg-success text-white">
                                <h5><i class="bi bi-gift"></i> 사은품 관리</h5>
                            </div>
                            <div class="card-body">
                                <p class="card-text">사은품 자동 분류 및 매출 정확도 향상</p>
                                <div class="list-group list-group-flush">
                                    <span class="list-group-item list-group-item-action text-muted">
                                        <i class="bi bi-graph-up"></i> 사은품 분석 (준비중)
                                    </span>
                                    <span class="list-group-item list-group-item-action text-muted">
                                        <i class="bi bi-funnel"></i> 분류 규칙 관리 (준비중)
                                    </span>
                                    <span class="list-group-item list-group-item-action text-muted">
                                        <i class="bi bi-bar-chart"></i> 분류 통계 (준비중)
                                    </span>
                                </div>
                                <div class="mt-3">
                                    <small class="text-muted">상태: <span class="badge bg-success">{{ gift_status }}</span></small>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-4">
                        <div class="card h-100">
                            <div class="card-header bg-info text-white">
                                <h5><i class="bi bi-gear"></i> 관리자</h5>
                            </div>
                            <div class="card-body">
                                <p class="card-text">시스템 설정 및 사용자 관리</p>
                                <div class="list-group list-group-flush">
                                    <a href="{{ url_for('admin.user_management') }}" class="list-group-item list-group-item-action">
                                        <i class="bi bi-people"></i> 사용자 관리
                                    </a>
                                    <a href="{{ url_for('admin.department_management') }}" class="list-group-item list-group-item-action">
                                        <i class="bi bi-building"></i> 부서 관리
                                    </a>
                                    <a href="{{ url_for('admin.code_management') }}" class="list-group-item list-group-item-action">
                                        <i class="bi bi-code-square"></i> 코드 관리
                                    </a>
                                    <a href="{{ url_for('admin.menu_management') }}" class="list-group-item list-group-item-action">
                                        <i class="bi bi-list"></i> 메뉴 관리
                                    </a>
                                    <a href="{{ url_for('admin.brand_management') }}" class="list-group-item list-group-item-action">
                                        <i class="bi bi-award"></i> 브랜드 관리
                                    </a>
                                    <a href="{{ url_for('admin.permissions') }}" class="list-group-item list-group-item-action">
                                        <i class="bi bi-shield-check"></i> 권한 관리
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="bi bi-people"></i> 고객 관리</h5>
                            </div>
                            <div class="card-body">
                                <p class="card-text">고객 서비스 및 A/S 관리</p>
                                <div class="list-group list-group-flush">
                                    <span class="list-group-item list-group-item-action text-muted">
                                        <i class="bi bi-arrow-repeat"></i> 무상 교환 접수 (준비중)
                                    </span>
                                    <span class="list-group-item list-group-item-action text-muted">
                                        <i class="bi bi-search"></i> 시리얼 검색 (준비중)
                                    </span>
                                    <span class="list-group-item list-group-item-action text-muted">
                                        <i class="bi bi-tools"></i> A/S 접수 내역 (준비중)
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="bi bi-activity"></i> 시스템 상태</h5>
                            </div>
                            <div class="card-body">
                                <div class="row text-center">
                                    <div class="col-md-6 mb-3">
                                        <div class="card text-white bg-success">
                                            <div class="card-body">
                                                <h6>데이터베이스</h6>
                                                <p><i class="bi bi-check-circle"></i> 정상</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-6 mb-3">
                                        <div class="card text-white bg-{{ 'success' if redis_client else 'warning' }}">
                                            <div class="card-body">
                                                <h6>Redis 캐시</h6>
                                                <p><i class="bi bi-{{ 'check-circle' if redis_client else 'exclamation-triangle' }}"></i> {{ '정상' if redis_client else '파일캐시' }}</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="card text-white bg-{{ 'success' if batch_status == '실행중' else 'warning' }}">
                                            <div class="card-body">
                                                <h6>배치 시스템</h6>
                                                <p><i class="bi bi-clock"></i> {{ batch_status }}</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="card text-white bg-success">
                                            <div class="card-body">
                                                <h6>사은품 분류</h6>
                                                <p><i class="bi bi-gift"></i> {{ gift_status }}</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <script>
            async function switchCompany(companyId) {
                try {
                    const response = await fetch('/api/switch-company', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            company_id: companyId
                        })
                    });
                    
                    if (response.ok) {
                        window.location.reload();
                    } else {
                        alert('회사 전환에 실패했습니다.');
                    }
                } catch (error) {
                    alert('회사 전환 중 오류가 발생했습니다.');
                }
            }
            </script>
            {% endblock %}
            """, 
            current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            redis_client=redis_client,
            batch_status=batch_status,
            batch_jobs_count=batch_jobs_count,
            gift_status=gift_status
            )
        
        except Exception as e:
            print(f"Dashboard error: {e}")
            return f"Dashboard 로딩 중 오류: {e}", 500
    
    # 회사 전환 API
    @app.route('/api/switch-company', methods=['POST'])
    @login_required
    def switch_company():
        """회사 전환 API"""
        try:
            # JSON과 Form data 둘 다 처리
            if request.is_json:
                data = request.get_json()
                company_id = data.get('company_id')
            else:
                company_id = request.form.get('company_id')
            
            if not company_id:
                return jsonify({'success': False, 'message': '회사 ID가 필요합니다.'}), 400
            
            # 접근 권한 확인
            user_id = session.get('member_seq')
            from app.common.middleware import multi_tenant
            
            if multi_tenant.has_company_access(user_id, company_id):
                session['current_company_id'] = company_id
                
                # 접근 로그
                multi_tenant.log_access('SWITCH_COMPANY', resource_id=str(company_id))
                
                return jsonify({'success': True, 'message': '회사가 전환되었습니다.'})
            else:
                return jsonify({'success': False, 'message': '해당 회사에 접근 권한이 없습니다.'}), 403
                
        except Exception as e:
            return jsonify({'success': False, 'message': f'오류: {e}'}), 500
    
    @app.route('/health')
    def health():
        """헬스 체크 엔드포인트"""
        health_info = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0'
        }
        
        # 배치 스케줄러 상태 추가
        try:
            from app.services.batch_scheduler import batch_scheduler
            health_info['batch_scheduler'] = {
                'running': batch_scheduler.is_running,
                'jobs_count': len(batch_scheduler.get_jobs())
            }
        except:
            health_info['batch_scheduler'] = {'running': False, 'jobs_count': 0}
            
        return health_info
    
    return app

# Flask-Login 사용자 로더
@login_manager.user_loader
def load_user(user_id):
    """사용자 로드"""
    try:
        from app.common.models import User
        return User.query.filter_by(seq=int(user_id)).first()
    except:
        return None

def init_db(app):
    """데이터베이스 초기화"""
    from app.common.models import db, init_db as init_models, create_default_data
    
    db.init_app(app)
    
    with app.app_context():
        try:
            # 테이블 생성
            init_models()
            
            # 기본 데이터 생성
            create_default_data()
            
        except Exception as e:
            print(f"❌ 데이터베이스 초기화 오류: {e}")
            import traceback
            print(f"   상세 오류: {traceback.format_exc()}") 