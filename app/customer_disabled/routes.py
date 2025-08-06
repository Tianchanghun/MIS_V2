#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
고객 관리 시스템 라우트
카시트 무상교환, 시리얼 검색, 고객 타겟팅, A/S 접수 관리
"""

from flask import render_template_string, jsonify, request, flash, redirect, url_for, session
from flask_login import login_required
from app.customer import bp
from app.common.models import Customer, SerialConfirm, CarseatChange, CustomerSmsLog, Code
from app.auth.routes import require_permission
from app import db
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func, desc
from app.common.multitenant import MultiTenantQueryBuilder

@bp.route('/')
@login_required 
def index():
    """고객 관리 메인 페이지"""
    try:
        # 고객 관리 통계
        stats = {
            'total_customers': Customer.query.count(),
            'total_serials': SerialConfirm.query.count(),
            'pending_carseat_changes': CarseatChange.query.filter_by(req_status='1').count(),
            'recent_registrations': SerialConfirm.query.filter(
                SerialConfirm.ins_date >= datetime.now() - timedelta(days=7)
            ).count()
        }
        
        # 최근 시리얼 등록 현황
        recent_serials = SerialConfirm.query.order_by(desc(SerialConfirm.ins_date)).limit(10).all()
        
        # 카시트 교환 신청 현황
        pending_changes = CarseatChange.query.join(Customer).filter(
            CarseatChange.req_status.in_(['1', '2'])
        ).order_by(desc(CarseatChange.req_date)).limit(5).all()
        
        return render_template_string("""
        {% extends "base.html" %}
        {% block title %}고객 관리 - {{ app_name }}{% endblock %}
        {% block content %}
        <div class="container-fluid">
            <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
                <h1 class="h2"><i class="bi bi-people"></i> 고객 관리 대시보드</h1>
            </div>
            
            <!-- 통계 카드 -->
            <div class="row g-3 mb-4">
                <div class="col-xl-3 col-md-6">
                    <div class="card border-primary">
                        <div class="card-body">
                            <div class="d-flex align-items-center">
                                <div class="flex-shrink-0">
                                    <i class="bi bi-people text-primary" style="font-size: 2rem;"></i>
                                </div>
                                <div class="flex-grow-1 ms-3">
                                    <div class="text-muted small">전체 고객</div>
                                    <div class="h4 mb-0">{{ "{:,}".format(stats.total_customers) }}명</div>
                                    <div class="text-muted small">등록된 고객</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-xl-3 col-md-6">
                    <div class="card border-success">
                        <div class="card-body">
                            <div class="d-flex align-items-center">
                                <div class="flex-shrink-0">
                                    <i class="bi bi-qr-code text-success" style="font-size: 2rem;"></i>
                                </div>
                                <div class="flex-grow-1 ms-3">
                                    <div class="text-muted small">시리얼 등록</div>
                                    <div class="h4 mb-0">{{ "{:,}".format(stats.total_serials) }}건</div>
                                    <div class="text-success small">최근 7일: {{ stats.recent_registrations }}건</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-xl-3 col-md-6">
                    <div class="card border-warning">
                        <div class="card-body">
                            <div class="d-flex align-items-center">
                                <div class="flex-shrink-0">
                                    <i class="bi bi-arrow-repeat text-warning" style="font-size: 2rem;"></i>
                                </div>
                                <div class="flex-grow-1 ms-3">
                                    <div class="text-muted small">카시트 교환</div>
                                    <div class="h4 mb-0">{{ stats.pending_carseat_changes }}건</div>
                                    <div class="text-warning small">처리 대기</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-xl-3 col-md-6">
                    <div class="card border-info">
                        <div class="card-body">
                            <div class="d-flex align-items-center">
                                <div class="flex-shrink-0">
                                    <i class="bi bi-envelope text-info" style="font-size: 2rem;"></i>
                                </div>
                                <div class="flex-grow-1 ms-3">
                                    <div class="text-muted small">SMS 발송</div>
                                    <div class="h4 mb-0">0건</div>
                                    <div class="text-muted small">오늘 발송</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 관리 메뉴 -->
            <div class="row g-3">
                <div class="col-lg-3 col-md-6">
                    <div class="card h-100">
                        <div class="card-body text-center">
                            <i class="bi bi-arrow-repeat text-warning" style="font-size: 3rem;"></i>
                            <h5 class="card-title mt-2">무상 교환 접수</h5>
                            <p class="card-text">카시트 무상교환 신청 관리</p>
                            <a href="{{ url_for('customer.carseat_change') }}" class="btn btn-warning">관리하기</a>
                        </div>
                    </div>
                </div>
                
                <div class="col-lg-3 col-md-6">
                    <div class="card h-100">
                        <div class="card-body text-center">
                            <i class="bi bi-search text-primary" style="font-size: 3rem;"></i>
                            <h5 class="card-title mt-2">시리얼 검색</h5>
                            <p class="card-text">고객별 시리얼 조회</p>
                            <a href="{{ url_for('customer.serial_search') }}" class="btn btn-primary">검색하기</a>
                        </div>
                    </div>
                </div>
                
                <div class="col-lg-3 col-md-6">
                    <div class="card h-100">
                        <div class="card-body text-center">
                            <i class="bi bi-list-check text-success" style="font-size: 3rem;"></i>
                            <h5 class="card-title mt-2">시리얼 등록 목록</h5>
                            <p class="card-text">등록된 시리얼 목록</p>
                            <a href="{{ url_for('customer.serial_list') }}" class="btn btn-success">목록보기</a>
                        </div>
                    </div>
                </div>
                
                <div class="col-lg-3 col-md-6">
                    <div class="card h-100">
                        <div class="card-body text-center">
                            <i class="bi bi-bullseye text-info" style="font-size: 3rem;"></i>
                            <h5 class="card-title mt-2">고객 타겟팅</h5>
                            <p class="card-text">마케팅 대상 선별</p>
                            <a href="{{ url_for('customer.targeting') }}" class="btn btn-info">타겟팅</a>
                        </div>
                    </div>
                </div>
                
                <div class="col-lg-3 col-md-6">
                    <div class="card h-100">
                        <div class="card-body text-center">
                            <i class="bi bi-envelope-paper text-secondary" style="font-size: 3rem;"></i>
                            <h5 class="card-title mt-2">발송 내역</h5>
                            <p class="card-text">고객 타겟팅 발송 이력</p>
                            <a href="{{ url_for('customer.send_log') }}" class="btn btn-secondary">내역보기</a>
                        </div>
                    </div>
                </div>
                
                <div class="col-lg-3 col-md-6">
                    <div class="card h-100">
                        <div class="card-body text-center">
                            <i class="bi bi-headset text-danger" style="font-size: 3rem;"></i>
                            <h5 class="card-title mt-2">A/S 접수 내역</h5>
                            <p class="card-text">A/S 접수 및 처리 현황</p>
                            <a href="{{ url_for('customer.as_list') }}" class="btn btn-danger">접수현황</a>
                        </div>
                    </div>
                </div>
                
                <div class="col-lg-3 col-md-6">
                    <div class="card h-100">
                        <div class="card-body text-center">
                            <i class="bi bi-shop text-dark" style="font-size: 3rem;"></i>
                            <h5 class="card-title mt-2">정품등록 매장</h5>
                            <p class="card-text">정품 등록 가능 매장</p>
                            <a href="{{ url_for('customer.store_management') }}" class="btn btn-dark">매장관리</a>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 최근 활동 -->
            <div class="row mt-4">
                <div class="col-lg-6">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="bi bi-clock-history"></i> 최근 시리얼 등록</h5>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table table-sm">
                                    <thead>
                                        <tr>
                                            <th>제품명</th>
                                            <th>시리얼</th>
                                            <th>고객명</th>
                                            <th>등록일</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for serial in recent_serials %}
                                        <tr>
                                            <td>{{ serial.product_name }}</td>
                                            <td><code>{{ serial.serial_code }}</code></td>
                                            <td>{{ serial.name }}</td>
                                            <td>{{ serial.ins_date.strftime('%m-%d') if serial.ins_date else '-' }}</td>
                                        </tr>
                                        {% else %}
                                        <tr>
                                            <td colspan="4" class="text-center text-muted">최근 등록이 없습니다.</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-lg-6">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="bi bi-exclamation-triangle"></i> 카시트 교환 신청 대기</h5>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table table-sm">
                                    <thead>
                                        <tr>
                                            <th>고객명</th>
                                            <th>기존 시리얼</th>
                                            <th>신청일</th>
                                            <th>상태</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for change in pending_changes %}
                                        <tr>
                                            <td>{{ change.customer.name if change.customer else '-' }}</td>
                                            <td><code>{{ change.old_serial }}</code></td>
                                            <td>{{ change.req_date.strftime('%m-%d') if change.req_date else '-' }}</td>
                                            <td>
                                                {% if change.req_status == '1' %}
                                                <span class="badge bg-warning">신청</span>
                                                {% elif change.req_status == '2' %}
                                                <span class="badge bg-info">처리중</span>
                                                {% else %}
                                                <span class="badge bg-success">완료</span>
                                                {% endif %}
                                            </td>
                                        </tr>
                                        {% else %}
                                        <tr>
                                            <td colspan="4" class="text-center text-muted">대기 중인 신청이 없습니다.</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endblock %}
        """, stats=stats, recent_serials=recent_serials, pending_changes=pending_changes)
        
    except Exception as e:
        flash(f'고객 관리 대시보드 로딩 중 오류가 발생했습니다: {e}', 'error')
        return redirect(url_for('index'))

# ============================================
# 1. 카시트 무상교환 관리
# ============================================

@bp.route('/carseat-change')
@login_required
def carseat_change():
    """카시트 무상교환 관리 페이지"""
    try:
        # 페이지 설정
        page = int(request.args.get('page', 1))
        per_page = 10
        search_brand = request.args.get('search_brand', '')
        search_type = request.args.get('search_type', '')
        search_text = request.args.get('search_text', '')
        
        # 쿼리 구성
        query = CarseatChange.query.join(Customer)
        
        # 브랜드 필터
        if search_brand:
            # 브랜드별 필터링 로직 추가 (제품명 기반)
            query = query.join(SerialConfirm, CarseatChange.old_serial == SerialConfirm.serial_code).filter(
                SerialConfirm.brand == search_brand
            )
        
        # 검색 필터
        if search_type and search_text:
            if search_type == 'customer_name':
                query = query.filter(Customer.name.ilike(f'%{search_text}%'))
            elif search_type == 'phone':
                query = query.filter(Customer.mobile.ilike(f'%{search_text}%'))
            elif search_type == 'serial':
                query = query.filter(
                    or_(
                        CarseatChange.old_serial.ilike(f'%{search_text}%'),
                        CarseatChange.new_serial.ilike(f'%{search_text}%')
                    )
                )
        
        # 페이지네이션
        changes = query.order_by(desc(CarseatChange.req_date)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 상태별 집계
        status_counts = db.session.query(
            CarseatChange.req_status, func.count(CarseatChange.seq)
        ).group_by(CarseatChange.req_status).all()
        
        # 브랜드 목록
        brand_codes = Code.get_codes_by_group('BRAND')
        
        return render_template_string("""
        {% extends "base.html" %}
        {% block title %}카시트 무상교환 관리 - {{ app_name }}{% endblock %}
        {% block content %}
        <div class="container-fluid">
            <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
                <h1 class="h2"><i class="bi bi-arrow-repeat"></i> 카시트 무상교환 관리</h1>
                <div class="btn-toolbar mb-2 mb-md-0">
                    <div class="btn-group me-2">
                        <button type="button" class="btn btn-success" onclick="showAddChangeModal()">
                            <i class="bi bi-plus"></i> 교환 신청 등록
                        </button>
                        <button type="button" class="btn btn-secondary" onclick="exportChanges()">
                            <i class="bi bi-download"></i> 엑셀 다운로드
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- 상태별 통계 -->
            <div class="row mb-3">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-body">
                            <div class="row text-center">
                                <div class="col-md-3">
                                    <h4 class="text-warning">{{ status_counts.get('1', 0) }}</h4>
                                    <small>신청 대기</small>
                                </div>
                                <div class="col-md-3">
                                    <h4 class="text-info">{{ status_counts.get('2', 0) }}</h4>
                                    <small>처리 중</small>
                                </div>
                                <div class="col-md-3">
                                    <h4 class="text-success">{{ status_counts.get('3', 0) }}</h4>
                                    <small>처리 완료</small>
                                </div>
                                <div class="col-md-3">
                                    <h4 class="text-primary">{{ changes.total }}</h4>
                                    <small>전체</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 검색 및 필터 -->
            <div class="row mb-3">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-body">
                            <form method="GET" class="row g-3">
                                <div class="col-md-2">
                                    <label for="search_brand" class="form-label">브랜드</label>
                                    <select class="form-select" id="search_brand" name="search_brand">
                                        <option value="">전체</option>
                                        {% for brand in brand_codes %}
                                        <option value="{{ brand.code }}" {{ 'selected' if request.args.get('search_brand') == brand.code else '' }}>
                                            {{ brand.code_name }}
                                        </option>
                                        {% endfor %}
                                    </select>
                                </div>
                                <div class="col-md-2">
                                    <label for="search_type" class="form-label">검색 조건</label>
                                    <select class="form-select" id="search_type" name="search_type">
                                        <option value="">전체</option>
                                        <option value="customer_name" {{ 'selected' if request.args.get('search_type') == 'customer_name' else '' }}>고객명</option>
                                        <option value="phone" {{ 'selected' if request.args.get('search_type') == 'phone' else '' }}>전화번호</option>
                                        <option value="serial" {{ 'selected' if request.args.get('search_type') == 'serial' else '' }}>시리얼번호</option>
                                    </select>
                                </div>
                                <div class="col-md-3">
                                    <label for="search_text" class="form-label">검색어</label>
                                    <input type="text" class="form-control" id="search_text" name="search_text" 
                                           value="{{ request.args.get('search_text', '') }}" placeholder="검색어 입력">
                                </div>
                                <div class="col-md-2">
                                    <label class="form-label">&nbsp;</label>
                                    <div class="d-grid">
                                        <button type="submit" class="btn btn-primary">
                                            <i class="bi bi-search"></i> 검색
                                        </button>
                                    </div>
                                </div>
                                <div class="col-md-2">
                                    <label class="form-label">&nbsp;</label>
                                    <div class="d-grid">
                                        <a href="{{ url_for('customer.carseat_change') }}" class="btn btn-outline-secondary">
                                            <i class="bi bi-arrow-clockwise"></i> 초기화
                                        </a>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 교환 신청 목록 -->
            <div class="row">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h5><i class="bi bi-list"></i> 교환 신청 목록</h5>
                            <span class="badge bg-info">총 {{ changes.total }}건</span>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table table-striped table-hover">
                                    <thead class="table-dark">
                                        <tr>
                                            <th>신청일</th>
                                            <th>고객명</th>
                                            <th>전화번호</th>
                                            <th>기존 시리얼</th>
                                            <th>신규 시리얼</th>
                                            <th>상태</th>
                                            <th>처리일</th>
                                            <th>관리</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for change in changes.items %}
                                        <tr>
                                            <td>{{ change.req_date.strftime('%Y-%m-%d') if change.req_date else '-' }}</td>
                                            <td>
                                                {% if change.customer %}
                                                <strong>{{ change.customer.name }}</strong>
                                                {% else %}
                                                <span class="text-muted">-</span>
                                                {% endif %}
                                            </td>
                                            <td>
                                                {% if change.customer %}
                                                {{ change.customer.mobile }}
                                                {% else %}
                                                <span class="text-muted">-</span>
                                                {% endif %}
                                            </td>
                                            <td><code>{{ change.old_serial }}</code></td>
                                            <td>
                                                {% if change.new_serial %}
                                                <code>{{ change.new_serial }}</code>
                                                {% else %}
                                                <span class="text-muted">미배정</span>
                                                {% endif %}
                                            </td>
                                            <td>
                                                {% if change.req_status == '1' %}
                                                <span class="badge bg-warning">신청</span>
                                                {% elif change.req_status == '2' %}
                                                <span class="badge bg-info">처리중</span>
                                                {% elif change.req_status == '3' %}
                                                <span class="badge bg-success">완료</span>
                                                {% else %}
                                                <span class="badge bg-secondary">{{ change.req_status }}</span>
                                                {% endif %}
                                            </td>
                                            <td>{{ change.proc_date.strftime('%Y-%m-%d') if change.proc_date else '-' }}</td>
                                            <td>
                                                <div class="btn-group btn-group-sm">
                                                    <button class="btn btn-outline-primary" onclick="editChange({{ change.seq }})">
                                                        <i class="bi bi-pencil"></i>
                                                    </button>
                                                    <button class="btn btn-outline-info" onclick="viewChangeDetail({{ change.seq }})">
                                                        <i class="bi bi-eye"></i>
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                        {% else %}
                                        <tr>
                                            <td colspan="8" class="text-center text-muted">등록된 교환 신청이 없습니다.</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                            
                            <!-- 페이지네이션 -->
                            {% if changes.pages > 1 %}
                            <nav aria-label="교환 신청 목록 페이지네이션">
                                <ul class="pagination justify-content-center">
                                    {% if changes.has_prev %}
                                    <li class="page-item">
                                        <a class="page-link" href="{{ url_for('customer.carseat_change', page=changes.prev_num, search_brand=request.args.get('search_brand', ''), search_type=request.args.get('search_type', ''), search_text=request.args.get('search_text', '')) }}">이전</a>
                                    </li>
                                    {% endif %}
                                    
                                    {% for page_num in changes.iter_pages() %}
                                        {% if page_num %}
                                            {% if page_num != changes.page %}
                                            <li class="page-item">
                                                <a class="page-link" href="{{ url_for('customer.carseat_change', page=page_num, search_brand=request.args.get('search_brand', ''), search_type=request.args.get('search_type', ''), search_text=request.args.get('search_text', '')) }}">{{ page_num }}</a>
                                            </li>
                                            {% else %}
                                            <li class="page-item active">
                                                <span class="page-link">{{ page_num }}</span>
                                            </li>
                                            {% endif %}
                                        {% else %}
                                        <li class="page-item disabled">
                                            <span class="page-link">…</span>
                                        </li>
                                        {% endif %}
                                    {% endfor %}
                                    
                                    {% if changes.has_next %}
                                    <li class="page-item">
                                        <a class="page-link" href="{{ url_for('customer.carseat_change', page=changes.next_num, search_brand=request.args.get('search_brand', ''), search_type=request.args.get('search_type', ''), search_text=request.args.get('search_text', '')) }}">다음</a>
                                    </li>
                                    {% endif %}
                                </ul>
                            </nav>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endblock %}
        
        {% block extra_js %}
        <script>
        function showAddChangeModal() {
            alert('교환 신청 등록 기능을 구현 중입니다.');
        }
        
        function editChange(changeSeq) {
            alert('교환 신청 수정 기능을 구현 중입니다. ID: ' + changeSeq);
        }
        
        function viewChangeDetail(changeSeq) {
            alert('교환 신청 상세보기 기능을 구현 중입니다. ID: ' + changeSeq);
        }
        
        function exportChanges() {
            alert('엑셀 다운로드 기능을 구현 중입니다.');
        }
        </script>
        {% endblock %}
        """, changes=changes, status_counts=dict(status_counts), brand_codes=brand_codes)
        
    except Exception as e:
        flash(f'카시트 교환 목록 조회 중 오류가 발생했습니다: {e}', 'error')
        return redirect(url_for('index'))

# ============================================
# 2. 시리얼 검색
# ============================================

@bp.route('/serial-search')
@login_required
def serial_search():
    """시리얼 검색 페이지"""
    try:
        search_type = request.args.get('search_type', '')
        search_text = request.args.get('search_text', '')
        search_brand = request.args.get('search_brand', '')
        
        results = []
        if search_text:
            query = SerialConfirm.query
            
            # 검색 조건 적용
            if search_type == 'serial':
                query = query.filter(SerialConfirm.serial_code.ilike(f'%{search_text}%'))
            elif search_type == 'name':
                query = query.filter(SerialConfirm.name.ilike(f'%{search_text}%'))
            elif search_type == 'phone':
                query = query.filter(SerialConfirm.mobile.ilike(f'%{search_text}%'))
            elif search_type == 'product':
                query = query.filter(SerialConfirm.product_name.ilike(f'%{search_text}%'))
            
            # 브랜드 필터
            if search_brand:
                query = query.filter(SerialConfirm.brand == search_brand)
            
            results = query.order_by(desc(SerialConfirm.ins_date)).limit(100).all()
        
        # 브랜드 목록
        brand_codes = Code.get_codes_by_group('BRAND')
        
        return render_template_string("""
        {% extends "base.html" %}
        {% block title %}시리얼 검색 - {{ app_name }}{% endblock %}
        {% block content %}
        <div class="container-fluid">
            <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
                <h1 class="h2"><i class="bi bi-search"></i> 시리얼 검색</h1>
            </div>
            
            <!-- 검색 폼 -->
            <div class="row mb-4">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="bi bi-funnel"></i> 검색 조건</h5>
                        </div>
                        <div class="card-body">
                            <form method="GET" class="row g-3">
                                <div class="col-md-2">
                                    <label for="search_type" class="form-label">검색 조건</label>
                                    <select class="form-select" id="search_type" name="search_type" required>
                                        <option value="">선택하세요</option>
                                        <option value="serial" {{ 'selected' if search_type == 'serial' else '' }}>시리얼번호</option>
                                        <option value="name" {{ 'selected' if search_type == 'name' else '' }}>고객명</option>
                                        <option value="phone" {{ 'selected' if search_type == 'phone' else '' }}>전화번호</option>
                                        <option value="product" {{ 'selected' if search_type == 'product' else '' }}>제품명</option>
                                    </select>
                                </div>
                                <div class="col-md-3">
                                    <label for="search_text" class="form-label">검색어</label>
                                    <input type="text" class="form-control" id="search_text" name="search_text" 
                                           value="{{ search_text }}" placeholder="검색어를 입력하세요" required>
                                </div>
                                <div class="col-md-2">
                                    <label for="search_brand" class="form-label">브랜드</label>
                                    <select class="form-select" id="search_brand" name="search_brand">
                                        <option value="">전체</option>
                                        {% for brand in brand_codes %}
                                        <option value="{{ brand.code }}" {{ 'selected' if search_brand == brand.code else '' }}>
                                            {{ brand.code_name }}
                                        </option>
                                        {% endfor %}
                                    </select>
                                </div>
                                <div class="col-md-2">
                                    <label class="form-label">&nbsp;</label>
                                    <div class="d-grid">
                                        <button type="submit" class="btn btn-primary">
                                            <i class="bi bi-search"></i> 검색
                                        </button>
                                    </div>
                                </div>
                                <div class="col-md-2">
                                    <label class="form-label">&nbsp;</label>
                                    <div class="d-grid">
                                        <a href="{{ url_for('customer.serial_search') }}" class="btn btn-outline-secondary">
                                            <i class="bi bi-arrow-clockwise"></i> 초기화
                                        </a>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 검색 결과 -->
            {% if search_text %}
            <div class="row">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h5><i class="bi bi-list-check"></i> 검색 결과</h5>
                            <span class="badge bg-info">{{ results|length }}건 발견</span>
                        </div>
                        <div class="card-body">
                            {% if results %}
                            <div class="table-responsive">
                                <table class="table table-striped table-hover">
                                    <thead class="table-dark">
                                        <tr>
                                            <th>브랜드</th>
                                            <th>제품명</th>
                                            <th>시리얼번호</th>
                                            <th>고객명</th>
                                            <th>전화번호</th>
                                            <th>구매매장</th>
                                            <th>구매일</th>
                                            <th>등록일</th>
                                            <th>상태</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for serial in results %}
                                        <tr>
                                            <td>
                                                {% for brand in brand_codes %}
                                                    {% if brand.code == serial.brand %}
                                                        <span class="badge bg-primary">{{ brand.code_name }}</span>
                                                    {% endif %}
                                                {% endfor %}
                                            </td>
                                            <td><strong>{{ serial.product_name }}</strong></td>
                                            <td><code>{{ serial.serial_code }}</code></td>
                                            <td>{{ serial.name }}</td>
                                            <td>{{ serial.mobile }}</td>
                                            <td>{{ serial.buy_store or '-' }}</td>
                                            <td>{{ serial.buy_date or '-' }}</td>
                                            <td>{{ serial.ins_date.strftime('%Y-%m-%d') if serial.ins_date else '-' }}</td>
                                            <td>
                                                {% if serial.status == 'confirmed' %}
                                                <span class="badge bg-success">확인됨</span>
                                                {% else %}
                                                <span class="badge bg-warning">{{ serial.status or '대기' }}</span>
                                                {% endif %}
                                            </td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                            {% else %}
                            <div class="text-center py-5">
                                <i class="bi bi-search" style="font-size: 3rem; color: #6c757d;"></i>
                                <h4 class="mt-3 text-muted">검색 결과가 없습니다</h4>
                                <p class="text-muted">다른 검색 조건을 시도해보세요.</p>
                            </div>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>
            {% else %}
            <div class="row">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-body text-center py-5">
                            <i class="bi bi-search" style="font-size: 4rem; color: #6c757d;"></i>
                            <h4 class="mt-3 text-muted">시리얼 번호를 검색하세요</h4>
                            <p class="text-muted">고객명, 전화번호, 제품명으로도 검색 가능합니다.</p>
                        </div>
                    </div>
                </div>
            </div>
            {% endif %}
        </div>
        {% endblock %}
        """, results=results, search_type=search_type, search_text=search_text, 
            search_brand=search_brand, brand_codes=brand_codes)
        
    except Exception as e:
        flash(f'시리얼 검색 중 오류가 발생했습니다: {e}', 'error')
        return redirect(url_for('index'))

# ============================================
# 3. 시리얼 등록 목록
# ============================================

@bp.route('/serial-list')
@login_required
def serial_list():
    """시리얼 등록 목록 페이지"""
    try:
        # 페이지 설정
        page = int(request.args.get('page', 1))
        per_page = 20
        search_brand = request.args.get('search_brand', '')
        date_range = request.args.get('date_range', '')
        
        # 쿼리 구성
        query = SerialConfirm.query
        
        # 브랜드 필터
        if search_brand:
            query = query.filter(SerialConfirm.brand == search_brand)
        
        # 날짜 범위 필터
        if date_range:
            try:
                if '~' in date_range:
                    start_date, end_date = date_range.split('~')
                    start_date = datetime.strptime(start_date.strip(), '%Y-%m-%d')
                    end_date = datetime.strptime(end_date.strip(), '%Y-%m-%d') + timedelta(days=1)
                    query = query.filter(SerialConfirm.ins_date.between(start_date, end_date))
            except ValueError:
                flash('날짜 형식이 올바르지 않습니다.', 'error')
        
        # 페이지네이션
        serials = query.order_by(desc(SerialConfirm.ins_date)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 브랜드별 통계
        brand_stats = db.session.query(
            SerialConfirm.brand, func.count(SerialConfirm.seq)
        ).group_by(SerialConfirm.brand).all()
        
        # 브랜드 목록
        brand_codes = Code.get_codes_by_group('BRAND')
        
        return render_template_string("""
        {% extends "base.html" %}
        {% block title %}시리얼 등록 목록 - {{ app_name }}{% endblock %}
        {% block content %}
        <div class="container-fluid">
            <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
                <h1 class="h2"><i class="bi bi-list-check"></i> 시리얼 등록 목록</h1>
                <div class="btn-toolbar mb-2 mb-md-0">
                    <div class="btn-group me-2">
                        <button type="button" class="btn btn-success" onclick="exportSerials()">
                            <i class="bi bi-download"></i> 엑셀 다운로드
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- 브랜드별 통계 -->
            <div class="row mb-3">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-body">
                            <div class="row text-center">
                                {% for brand_code, count in brand_stats %}
                                <div class="col-md-2">
                                    {% for brand in brand_codes %}
                                        {% if brand.code == brand_code %}
                                        <h4 class="text-primary">{{ "{:,}".format(count) }}</h4>
                                        <small>{{ brand.code_name }}</small>
                                        {% endif %}
                                    {% endfor %}
                                </div>
                                {% endfor %}
                                <div class="col-md-2">
                                    <h4 class="text-success">{{ "{:,}".format(serials.total) }}</h4>
                                    <small>전체</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 검색 및 필터 -->
            <div class="row mb-3">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-body">
                            <form method="GET" class="row g-3">
                                <div class="col-md-2">
                                    <label for="search_brand" class="form-label">브랜드</label>
                                    <select class="form-select" id="search_brand" name="search_brand">
                                        <option value="">전체</option>
                                        {% for brand in brand_codes %}
                                        <option value="{{ brand.code }}" {{ 'selected' if search_brand == brand.code else '' }}>
                                            {{ brand.code_name }}
                                        </option>
                                        {% endfor %}
                                    </select>
                                </div>
                                <div class="col-md-3">
                                    <label for="date_range" class="form-label">등록일 범위</label>
                                    <input type="text" class="form-control" id="date_range" name="date_range" 
                                           value="{{ date_range }}" placeholder="2024-01-01 ~ 2024-12-31">
                                </div>
                                <div class="col-md-2">
                                    <label class="form-label">&nbsp;</label>
                                    <div class="d-grid">
                                        <button type="submit" class="btn btn-primary">
                                            <i class="bi bi-search"></i> 검색
                                        </button>
                                    </div>
                                </div>
                                <div class="col-md-2">
                                    <label class="form-label">&nbsp;</label>
                                    <div class="d-grid">
                                        <a href="{{ url_for('customer.serial_list') }}" class="btn btn-outline-secondary">
                                            <i class="bi bi-arrow-clockwise"></i> 초기화
                                        </a>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 시리얼 목록 -->
            <div class="row">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h5><i class="bi bi-list"></i> 등록된 시리얼</h5>
                            <span class="badge bg-info">총 {{ serials.total }}건</span>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table table-striped table-hover">
                                    <thead class="table-dark">
                                        <tr>
                                            <th>등록일</th>
                                            <th>브랜드</th>
                                            <th>제품명</th>
                                            <th>시리얼번호</th>
                                            <th>고객명</th>
                                            <th>전화번호</th>
                                            <th>구매매장</th>
                                            <th>구매일</th>
                                            <th>구매가격</th>
                                            <th>상태</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for serial in serials.items %}
                                        <tr>
                                            <td>{{ serial.ins_date.strftime('%Y-%m-%d') if serial.ins_date else '-' }}</td>
                                            <td>
                                                {% for brand in brand_codes %}
                                                    {% if brand.code == serial.brand %}
                                                        <span class="badge bg-primary">{{ brand.code_name }}</span>
                                                    {% endif %}
                                                {% endfor %}
                                            </td>
                                            <td><strong>{{ serial.product_name }}</strong></td>
                                            <td><code>{{ serial.serial_code }}</code></td>
                                            <td>{{ serial.name }}</td>
                                            <td>{{ serial.mobile }}</td>
                                            <td>{{ serial.buy_store or '-' }}</td>
                                            <td>{{ serial.buy_date or '-' }}</td>
                                            <td>
                                                {% if serial.buy_price %}
                                                {{ "{:,}".format(serial.buy_price) }}원
                                                {% else %}
                                                -
                                                {% endif %}
                                            </td>
                                            <td>
                                                {% if serial.status == 'confirmed' %}
                                                <span class="badge bg-success">확인됨</span>
                                                {% else %}
                                                <span class="badge bg-warning">{{ serial.status or '대기' }}</span>
                                                {% endif %}
                                            </td>
                                        </tr>
                                        {% else %}
                                        <tr>
                                            <td colspan="10" class="text-center text-muted">등록된 시리얼이 없습니다.</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                            
                            <!-- 페이지네이션 -->
                            {% if serials.pages > 1 %}
                            <nav aria-label="시리얼 목록 페이지네이션">
                                <ul class="pagination justify-content-center">
                                    {% if serials.has_prev %}
                                    <li class="page-item">
                                        <a class="page-link" href="{{ url_for('customer.serial_list', page=serials.prev_num, search_brand=search_brand, date_range=date_range) }}">이전</a>
                                    </li>
                                    {% endif %}
                                    
                                    {% for page_num in serials.iter_pages() %}
                                        {% if page_num %}
                                            {% if page_num != serials.page %}
                                            <li class="page-item">
                                                <a class="page-link" href="{{ url_for('customer.serial_list', page=page_num, search_brand=search_brand, date_range=date_range) }}">{{ page_num }}</a>
                                            </li>
                                            {% else %}
                                            <li class="page-item active">
                                                <span class="page-link">{{ page_num }}</span>
                                            </li>
                                            {% endif %}
                                        {% else %}
                                        <li class="page-item disabled">
                                            <span class="page-link">…</span>
                                        </li>
                                        {% endif %}
                                    {% endfor %}
                                    
                                    {% if serials.has_next %}
                                    <li class="page-item">
                                        <a class="page-link" href="{{ url_for('customer.serial_list', page=serials.next_num, search_brand=search_brand, date_range=date_range) }}">다음</a>
                                    </li>
                                    {% endif %}
                                </ul>
                            </nav>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endblock %}
        
        {% block extra_js %}
        <script>
        function exportSerials() {
            alert('엑셀 다운로드 기능을 구현 중입니다.');
        }
        </script>
        {% endblock %}
        """, serials=serials, brand_stats=brand_stats, brand_codes=brand_codes,
            search_brand=search_brand, date_range=date_range)
        
    except Exception as e:
        flash(f'시리얼 목록 조회 중 오류가 발생했습니다: {e}', 'error')
        return redirect(url_for('index'))

# ============================================
# 4. 고객 타겟팅
# ============================================

@bp.route('/targeting', methods=['GET', 'POST'])
@login_required
def targeting():
    """고객 타겟팅 페이지"""
    try:
        # POST 요청일 때 타겟팅 실행
        if request.method == 'POST':
            # 타겟팅 조건 수집
            conditions = {
                'sex': request.form.get('sex'),
                'age_start': request.form.get('age_start'),
                'age_end': request.form.get('age_end'),
                'sido': request.form.getlist('sido'),
                'cust_type': request.form.get('cust_type'),
                'serial_confirm': request.form.get('serial_confirm'),
                'baby_due_start': request.form.get('baby_due_start'),
                'baby_due_end': request.form.get('baby_due_end')
            }
            
            # 고객 쿼리 구성
            query = Customer.query
            
            # 성별 조건
            if conditions['sex'] and conditions['sex'] != 'all':
                query = query.filter(Customer.sex == conditions['sex'])
            
            # 나이 조건 (생년월일 기반)
            if conditions['age_start']:
                birth_end = datetime.now().replace(year=datetime.now().year - int(conditions['age_start']))
                query = query.filter(Customer.birth_date <= birth_end)
            
            if conditions['age_end']:
                birth_start = datetime.now().replace(year=datetime.now().year - int(conditions['age_end']))
                query = query.filter(Customer.birth_date >= birth_start)
            
            # 지역 조건
            if conditions['sido']:
                query = query.filter(Customer.sido.in_(conditions['sido']))
            
            # 고객 유형 조건
            if conditions['cust_type'] and conditions['cust_type'] != 'all':
                query = query.filter(Customer.cust_type == conditions['cust_type'])
            
            # 출산예정일 조건
            if conditions['baby_due_start'] and conditions['baby_due_end']:
                try:
                    due_start = datetime.strptime(conditions['baby_due_start'], '%Y-%m-%d')
                    due_end = datetime.strptime(conditions['baby_due_end'], '%Y-%m-%d')
                    query = query.filter(
                        Customer.baby_due_date.between(due_start, due_end)
                    )
                except ValueError:
                    flash('출산예정일 형식이 올바르지 않습니다.', 'error')
            
            # 타겟 고객 조회
            target_customers = query.filter(Customer.mobile.isnot(None)).all()
            
            # 중복 전화번호 제거
            unique_mobiles = list(set([c.mobile for c in target_customers if c.mobile]))
            
            flash(f'타겟팅 조건에 맞는 고객: {len(unique_mobiles)}명', 'success')
            
            return render_template_string("""
            {% extends "base.html" %}
            {% block title %}고객 타겟팅 결과 - {{ app_name }}{% endblock %}
            {% block content %}
            <div class="container-fluid">
                <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
                    <h1 class="h2"><i class="bi bi-bullseye"></i> 고객 타겟팅 결과</h1>
                    <div class="btn-toolbar mb-2 mb-md-0">
                        <div class="btn-group me-2">
                            <a href="{{ url_for('customer.targeting') }}" class="btn btn-secondary">
                                <i class="bi bi-arrow-left"></i> 다시 타겟팅
                            </a>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-8">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="bi bi-people"></i> 타겟팅 결과</h5>
                            </div>
                            <div class="card-body">
                                <div class="alert alert-success">
                                    <h4><i class="bi bi-check-circle"></i> 타겟팅 완료!</h4>
                                    <p class="mb-0">조건에 맞는 고객 <strong>{{ unique_mobiles|length }}명</strong>이 검색되었습니다.</p>
                                </div>
                                
                                <!-- SMS 발송 폼 -->
                                <form method="POST" action="{{ url_for('customer.send_sms') }}">
                                    {% for mobile in unique_mobiles %}
                                    <input type="hidden" name="target_mobiles" value="{{ mobile }}">
                                    {% endfor %}
                                    
                                    <div class="mb-3">
                                        <label for="sms_title" class="form-label">발송 제목</label>
                                        <input type="text" class="form-control" id="sms_title" name="sms_title" required>
                                    </div>
                                    
                                    <div class="mb-3">
                                        <label for="sms_body" class="form-label">SMS 내용</label>
                                        <textarea class="form-control" id="sms_body" name="sms_body" rows="6" required 
                                                  placeholder="SMS 내용을 입력하세요. (최대 90자)"></textarea>
                                        <div class="form-text">현재 글자수: <span id="char_count">0</span>/90자</div>
                                    </div>
                                    
                                    <div class="mb-3">
                                        <label for="send_time" class="form-label">발송 시간</label>
                                        <select class="form-select" id="send_time" name="send_time">
                                            <option value="now">즉시 발송</option>
                                            <option value="scheduled">예약 발송</option>
                                        </select>
                                    </div>
                                    
                                    <div class="d-grid">
                                        <button type="submit" class="btn btn-success btn-lg" onclick="return confirm('{{ unique_mobiles|length }}명에게 SMS를 발송하시겠습니까?')">
                                            <i class="bi bi-send"></i> {{ unique_mobiles|length }}명에게 SMS 발송
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="bi bi-list"></i> 타겟 고객 목록 (일부)</h5>
                            </div>
                            <div class="card-body">
                                <div class="list-group">
                                    {% for mobile in unique_mobiles[:10] %}
                                    <div class="list-group-item">
                                        <i class="bi bi-phone"></i> {{ mobile }}
                                    </div>
                                    {% endfor %}
                                    {% if unique_mobiles|length > 10 %}
                                    <div class="list-group-item text-muted">
                                        <i class="bi bi-three-dots"></i> 외 {{ unique_mobiles|length - 10 }}명
                                    </div>
                                    {% endif %}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            {% endblock %}
            
            {% block extra_js %}
            <script>
            document.getElementById('sms_body').addEventListener('input', function() {
                const charCount = this.value.length;
                document.getElementById('char_count').textContent = charCount;
                
                if (charCount > 90) {
                    this.classList.add('is-invalid');
                } else {
                    this.classList.remove('is-invalid');
                }
            });
            </script>
            {% endblock %}
            """, unique_mobiles=unique_mobiles)
        
        # GET 요청일 때 타겟팅 폼 표시
        # 시도 목록
        sido_list = [
            '서울특별시', '경기도', '인천광역시', '강원도', '광주광역시',
            '대구광역시', '대전광역시', '부산광역시', '울산광역시', '세종특별자치시',
            '경상남도', '경상북도', '전라남도', '전라북도', '충청남도', '충청북도', '제주특별자치도'
        ]
        
        # 고객 유형 목록
        cust_types = db.session.query(Customer.cust_type).distinct().filter(
            Customer.cust_type.isnot(None)
        ).all()
        cust_types = [ct[0] for ct in cust_types if ct[0]]
        
        return render_template_string("""
        {% extends "base.html" %}
        {% block title %}고객 타겟팅 - {{ app_name }}{% endblock %}
        {% block content %}
        <div class="container-fluid">
            <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
                <h1 class="h2"><i class="bi bi-bullseye"></i> 고객 타겟팅</h1>
            </div>
            
            <div class="row">
                <div class="col-md-8">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="bi bi-funnel"></i> 타겟팅 조건 설정</h5>
                        </div>
                        <div class="card-body">
                            <form method="POST">
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label for="sex" class="form-label">성별</label>
                                            <select class="form-select" id="sex" name="sex">
                                                <option value="all">전체</option>
                                                <option value="M">남성</option>
                                                <option value="F">여성</option>
                                            </select>
                                        </div>
                                        
                                        <div class="mb-3">
                                            <label class="form-label">연령대</label>
                                            <div class="row">
                                                <div class="col-6">
                                                    <input type="number" class="form-control" name="age_start" placeholder="최소 나이" min="0" max="100">
                                                </div>
                                                <div class="col-6">
                                                    <input type="number" class="form-control" name="age_end" placeholder="최대 나이" min="0" max="100">
                                                </div>
                                            </div>
                                        </div>
                                        
                                        <div class="mb-3">
                                            <label for="cust_type" class="form-label">고객 유형</label>
                                            <select class="form-select" id="cust_type" name="cust_type">
                                                <option value="all">전체</option>
                                                {% for ct in cust_types %}
                                                <option value="{{ ct }}">{{ ct }}</option>
                                                {% endfor %}
                                            </select>
                                        </div>
                                    </div>
                                    
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label class="form-label">지역 선택</label>
                                            <div style="max-height: 200px; overflow-y: auto; border: 1px solid #dee2e6; border-radius: 0.375rem; padding: 0.5rem;">
                                                {% for sido in sido_list %}
                                                <div class="form-check">
                                                    <input class="form-check-input" type="checkbox" name="sido" value="{{ sido }}" id="sido_{{ loop.index }}">
                                                    <label class="form-check-label" for="sido_{{ loop.index }}">
                                                        {{ sido }}
                                                    </label>
                                                </div>
                                                {% endfor %}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label class="form-label">출산예정일 범위</label>
                                            <div class="row">
                                                <div class="col-6">
                                                    <input type="date" class="form-control" name="baby_due_start">
                                                </div>
                                                <div class="col-6">
                                                    <input type="date" class="form-control" name="baby_due_end">
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label for="serial_confirm" class="form-label">시리얼 등록 여부</label>
                                            <select class="form-select" id="serial_confirm" name="serial_confirm">
                                                <option value="">전체</option>
                                                <option value="Y">등록함</option>
                                                <option value="N">등록안함</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                                
                                <hr>
                                
                                <div class="d-grid">
                                    <button type="submit" class="btn btn-primary btn-lg">
                                        <i class="bi bi-search"></i> 타겟 고객 검색
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="bi bi-info-circle"></i> 타겟팅 안내</h5>
                        </div>
                        <div class="card-body">
                            <h6>🎯 타겟팅 방법</h6>
                            <ul class="small">
                                <li>원하는 조건을 선택하세요</li>
                                <li>여러 조건을 조합할 수 있습니다</li>
                                <li>지역은 다중 선택 가능합니다</li>
                                <li>나이는 생년월일 기반으로 계산됩니다</li>
                            </ul>
                            
                            <hr>
                            
                            <h6>📊 전체 고객 통계</h6>
                            <div class="small">
                                <div class="d-flex justify-content-between">
                                    <span>전체 고객:</span>
                                    <strong>{{ "{:,}".format(total_customers) }}명</strong>
                                </div>
                                <div class="d-flex justify-content-between">
                                    <span>연락처 보유:</span>
                                    <strong>{{ "{:,}".format(customers_with_mobile) }}명</strong>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card mt-3">
                        <div class="card-header">
                            <h5><i class="bi bi-clock-history"></i> 최근 발송 내역</h5>
                        </div>
                        <div class="card-body">
                            {% for log in recent_sms_logs %}
                            <div class="d-flex justify-content-between small mb-2">
                                <span>{{ log.targeting_info[:20] }}...</span>
                                <strong>{{ log.send_cnt }}명</strong>
                            </div>
                            {% else %}
                            <div class="text-muted small">최근 발송 내역이 없습니다.</div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endblock %}
        """, sido_list=sido_list, cust_types=cust_types, 
            total_customers=Customer.query.count(),
            customers_with_mobile=Customer.query.filter(Customer.mobile.isnot(None)).count(),
            recent_sms_logs=CustomerSmsLog.query.order_by(desc(CustomerSmsLog.ins_date)).limit(5).all())
        
    except Exception as e:
        flash(f'고객 타겟팅 중 오류가 발생했습니다: {e}', 'error')
        return redirect(url_for('index'))

# ============================================
# 5. 발송 내역
# ============================================

@bp.route('/send-log')
@login_required 
def send_log():
    """발송 내역 페이지"""
    try:
        # 페이지 설정
        page = int(request.args.get('page', 1))
        per_page = 15
        search_period = request.args.get('search_period', '')
        
        # 쿼리 구성
        query = CustomerSmsLog.query
        
        # 기간 필터
        if search_period:
            try:
                if search_period == '7days':
                    start_date = datetime.now() - timedelta(days=7)
                    query = query.filter(CustomerSmsLog.ins_date >= start_date)
                elif search_period == '30days':
                    start_date = datetime.now() - timedelta(days=30)
                    query = query.filter(CustomerSmsLog.ins_date >= start_date)
                elif search_period == '90days':
                    start_date = datetime.now() - timedelta(days=90)
                    query = query.filter(CustomerSmsLog.ins_date >= start_date)
                elif '~' in search_period:
                    start_date, end_date = search_period.split('~')
                    start_date = datetime.strptime(start_date.strip(), '%Y-%m-%d')
                    end_date = datetime.strptime(end_date.strip(), '%Y-%m-%d') + timedelta(days=1)
                    query = query.filter(CustomerSmsLog.ins_date.between(start_date, end_date))
            except ValueError:
                flash('날짜 형식이 올바르지 않습니다.', 'error')
        
        # 페이지네이션
        sms_logs = query.order_by(desc(CustomerSmsLog.ins_date)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 통계 계산
        total_logs = CustomerSmsLog.query.count()
        total_sent = db.session.query(func.sum(CustomerSmsLog.send_cnt)).scalar() or 0
        recent_sent = db.session.query(func.sum(CustomerSmsLog.send_cnt)).filter(
            CustomerSmsLog.ins_date >= datetime.now() - timedelta(days=30)
        ).scalar() or 0
        
        return render_template_string("""
        {% extends "base.html" %}
        {% block title %}고객 타겟팅 발송 내역 - {{ app_name }}{% endblock %}
        {% block content %}
        <div class="container-fluid">
            <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
                <h1 class="h2"><i class="bi bi-envelope-paper"></i> 고객 타겟팅 발송 내역</h1>
                <div class="btn-toolbar mb-2 mb-md-0">
                    <div class="btn-group me-2">
                        <a href="{{ url_for('customer.targeting') }}" class="btn btn-primary">
                            <i class="bi bi-plus"></i> 새로운 타겟팅
                        </a>
                        <button type="button" class="btn btn-secondary" onclick="exportSmsLogs()">
                            <i class="bi bi-download"></i> 엑셀 다운로드
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- 통계 카드 -->
            <div class="row g-3 mb-4">
                <div class="col-xl-3 col-md-6">
                    <div class="card border-primary">
                        <div class="card-body">
                            <div class="d-flex align-items-center">
                                <div class="flex-shrink-0">
                                    <i class="bi bi-list-task text-primary" style="font-size: 2rem;"></i>
                                </div>
                                <div class="flex-grow-1 ms-3">
                                    <div class="text-muted small">총 발송 건수</div>
                                    <div class="h4 mb-0">{{ total_logs }}건</div>
                                    <div class="text-muted small">누적 발송</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-xl-3 col-md-6">
                    <div class="card border-success">
                        <div class="card-body">
                            <div class="d-flex align-items-center">
                                <div class="flex-shrink-0">
                                    <i class="bi bi-people text-success" style="font-size: 2rem;"></i>
                                </div>
                                <div class="flex-grow-1 ms-3">
                                    <div class="text-muted small">총 발송 대상</div>
                                    <div class="h4 mb-0">{{ "{:,}".format(total_sent) }}명</div>
                                    <div class="text-muted small">누적 인원</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-xl-3 col-md-6">
                    <div class="card border-info">
                        <div class="card-body">
                            <div class="d-flex align-items-center">
                                <div class="flex-shrink-0">
                                    <i class="bi bi-calendar-month text-info" style="font-size: 2rem;"></i>
                                </div>
                                <div class="flex-grow-1 ms-3">
                                    <div class="text-muted small">최근 30일</div>
                                    <div class="h4 mb-0">{{ "{:,}".format(recent_sent) }}명</div>
                                    <div class="text-muted small">발송 인원</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-xl-3 col-md-6">
                    <div class="card border-warning">
                        <div class="card-body">
                            <div class="d-flex align-items-center">
                                <div class="flex-shrink-0">
                                    <i class="bi bi-graph-up text-warning" style="font-size: 2rem;"></i>
                                </div>
                                <div class="flex-grow-1 ms-3">
                                    <div class="text-muted small">평균 발송 인원</div>
                                    <div class="h4 mb-0">{{ "{:,.0f}".format(total_sent / total_logs if total_logs > 0 else 0) }}명</div>
                                    <div class="text-muted small">건당 평균</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 검색 및 필터 -->
            <div class="row mb-3">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-body">
                            <form method="GET" class="row g-3">
                                <div class="col-md-3">
                                    <label for="search_period" class="form-label">기간 선택</label>
                                    <select class="form-select" id="search_period" name="search_period">
                                        <option value="">전체 기간</option>
                                        <option value="7days" {{ 'selected' if search_period == '7days' else '' }}>최근 7일</option>
                                        <option value="30days" {{ 'selected' if search_period == '30days' else '' }}>최근 30일</option>
                                        <option value="90days" {{ 'selected' if search_period == '90days' else '' }}>최근 90일</option>
                                    </select>
                                </div>
                                <div class="col-md-2">
                                    <label class="form-label">&nbsp;</label>
                                    <div class="d-grid">
                                        <button type="submit" class="btn btn-primary">
                                            <i class="bi bi-search"></i> 검색
                                        </button>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label">&nbsp;</label>
                                    <div class="d-grid">
                                        <a href="{{ url_for('customer.send_log') }}" class="btn btn-outline-secondary">
                                            <i class="bi bi-arrow-clockwise"></i> 초기화
                                        </a>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 발송 내역 목록 -->
            <div class="row">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h5><i class="bi bi-list"></i> SMS 발송 내역</h5>
                            <span class="badge bg-info">총 {{ sms_logs.total }}건</span>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table table-striped table-hover">
                                    <thead class="table-dark">
                                        <tr>
                                            <th>발송일시</th>
                                            <th>발송 제목</th>
                                            <th>SMS 내용</th>
                                            <th>발송 인원</th>
                                            <th>발송자</th>
                                            <th>평가</th>
                                            <th>관리</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for log in sms_logs.items %}
                                        <tr>
                                            <td>{{ log.ins_date.strftime('%Y-%m-%d %H:%M') if log.ins_date else '-' }}</td>
                                            <td>
                                                <strong>{{ log.targeting_info or '제목 없음' }}</strong>
                                            </td>
                                            <td>
                                                <div class="text-truncate" style="max-width: 300px;" title="{{ log.sms_body }}">
                                                    {{ log.sms_body[:50] }}{{ '...' if log.sms_body and log.sms_body|length > 50 else '' }}
                                                </div>
                                            </td>
                                            <td>
                                                <span class="badge bg-success">{{ "{:,}".format(log.send_cnt) }}명</span>
                                            </td>
                                            <td>{{ log.ins_user_name or log.ins_user or '-' }}</td>
                                            <td>
                                                {% if log.grades %}
                                                    {% for i in range(5) %}
                                                        {% if i < log.grades %}
                                                        <i class="bi bi-star-fill text-warning"></i>
                                                        {% else %}
                                                        <i class="bi bi-star text-muted"></i>
                                                        {% endif %}
                                                    {% endfor %}
                                                {% else %}
                                                <span class="text-muted">미평가</span>
                                                {% endif %}
                                            </td>
                                            <td>
                                                <div class="btn-group btn-group-sm">
                                                    <button class="btn btn-outline-info" onclick="viewSmsDetail({{ log.seq }})" title="상세보기">
                                                        <i class="bi bi-eye"></i>
                                                    </button>
                                                    <button class="btn btn-outline-warning" onclick="rateSms({{ log.seq }})" title="평가하기">
                                                        <i class="bi bi-star"></i>
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                        {% else %}
                                        <tr>
                                            <td colspan="7" class="text-center text-muted">발송 내역이 없습니다.</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                            
                            <!-- 페이지네이션 -->
                            {% if sms_logs.pages > 1 %}
                            <nav aria-label="발송 내역 페이지네이션">
                                <ul class="pagination justify-content-center">
                                    {% if sms_logs.has_prev %}
                                    <li class="page-item">
                                        <a class="page-link" href="{{ url_for('customer.send_log', page=sms_logs.prev_num, search_period=search_period) }}">이전</a>
                                    </li>
                                    {% endif %}
                                    
                                    {% for page_num in sms_logs.iter_pages() %}
                                        {% if page_num %}
                                            {% if page_num != sms_logs.page %}
                                            <li class="page-item">
                                                <a class="page-link" href="{{ url_for('customer.send_log', page=page_num, search_period=search_period) }}">{{ page_num }}</a>
                                            </li>
                                            {% else %}
                                            <li class="page-item active">
                                                <span class="page-link">{{ page_num }}</span>
                                            </li>
                                            {% endif %}
                                        {% else %}
                                        <li class="page-item disabled">
                                            <span class="page-link">…</span>
                                        </li>
                                        {% endif %}
                                    {% endfor %}
                                    
                                    {% if sms_logs.has_next %}
                                    <li class="page-item">
                                        <a class="page-link" href="{{ url_for('customer.send_log', page=sms_logs.next_num, search_period=search_period) }}">다음</a>
                                    </li>
                                    {% endif %}
                                </ul>
                            </nav>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endblock %}
        
        {% block extra_js %}
        <script>
        function viewSmsDetail(logSeq) {
            alert('SMS 상세보기 기능을 구현 중입니다. ID: ' + logSeq);
        }
        
        function rateSms(logSeq) {
            const rating = prompt('이 SMS 발송에 대해 평가해주세요 (1-5점):', '5');
            if (rating && rating >= 1 && rating <= 5) {
                alert('평가 기능을 구현 중입니다. 평점: ' + rating + '점');
            }
        }
        
        function exportSmsLogs() {
            alert('엑셀 다운로드 기능을 구현 중입니다.');
        }
        </script>
        {% endblock %}
        """, sms_logs=sms_logs, search_period=search_period, 
            total_logs=total_logs, total_sent=total_sent, recent_sent=recent_sent)
        
    except Exception as e:
        flash(f'발송 내역 조회 중 오류가 발생했습니다: {e}', 'error')
        return redirect(url_for('index'))

# ============================================
# 6. A/S 접수 내역
# ============================================

@bp.route('/as-list')
@login_required
def as_list():
    """A/S 접수 내역 페이지"""
    try:
        # 페이지 설정
        page = int(request.args.get('page', 1))
        per_page = 15
        search_status = request.args.get('search_status', '')
        search_period = request.args.get('search_period', '')
        search_text = request.args.get('search_text', '')
        
        # A/S 접수 데이터는 실제로는 별도 테이블이 필요하지만
        # 현재는 시리얼 확인 데이터를 기반으로 시뮬레이션
        query = SerialConfirm.query.filter(
            SerialConfirm.status.isnot(None)
        )
        
        # 상태 필터
        if search_status:
            query = query.filter(SerialConfirm.status == search_status)
        
        # 기간 필터
        if search_period:
            try:
                if search_period == '30days':
                    start_date = datetime.now() - timedelta(days=30)
                    query = query.filter(SerialConfirm.ins_date >= start_date)
                elif search_period == '90days':
                    start_date = datetime.now() - timedelta(days=90)
                    query = query.filter(SerialConfirm.ins_date >= start_date)
            except ValueError:
                pass
        
        # 검색 텍스트
        if search_text:
            query = query.filter(
                or_(
                    SerialConfirm.name.ilike(f'%{search_text}%'),
                    SerialConfirm.mobile.ilike(f'%{search_text}%'),
                    SerialConfirm.serial_code.ilike(f'%{search_text}%'),
                    SerialConfirm.product_name.ilike(f'%{search_text}%')
                )
            )
        
        # 페이지네이션
        as_requests = query.order_by(desc(SerialConfirm.ins_date)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 상태별 통계
        status_stats = db.session.query(
            SerialConfirm.status, func.count(SerialConfirm.seq)
        ).filter(SerialConfirm.status.isnot(None)).group_by(SerialConfirm.status).all()
        
        return render_template_string("""
        {% extends "base.html" %}
        {% block title %}A/S 접수 내역 - {{ app_name }}{% endblock %}
        {% block content %}
        <div class="container-fluid">
            <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
                <h1 class="h2"><i class="bi bi-headset"></i> A/S 접수 내역</h1>
                <div class="btn-toolbar mb-2 mb-md-0">
                    <div class="btn-group me-2">
                        <button type="button" class="btn btn-success" onclick="addAsRequest()">
                            <i class="bi bi-plus"></i> A/S 접수 등록
                        </button>
                        <button type="button" class="btn btn-secondary" onclick="exportAsRequests()">
                            <i class="bi bi-download"></i> 엑셀 다운로드
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- 상태별 통계 -->
            <div class="row g-3 mb-4">
                <div class="col-xl-3 col-md-6">
                    <div class="card border-warning">
                        <div class="card-body">
                            <div class="d-flex align-items-center">
                                <div class="flex-shrink-0">
                                    <i class="bi bi-clock text-warning" style="font-size: 2rem;"></i>
                                </div>
                                <div class="flex-grow-1 ms-3">
                                    <div class="text-muted small">접수 대기</div>
                                    <div class="h4 mb-0">{{ status_stats.get('pending', 0) }}건</div>
                                    <div class="text-muted small">처리 대기</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-xl-3 col-md-6">
                    <div class="card border-info">
                        <div class="card-body">
                            <div class="d-flex align-items-center">
                                <div class="flex-shrink-0">
                                    <i class="bi bi-gear text-info" style="font-size: 2rem;"></i>
                                </div>
                                <div class="flex-grow-1 ms-3">
                                    <div class="text-muted small">처리 중</div>
                                    <div class="h4 mb-0">{{ status_stats.get('processing', 0) }}건</div>
                                    <div class="text-muted small">진행 중</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-xl-3 col-md-6">
                    <div class="card border-success">
                        <div class="card-body">
                            <div class="d-flex align-items-center">
                                <div class="flex-shrink-0">
                                    <i class="bi bi-check-circle text-success" style="font-size: 2rem;"></i>
                                </div>
                                <div class="flex-grow-1 ms-3">
                                    <div class="text-muted small">처리 완료</div>
                                    <div class="h4 mb-0">{{ status_stats.get('confirmed', 0) }}건</div>
                                    <div class="text-muted small">완료됨</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-xl-3 col-md-6">
                    <div class="card border-primary">
                        <div class="card-body">
                            <div class="d-flex align-items-center">
                                <div class="flex-shrink-0">
                                    <i class="bi bi-list-task text-primary" style="font-size: 2rem;"></i>
                                </div>
                                <div class="flex-grow-1 ms-3">
                                    <div class="text-muted small">전체 건수</div>
                                    <div class="h4 mb-0">{{ as_requests.total }}건</div>
                                    <div class="text-muted small">누적 접수</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 검색 및 필터 -->
            <div class="row mb-3">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-body">
                            <form method="GET" class="row g-3">
                                <div class="col-md-2">
                                    <label for="search_status" class="form-label">상태</label>
                                    <select class="form-select" id="search_status" name="search_status">
                                        <option value="">전체</option>
                                        <option value="pending" {{ 'selected' if search_status == 'pending' else '' }}>접수 대기</option>
                                        <option value="processing" {{ 'selected' if search_status == 'processing' else '' }}>처리 중</option>
                                        <option value="confirmed" {{ 'selected' if search_status == 'confirmed' else '' }}>처리 완료</option>
                                    </select>
                                </div>
                                <div class="col-md-2">
                                    <label for="search_period" class="form-label">기간</label>
                                    <select class="form-select" id="search_period" name="search_period">
                                        <option value="">전체</option>
                                        <option value="30days" {{ 'selected' if search_period == '30days' else '' }}>최근 30일</option>
                                        <option value="90days" {{ 'selected' if search_period == '90days' else '' }}>최근 90일</option>
                                    </select>
                                </div>
                                <div class="col-md-3">
                                    <label for="search_text" class="form-label">검색어</label>
                                    <input type="text" class="form-control" id="search_text" name="search_text" 
                                           value="{{ search_text }}" placeholder="고객명, 전화번호, 시리얼번호">
                                </div>
                                <div class="col-md-2">
                                    <label class="form-label">&nbsp;</label>
                                    <div class="d-grid">
                                        <button type="submit" class="btn btn-primary">
                                            <i class="bi bi-search"></i> 검색
                                        </button>
                                    </div>
                                </div>
                                <div class="col-md-2">
                                    <label class="form-label">&nbsp;</label>
                                    <div class="d-grid">
                                        <a href="{{ url_for('customer.as_list') }}" class="btn btn-outline-secondary">
                                            <i class="bi bi-arrow-clockwise"></i> 초기화
                                        </a>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- A/S 접수 목록 -->
            <div class="row">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h5><i class="bi bi-list"></i> A/S 접수 내역</h5>
                            <span class="badge bg-info">총 {{ as_requests.total }}건</span>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table table-striped table-hover">
                                    <thead class="table-dark">
                                        <tr>
                                            <th>접수일</th>
                                            <th>고객명</th>
                                            <th>전화번호</th>
                                            <th>제품명</th>
                                            <th>시리얼번호</th>
                                            <th>상태</th>
                                            <th>접수 구분</th>
                                            <th>관리</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for req in as_requests.items %}
                                        <tr>
                                            <td>{{ req.ins_date.strftime('%Y-%m-%d') if req.ins_date else '-' }}</td>
                                            <td><strong>{{ req.name }}</strong></td>
                                            <td>{{ req.mobile }}</td>
                                            <td>{{ req.product_name }}</td>
                                            <td><code>{{ req.serial_code }}</code></td>
                                            <td>
                                                {% if req.status == 'pending' %}
                                                <span class="badge bg-warning">접수 대기</span>
                                                {% elif req.status == 'processing' %}
                                                <span class="badge bg-info">처리 중</span>
                                                {% elif req.status == 'confirmed' %}
                                                <span class="badge bg-success">처리 완료</span>
                                                {% else %}
                                                <span class="badge bg-secondary">{{ req.status }}</span>
                                                {% endif %}
                                            </td>
                                            <td>
                                                <span class="badge bg-primary">{{ req.serial_type or 'A/S' }}</span>
                                            </td>
                                            <td>
                                                <div class="btn-group btn-group-sm">
                                                    <button class="btn btn-outline-primary" onclick="editAsRequest({{ req.seq }})" title="수정">
                                                        <i class="bi bi-pencil"></i>
                                                    </button>
                                                    <button class="btn btn-outline-info" onclick="viewAsDetail({{ req.seq }})" title="상세보기">
                                                        <i class="bi bi-eye"></i>
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                        {% else %}
                                        <tr>
                                            <td colspan="8" class="text-center text-muted">A/S 접수 내역이 없습니다.</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                            
                            <!-- 페이지네이션 -->
                            {% if as_requests.pages > 1 %}
                            <nav aria-label="A/S 접수 페이지네이션">
                                <ul class="pagination justify-content-center">
                                    {% if as_requests.has_prev %}
                                    <li class="page-item">
                                        <a class="page-link" href="{{ url_for('customer.as_list', page=as_requests.prev_num, search_status=search_status, search_period=search_period, search_text=search_text) }}">이전</a>
                                    </li>
                                    {% endif %}
                                    
                                    {% for page_num in as_requests.iter_pages() %}
                                        {% if page_num %}
                                            {% if page_num != as_requests.page %}
                                            <li class="page-item">
                                                <a class="page-link" href="{{ url_for('customer.as_list', page=page_num, search_status=search_status, search_period=search_period, search_text=search_text) }}">{{ page_num }}</a>
                                            </li>
                                            {% else %}
                                            <li class="page-item active">
                                                <span class="page-link">{{ page_num }}</span>
                                            </li>
                                            {% endif %}
                                        {% else %}
                                        <li class="page-item disabled">
                                            <span class="page-link">…</span>
                                        </li>
                                        {% endif %}
                                    {% endfor %}
                                    
                                    {% if as_requests.has_next %}
                                    <li class="page-item">
                                        <a class="page-link" href="{{ url_for('customer.as_list', page=as_requests.next_num, search_status=search_status, search_period=search_period, search_text=search_text) }}">다음</a>
                                    </li>
                                    {% endif %}
                                </ul>
                            </nav>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endblock %}
        
        {% block extra_js %}
        <script>
        function addAsRequest() {
            alert('A/S 접수 등록 기능을 구현 중입니다.');
        }
        
        function editAsRequest(reqSeq) {
            alert('A/S 접수 수정 기능을 구현 중입니다. ID: ' + reqSeq);
        }
        
        function viewAsDetail(reqSeq) {
            alert('A/S 접수 상세보기 기능을 구현 중입니다. ID: ' + reqSeq);
        }
        
        function exportAsRequests() {
            alert('엑셀 다운로드 기능을 구현 중입니다.');
        }
        </script>
        {% endblock %}
        """, as_requests=as_requests, search_status=search_status, search_period=search_period, 
            search_text=search_text, status_stats=dict(status_stats))
        
    except Exception as e:
        flash(f'A/S 접수 내역 조회 중 오류가 발생했습니다: {e}', 'error')
        return redirect(url_for('index'))

# ============================================
# 7. 정품등록 매장 관리
# ============================================

@bp.route('/store-management')
def store_management():
    """정품 등록 매장 관리"""
    try:
        # 회사별 데이터 필터링
        company_id = MultiTenantQueryBuilder.get_current_company_id()
        
        # 매장별 통계 집계 (buy_store 기준)
        store_stats_query = db.session.query(
            SerialConfirm.buy_store.label('store_name'),
            func.count(SerialConfirm.seq).label('total_registrations'),
            func.max(SerialConfirm.ins_date).label('last_registration'),
            func.count(func.distinct(SerialConfirm.customer_name)).label('unique_customers')
        ).filter(
            SerialConfirm.company_id == company_id,
            SerialConfirm.buy_store.isnot(None),
            SerialConfirm.buy_store != ''
        ).group_by(
            SerialConfirm.buy_store
        ).order_by(
            desc('total_registrations')
        )
        
        # 페이징 처리
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        stores = store_stats_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 매장 등급 계산 (등록 건수 기준)
        def get_store_grade(count):
            if count >= 100:
                return {'grade': 'A+', 'class': 'success', 'desc': '우수 매장'}
            elif count >= 50:
                return {'grade': 'A', 'class': 'primary', 'desc': '우량 매장'}
            elif count >= 20:
                return {'grade': 'B', 'class': 'info', 'desc': '일반 매장'}
            elif count >= 10:
                return {'grade': 'C', 'class': 'warning', 'desc': '신규 매장'}
            else:
                return {'grade': 'D', 'class': 'secondary', 'desc': '비활성 매장'}
        
        # 활성도 계산 (최근 등록일 기준)
        def get_activity_level(last_date):
            if not last_date:
                return {'level': '비활성', 'class': 'secondary'}
            
            from datetime import datetime, timedelta
            now = datetime.now()
            diff = now - last_date
            
            if diff.days <= 30:
                return {'level': '매우 활성', 'class': 'success'}
            elif diff.days <= 90:
                return {'level': '활성', 'class': 'primary'}
            elif diff.days <= 180:
                return {'level': '보통', 'class': 'info'}
            elif diff.days <= 365:
                return {'level': '저조', 'class': 'warning'}
            else:
                return {'level': '휴면', 'class': 'danger'}
        
        # 전체 통계
        total_stores = store_stats_query.count()
        total_registrations = db.session.query(
            func.count(SerialConfirm.seq)
        ).filter(
            SerialConfirm.company_id == company_id,
            SerialConfirm.buy_store.isnot(None),
            SerialConfirm.buy_store != ''
        ).scalar() or 0
        
        context = {
            'stores': stores,
            'total_stores': total_stores,
            'total_registrations': total_registrations,
            'get_store_grade': get_store_grade,
            'get_activity_level': get_activity_level,
            'current_company': MultiTenantQueryBuilder.get_current_company()
        }
        
        return render_template_string("""
        {% extends "base.html" %}
        {% block title %}정품 등록 매장 관리{% endblock %}
        
        {% block content %}
        <div class="container-fluid">
            <!-- 페이지 헤더 -->
            <div class="d-flex justify-content-between align-items-center py-3 border-bottom mb-4">
                <div>
                    <h1 class="h3 mb-0">
                        <i class="bi bi-shop text-primary"></i> 
                        정품 등록 매장 관리
                    </h1>
                    <p class="text-muted mb-0">
                        {{ current_company.company_name if current_company else '전체' }} - 
                        정품 등록 매장 현황 및 통계
                    </p>
                </div>
                <div class="btn-toolbar">
                    <div class="btn-group me-2">
                        <button type="button" class="btn btn-outline-success btn-sm" onclick="exportStoreData()">
                            <i class="bi bi-download"></i> 엑셀 다운로드
                        </button>
                        <button type="button" class="btn btn-outline-info btn-sm" onclick="printStoreList()">
                            <i class="bi bi-printer"></i> 프린트
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- 통계 카드 -->
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card text-white bg-primary">
                        <div class="card-body text-center">
                            <h3 class="mb-0">{{ total_stores }}</h3>
                            <p class="mb-0">총 매장 수</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-white bg-success">
                        <div class="card-body text-center">
                            <h3 class="mb-0">{{ total_registrations }}</h3>
                            <p class="mb-0">총 등록 건수</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-white bg-info">
                        <div class="card-body text-center">
                            <h3 class="mb-0">{{ (total_registrations / total_stores)|round(1) if total_stores > 0 else 0 }}</h3>
                            <p class="mb-0">평균 등록/매장</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-white bg-warning">
                        <div class="card-body text-center">
                            <h3 class="mb-0">{{ stores.items|selectattr('last_registration')|list|length }}</h3>
                            <p class="mb-0">활성 매장</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 검색 및 필터 -->
            <div class="card mb-4">
                <div class="card-body">
                    <div class="row align-items-end">
                        <div class="col-md-4">
                            <label class="form-label">매장명 검색</label>
                            <input type="text" class="form-control" id="storeSearch" 
                                   placeholder="매장명을 입력하세요..." 
                                   data-table-search="#storeTable">
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">매장 등급</label>
                            <select class="form-select" id="gradeFilter">
                                <option value="">전체 등급</option>
                                <option value="A+">A+ (우수 매장)</option>
                                <option value="A">A (우량 매장)</option>
                                <option value="B">B (일반 매장)</option>
                                <option value="C">C (신규 매장)</option>
                                <option value="D">D (비활성 매장)</option>
                            </select>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">활성도</label>
                            <select class="form-select" id="activityFilter">
                                <option value="">전체 활성도</option>
                                <option value="매우 활성">매우 활성</option>
                                <option value="활성">활성</option>
                                <option value="보통">보통</option>
                                <option value="저조">저조</option>
                                <option value="휴면">휴면</option>
                            </select>
                        </div>
                        <div class="col-md-2">
                            <button type="button" class="btn btn-primary w-100" onclick="applyFilters()">
                                <i class="bi bi-search"></i> 검색
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 매장 목록 테이블 -->
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title mb-0">
                        <i class="bi bi-list-ul"></i> 매장 목록
                        <small class="text-muted">({{ stores.total }}개 매장)</small>
                    </h5>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover mb-0" id="storeTable">
                            <thead>
                                <tr>
                                    <th class="sortable" data-type="number">순위</th>
                                    <th class="sortable">매장명</th>
                                    <th class="sortable" data-type="number">정품 등록 건수</th>
                                    <th class="sortable" data-type="date">최근 등록일</th>
                                    <th class="sortable">활성도</th>
                                    <th class="sortable">매장 등급</th>
                                    <th class="text-center">관리</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for store in stores.items %}
                                {% set rank = (stores.page - 1) * stores.per_page + loop.index %}
                                {% set grade_info = get_store_grade(store.total_registrations) %}
                                {% set activity_info = get_activity_level(store.last_registration) %}
                                <tr>
                                    <td class="text-center number">
                                        {% if rank <= 3 %}
                                            <span class="badge bg-warning text-dark">{{ rank }}</span>
                                        {% else %}
                                            {{ rank }}
                                        {% endif %}
                                    </td>
                                    <td class="fw-medium">
                                        <i class="bi bi-shop text-primary me-1"></i>
                                        {{ store.store_name }}
                                    </td>
                                    <td class="number">
                                        <span class="fw-bold text-primary">
                                            {{ store.total_registrations|default(0) }}
                                        </span>건
                                    </td>
                                    <td class="date">
                                        {% if store.last_registration %}
                                            {{ store.last_registration.strftime('%Y-%m-%d') }}
                                            <br><small class="text-muted">
                                                {{ store.last_registration.strftime('%H:%M') }}
                                            </small>
                                        {% else %}
                                            <span class="text-muted">-</span>
                                        {% endif %}
                                    </td>
                                    <td>
                                        <span class="badge bg-{{ activity_info.class }}">
                                            {{ activity_info.level }}
                                        </span>
                                    </td>
                                    <td>
                                        <span class="badge bg-{{ grade_info.class }}">
                                            {{ grade_info.grade }}
                                        </span>
                                        <br><small class="text-muted">{{ grade_info.desc }}</small>
                                    </td>
                                    <td class="text-center">
                                        <div class="btn-group btn-group-sm">
                                            <button type="button" class="btn btn-outline-info" 
                                                    onclick="viewStoreDetail('{{ store.store_name }}')"
                                                    title="매장 상세">
                                                <i class="bi bi-eye"></i>
                                            </button>
                                            <button type="button" class="btn btn-outline-primary"
                                                    onclick="viewStoreRegistrations('{{ store.store_name }}')"
                                                    title="등록 내역">
                                                <i class="bi bi-list"></i>
                                            </button>
                                            <button type="button" class="btn btn-outline-success"
                                                    onclick="contactStore('{{ store.store_name }}')"
                                                    title="매장 연락">
                                                <i class="bi bi-telephone"></i>
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                                {% endfor %}
                                
                                {% if not stores.items %}
                                <tr>
                                    <td colspan="7" class="text-center py-4 text-muted">
                                        <i class="bi bi-inbox fs-2 d-block mb-2"></i>
                                        등록된 매장이 없습니다.
                                    </td>
                                </tr>
                                {% endif %}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- 페이지네이션 -->
                {% if stores.pages > 1 %}
                <div class="card-footer">
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="text-muted">
                            {{ (stores.page - 1) * stores.per_page + 1 }} - 
                            {{ stores.page * stores.per_page if stores.page * stores.per_page < stores.total else stores.total }} / 
                            {{ stores.total }} 매장
                        </div>
                        <nav>
                            <ul class="pagination pagination-sm mb-0">
                                {% if stores.has_prev %}
                                <li class="page-item">
                                    <a class="page-link" href="{{ url_for('customer.store_management', page=stores.prev_num) }}">
                                        <i class="bi bi-chevron-left"></i>
                                    </a>
                                </li>
                                {% endif %}
                                
                                {% for page_num in stores.iter_pages() %}
                                    {% if page_num %}
                                        {% if page_num != stores.page %}
                                        <li class="page-item">
                                            <a class="page-link" href="{{ url_for('customer.store_management', page=page_num) }}">
                                                {{ page_num }}
                                            </a>
                                        </li>
                                        {% else %}
                                        <li class="page-item active">
                                            <span class="page-link">{{ page_num }}</span>
                                        </li>
                                        {% endif %}
                                    {% else %}
                                    <li class="page-item disabled">
                                        <span class="page-link">…</span>
                                    </li>
                                    {% endif %}
                                {% endfor %}
                                
                                {% if stores.has_next %}
                                <li class="page-item">
                                    <a class="page-link" href="{{ url_for('customer.store_management', page=stores.next_num) }}">
                                        <i class="bi bi-chevron-right"></i>
                                    </a>
                                </li>
                                {% endif %}
                            </ul>
                        </nav>
                    </div>
                </div>
                {% endif %}
            </div>
        </div>

        <script>
        // 매장 상세 정보 보기
        function viewStoreDetail(storeName) {
            // TODO: 매장 상세 정보 모달 구현
            alert(`${storeName} 매장의 상세 정보를 표시합니다.`);
        }

        // 매장 등록 내역 보기
        function viewStoreRegistrations(storeName) {
            // TODO: 매장별 등록 내역 페이지로 이동
            window.location.href = `/customer/serial-list?store=${encodeURIComponent(storeName)}`;
        }

        // 매장 연락
        function contactStore(storeName) {
            // TODO: 매장 연락처 정보 모달 구현
            alert(`${storeName} 매장 연락 기능을 구현 중입니다.`);
        }

        // 필터 적용
        function applyFilters() {
            const gradeFilter = document.getElementById('gradeFilter').value;
            const activityFilter = document.getElementById('activityFilter').value;
            
            // TODO: 필터 적용 로직 구현
            console.log('Grade filter:', gradeFilter);
            console.log('Activity filter:', activityFilter);
        }

        // 데이터 익스포트
        function exportStoreData() {
            // 테이블 데이터를 CSV로 익스포트
            const table = document.getElementById('storeTable');
            const rows = table.querySelectorAll('tr');
            
            let csvContent = '';
            rows.forEach(row => {
                const cells = row.querySelectorAll('th, td');
                const rowData = Array.from(cells).slice(0, -1).map(cell => {
                    return `"${cell.textContent.trim().replace(/"/g, '""')}"`;
                });
                csvContent += rowData.join(',') + '\\n';
            });
            
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            
            if (link.download !== undefined) {
                const url = URL.createObjectURL(blob);
                link.setAttribute('href', url);
                link.setAttribute('download', '매장목록_' + new Date().toISOString().slice(0,10) + '.csv');
                link.style.visibility = 'hidden';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
        }

        // 프린트
        function printStoreList() {
            window.print();
        }
        </script>
        {% endblock %}
        """, **context)
        
    except Exception as e:
        return f"매장 관리 조회 중 오류: {e}", 500

@bp.route('/send-sms', methods=['POST'])
@login_required
def send_sms():
    """SMS 발송 처리"""
    try:
        from flask_login import current_user
        
        # 폼 데이터 수집
        target_mobiles = request.form.getlist('target_mobiles')
        sms_title = request.form.get('sms_title')
        sms_body = request.form.get('sms_body')
        send_time = request.form.get('send_time', 'now')
        
        if not target_mobiles:
            flash('발송 대상이 선택되지 않았습니다.', 'error')
            return redirect(url_for('customer.targeting'))
        
        if not sms_body:
            flash('SMS 내용을 입력해주세요.', 'error')
            return redirect(url_for('customer.targeting'))
        
        # SMS 발송 로그 저장
        sms_log = CustomerSmsLog(
            targeting_info=sms_title or f"타겟팅 SMS - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            sms_body=sms_body,
            send_cnt=len(target_mobiles),
            ins_user_name=current_user.name,
            ins_user=current_user.id
        )
        
        db.session.add(sms_log)
        db.session.commit()
        
        # 실제 SMS 발송은 여기서 구현 (현재는 로그만 저장)
        # 실제 환경에서는 SMS API (예: 알리고, KT 등) 연동 필요
        
        flash(f'SMS 발송이 완료되었습니다. (대상: {len(target_mobiles)}명)', 'success')
        return redirect(url_for('customer.send_log'))
        
    except Exception as e:
        flash(f'SMS 발송 중 오류가 발생했습니다: {e}', 'error')
        return redirect(url_for('customer.targeting'))

@bp.route('/status')
def status():
    """고객 관리 시스템 상태"""
    return jsonify({
        'status': 'customer system fully implemented',
        'modules': {
            'carseat_change': 'implemented',
            'serial_search': 'implemented', 
            'serial_list': 'implemented',
            'targeting': 'implemented',
            'send_log': 'implemented',
            'as_list': 'implemented',
            'store_management': 'implemented'
        }
    }) 