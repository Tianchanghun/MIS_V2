"""
MIS v2 데이터베이스 모델
레거시 시스템 + 멀티테넌트 확장
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
import json

db = SQLAlchemy()

# =============================================================================
# 레거시 시스템 모델 (기존 DB 테이블 정확히 매핑)
# =============================================================================

class User(UserMixin, db.Model):
    """사용자 모델 - 레거시 tbl_member 테이블 정확 매핑"""
    __tablename__ = 'tbl_member'
    
    # 기본 정보
    seq = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id = db.Column(db.String(50))  # 로그인 ID
    password = db.Column(db.Text)  # 평문 저장 (레거시)
    id_number = db.Column(db.String(20))
    name = db.Column(db.String(50))
    sex = db.Column(db.String(1))
    mobile = db.Column(db.String(20))
    extension_number = db.Column(db.String(10))
    
    # 직책/직급 정보
    job_position = db.Column(db.Integer)
    job_position_name = db.Column(db.String(50))
    rank_position = db.Column(db.Integer)
    rank_position_name = db.Column(db.String(50))
    promotion_date = db.Column(db.DateTime)
    
    # 근무 정보
    join_date = db.Column(db.DateTime)
    leave_date = db.Column(db.DateTime)
    rest_s_date = db.Column(db.DateTime)
    rest_e_date = db.Column(db.DateTime)
    
    # 개인 정보
    birth_date = db.Column(db.DateTime)
    birth_type = db.Column(db.String(1))
    email_id = db.Column(db.String(100))
    email_password = db.Column(db.Text)
    married = db.Column(db.String(1))
    children_cnt = db.Column(db.Integer)
    biz_card_num = db.Column(db.String(20))
    
    # 시스템 정보
    super_user = db.Column(db.String(1))  # Y/N
    member_status = db.Column(db.String(1))  # A: 활성, D: 비활성
    in_out_id = db.Column(db.String(20))
    work_group = db.Column(db.Integer)
    
    # 생성/수정 정보
    ins_user = db.Column(db.String(50))
    ins_date = db.Column(db.DateTime)
    upt_user = db.Column(db.String(50))
    upt_date = db.Column(db.DateTime)
    
    # Flask-Login 메서드
    def get_id(self):
        """Flask-Login required method"""
        return str(self.seq)
    
    def verify_password(self, password):
        """비밀번호 확인 - 레거시는 평문 저장"""
        return self.password == password
    
    @property
    def is_active(self):
        """활성 상태 확인"""
        return self.member_status == 'A'
    
    @property
    def is_super_user(self):
        """슈퍼유저 여부 확인"""
        return self.super_user == 'Y'
    
    # 멀티테넌트 지원 메서드
    @property
    def company_id(self):
        """기본 회사 ID 반환 (레거시 호환)"""
        # 사용자의 주 소속 회사 조회
        primary_company = UserCompany.query.filter_by(
            user_seq=self.seq, 
            is_primary=True, 
            is_active=True
        ).first()
        
        if primary_company:
            return primary_company.company_id
        
        # 주 소속이 없으면 첫 번째 접근 가능한 회사
        first_company = UserCompany.query.filter_by(
            user_seq=self.seq, 
            is_active=True
        ).first()
        
        return first_company.company_id if first_company else 1  # 기본값 1
    
    def get_accessible_companies(self):
        """접근 가능한 회사 목록"""
        return UserCompany.query.filter_by(user_seq=self.seq, is_active=True).all()
    
    def has_company_access(self, company_id):
        """특정 회사 접근 권한 확인"""
        if self.is_super_user:
            return True
        
        access = UserCompany.query.filter_by(
            user_seq=self.seq,
            company_id=company_id,
            is_active=True
        ).first()
        return access is not None
    
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'seq': self.seq,
            'id': self.id,
            'name': self.name,
            'member_status': self.member_status,
            'super_user': self.super_user,
            'work_group': self.work_group,
            'biz_card_num': self.biz_card_num,
            'company_id': self.company_id,
            'is_super_user': self.is_super_user
        }
    
    def __repr__(self):
        return f'<User {self.id}({self.name})>'

class Menu(db.Model):
    """메뉴 관리 (tbl_category 매핑) - 실제 레거시 스키마"""
    __tablename__ = 'tbl_category'
    
    seq = db.Column(db.Integer, primary_key=True)
    menu_seq = db.Column(db.Integer)  # 메뉴 그룹 번호
    parent_seq = db.Column(db.Integer)  # 상위 메뉴 SEQ
    depth = db.Column(db.Integer)  # 메뉴 깊이
    sort = db.Column(db.Integer)  # 정렬 순서
    icon = db.Column(db.String(100))  # 메뉴 아이콘
    name = db.Column(db.String(100))  # 메뉴명
    url = db.Column(db.String(200))  # URL
    use_web_yn = db.Column(db.String(1))  # 웹 사용 여부
    use_mob_yn = db.Column(db.String(1))  # 모바일 사용 여부
    use_log_yn = db.Column(db.String(1))  # 로그 사용 여부
    ins_user = db.Column(db.String(50))
    ins_date = db.Column(db.DateTime)
    upt_user = db.Column(db.String(50))
    upt_date = db.Column(db.DateTime)
    
    def to_dict(self):
        """딕셔너리로 변환 (실제 레거시 필드)"""
        return {
            'seq': self.seq,
            'menu_seq': self.menu_seq,
            'parent_seq': self.parent_seq,
            'depth': self.depth,
            'sort': self.sort,
            'icon': self.icon,
            'name': self.name,
            'url': self.url,
            'use_web_yn': self.use_web_yn,
            'use_mob_yn': self.use_mob_yn,
            'use_log_yn': self.use_log_yn,
            'ins_user': self.ins_user,
            'ins_date': self.ins_date.isoformat() if self.ins_date else None,
            'upt_user': self.upt_user,
            'upt_date': self.upt_date.isoformat() if self.upt_date else None
        }
    
    def __repr__(self):
        return f'<Menu {self.name}>'

class Department(db.Model):
    """부서 관리 - 레거시 tbl_department 테이블"""
    __tablename__ = 'tbl_department'
    
    seq = db.Column(db.Integer, primary_key=True)
    dept_name = db.Column(db.String(100))  # 부서명
    report_yn = db.Column(db.String(1))  # 보고서 사용 여부
    font_color = db.Column(db.String(10))  # 폰트 색상
    bg_color = db.Column(db.String(10))  # 배경 색상
    sort = db.Column(db.Integer)  # 정렬 순서
    use_yn = db.Column(db.String(1), default='Y')  # 사용 여부
    ins_user = db.Column(db.String(50))
    ins_date = db.Column(db.DateTime)
    upt_user = db.Column(db.String(50))
    upt_date = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Department {self.dept_name}>'

class MemberDept(db.Model):
    """사용자-부서 관계 - 레거시 tbl_memberdept 테이블"""
    __tablename__ = 'tbl_memberdept'
    
    seq = db.Column(db.Integer, primary_key=True)
    member_seq = db.Column(db.Integer, db.ForeignKey('tbl_member.seq'))
    dept_seq = db.Column(db.Integer, db.ForeignKey('tbl_department.seq'))
    
    # 관계 설정
    member = db.relationship('User', backref='member_depts')
    department = db.relationship('Department', backref='member_depts')

class MemberAuth(db.Model):
    """사용자 권한 - 레거시 tbl_memberauth 테이블"""
    __tablename__ = 'tbl_memberauth'
    
    seq = db.Column(db.Integer, primary_key=True)
    member_seq = db.Column(db.Integer, db.ForeignKey('tbl_member.seq'))
    menu_seq = db.Column(db.Integer, db.ForeignKey('tbl_category.seq'))
    auth_create = db.Column(db.String(1))  # Y/N
    auth_read = db.Column(db.String(1))  # Y/N
    auth_update = db.Column(db.String(1))  # Y/N
    auth_delete = db.Column(db.String(1))  # Y/N
    ins_user = db.Column(db.String(50))
    ins_date = db.Column(db.DateTime)
    upt_user = db.Column(db.String(50))
    upt_date = db.Column(db.DateTime)
    
    # 관계 설정
    member = db.relationship('User', backref='member_auths')
    menu = db.relationship('Menu', backref='member_auths')

class DeptAuth(db.Model):
    """부서 권한 - 레거시 tbl_deptauth 테이블"""
    __tablename__ = 'tbl_deptauth'
    
    seq = db.Column(db.Integer, primary_key=True)
    dept_seq = db.Column(db.Integer, db.ForeignKey('tbl_department.seq'))
    menu_seq = db.Column(db.Integer, db.ForeignKey('tbl_category.seq'))
    auth_create = db.Column(db.String(1))  # Y/N
    auth_read = db.Column(db.String(1))  # Y/N
    auth_update = db.Column(db.String(1))  # Y/N
    auth_delete = db.Column(db.String(1))  # Y/N
    ins_user = db.Column(db.String(50))
    ins_date = db.Column(db.DateTime)
    upt_user = db.Column(db.String(50))
    upt_date = db.Column(db.DateTime)
    
    # 관계 설정
    department = db.relationship('Department', backref='dept_auths')
    menu = db.relationship('Menu', backref='dept_auths')
    
class Code(db.Model):
    """코드 관리 - 레거시 tbl_code 테이블"""
    __tablename__ = 'tbl_code'
    
    seq = db.Column(db.Integer, primary_key=True)
    code_seq = db.Column(db.Integer)  # 코드 그룹 번호
    parent_seq = db.Column(db.Integer)  # 상위 코드 SEQ
    depth = db.Column(db.Integer)  # 코드 깊이
    sort = db.Column(db.Integer)  # 정렬 순서
    code = db.Column(db.String(50))  # 코드
    code_name = db.Column(db.String(100))  # 코드명
    code_info = db.Column(db.Text)  # 코드 설명
    ins_user = db.Column(db.String(50))
    ins_date = db.Column(db.DateTime)
    upt_user = db.Column(db.String(50))
    upt_date = db.Column(db.DateTime)
    
    @classmethod
    def get_code_groups(cls):
        """코드 그룹 목록 조회 (depth=0)"""
        return cls.query.filter_by(depth=0).order_by(cls.sort.asc(), cls.code_name.asc()).all()
    
    @classmethod
    def get_codes_by_parent_seq(cls, parent_seq):
        """상위 코드의 하위 코드들 조회"""
        return cls.query.filter_by(parent_seq=parent_seq).order_by(cls.sort.asc(), cls.code_name.asc()).all()
    
    @classmethod
    def get_codes_by_group_code(cls, group_code):
        """그룹 코드로 하위 코드들 조회"""
        group = cls.query.filter_by(code=group_code, depth=0).first()
        if group:
            return cls.get_codes_by_parent_seq(group.seq)
        return []
    
    def to_dict(self):
        """코드 정보를 딕셔너리로 변환"""
        return {
            'seq': self.seq,
            'code_seq': self.code_seq,
            'parent_seq': self.parent_seq,
            'depth': self.depth,
            'sort': self.sort,
            'code': self.code,
            'code_name': self.code_name,
            'code_info': self.code_info,
            'ins_user': self.ins_user,
            'ins_date': self.ins_date.isoformat() if self.ins_date else None,
            'upt_user': self.upt_user,
            'upt_date': self.upt_date.isoformat() if self.upt_date else None
        }
    
    def __repr__(self):
        return f'<Code {self.code}:{self.code_name}>'

class Brand(db.Model):
    """브랜드 정보 (tbl_brand 레거시 테이블)"""
    __tablename__ = 'tbl_brand'
    
    seq = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)  # 멀티테넌트 확장
    brand_code = db.Column(db.String(10), nullable=False)
    brand_eng_name = db.Column(db.String(50), nullable=False)
    brand_name = db.Column(db.String(50), nullable=False)
    brand_info = db.Column(db.String(255), nullable=False)
    sort = db.Column(db.Integer, nullable=False, default=1)
    use_yn = db.Column(db.String(1), nullable=False, default='Y')
    ins_user = db.Column(db.String(50), nullable=False)
    ins_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    upt_user = db.Column(db.String(50))
    upt_date = db.Column(db.DateTime)
    
    def to_dict(self):
        """브랜드 정보를 딕셔너리로 변환"""
        return {
            'seq': self.seq,
            'company_id': self.company_id,
            'brand_code': self.brand_code,
            'brand_eng_name': self.brand_eng_name,
            'brand_name': self.brand_name,
            'brand_info': self.brand_info,
            'sort': self.sort,
            'use_yn': self.use_yn,
            'ins_user': self.ins_user,
            'ins_date': self.ins_date.isoformat() if self.ins_date else None,
            'upt_user': self.upt_user,
            'upt_date': self.upt_date.isoformat() if self.upt_date else None
        }

# =============================================================================
# 멀티테넌트 확장 모델 (새로 추가, 기존 테이블과 연동)
# =============================================================================

class Company(db.Model):
    """회사 마스터 - 멀티테넌트 확장"""
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    company_code = db.Column(db.String(20), unique=True, nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    company_name_en = db.Column(db.String(100))
    
    # 회사 기본 정보
    business_number = db.Column(db.String(20))
    ceo_name = db.Column(db.String(50))
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    
    # 시스템 설정
    is_active = db.Column(db.Boolean, default=True)
    logo_url = db.Column(db.String(500))
    theme_color = db.Column(db.String(10), default='#007bff')
    
    # 멀티테넌트 설정
    data_isolation_level = db.Column(db.String(20), default='STRICT')  # STRICT, SHARED
    allow_data_sharing = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserCompany(db.Model):
    """사용자-회사 관계 - 멀티테넌트 확장"""
    __tablename__ = 'user_companies'
    
    id = db.Column(db.Integer, primary_key=True)
    user_seq = db.Column(db.Integer, db.ForeignKey('tbl_member.seq'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # 권한 설정
    role = db.Column(db.String(50), nullable=False, default='user')  # admin, manager, user
    permissions = db.Column(db.JSON)  # 세부 권한 설정
    
    # 상태 정보
    is_primary = db.Column(db.Boolean, default=False)  # 주 소속 회사 여부
    is_active = db.Column(db.Boolean, default=True)
    
    # 접근 제한
    access_start_date = db.Column(db.Date)
    access_end_date = db.Column(db.Date)
    last_access_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    user = db.relationship('User', backref='user_companies')
    company = db.relationship('Company', backref='user_companies')
    
    @property
    def user_id(self):
        """하위 호환성을 위한 user_id 속성"""
        return self.user_seq

# ==================== ERPia 배치 설정 모델 ====================

class CompanyErpiaConfig(db.Model):
    """회사별 ERPia 연동 설정"""
    __tablename__ = 'company_erpia_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    admin_code = db.Column(db.String(100), nullable=False, comment='ERPia 관리자 코드')
    password_encrypted = db.Column(db.Text, nullable=False, comment='ERPia 비밀번호 (암호화)')
    api_url = db.Column(db.String(500), default='http://www.erpia.net/xml/xml.asp', comment='ERPia API URL')
    
    # 배치 스케줄 설정 (기존 컬럼)
    batch_enabled = db.Column(db.Boolean, default=True, comment='배치 활성화 여부')
    batch_hour = db.Column(db.Integer, default=2, comment='배치 실행 시간')
    batch_minute = db.Column(db.Integer, default=0, comment='배치 실행 분')
    
    # 사은품 처리 설정 (기존 컬럼)
    auto_gift_classify = db.Column(db.Boolean, default=True, comment='사은품 자동 분류')
    gift_keywords = db.Column(db.Text, comment='사은품 키워드 (JSON)')
    
    # 동기화 상태 정보
    last_sync_date = db.Column(db.DateTime, comment='마지막 동기화 일시')
    sync_error_count = db.Column(db.Integer, default=0, comment='연속 동기화 오류 횟수')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계
    company = db.relationship("Company", back_populates="erpia_config")
    
    @property
    def password(self):
        """비밀번호 getter (복호화)"""
        # 현재는 평문으로 저장 (추후 암호화 구현)
        return self.password_encrypted
    
    @password.setter
    def password(self, value):
        """비밀번호 setter (암호화)"""
        # 현재는 평문으로 저장 (추후 암호화 구현)
        self.password_encrypted = value
    
    @property
    def is_active(self):
        """활성화 여부 (batch_enabled 매핑)"""
        return self.batch_enabled
    
    @is_active.setter
    def is_active(self, value):
        """활성화 여부 setter"""
        self.batch_enabled = value
    
    def to_dict(self):
        """설정 정보를 딕셔너리로 변환 (비밀번호 제외)"""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'admin_code': self.admin_code,
            'api_url': self.api_url,
            'is_active': self.is_active,
            'last_sync_date': self.last_sync_date.isoformat() if self.last_sync_date else None,
            'sync_error_count': self.sync_error_count or 0,
            'batch_hour': self.batch_hour,
            'batch_minute': self.batch_minute,
            'auto_gift_classify': self.auto_gift_classify,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ErpiaBatchSettings(db.Model):
    """ERPia 배치 설정 (웹 관리)"""
    __tablename__ = 'erpia_batch_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    setting_key = db.Column(db.String(100), nullable=False, comment='설정 키')
    setting_value = db.Column(db.Text, nullable=False, comment='설정 값')
    setting_type = db.Column(db.String(50), nullable=False, comment='설정 타입 (time, number, boolean, text)')
    description = db.Column(db.Text, comment='설정 설명')
    min_value = db.Column(db.Integer, comment='최소값')
    max_value = db.Column(db.Integer, comment='최대값')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('company_id', 'setting_key', name='uk_company_setting'),
    )
    
    def to_dict(self):
        """설정을 딕셔너리로 변환"""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'setting_key': self.setting_key,
            'setting_value': self.setting_value,
            'setting_type': self.setting_type,
            'description': self.description,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ErpiaBatchLog(db.Model):
    """ERPia 배치 실행 로그"""
    __tablename__ = 'erpia_batch_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    admin_code = db.Column(db.String(100), comment='ERPia 관리자 코드 (회사 식별용)')
    batch_type = db.Column(db.String(50), nullable=False, comment='배치 타입 (daily_sales, manual, test)')
    start_time = db.Column(db.DateTime, nullable=False, comment='시작 시간')
    end_time = db.Column(db.DateTime, comment='종료 시간')
    status = db.Column(db.String(20), nullable=False, comment='상태 (RUNNING, SUCCESS, FAILED)')
    
    # 실행 결과
    total_pages = db.Column(db.Integer, comment='총 페이지 수')
    processed_orders = db.Column(db.Integer, comment='처리된 주문 수')
    processed_products = db.Column(db.Integer, comment='처리된 상품 수')
    gift_products = db.Column(db.Integer, comment='사은품 상품 수')
    error_count = db.Column(db.Integer, default=0, comment='오류 수')
    
    # 상세 정보
    date_range = db.Column(db.String(50), comment='날짜 범위 (20250805-20250805)')
    error_message = db.Column(db.Text, comment='오류 메시지')
    execution_details = db.Column(db.Text, comment='실행 상세 정보 (JSON)')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """로그를 딕셔너리로 변환"""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'admin_code': self.admin_code,
            'batch_type': self.batch_type,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'total_pages': self.total_pages,
            'processed_orders': self.processed_orders,
            'processed_products': self.processed_products,
            'gift_products': self.gift_products,
            'error_count': self.error_count,
            'date_range': self.date_range,
            'error_message': self.error_message,
            'execution_details': self.execution_details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# ==================== 매출분석 테이블 (회사별 분리) ====================

class SalesAnalysisMaster(db.Model):
    """매출 분석 마스터 테이블 (회사별 데이터 분리)"""
    __tablename__ = 'sales_analysis_master'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    sales_no = db.Column(db.String(50), nullable=False, comment='판매 번호')
    sale_date = db.Column(db.Date, nullable=False, comment='판매 일자')
    site_code = db.Column(db.String(50), comment='사이트 코드')
    ger_code = db.Column(db.String(50), comment='거래처 코드')
    customer_name = db.Column(db.String(100), comment='고객명')
    
    # 상품 정보
    product_code = db.Column(db.String(50), comment='상품 코드')
    product_name = db.Column(db.String(200), comment='상품명')
    product_type = db.Column(db.String(20), comment='상품 유형 (PRODUCT, GIFT)')
    brand_code = db.Column(db.String(50), comment='브랜드 코드')
    brand_name = db.Column(db.String(100), comment='브랜드명')
    
    # 금액 및 수량
    quantity = db.Column(db.Integer, comment='수량')
    supply_price = db.Column(db.Integer, comment='공급가')
    sell_price = db.Column(db.Integer, comment='판매가')
    total_amount = db.Column(db.Integer, comment='총 금액')
    delivery_amt = db.Column(db.Integer, comment='배송비')
    
    # 분류 정보
    is_revenue = db.Column(db.Boolean, default=True, comment='매출 집계 포함 여부')
    analysis_category = db.Column(db.String(50), comment='분석 카테고리')
    gift_classification = db.Column(db.String(50), comment='사은품 분류 (AUTO, MANUAL, KEYWORD)')
    
    # 배송 정보
    recipient_name = db.Column(db.String(100), comment='수령인명')
    address = db.Column(db.String(500), comment='주소')
    tracking_no = db.Column(db.String(100), comment='송장번호')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 인덱스
    __table_args__ = (
        db.Index('idx_sales_company_date', 'company_id', 'sale_date'),
        db.Index('idx_sales_company_type', 'company_id', 'product_type'),
        db.Index('idx_sales_no', 'sales_no'),
    )
    
    def to_dict(self):
        """매출 데이터를 딕셔너리로 변환"""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'sales_no': self.sales_no,
            'sale_date': self.sale_date.isoformat() if self.sale_date else None,
            'site_code': self.site_code,
            'ger_code': self.ger_code,
            'customer_name': self.customer_name,
            'product_code': self.product_code,
            'product_name': self.product_name,
            'product_type': self.product_type,
            'brand_code': self.brand_code,
            'brand_name': self.brand_name,
            'quantity': self.quantity,
            'supply_price': self.supply_price,
            'sell_price': self.sell_price,
            'total_amount': self.total_amount,
            'delivery_amt': self.delivery_amt,
            'is_revenue': self.is_revenue,
            'analysis_category': self.analysis_category,
            'gift_classification': self.gift_classification,
            'recipient_name': self.recipient_name,
            'address': self.address,
            'tracking_no': self.tracking_no,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# =============================================================================
# ERPia 연동 모델 (기존 유지, 회사별 분리 지원)
# =============================================================================

class ErpiaOrderMaster(db.Model):
    """ERPia 주문 마스터"""
    __tablename__ = 'erpia_order_master'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, default=1)
    
    # ERPia 필드들 (기존 유지)
    site_key_code = db.Column(db.String(10))
    site_code = db.Column(db.String(10))
    site_id = db.Column(db.String(50))
    ger_code = db.Column(db.String(10))
    sl_no = db.Column(db.String(20), nullable=False, index=True)
    order_no = db.Column(db.String(50))
    j_date = db.Column(db.DateTime)
    j_time = db.Column(db.String(10))
    j_email = db.Column(db.String(100))
    j_id = db.Column(db.String(50))
    j_name = db.Column(db.String(100))
    j_tel = db.Column(db.String(20))
    j_hp = db.Column(db.String(20))
    j_post = db.Column(db.String(10))
    j_addr = db.Column(db.Text)
    a_addr = db.Column(db.Text)
    a_sido = db.Column(db.String(50))
    a_sigungu = db.Column(db.String(50))
    m_date = db.Column(db.DateTime)
    b_amt = db.Column(db.Numeric(15, 2))
    dis_gong_amt = db.Column(db.Numeric(15, 2))
    claim_yn = db.Column(db.String(1))
    site_ct_code = db.Column(db.String(10))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 관계 설정
    company = db.relationship('Company')

# =============================================================================
# 초기화 함수
# =============================================================================

def init_db():
    """데이터베이스 초기화"""
    try:
        db.create_all()
        print("✅ 레거시 + 멀티테넌트 데이터베이스 초기화 완료")
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 실패: {e}")

def create_default_data():
    """기본 데이터 생성"""
    try:
        # 기존 데이터 확인
        if Company.query.count() > 0:
            print("✅ 기본 데이터가 이미 존재합니다.")
            
            # ERPia 설정이 없는 경우에만 추가
            if CompanyErpiaConfig.query.count() == 0:
                create_erpia_default_settings()
            
            return
        
        print("🔧 기본 데이터 생성 중...")
        
        # 1. 회사 생성
        aone = Company(
            company_name='에이원',
            company_code='AONE',
            is_active=True,
            is_primary=True
        )
        db.session.add(aone)
        
        aone_world = Company(
            company_name='에이원 월드',
            company_code='AONE_WORLD',
            is_active=True,
            is_primary=False
        )
        db.session.add(aone_world)
        
        db.session.flush()  # ID 생성을 위해
        
        # 2. chjeon 사용자의 주소속을 에이원으로 설정
        chjeon = User.query.filter_by(id='chjeon').first()
        if chjeon:
            # 기존 회사 관계 삭제
            UserCompany.query.filter_by(user_seq=chjeon.seq).delete()
            
            # 에이원을 주소속으로 설정
            user_company_aone = UserCompany(
                user_seq=chjeon.seq,
                company_id=aone.id,
                is_primary=True,
                is_active=True,
                joined_at=datetime.utcnow()
            )
            db.session.add(user_company_aone)
            
            # 에이원월드를 부속으로 설정
            user_company_world = UserCompany(
                user_seq=chjeon.seq,
                company_id=aone_world.id,
                is_primary=False,
                is_active=True,
                joined_at=datetime.utcnow()
            )
            db.session.add(user_company_world)
            
            print(f"✅ {chjeon.name} 사용자의 주소속을 에이원으로 설정했습니다.")
        
        # 3. admin 사용자도 동일하게 설정
        admin = User.query.filter_by(id='admin').first()
        if admin:
            UserCompany.query.filter_by(user_seq=admin.seq).delete()
            
            user_company_aone = UserCompany(
                user_seq=admin.seq,
                company_id=aone.id,
                is_primary=True,
                is_active=True,
                joined_at=datetime.utcnow()
            )
            db.session.add(user_company_aone)
            
            user_company_world = UserCompany(
                user_seq=admin.seq,
                company_id=aone_world.id,
                is_primary=False,
                is_active=True,
                joined_at=datetime.utcnow()
            )
            db.session.add(user_company_world)
            
            print(f"✅ {admin.name} 사용자 설정 완료")
        
        # 4. ERPia 설정 생성 (기존 스키마 호환)
        erpia_config_aone = CompanyErpiaConfig(
            company_id=aone.id,
            admin_code='aone',
            password_encrypted='ka22fslfod1vid',  # 실제로는 암호화 필요
            api_url='http://www.erpia.net/xml/xml.asp',
            batch_enabled=True,
            batch_hour=2,
            batch_minute=0,
            auto_gift_classify=True,
            gift_keywords='["사은품", "증정품", "무료", "샘플", "체험"]'
        )
        db.session.add(erpia_config_aone)
        
        # 5. 기본 배치 설정 생성 (에이원)
        default_batch_settings = [
            {
                'setting_key': 'schedule_time',
                'setting_value': '02:00',
                'setting_type': 'time',
                'description': '일일 배치 실행 시간',
                'min_value': None,
                'max_value': None
            },
            {
                'setting_key': 'call_interval',
                'setting_value': '3',
                'setting_type': 'number',
                'description': 'API 호출 간격 (초)',
                'min_value': 1,
                'max_value': 60
            },
            {
                'setting_key': 'page_size',
                'setting_value': '30',
                'setting_type': 'number',
                'description': '페이지당 데이터 건수',
                'min_value': 1,
                'max_value': 30
            },
            {
                'setting_key': 'auto_batch_enabled',
                'setting_value': 'true',
                'setting_type': 'boolean',
                'description': '자동 배치 활성화',
                'min_value': None,
                'max_value': None
            },
            {
                'setting_key': 'auto_gift_classify',
                'setting_value': 'true',
                'setting_type': 'boolean',
                'description': '사은품 자동 분류',
                'min_value': None,
                'max_value': None
            },
            {
                'setting_key': 'retry_count',
                'setting_value': '3',
                'setting_type': 'number',
                'description': '재시도 횟수',
                'min_value': 1,
                'max_value': 10
            },
            {
                'setting_key': 'schedule_type',
                'setting_value': 'daily',
                'setting_type': 'text',
                'description': '스케줄 타입 (daily, weekly, manual)',
                'min_value': None,
                'max_value': None
            },
            {
                'setting_key': 'schedule_days',
                'setting_value': '1,2,3,4,5,6,7',
                'setting_type': 'text',
                'description': '실행 요일 (1=월, 7=일)',
                'min_value': None,
                'max_value': None
            }
        ]
        
        for setting_data in default_batch_settings:
            # 에이원 설정
            setting_aone = ErpiaBatchSettings(
                company_id=aone.id,
                **setting_data
            )
            db.session.add(setting_aone)
            
            # 에이원월드 설정 (시간만 다르게)
            setting_world = ErpiaBatchSettings(
                company_id=aone_world.id,
                **setting_data
            )
            # 에이원월드는 04:00으로 설정 (충돌 방지)
            if setting_data['setting_key'] == 'schedule_time':
                setting_world.setting_value = '04:00'
            db.session.add(setting_world)
        
        db.session.commit()
        print("✅ 레거시 + 멀티테넌트 기본 데이터 생성 완료")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ 기본 데이터 생성 실패: {e}")
        raise

def create_erpia_default_settings():
    """ERPia 기본 설정만 생성"""
    try:
        aone = Company.query.filter_by(company_code='AONE').first()
        aone_world = Company.query.filter_by(company_code='AONE_WORLD').first()
        
        if not aone or not aone_world:
            print("❌ 회사 정보가 없습니다.")
            return
        
        # ERPia 설정이 없으면 생성 (기존 스키마 호환)
        if not CompanyErpiaConfig.query.filter_by(company_id=aone.id).first():
            erpia_config_aone = CompanyErpiaConfig(
                company_id=aone.id,
                admin_code='aone',
                password_encrypted='ka22fslfod1vid',
                api_url='http://www.erpia.net/xml/xml.asp',
                batch_enabled=True,
                batch_hour=2,
                batch_minute=0,
                auto_gift_classify=True,
                gift_keywords='["사은품", "증정품", "무료", "샘플", "체험"]'
            )
            db.session.add(erpia_config_aone)
            print("✅ 에이원 ERPia 설정 생성")
        
        # 배치 설정 생성
        default_batch_settings = [
            ('schedule_time', '02:00', 'time', '일일 배치 실행 시간'),
            ('call_interval', '3', 'number', 'API 호출 간격 (초)'),
            ('page_size', '30', 'number', '페이지당 데이터 건수'),
            ('auto_batch_enabled', 'true', 'boolean', '자동 배치 활성화'),
            ('auto_gift_classify', 'true', 'boolean', '사은품 자동 분류'),
            ('retry_count', '3', 'number', '재시도 횟수'),
            ('schedule_type', 'daily', 'text', '스케줄 타입'),
            ('schedule_days', '1,2,3,4,5,6,7', 'text', '실행 요일')
        ]
        
        for key, value, type_, desc in default_batch_settings:
            if not ErpiaBatchSettings.query.filter_by(company_id=aone.id, setting_key=key).first():
                setting_aone = ErpiaBatchSettings(
                    company_id=aone.id,
                    setting_key=key,
                    setting_value=value,
                    setting_type=type_,
                    description=desc
                )
                db.session.add(setting_aone)
            
            if not ErpiaBatchSettings.query.filter_by(company_id=aone_world.id, setting_key=key).first():
                # 에이원월드는 04:00으로 설정 (충돌 방지)
                world_value = '04:00' if key == 'schedule_time' else value
                setting_world = ErpiaBatchSettings(
                    company_id=aone_world.id,
                    setting_key=key,
                    setting_value=world_value,
                    setting_type=type_,
                    description=desc
                )
                db.session.add(setting_world)
        
        db.session.commit()
        print("✅ ERPia 기본 설정 생성 완료")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ ERPia 설정 생성 실패: {e}")

# Company 모델에 관계 추가
Company.erpia_config = db.relationship("CompanyErpiaConfig", back_populates="company", uselist=False) 