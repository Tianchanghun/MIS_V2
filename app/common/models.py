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
    """브랜드 관리 - 레거시 tbl_brand 테이블"""
    __tablename__ = 'tbl_brand'
    
    seq = db.Column(db.Integer, primary_key=True)
    brand_code = db.Column(db.String(20))  # 브랜드 코드
    brand_name = db.Column(db.String(100))  # 브랜드명
    brand_eng_name = db.Column(db.String(100))  # 브랜드 영문명
    brand_info = db.Column(db.Text)  # 브랜드 설명
    sort = db.Column(db.Integer)  # 정렬 순서
    use_yn = db.Column(db.String(1), default='Y')  # 사용 여부
    ins_user = db.Column(db.String(50))
    ins_date = db.Column(db.DateTime)
    upt_user = db.Column(db.String(50))
    upt_date = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Brand {self.brand_name}>'

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

class CompanyErpiaConfig(db.Model):
    """회사별 ERPia 연동 설정 - 멀티테넌트 확장"""
    __tablename__ = 'company_erpia_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), unique=True, nullable=False)
    
    # ERPia 인증 정보
    admin_code = db.Column(db.String(100), nullable=False)
    password_encrypted = db.Column(db.Text, nullable=False)
    api_url = db.Column(db.String(500), default='http://www.erpia.net/xml/xml.asp')
    
    # 배치 스케줄 설정
    batch_enabled = db.Column(db.Boolean, default=True)
    batch_hour = db.Column(db.Integer, default=2)
    batch_minute = db.Column(db.Integer, default=0)
    
    # 사은품 처리 설정
    auto_gift_classify = db.Column(db.Boolean, default=True)
    gift_keywords = db.Column(db.Text)  # JSON 배열
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    company = db.relationship('Company', backref='erpia_config')

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
    """기본 멀티테넌트 데이터 생성"""
    try:
        # 에이원 회사 정보 확인/생성
        aone = Company.query.filter_by(company_code='AONE').first()
        if not aone:
            aone = Company(
                company_code='AONE',
                company_name='에이원',
                company_name_en='AONE',
                theme_color='#007bff',
                is_active=True
            )
            db.session.add(aone)
            db.session.flush()
        
        # 에이원월드 회사 정보 확인/생성
        aone_world = Company.query.filter_by(company_code='AONE_WORLD').first()
        if not aone_world:
            aone_world = Company(
                company_code='AONE_WORLD',
                company_name='에이원월드',
                company_name_en='AONE WORLD',
                theme_color='#28a745',
                is_active=True
            )
            db.session.add(aone_world)
            db.session.flush()
        
        # 기존 레거시 사용자들에게 회사 접근 권한 부여
        existing_users = User.query.filter_by(member_status='A').all()
        
        for user in existing_users:
            # 에이원 접근 권한 확인/생성
            aone_access = UserCompany.query.filter_by(
                user_seq=user.seq, company_id=aone.id
            ).first()
            if not aone_access:
                # 전창훈(chjeon)은 에이원이 주소속
                is_primary = (user.id == 'chjeon')
                aone_access = UserCompany(
                    user_seq=user.seq,
                    company_id=aone.id,
                    role='admin' if user.is_super_user else 'user',
                    is_primary=is_primary,
                    is_active=True
                )
                db.session.add(aone_access)
            
            # 슈퍼유저는 에이원월드도 접근 가능
            if user.is_super_user:
                world_access = UserCompany.query.filter_by(
                    user_seq=user.seq, company_id=aone_world.id
                ).first()
                if not world_access:
                    # 전창훈의 경우 에이원월드는 부소속
                    is_primary_world = False
                    world_access = UserCompany(
                        user_seq=user.seq,
                        company_id=aone_world.id,
                        role='admin',
                        is_primary=is_primary_world,
                        is_active=True
                    )
                    db.session.add(world_access)
        
        # 에이원 ERPia 설정 생성
        aone_erpia = CompanyErpiaConfig.query.filter_by(company_id=aone.id).first()
        if not aone_erpia:
            aone_erpia = CompanyErpiaConfig(
                company_id=aone.id,
                admin_code='aone',
                password_encrypted='ka22fslfod1vid',  # 실제로는 암호화 필요
                batch_hour=2,
                batch_minute=0,
                auto_gift_classify=True,
                gift_keywords='["사은품", "증정품", "무료", "샘플", "체험"]'
            )
            db.session.add(aone_erpia)
        
        db.session.commit()
        print("✅ 레거시 + 멀티테넌트 기본 데이터 생성 완료")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ 기본 데이터 생성 실패: {e}")
        raise 