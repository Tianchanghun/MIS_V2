#!/usr/bin/env python3
"""
ERPia API 설정 관리 모델
- 페이징 크기, 호출 간격 등 설정 관리
- 웹에서 동적 설정 변경 가능
- 기본값 자동 적용
"""

from app import db
from datetime import datetime

class ErpiaSettings(db.Model):
    """ERPia API 설정 테이블"""
    __tablename__ = 'erpia_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(50), unique=True, nullable=False, comment='설정 키')
    setting_value = db.Column(db.String(200), nullable=False, comment='설정 값')
    setting_type = db.Column(db.String(20), default='string', comment='설정 타입 (string, int, float, bool)')
    description = db.Column(db.String(200), comment='설정 설명')
    min_value = db.Column(db.Integer, comment='최소값 (숫자 타입)')
    max_value = db.Column(db.Integer, comment='최대값 (숫자 타입)')
    is_active = db.Column(db.Boolean, default=True, comment='활성화 여부')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='생성일시')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='수정일시')
    
    def __repr__(self):
        return f'<ErpiaSettings {self.setting_key}={self.setting_value}>'
    
    @staticmethod
    def get_setting(key: str, default_value=None):
        """설정값 조회 (타입 변환 포함)"""
        setting = ErpiaSettings.query.filter_by(setting_key=key, is_active=True).first()
        
        if not setting:
            return default_value
        
        try:
            # 타입에 따른 변환
            if setting.setting_type == 'int':
                return int(setting.setting_value)
            elif setting.setting_type == 'float':
                return float(setting.setting_value)
            elif setting.setting_type == 'bool':
                return setting.setting_value.lower() in ('true', '1', 'yes', 'on')
            else:
                return setting.setting_value
        except (ValueError, AttributeError):
            return default_value
    
    @staticmethod
    def set_setting(key: str, value, setting_type: str = 'string', description: str = None, 
                   min_value: int = None, max_value: int = None):
        """설정값 저장/업데이트"""
        setting = ErpiaSettings.query.filter_by(setting_key=key).first()
        
        if setting:
            # 기존 설정 업데이트
            setting.setting_value = str(value)
            setting.setting_type = setting_type
            if description:
                setting.description = description
            if min_value is not None:
                setting.min_value = min_value
            if max_value is not None:
                setting.max_value = max_value
            setting.updated_at = datetime.utcnow()
        else:
            # 새 설정 생성
            setting = ErpiaSettings(
                setting_key=key,
                setting_value=str(value),
                setting_type=setting_type,
                description=description,
                min_value=min_value,
                max_value=max_value
            )
            db.session.add(setting)
        
        db.session.commit()
        return setting
    
    @staticmethod
    def get_page_size():
        """페이징 크기 조회 (기본값: 30)"""
        return ErpiaSettings.get_setting('page_size', 30)
    
    @staticmethod
    def get_call_interval():
        """호출 간격 조회 (기본값: 3초)"""
        return ErpiaSettings.get_setting('call_interval', 3)
    
    @staticmethod
    def get_timeout():
        """타임아웃 조회 (기본값: 30초)"""
        return ErpiaSettings.get_setting('timeout', 30)
    
    @staticmethod
    def get_retry_count():
        """재시도 횟수 조회 (기본값: 3회)"""
        return ErpiaSettings.get_setting('retry_count', 3)
    
    @staticmethod
    def initialize_default_settings():
        """기본 설정값 초기화"""
        default_settings = [
            {
                'key': 'page_size',
                'value': 30,
                'type': 'int',
                'description': 'ERPia API 페이징 크기 (최대 30건 권장)',
                'min_value': 1,
                'max_value': 30
            },
            {
                'key': 'call_interval',
                'value': 3,
                'type': 'int',
                'description': 'ERPia API 호출 간격 (초)',
                'min_value': 1,
                'max_value': 10
            },
            {
                'key': 'timeout',
                'value': 30,
                'type': 'int',
                'description': 'ERPia API 요청 타임아웃 (초)',
                'min_value': 10,
                'max_value': 120
            },
            {
                'key': 'retry_count',
                'value': 3,
                'type': 'int',
                'description': 'ERPia API 재시도 횟수',
                'min_value': 1,
                'max_value': 5
            },
            {
                'key': 'auto_sync_enabled',
                'value': True,
                'type': 'bool',
                'description': 'ERPia 자동 동기화 활성화 여부'
            },
            {
                'key': 'sync_schedule_daily',
                'value': '02:00',
                'type': 'string',
                'description': '일일 동기화 시간 (HH:MM 형식)'
            },
            {
                'key': 'sync_schedule_weekly',
                'value': 'sunday',
                'type': 'string',
                'description': '주간 동기화 요일 (monday~sunday)'
            }
        ]
        
        for setting_data in default_settings:
            ErpiaSettings.set_setting(
                key=setting_data['key'],
                value=setting_data['value'],
                setting_type=setting_data['type'],
                description=setting_data['description'],
                min_value=setting_data.get('min_value'),
                max_value=setting_data.get('max_value')
            )
        
        print("✅ ERPia 기본 설정값 초기화 완료")

class ErpiaSyncLog(db.Model):
    """ERPia 동기화 로그 테이블"""
    __tablename__ = 'erpia_sync_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    sync_type = db.Column(db.String(50), nullable=False, comment='동기화 유형 (codes, customers, products, etc.)')
    sync_mode = db.Column(db.String(20), nullable=False, comment='동기화 모드 (auto, manual)')
    status = db.Column(db.String(20), nullable=False, comment='상태 (running, success, failed)')
    total_records = db.Column(db.Integer, default=0, comment='총 레코드 수')
    processed_records = db.Column(db.Integer, default=0, comment='처리된 레코드 수')
    error_message = db.Column(db.Text, comment='오류 메시지')
    start_time = db.Column(db.DateTime, default=datetime.utcnow, comment='시작 시간')
    end_time = db.Column(db.DateTime, comment='종료 시간')
    duration_seconds = db.Column(db.Integer, comment='소요 시간 (초)')
    
    def __repr__(self):
        return f'<ErpiaSyncLog {self.sync_type}-{self.status}>'
    
    @property
    def success_rate(self):
        """성공률 계산"""
        if self.total_records == 0:
            return 0
        return round((self.processed_records / self.total_records) * 100, 2)
    
    def complete_sync(self, status: str = 'success', error_message: str = None):
        """동기화 완료 처리"""
        self.status = status
        self.end_time = datetime.utcnow()
        self.duration_seconds = int((self.end_time - self.start_time).total_seconds())
        if error_message:
            self.error_message = error_message
        db.session.commit() 