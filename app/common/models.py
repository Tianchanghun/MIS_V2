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
    """사용자 모델 - 간소화 + 멀티테넌트 강화"""
    __tablename__ = 'tbl_member'
    
    # 기본 정보
    seq = db.Column(db.Integer, primary_key=True, autoincrement=True)
    login_id = db.Column('id', db.String(50), nullable=False)  # 실제 컬럼명: id
    password = db.Column('password', db.Text, nullable=False)  # 실제 컬럼명: password
    name = db.Column('name', db.String(50), nullable=False)  # 실제 컬럼명: name
    id_number = db.Column('id_number', db.String(20))  # 실제 컬럼명: id_number
    
    # 연락처 정보
    email = db.Column('email_id', db.String(100))  # 실제 컬럼명: email_id
    mobile = db.Column('mobile', db.String(20))  # 실제 컬럼명: mobile
    extension_number = db.Column('extension_number', db.String(10))  # 실제 컬럼명: extension_number
    
    # 시스템 정보
    super_user = db.Column('super_user', db.String(1), default='N')  # 실제 컬럼명: super_user
    member_status = db.Column('member_status', db.String(1), default='Y')  # 실제 컬럼명: member_status
    
    # 생성/수정 정보
    ins_user = db.Column('ins_user', db.String(50))
    ins_date = db.Column('ins_date', db.DateTime)
    upt_user = db.Column('upt_user', db.String(50))
    upt_date = db.Column('upt_date', db.DateTime)
    
    # 멀티테넌트 지원 (이미 DB에 존재하는 컬럼)
    company_id = db.Column('company_id', db.Integer, default=1)
    
    # Flask-Login 메서드
    def get_id(self):
        """Flask-Login required method"""
        return str(self.seq)
    
    def verify_password(self, password):
        """비밀번호 확인"""
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password, password)
    
    @property
    def is_active(self):
        """활성 상태 확인"""
        return self.member_status == 'Y'
    
    @property
    def is_super_user(self):
        """슈퍼유저 여부 확인"""
        return self.super_user == 'Y'
    
    # 멀티테넌트 메서드
    def get_companies(self):
        """접근 가능한 회사 목록"""
        companies = []
        # 기본 company_id로 회사 정보 조회
        if self.company_id:
            from app.common.models import Company
            company = Company.query.get(self.company_id)
            if company:
                companies.append(company)
        return companies
    
    def get_primary_company(self):
        """주 소속 회사"""
        if self.company_id:
            from app.common.models import Company
            return Company.query.get(self.company_id)
        return None
    
    def has_company_access(self, company_id):
        """특정 회사 접근 권한 확인"""
        if self.is_super_user:
            return True
        return self.company_id == company_id
    
    def get_departments(self, company_id=None):
        """부서 목록 조회 (회사별 필터링 가능)"""
        departments = []
        for ud in self.user_departments:
            if company_id is None or self.has_company_access(company_id):
                departments.append(ud.department)
        return departments
    
    def to_dict(self):
        """딕셔너리 변환"""
        companies = []
        if self.company_id:
            company = self.get_primary_company()
            if company:
                companies.append({
                    'company_id': company.id,
                    'company_name': company.company_name,
                    'company_code': company.company_code,
                    'is_primary': True,
                    'role': 'admin' if self.super_user == 'Y' else 'user'
                })
        
        departments = []
        for ud in self.user_departments:
            departments.append({
                'seq': ud.dept_seq,
                'name': ud.department.dept_name
            })
        
        return {
            'seq': self.seq,
            'login_id': self.login_id,
            'name': self.name,
            'id_number': self.id_number,
            'email': self.email,
            'mobile': self.mobile,
            'extension_number': self.extension_number,
            'super_user': self.super_user,
            'member_status': self.member_status,
            'companies': companies,
            'departments': departments
        }
    
    def __repr__(self):
        return f'<User {self.login_id}({self.name})>'

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
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), default=1)  # 사용 회사
    ins_user = db.Column(db.String(50))
    ins_date = db.Column(db.DateTime)
    upt_user = db.Column(db.String(50))
    upt_date = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Department {self.dept_name}>'
    
    def to_dict(self):
        """딕셔너리 변환"""
        return {
            'seq': self.seq,
            'dept_name': self.dept_name,
            'sort': self.sort or 1,
            'use_yn': self.use_yn or 'Y',
            'company_id': self.company_id or 1,
            'ins_user': self.ins_user,
            'ins_date': self.ins_date.isoformat() if self.ins_date else None,
            'upt_user': self.upt_user,
            'upt_date': self.upt_date.isoformat() if self.upt_date else None
        }

class MemberDept(db.Model):
    """사용자-부서 관계 - 레거시 tbl_memberdept 테이블"""
    __tablename__ = 'tbl_memberdept'
    
    seq = db.Column(db.Integer, primary_key=True)
    member_seq = db.Column('member_seq', db.Integer, db.ForeignKey('tbl_member.seq'))  # 실제 컬럼명
    dept_seq = db.Column('dept_seq', db.Integer, db.ForeignKey('tbl_department.seq'))  # 실제 컬럼명
    
    # 별칭 속성 (하위 호환성)
    @property 
    def user_seq(self):
        return self.member_seq
        
    @user_seq.setter
    def user_seq(self, value):
        self.member_seq = value
    
    # 관계 설정
    user = db.relationship('User', backref='user_departments', foreign_keys=[member_seq])
    department = db.relationship('Department', backref='dept_users')

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
    
    @classmethod
    def get_codes_by_parent(cls, parent_seq):
        """상위 코드 기준 하위 코드 목록 조회"""
        return cls.query.filter_by(parent_seq=parent_seq).order_by(cls.sort.asc(), cls.code_name.asc()).all()
    
    @classmethod
    def get_codes_by_group_name(cls, group_name, company_id=None):
        """그룹명으로 코드 목록 조회 (개선된 정렬)"""
        try:
            # 년도는 최신순, 나머지는 sort 기준 정렬
            if group_name == '년도':
                # 부모 그룹 찾기
                parent_group = cls.query.filter(
                    cls.code_name == group_name,
                    cls.depth == 0
                ).first()
                
                if parent_group:
                    codes = cls.query.filter(
                        cls.parent_seq == parent_group.seq
                    ).order_by(cls.code.desc()).all()  # 년도는 내림차순 (최신순)
                else:
                    codes = []
            else:
                # 다른 코드들은 sort 기준 오름차순
                parent_group = cls.query.filter(
                    cls.code_name == group_name,
                    cls.depth == 0
                ).first()
                
                if parent_group:
                    codes = cls.query.filter(
                        cls.parent_seq == parent_group.seq
                    ).order_by(cls.sort.asc(), cls.seq.asc()).all()
                else:
                    codes = []
            
            return codes
            
        except Exception as e:
            print(f"코드 조회 오류: {e}")
            return []
    
    @classmethod
    def get_types_by_product_category(cls, product_category_seq):
        """품목(PRD) 선택 시 해당 품목의 하위 타입들 조회"""
        try:
            # 선택된 품목(PRD 하위)을 parent_seq로 하는 타입들 조회
            types = cls.query.filter_by(parent_seq=product_category_seq).order_by(cls.sort.asc()).all()
            return types
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"❌ 품목별 타입 조회 실패: {e}")
            return []
    
    @classmethod
    def get_child_codes(cls, parent_seq):
        """상위 코드의 하위 코드 목록 조회"""
        codes = cls.query.filter_by(parent_seq=parent_seq).order_by(cls.sort.asc(), cls.code_name.asc()).all()
        return [{'seq': code.seq, 'code': code.code, 'code_name': code.code_name} for code in codes]

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
    
    @classmethod
    def get_brands_by_company(cls, company_id=None):
        """회사별 브랜드 목록 조회"""
        query = cls.query
        if company_id:
            # 멀티테넌트 지원: 회사별 또는 공통 브랜드
            query = query.filter(
                db.or_(
                    cls.company_id == company_id,
                    cls.company_id.is_(None)  # 공통 브랜드
                )
            )
        brands = query.order_by(cls.sort.asc(), cls.brand_name.asc()).all()
        return [{'seq': brand.seq, 'code': brand.brand_code, 'code_name': brand.brand_name} for brand in brands]

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

class ErpiaCustomer(db.Model):
    """ERPia 매장(거래처) 정보 모델"""
    __tablename__ = 'erpia_customer'
    
    # 기본 키
    seq = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # ERPia 기본 정보 (45개 필드)
    customer_code = db.Column('g_code', db.String(50), index=True)  # ERPia 거래처 코드
    customer_name = db.Column('g_name', db.String(200))  # 거래처명
    ceo = db.Column('g_ceo', db.String(100))  # 대표자
    business_number = db.Column('g_sano', db.String(50))  # 사업자번호
    business_type = db.Column('g_up', db.String(100))  # 업태
    business_item = db.Column('g_jong', db.String(100))  # 종목
    
    # 연락처 정보
    phone = db.Column('g_tel', db.String(50))  # 전화
    fax = db.Column('g_fax', db.String(50))  # 팩스
    
    # 담당자 정보
    our_manager = db.Column('g_damdang', db.String(100))  # (우리회사의) 거래처 담당
    customer_manager = db.Column('g_gdamdang', db.String(50))  # 거래처 담당자
    customer_manager_tel = db.Column('g_gdamdang_tel', db.String(50))  # 거래처 담당자 연락처
    customer_manager_tel2 = db.Column('g_gdamdang_tel2', db.String(50))  # 거래처 담당자 연락처2 (알림톡 추가 발송용)
    
    # 주소 정보
    location = db.Column('g_location', db.String(200))  # 위물도시선물
    zip_code1 = db.Column('g_post1', db.String(20))  # 우편번호
    address1 = db.Column('g_juso1', db.String(500))  # 주소
    zip_code2 = db.Column('g_post2', db.String(20))  # 사업거치선 우편번호
    address2 = db.Column('g_juso2', db.String(500))  # 사업거치선 주소
    
    # 관리 정보
    remarks = db.Column('g_remk', db.Text)  # 비고
    program_usage = db.Column('g_program_sayong', db.String(10))  # SCM 사용여부
    input_user = db.Column('in_user', db.String(50))  # 등록자
    edit_date = db.Column('edit_date', db.String(50))  # 최종수정일
    status = db.Column('stts', db.String(10))  # 상태 (0:사용, 9:미사용)
    online_code = db.Column('g_oncode', db.String(50))  # 자체거래처코드
    
    # 세금 관련 담당자
    tax_manager = db.Column('tax_gdamdang', db.String(100))  # 사업거치선 담당자 이름
    tax_manager_tel = db.Column('tax_gdamdang_tel', db.String(50))  # 사업거치선 담당자 연락처
    tax_email = db.Column('tax_email', db.String(200))  # 사업거치선 담당자 이메일
    
    # 연계 정보
    link_code_acct = db.Column('link_code_acct', db.String(50))  # 회계 연계코드
    jo_type = db.Column('g_jo_type', db.String(50))  # 거래(업종)구분
    
    # 매입 단가 정보
    dan_ga_gu = db.Column('g_danga_gu', db.String(50))  # 매입단가
    discount_yul = db.Column('g_discount_yul', db.String(50))  # 매입단가 할인율등록
    discount_or_up = db.Column('g_discount_or_up', db.String(50))  # 할인율등록구분
    use_recent_danga_yn = db.Column('use_recent_danga_yn', db.String(10))  # 최근판단단가 우선적용률
    
    # 매입 단가 정보 (J 버전)
    dan_ga_gu_j = db.Column('g_danga_gu_j', db.String(50))  # 매입단가
    discount_yul_j = db.Column('g_discount_yul_j', db.String(50))  # 매입단가 할인율등록
    discount_or_up_j = db.Column('g_discount_or_up_j', db.String(50))  # 할인율등록구분
    use_recent_danga_yn_j = db.Column('use_recent_danga_yn_j', db.String(10))  # 최근판단단가 우선적용률
    
    # 계좌 정보
    account = db.Column('g_account', db.String(100))  # 계좌번호
    bank_name = db.Column('g_bank_name', db.String(100))  # 은행명
    bank_holder = db.Column('g_bank_holder', db.String(100))  # 예금주
    
    # 배송 정보
    tag_code = db.Column('g_tag_code', db.String(50))  # 택배사코드
    tag_cust_code = db.Column('g_tag_cust_code', db.String(50))  # 택배 연계코드
    direct_shipping_type = db.Column('g_direct_shipping_type', db.String(50))  # 직배송업체구분
    
    # 추가 메모
    memo = db.Column('g_memo', db.Text)  # 메모
    
    # ERPia 수집 정보
    admin_code = db.Column('admin_code', db.String(50))  # ERPia 관리자 코드 (회사 식별용)
    company_id = db.Column('company_id', db.Integer, default=1)  # 회사 ID
    
    # ========== 추가 분류 필드 (MIS v2 확장) ==========
    # 레거시 분류 (CST 그룹)
    distribution_type = db.Column('distribution_type', db.String(50))  # 유통 (DIS)
    channel_type = db.Column('channel_type', db.String(50))  # 채널 (CH)
    sales_type = db.Column('sales_type', db.String(50))  # 매출 (SL)
    business_form = db.Column('business_form', db.String(50))  # 매장형태 (TY)
    
    # 신규 분류 (이미지 기반)
    brand_zone = db.Column('brand_zone', db.String(50))  # 브랜드존 (BZ)
    nuna_zoning = db.Column('nuna_zoning', db.String(50))  # 뉴나 브랜드 조닝 (NZ)
    region = db.Column('region', db.String(50))  # 지역 (RG)
    financial_group = db.Column('financial_group', db.String(50))  # 가결산 구분값 (FG)
    
    # 매장 사용 여부 (레거시 호환)
    shop_yn = db.Column('shop_yn', db.String(1), default='Y')  # 매장 사용 여부
    
    # 생성/수정 정보
    ins_user = db.Column('ins_user', db.String(50))
    ins_date = db.Column('ins_date', db.DateTime, default=datetime.utcnow)
    upt_user = db.Column('upt_user', db.String(50))
    upt_date = db.Column('upt_date', db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """매장 정보를 딕셔너리로 변환"""
        return {
            'seq': self.seq,
            'customer_code': self.customer_code,
            'customer_name': self.customer_name,
            'ceo': self.ceo,
            'business_number': self.business_number,
            'business_type': self.business_type,
            'business_item': self.business_item,
            'phone': self.phone,
            'fax': self.fax,
            'our_manager': self.our_manager,
            'customer_manager': self.customer_manager,
            'customer_manager_tel': self.customer_manager_tel,
            'customer_manager_tel2': self.customer_manager_tel2,
            'location': self.location,
            'zip_code1': self.zip_code1,
            'address1': self.address1,
            'zip_code2': self.zip_code2,
            'address2': self.address2,
            'remarks': self.remarks,
            'program_usage': self.program_usage,
            'input_user': self.input_user,
            'edit_date': self.edit_date,
            'status': self.status,
            'online_code': self.online_code,
            'tax_manager': self.tax_manager,
            'tax_manager_tel': self.tax_manager_tel,
            'tax_email': self.tax_email,
            'link_code_acct': self.link_code_acct,
            'jo_type': self.jo_type,
            'dan_ga_gu': self.dan_ga_gu,
            'discount_yul': self.discount_yul,
            'discount_or_up': self.discount_or_up,
            'use_recent_danga_yn': self.use_recent_danga_yn,
            'dan_ga_gu_j': self.dan_ga_gu_j,
            'discount_yul_j': self.discount_yul_j,
            'discount_or_up_j': self.discount_or_up_j,
            'use_recent_danga_yn_j': self.use_recent_danga_yn_j,
            'account': self.account,
            'bank_name': self.bank_name,
            'bank_holder': self.bank_holder,
            'tag_code': self.tag_code,
            'tag_cust_code': self.tag_cust_code,
            'direct_shipping_type': self.direct_shipping_type,
            'memo': self.memo,
            'admin_code': self.admin_code,
            'company_id': self.company_id,
            # 분류 정보
            'distribution_type': self.distribution_type,
            'channel_type': self.channel_type,
            'sales_type': self.sales_type,
            'business_form': self.business_form,
            'brand_zone': self.brand_zone,
            'nuna_zoning': self.nuna_zoning,
            'region': self.region,
            'financial_group': self.financial_group,
            'shop_yn': self.shop_yn,
            # 시스템 정보
            'ins_user': self.ins_user,
            'ins_date': self.ins_date.isoformat() if self.ins_date else None,
            'upt_user': self.upt_user,
            'upt_date': self.upt_date.isoformat() if self.upt_date else None,
        }
    
    @classmethod
    def get_by_customer_code(cls, customer_code: str, company_id: int = None):
        """거래처 코드로 매장 정보 조회"""
        query = cls.query.filter_by(customer_code=customer_code)
        if company_id:
            query = query.filter_by(company_id=company_id)
        return query.first()
    
    @classmethod
    def get_active_shops(cls, company_id: int = None):
        """활성 매장 목록 조회"""
        query = cls.query.filter_by(shop_yn='Y', status='0')
        if company_id:
            query = query.filter_by(company_id=company_id)
        return query.order_by(cls.customer_name.asc()).all()
    
    @classmethod
    def search_shops(cls, keyword: str, company_id: int = None):
        """매장 검색"""
        query = cls.query.filter(
            db.or_(
                cls.customer_name.like(f'%{keyword}%'),
                cls.customer_code.like(f'%{keyword}%'),
                cls.our_manager.like(f'%{keyword}%'),
                cls.address1.like(f'%{keyword}%')
            )
        )
        if company_id:
            query = query.filter_by(company_id=company_id)
        return query.order_by(cls.customer_name.asc()).all()

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
        chjeon = User.query.filter_by(login_id='chjeon').first()
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
        admin = User.query.filter_by(login_id='admin').first()
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

# 별칭 설정 (하위 호환성)
UserDepartment = MemberDept 

# =============================================================================
# 상품관리 모델 (신규)
# =============================================================================

class Product(db.Model):
    """상품 마스터"""
    __tablename__ = 'products'
    
    # 기본 정보
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # 분류 정보 (모두 코드 체계 활용)
    brand_code_seq = db.Column(db.Integer, db.ForeignKey('tbl_code.seq'))      # 브랜드 (BRAND 그룹)
    category_code_seq = db.Column(db.Integer, db.ForeignKey('tbl_code.seq'))   # 품목 (PRT 그룹)
    type_code_seq = db.Column(db.Integer, db.ForeignKey('tbl_code.seq'))       # 타입 (TP 그룹)
    year_code_seq = db.Column(db.Integer, db.ForeignKey('tbl_code.seq'))       # 년도 (YR 그룹)
    
    # 확장 분류 정보 (새로 추가)
    color_code_seq = db.Column(db.Integer, db.ForeignKey('tbl_code.seq'))      # 색상 (COLOR 그룹)
    div_type_code_seq = db.Column(db.Integer, db.ForeignKey('tbl_code.seq'))   # 구분타입 (DIVTYPE 그룹)
    product_code_seq = db.Column(db.Integer, db.ForeignKey('tbl_code.seq'))    # 제품코드 (PRODCODE 그룹)
    
    # 상품 정보
    product_name = db.Column(db.String(100), nullable=False)
    product_code = db.Column(db.String(50))
    std_product_code = db.Column(db.String(50))  # 자가코드 (레거시 StdDivProdCode)
    price = db.Column(db.Integer, default=0)  # 상품가격(Tag)
    description = db.Column(db.Text)  # 상품 정보
    manual_file_path = db.Column(db.String(500))  # 사용설명서 PDF 경로
    
    # 상태 관리
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # 사용여부
    use_yn = db.Column(db.String(1), default='Y')  # 레거시 호환용 UseYN
    
    # 레거시 연결 (새로 추가)
    legacy_seq = db.Column(db.Integer, unique=True, nullable=True)  # 레거시 MstSeq 연결
    
    # 시스템 필드
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))
    
    # 관계 설정 (모두 코드 체계 사용)
    company = db.relationship('Company', backref='products')
    brand_code = db.relationship('Code', foreign_keys=[brand_code_seq], backref='brand_products')
    category_code = db.relationship('Code', foreign_keys=[category_code_seq], backref='category_products')
    type_code = db.relationship('Code', foreign_keys=[type_code_seq], backref='type_products')
    year_code = db.relationship('Code', foreign_keys=[year_code_seq], backref='year_products')
    
    # 확장 분류 관계 설정 (새로 추가)
    color_code = db.relationship('Code', foreign_keys=[color_code_seq], backref='color_products')
    div_type_code = db.relationship('Code', foreign_keys=[div_type_code_seq], backref='div_type_products')
    product_code = db.relationship('Code', foreign_keys=[product_code_seq], backref='product_code_products')
    
    def __repr__(self):
        return f'<Product {self.product_name}>'
    
    def to_dict(self):
        """딕셔너리 변환"""
        # ProductDetail에서 자가코드 가져오기 (SQL 직접 사용)
        std_code = None
        try:
            result = db.session.execute(db.text("""
                SELECT std_div_prod_code 
                FROM product_details 
                WHERE product_id = :product_id 
                LIMIT 1
            """), {'product_id': self.id})
            row = result.fetchone()
            std_code = row.std_div_prod_code if row else None
        except:
            std_code = None
        
        return {
            'id': self.id,
            'company_id': self.company_id,
            'company_name': self.company.company_name if self.company else '',
            'brand_code_seq': self.brand_code_seq,
            'brand_name': self.brand_code.code_name if self.brand_code else '',
            'category_code_seq': self.category_code_seq,
            'category_name': self.category_code.code_name if self.category_code else '',
            'type_code_seq': self.type_code_seq,
            'type_name': self.type_code.code_name if self.type_code else '',
            'year_code_seq': self.year_code_seq,
            'year_name': self.year_code.code_name if self.year_code else '',
            'year_code_name': self.year_code.code_name if self.year_code else '',  # 템플릿 호환성
            
            # 확장 분류 정보 (새로 추가)
            'color_code_seq': self.color_code_seq,
            'color_name': self.color_code.code_name if self.color_code else '',
            'div_type_code_seq': self.div_type_code_seq,
            'div_type_name': self.div_type_code.code_name if self.div_type_code else '',
            'product_code_seq': self.product_code_seq,
            'product_code_name': self.product_code.code_name if self.product_code else '',
            
            'product_name': self.product_name,
            'product_code': self.product_code,
            'std_product_code': std_code,  # ProductDetail에서 가져온 실제 자가코드
            'price': self.price,
            'description': self.description,
            'manual_file_path': self.manual_file_path,
            'is_active': self.is_active,
            'use_yn': self.use_yn,
            'legacy_seq': self.legacy_seq,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }
    
    @classmethod
    def get_by_company(cls, company_id, active_only=True):
        """회사별 상품 목록 조회"""
        query = cls.query.filter_by(company_id=company_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(cls.product_name).all()
    
    @classmethod
    def search_products(cls, company_id, search_term=None, brand_code_seq=None, 
                       category_code_seq=None, type_code_seq=None, year_code_seq=None, active_only=True):
        """상품 검색"""
        query = cls.query.filter_by(company_id=company_id)
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        if search_term:
            search_pattern = f'%{search_term}%'
            query = query.filter(
                db.or_(
                    cls.product_name.ilike(search_pattern),
                    cls.product_code.ilike(search_pattern),
                    cls.description.ilike(search_pattern)
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
        
        return query.order_by(cls.product_name).all()

class ProductDetail(db.Model):
    """상품 상세 (색상별/옵션별 관리)"""
    __tablename__ = 'product_details'
    
    # 기본 정보
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    # 자가코드 구성요소 (레거시 호환)
    brand_code = db.Column(db.String(2))           # 브랜드 코드 (2자리)
    div_type_code = db.Column(db.String(1))        # 구분타입 코드 (1자리)
    prod_group_code = db.Column(db.String(2))      # 제품그룹 코드 (2자리) 
    prod_type_code = db.Column(db.String(2))       # 제품타입 코드 (2자리)
    prod_code = db.Column(db.String(2))            # 제품코드 (2자리)
    prod_type2_code = db.Column(db.String(2))      # 제품타입2 코드 (2자리)
    year_code = db.Column(db.String(1))            # 년도 코드 (1자리)
    color_code = db.Column(db.String(3))           # 색상 코드 (3자리)
    
    # 완성된 자가코드
    std_div_prod_code = db.Column(db.String(16), unique=True, nullable=False)  # 조합된 자가코드
    
    # 색상별 상품 정보
    product_name = db.Column(db.String(200))        # 색상별 상품명
    additional_price = db.Column(db.Integer, default=0)  # 색상별 추가 가격
    stock_quantity = db.Column(db.Integer, default=0)    # 재고 수량
    
    # 상태 관리
    status = db.Column(db.String(20), default='Active')  # Active, Inactive, Discontinued
    
    # 레거시 연결 (새로 추가)
    legacy_seq = db.Column(db.Integer, unique=True, nullable=True)  # 레거시 Seq 연결
    
    # 시스템 필드
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))
    
    # 관계 설정
    product = db.relationship('Product', backref='product_details')
    
    def __repr__(self):
        return f'<ProductDetail {self.std_div_prod_code}>'
    
    def to_dict(self):
        """딕셔너리 변환"""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'brand_code': self.brand_code,
            'div_type_code': self.div_type_code,
            'prod_group_code': self.prod_group_code,
            'prod_type_code': self.prod_type_code,
            'prod_code': self.prod_code,
            'prod_type2_code': self.prod_type2_code,
            'year_code': self.year_code,
            'color_code': self.color_code,
            'std_div_prod_code': self.std_div_prod_code,
            'product_name': self.product_name,
            'additional_price': self.additional_price,
            'stock_quantity': self.stock_quantity,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }
    
    @classmethod
    def generate_std_code(cls, brand_code, div_type_code, prod_group_code, 
                         prod_type_code, prod_code, prod_type2_code, year_code, color_code):
        """자가코드 생성 (16자리)"""
        return f"{brand_code}{div_type_code}{prod_group_code}{prod_type_code}{prod_code}{prod_type2_code}{year_code}{color_code}"
    
    @classmethod
    def find_by_std_code(cls, std_code):
        """자가코드로 상품 상세 조회"""
        return cls.query.filter_by(std_div_prod_code=std_code).first()

class ProductHistory(db.Model):
    """상품 변경 이력"""
    __tablename__ = 'product_history'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    action = db.Column(db.String(20), nullable=False)  # CREATE, UPDATE, DELETE
    changed_fields = db.Column(db.JSON)  # 변경된 필드들
    old_values = db.Column(db.JSON)      # 이전 값들
    new_values = db.Column(db.JSON)      # 새로운 값들
    
    # 시스템 필드
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(50))
    
    # 관계 설정
    product = db.relationship('Product', backref='history')
    
    def __repr__(self):
        return f'<ProductHistory {self.product_id}:{self.action}>' 