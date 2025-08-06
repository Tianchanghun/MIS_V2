#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
멀티테넌트 시스템 유틸리티
회사별 데이터 격리 및 관리
"""

from flask import request, session, g, abort, current_app
from functools import wraps
from app.common.models import Company, UserCompany

class MultiTenantMiddleware:
    """멀티테넌트 미들웨어"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        app.before_request(self.before_request)
    
    def before_request(self):
        """요청 전 회사 컨텍스트 설정"""
        
        # 현재 활성 회사 ID 가져오기 (세션 우선, 기본값: 에이원)
        current_company_id = session.get('current_company_id')
        user_seq = session.get('member_seq')
        
        if current_company_id and user_seq:
            # 사용자가 해당 회사에 접근 권한이 있는지 확인
            if self.has_company_access(user_seq, current_company_id):
                g.current_company_id = current_company_id
                g.current_company = self.get_company(current_company_id)
            else:
                # 권한이 없으면 기본 회사로 설정
                g.current_company_id = self.get_user_primary_company(user_seq)
                g.current_company = self.get_company(g.current_company_id)
                session['current_company_id'] = g.current_company_id
        elif user_seq:
            # 로그인했지만 회사가 설정되지 않은 경우 - 기본 회사 설정
            g.current_company_id = self.get_user_primary_company(user_seq)
            g.current_company = self.get_company(g.current_company_id)
            session['current_company_id'] = g.current_company_id
        else:
            # 로그인하지 않은 경우 기본값
            g.current_company_id = 1  # 에이원
            g.current_company = self.get_company(1)
    
    def has_company_access(self, user_seq: int, company_id: int) -> bool:
        """사용자의 회사 접근 권한 확인"""
        access = UserCompany.query.filter_by(
            user_seq=user_seq,
            company_id=company_id,
            is_active=True
        ).first()
        
        return access is not None
    
    def get_user_primary_company(self, user_seq: int) -> int:
        """사용자의 주 소속 회사 ID 반환"""
        primary = UserCompany.query.filter_by(
            user_seq=user_seq,
            is_primary=True,
            is_active=True
        ).first()
        
        if primary:
            return primary.company_id
        
        # primary가 없으면 첫 번째 활성 회사 반환
        first_company = UserCompany.query.filter_by(
            user_seq=user_seq,
            is_active=True
        ).first()
        
        return first_company.company_id if first_company else 1
    
    def get_company(self, company_id: int):
        """회사 정보 조회"""
        return Company.query.get(company_id)

def require_company_access(permission=None):
    """회사 접근 권한 필요 데코레이터"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_company_id') or not g.current_company_id:
                abort(403, '회사를 선택해주세요.')
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def company_context(company_id_param='company_id'):
    """URL 파라미터로 회사 컨텍스트 설정"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            company_id = kwargs.get(company_id_param) or request.json.get(company_id_param)
            
            if company_id:
                g.current_company_id = company_id
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class MultiTenantQueryBuilder:
    """멀티테넌트 쿼리 빌더"""
    
    @staticmethod
    def apply_company_filter(query, model, company_id=None):
        """회사 필터 자동 적용"""
        
        if company_id is None:
            company_id = getattr(g, 'current_company_id', 1)
        
        if company_id and hasattr(model, 'company_id'):
            query = query.filter(model.company_id == company_id)
        
        return query
    
    @staticmethod
    def get_current_company_id():
        """현재 활성 회사 ID 조회"""
        return getattr(g, 'current_company_id', 1)
    
    @staticmethod
    def get_current_company():
        """현재 활성 회사 정보 조회"""
        return getattr(g, 'current_company', None)

def get_company_list():
    """활성화된 회사 목록 조회"""
    return Company.query.filter_by(is_active=True).all()

def get_user_companies(user_seq):
    """사용자가 접근 가능한 회사 목록 조회"""
    return UserCompany.query.filter_by(
        user_seq=user_seq,
        is_active=True
    ).join(Company).filter(Company.is_active == True).all()

def get_company_by_code(company_code):
    """회사 코드로 회사 조회"""
    return Company.query.filter_by(company_code=company_code, is_active=True).first()

def switch_company(company_id, user_seq=None):
    """회사 전환"""
    if user_seq is None:
        user_seq = session.get('member_seq')
    
    if not user_seq:
        return False
    
    # 접근 권한 확인
    access = UserCompany.query.filter_by(
        user_seq=user_seq,
        company_id=company_id,
        is_active=True
    ).first()
    
    if not access:
        return False
    
    company = Company.query.get(company_id)
    if not company or not company.is_active:
        return False
    
    # 세션 업데이트
    session['current_company_id'] = company_id
    g.current_company_id = company_id
    g.current_company = company
    
    # 마지막 접근 시간 업데이트
    from datetime import datetime
    access.last_access_at = datetime.utcnow()
    from app import db
    db.session.commit()
    
    return True 