"""
멀티테넌트 미들웨어
회사 컨텍스트 자동 관리 및 데이터 접근 제어
"""
from flask import request, session, g, abort, current_app
from functools import wraps
from app.common.models import User, Company, UserCompany, db
import datetime

class MultiTenantMiddleware:
    """멀티테넌트 미들웨어"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Flask 앱에 미들웨어 등록"""
        app.before_request(self.before_request)
        app.teardown_appcontext(self.teardown_appcontext)
    
    def before_request(self):
        """요청 전 회사 컨텍스트 설정"""
        try:
            # 현재 활성 회사 ID 가져오기
            current_company_id = session.get('current_company_id')
            user_id = session.get('member_seq')
            
            if current_company_id and user_id:
                # 사용자가 해당 회사에 접근 권한이 있는지 확인
                if self.has_company_access(user_id, current_company_id):
                    g.current_company_id = current_company_id
                    g.current_company = self.get_company(current_company_id)
                    g.current_user_id = user_id
                else:
                    # 권한이 없으면 기본 회사로 설정
                    default_company = self.get_user_default_company(user_id)
                    if default_company:
                        g.current_company_id = default_company.id
                        g.current_company = default_company
                        session['current_company_id'] = default_company.id
                    else:
                        g.current_company_id = None
                        g.current_company = None
            else:
                # 로그인된 사용자의 기본 회사 설정
                if user_id:
                    default_company = self.get_user_default_company(user_id)
                    if default_company:
                        g.current_company_id = default_company.id
                        g.current_company = default_company
                        session['current_company_id'] = default_company.id
                        
                g.current_company_id = session.get('current_company_id')
                g.current_company = self.get_company(g.current_company_id) if g.current_company_id else None
                g.current_user_id = user_id
            
        except Exception as e:
            current_app.logger.error(f"멀티테넌트 미들웨어 오류: {e}")
            g.current_company_id = None
            g.current_company = None
            g.current_user_id = None
    
    def teardown_appcontext(self, exception):
        """요청 종료 후 정리"""
        pass
    
    def has_company_access(self, user_id: int, company_id: int) -> bool:
        """사용자의 회사 접근 권한 확인"""
        try:
            # 슈퍼유저는 모든 회사 접근 가능
            user = User.query.filter_by(seq=user_id).first()
            if user and user.is_super_user:
                return True
            
            # 일반 사용자는 할당된 회사만 접근 가능
            access = UserCompany.query.filter_by(
                user_seq=user_id,  # user_id → user_seq
                company_id=company_id,
                is_active=True
            ).first()
            
            return access is not None
        except Exception:
            return False
    
    def get_company(self, company_id: int):
        """회사 정보 조회"""
        try:
            if company_id:
                return Company.query.filter_by(id=company_id, is_active=True).first()
        except Exception:
            pass
        return None
    
    def get_user_default_company(self, user_id: int):
        """사용자의 기본 회사 조회"""
        try:
            # 주 소속 회사가 있으면 우선
            primary_access = UserCompany.query.filter_by(
                user_seq=user_id,
                is_primary=True,
                is_active=True
            ).first()
            
            if primary_access:
                return primary_access.company
            
            # 주 소속이 없으면 첫 번째 접근 가능한 회사
            first_access = UserCompany.query.filter_by(
                user_seq=user_id,
                is_active=True
            ).first()
            
            if first_access:
                return first_access.company
                
        except Exception:
            pass
        return None
    
    def log_access(self, action_type: str, resource_type: str = None, resource_id: str = None, 
                   success: bool = True, error_message: str = None):
        """접근 로그 기록"""
        try:
            if hasattr(g, 'current_user_id') and g.current_user_id:
                # UserAccessLog 모델이 제거되었으므로, 임시로 로그 기록 로직을 제거합니다.
                # 필요한 경우, 다른 로깅 메커니즘을 사용해야 합니다.
                pass # 임시 제거
        except Exception as e:
            current_app.logger.error(f"접근 로그 기록 실패: {e}")

# 전역 미들웨어 인스턴스
multi_tenant = MultiTenantMiddleware()

# =============================================================================
# 데코레이터 함수들
# =============================================================================

def require_company_access(permission=None):
    """회사 접근 권한 필요 데코레이터"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_company_id') or not g.current_company_id:
                multi_tenant.log_access('ACCESS_DENIED', error_message='회사가 선택되지 않음')
                abort(403, '회사를 선택해주세요.')
            
            if permission:
                if not check_permission(g.current_company_id, permission):
                    multi_tenant.log_access('PERMISSION_DENIED', error_message=f'권한 부족: {permission}')
                    abort(403, '권한이 없습니다.')
            
            multi_tenant.log_access('ACCESS_GRANTED', resource_type=f.__name__)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def company_context(company_id_param='company_id'):
    """URL 파라미터로 회사 컨텍스트 설정"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            company_id = kwargs.get(company_id_param) or request.json.get(company_id_param) if request.is_json else None
            
            if company_id:
                # 접근 권한 확인
                user_id = session.get('member_seq')
                if not multi_tenant.has_company_access(user_id, company_id):
                    multi_tenant.log_access('ACCESS_DENIED', error_message=f'회사 접근 권한 없음: {company_id}')
                    abort(403, '해당 회사에 접근 권한이 없습니다.')
                
                g.current_company_id = company_id
                g.current_company = multi_tenant.get_company(company_id)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_data_access(resource_type: str):
    """데이터 접근 로깅 데코레이터"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
                multi_tenant.log_access('DATA_ACCESS', resource_type=resource_type, success=True)
                return result
            except Exception as e:
                multi_tenant.log_access('DATA_ACCESS', resource_type=resource_type, 
                                      success=False, error_message=str(e))
                raise
        return decorated_function
    return decorator

def check_permission(company_id: int, permission: str) -> bool:
    """권한 확인 함수"""
    try:
        user_id = getattr(g, 'current_user_id', None)
        if not user_id:
            return False
        
        # 슈퍼유저는 모든 권한
        user = User.query.filter_by(seq=user_id).first()
        if user and user.is_super_user:
            return True
        
        # 사용자-회사 관계에서 권한 확인
        user_company = UserCompany.query.filter_by(
            user_seq=user_id,
            company_id=company_id,
            is_active=True
        ).first()
        
        if not user_company:
            return False
        
        # 관리자는 모든 권한
        if user_company.role == 'admin':
            return True
        
        # 세부 권한 확인 (추후 구현)
        permissions = user_company.permissions or {}
        return permissions.get(permission, False)
        
    except Exception:
        return False

# =============================================================================
# 멀티테넌트 쿼리 헬퍼
# =============================================================================

class MultiTenantQueryBuilder:
    """멀티테넌트 쿼리 빌더"""
    
    @staticmethod
    def apply_company_filter(query, model, company_id=None):
        """회사 필터 자동 적용"""
        if company_id is None:
            company_id = getattr(g, 'current_company_id', None)
        
        if company_id and hasattr(model, 'company_id'):
            query = query.filter(model.company_id == company_id)
        
        return query
    
    @staticmethod
    def get_accessible_companies(user_id: int) -> list:
        """사용자가 접근 가능한 회사 목록"""
        try:
            from app.common.models import UserCompany
            
            companies = db.session.query(UserCompany).filter_by(
                user_seq=user_id,
                is_active=True
            ).all()
            
            return [uc.company for uc in companies if uc.company and uc.company.is_active]
        except Exception:
            return []
    
    @staticmethod
    def can_access_shared_data(source_company_id: int, target_company_id: int, 
                             data_type: str) -> bool:
        """공유 데이터 접근 권한 확인"""
        try:
            from app.common.models import SharedDataPolicy
            
            policy = SharedDataPolicy.query.filter_by(
                source_company_id=source_company_id,
                target_company_id=target_company_id,
                data_type=data_type,
                is_active=True
            ).first()
            
            return policy is not None
        except Exception:
            return False 