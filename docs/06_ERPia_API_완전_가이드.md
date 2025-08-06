# 📡 ERPia API 완전 가이드 v2.0

## 📋 목차
1. [API 개요](#api-개요)
2. [인증 정보](#인증-정보)
3. [API 모드별 상세](#api-모드별-상세)
4. [Python 구현](#python-구현)
5. [Flask 서비스 통합](#flask-서비스-통합)
6. [배치 스케줄링 웹 설정](#배치-스케줄링-웹-설정)
7. [사은품 처리 로직](#사은품-처리-로직)
8. [멀티테넌트 지원](#멀티테넌트-지원)
9. [모니터링 및 로그](#모니터링-및-로그)

---

## 🎯 API 개요

ERPia API는 **XML 기반 HTTP GET 요청**으로 동작하며, **EUC-KR 인코딩**을 사용합니다.

### **기본 URL 구조**
```
http://www.erpia.net/xml/xml.asp?mode={모드}&admin_code={관리자코드}&pwd={비밀번호}&{추가파라미터}
```

### **핵심 제약사항**
- **인코딩**: EUC-KR → UTF-8 변환 필수
- **페이징**: 최대 30건 (onePageCnt=30)
- **호출 간격**: 최소 3초 (안전성 고려)
- **배치 설정**: 웹에서 시간/주기 설정 가능

---

## 🔐 인증 정보

### **에이원 계정** (확인 완료)
- **관리자 코드**: `aone`
- **비밀번호**: `ka22fslfod1vid`
- **API 서버**: `http://www.erpia.net/`

### **에이원 월드 계정** (추후 설정)
- **관리자 코드**: 웹에서 설정
- **비밀번호**: 웹에서 설정
- **설정 화면**: 관리자 → ERPia 설정

---

## 📊 API 모드별 상세

### **1. 매출 데이터 조회** (`mode=jumun`) - **핵심 배치**
```
GET http://www.erpia.net/xml/xml.asp?mode=jumun&admin_code=aone&pwd=ka22fslfod1vid&sDate=20250805&eDate=20250805&page=1&datetype=m
```

#### **파라미터**
- `sDate`: 시작일 (YYYYMMDD)
- `eDate`: 종료일 (YYYYMMDD)  
- `page`: 페이지 번호 (1부터 시작)
- `datetype`: m (수정일 기준)
- `onePageCnt`: 페이지당 건수 (최대 30, 웹 설정 가능)

#### **XML 응답 구조**
```xml
<root>
    <info>
        <Sl_No>OT202508050001</Sl_No>
        <Site_Code>AONE001</Site_Code>
        <GerCode>G001</GerCode>
        <Jname>홍길동</Jname>
        <mDate>2025-08-05</mDate>
        <bAmt>3000</bAmt>
        <GoodsInfo>
            <Gcode>P001</Gcode>
            <Gname>NUNA 카시트</Gname>
            <Gqty>1</Gqty>
            <gongAmt>450000</gongAmt>
            <panAmt>450000</panAmt>
            <subul_kind>221</subul_kind>
        </GoodsInfo>
        <GoodsInfo>
            <Gcode>G001</Gcode>
            <Gname>사은품 패드</Gname>
            <Gqty>1</Gqty>
            <gongAmt>0</gongAmt>
            <panAmt>0</panAmt>
            <subul_kind>221</subul_kind>
        </GoodsInfo>
        <BeaInfo>
            <Bname>홍길동</Bname>
            <Baddr>서울시 강남구</Baddr>
            <songNo>123456789</songNo>
        </BeaInfo>
    </info>
</root>
```

#### **사은품 식별 로직** ⭐
```python
def classify_product_type(gong_amt, pan_amt, product_name):
    """상품 유형 분류 (일반상품 vs 사은품)"""
    
    # 0원 상품은 사은품으로 분류
    if int(gong_amt) == 0 and int(pan_amt) == 0:
        return {
            'product_type': 'GIFT',           # 사은품
            'is_revenue': False,              # 매출 집계 제외
            'analysis_category': '사은품',     # 분석 카테고리
            'revenue_impact': 0               # 매출 영향 없음
        }
    else:
        return {
            'product_type': 'PRODUCT',        # 일반상품
            'is_revenue': True,               # 매출 집계 포함
            'analysis_category': '매출상품',   # 분석 카테고리  
            'revenue_impact': int(gong_amt)   # 실제 매출액
        }
```

### **2. 거래처 정보 조회** (`mode=cust`)
```
GET http://www.erpia.net/xml/xml.asp?mode=cust&admin_code=aone&pwd=ka22fslfod1vid&sDate=20250101&eDate=20251231&onePageCnt=30&page=1
```

### **3. 상품 정보 조회** (`mode=item`)
```
GET http://www.erpia.net/xml/xml.asp?mode=item&admin_code=aone&pwd=ka22fslfod1vid&onePageCnt=30&page=1
```

### **4. 기타 지원 모드**
- `mode=sitecode`: 사이트 코드 조회
- `mode=marketcode`: 마켓 코드 조회  
- `mode=changgocode`: 창고 코드 조회
- `mode=brandcode`: 브랜드 코드 조회
- `mode=taebaescode`: 택배사 코드 조회

---

## 🐍 Python 구현

### **1. 기본 ERPia API 클라이언트**
```python
import requests
import xml.etree.ElementTree as ET
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class BatchSettings:
    """배치 설정 (웹에서 관리)"""
    schedule_time: str = "02:00"          # 실행 시간
    call_interval: int = 3                # API 호출 간격(초)
    page_size: int = 30                   # 페이지당 건수
    retry_count: int = 3                  # 재시도 횟수
    timeout: int = 30                     # 타임아웃(초)
    auto_gift_classify: bool = True       # 사은품 자동 분류
    
class ErpiaApiClient:
    """ERPia API 클라이언트 (웹 설정 기반)"""
    
    def __init__(self, company_id: int = 1):
        """
        Args:
            company_id: 회사 ID (1=에이원, 2=에이원월드)
        """
        self.company_id = company_id
        self.base_url = "http://www.erpia.net/xml/xml.asp"
        self.settings = self._load_batch_settings()
        self.credentials = self._load_company_credentials()
        
    def _load_batch_settings(self) -> BatchSettings:
        """웹에서 설정한 배치 설정 로드"""
        from app.models.erpia_settings import ErpiaSettings
        
        settings = {}
        for setting in ErpiaSettings.query.filter_by(company_id=self.company_id).all():
            settings[setting.setting_key] = setting.setting_value
            
        return BatchSettings(
            schedule_time=settings.get('schedule_time', '02:00'),
            call_interval=int(settings.get('call_interval', 3)),
            page_size=int(settings.get('page_size', 30)),
            retry_count=int(settings.get('retry_count', 3)),
            timeout=int(settings.get('timeout', 30)),
            auto_gift_classify=settings.get('auto_gift_classify', 'true').lower() == 'true'
        )
    
    def _load_company_credentials(self) -> Dict[str, str]:
        """회사별 ERPia 인증 정보 로드"""
        from app.models.company_erpia_config import CompanyErpiaConfig
        
        config = CompanyErpiaConfig.query.filter_by(company_id=self.company_id).first()
        if not config:
            raise ValueError(f"ERPia 설정이 없습니다. 회사 ID: {self.company_id}")
            
        return {
            'admin_code': config.admin_code,
            'password': config.password
        }
    
    def fetch_sales_data(self, start_date: str, end_date: str) -> List[Dict]:
        """매출 데이터 조회 (사은품 자동 분류 포함)"""
        all_data = []
        page = 1
        
        while True:
            # API 호출 간격 준수
            if page > 1:
                time.sleep(self.settings.call_interval)
            
            params = {
                'mode': 'jumun',
                'admin_code': self.credentials['admin_code'],
                'pwd': self.credentials['password'],
                'sDate': start_date,
                'eDate': end_date,
                'page': page,
                'datetype': 'm',
                'onePageCnt': self.settings.page_size
            }
            
            try:
                response = requests.get(
                    self.base_url, 
                    params=params,
                    timeout=self.settings.timeout
                )
                response.encoding = 'euc-kr'
                
                # XML 파싱
                root = ET.fromstring(response.text)
                info_nodes = root.findall('info')
                
                if not info_nodes:
                    break
                
                # 데이터 처리 및 사은품 분류
                for info in info_nodes:
                    order_data = self._parse_order_data(info)
                    all_data.append(order_data)
                
                page += 1
                
            except Exception as e:
                self._log_error(f"API 호출 실패 (페이지 {page}): {str(e)}")
                if page == 1:  # 첫 페이지 실패 시 중단
                    raise
                break
        
        return all_data
    
    def _parse_order_data(self, info_node) -> Dict:
        """주문 데이터 파싱 및 사은품 분류"""
        order = {
            'sl_no': self._get_text(info_node, 'Sl_No'),
            'site_code': self._get_text(info_node, 'Site_Code'),
            'ger_code': self._get_text(info_node, 'GerCode'),
            'customer_name': self._get_text(info_node, 'Jname'),
            'order_date': self._get_text(info_node, 'mDate'),
            'delivery_amt': int(self._get_text(info_node, 'bAmt', '0')),
            'products': [],
            'delivery_info': {},
            'company_id': self.company_id
        }
        
        # 상품 정보 파싱 (사은품 분류 포함)
        for goods in info_node.findall('GoodsInfo'):
            product = self._parse_product_data(goods)
            order['products'].append(product)
        
        # 배송 정보 파싱
        delivery_node = info_node.find('BeaInfo')
        if delivery_node is not None:
            order['delivery_info'] = {
                'recipient_name': self._get_text(delivery_node, 'Bname'),
                'address': self._get_text(delivery_node, 'Baddr'),
                'tracking_no': self._get_text(delivery_node, 'songNo'),
                'phone': self._get_text(delivery_node, 'Bhp')
            }
        
        return order
    
    def _parse_product_data(self, goods_node) -> Dict:
        """상품 데이터 파싱 및 사은품 자동 분류"""
        gong_amt = int(self._get_text(goods_node, 'gongAmt', '0'))
        pan_amt = int(self._get_text(goods_node, 'panAmt', '0'))
        product_name = self._get_text(goods_node, 'Gname')
        
        product = {
            'product_code': self._get_text(goods_node, 'Gcode'),
            'product_name': product_name,
            'quantity': int(self._get_text(goods_node, 'Gqty', '0')),
            'supply_price': gong_amt,
            'sell_price': pan_amt,
            'subul_kind': self._get_text(goods_node, 'subul_kind'),
            'brand_code': self._get_text(goods_node, 'brandCode'),
            'brand_name': self._get_text(goods_node, 'brandName')
        }
        
        # 사은품 자동 분류 로직 적용
        if self.settings.auto_gift_classify:
            classification = self._classify_product_type(gong_amt, pan_amt, product_name)
            product.update(classification)
        
        return product
    
    def _classify_product_type(self, gong_amt: int, pan_amt: int, product_name: str) -> Dict:
        """상품 유형 분류 (일반상품 vs 사은품)"""
        
        # 0원 상품은 사은품으로 분류
        if gong_amt == 0 and pan_amt == 0:
            return {
                'product_type': 'GIFT',           # 사은품
                'is_revenue': False,              # 매출 집계 제외
                'analysis_category': '사은품',     # 분석 카테고리
                'revenue_impact': 0,              # 매출 영향 없음
                'gift_classification': 'AUTO'     # 자동 분류
            }
        else:
            return {
                'product_type': 'PRODUCT',        # 일반상품
                'is_revenue': True,               # 매출 집계 포함
                'analysis_category': '매출상품',   # 분석 카테고리  
                'revenue_impact': gong_amt,       # 실제 매출액
                'gift_classification': None       # 해당없음
            }
    
    def _get_text(self, node, tag: str, default: str = '') -> str:
        """XML 노드에서 텍스트 안전하게 추출"""
        element = node.find(tag)
        return element.text if element is not None and element.text else default
    
    def _log_error(self, message: str):
        """오류 로그 기록"""
        from app.services.logging_service import log_batch_error
        log_batch_error(f"ERPia API [{self.company_id}]: {message}")
```

### **2. 웹 기반 배치 스케줄러**
```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import current_app

class ErpiaBatchScheduler:
    """웹 설정 기반 ERPia 배치 스케줄러"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler(daemon=True)
        self.is_running = False
    
    def start_scheduler(self):
        """스케줄러 시작"""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            self._update_schedules()
    
    def stop_scheduler(self):
        """스케줄러 중지"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
    
    def _update_schedules(self):
        """웹 설정에 따라 스케줄 업데이트"""
        from app.models.company import Company
        
        # 기존 작업 모두 제거
        self.scheduler.remove_all_jobs()
        
        # 활성화된 회사별로 스케줄 등록
        for company in Company.query.filter_by(is_active=True).all():
            settings = self._load_company_batch_settings(company.id)
            
            if settings and settings.get('auto_batch_enabled', False):
                # 일일 매출 수집 스케줄
                schedule_time = settings.get('schedule_time', '02:00')
                hour, minute = map(int, schedule_time.split(':'))
                
                self.scheduler.add_job(
                    func=self._run_daily_batch,
                    trigger=CronTrigger(hour=hour, minute=minute),
                    args=[company.id],
                    id=f'daily_batch_{company.id}',
                    name=f'{company.company_name} 일일 배치',
                    misfire_grace_time=300  # 5분 지연 허용
                )
    
    def _run_daily_batch(self, company_id: int):
        """일일 배치 실행"""
        try:
            from app.services.erpia_batch_service import ErpiaBatchService
            
            batch_service = ErpiaBatchService(company_id)
            
            # 어제 데이터 수집
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            result = batch_service.collect_daily_sales(yesterday, yesterday)
            
            self._log_batch_result(company_id, 'daily_sales', result)
            
        except Exception as e:
            self._log_batch_error(company_id, f"일일 배치 실패: {str(e)}")
    
    def update_company_schedule(self, company_id: int):
        """특정 회사의 스케줄 업데이트"""
        # 기존 작업 제거
        job_id = f'daily_batch_{company_id}'
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        # 새 스케줄 등록
        settings = self._load_company_batch_settings(company_id)
        if settings and settings.get('auto_batch_enabled', False):
            schedule_time = settings.get('schedule_time', '02:00')
            hour, minute = map(int, schedule_time.split(':'))
            
            self.scheduler.add_job(
                func=self._run_daily_batch,
                trigger=CronTrigger(hour=hour, minute=minute),
                args=[company_id],
                id=job_id,
                name=f'Company {company_id} 일일 배치'
            )
```

---

## 🌐 Flask 서비스 통합

### **1. ERPia 설정 관리 API**
```python
from flask import Blueprint, request, jsonify
from app.models.erpia_settings import ErpiaSettings
from app.services.erpia_batch_scheduler import ErpiaBatchScheduler

erpia_bp = Blueprint('erpia', __name__)

@erpia_bp.route('/api/erpia/settings/<int:company_id>', methods=['GET'])
@login_required
def get_erpia_settings(company_id):
    """ERPia 설정 조회"""
    settings = {}
    for setting in ErpiaSettings.query.filter_by(company_id=company_id).all():
        settings[setting.setting_key] = {
            'value': setting.setting_value,
            'description': setting.description,
            'type': setting.setting_type
        }
    
    return jsonify(settings)

@erpia_bp.route('/api/erpia/settings/<int:company_id>', methods=['POST'])
@login_required
@permission_required('admin_erpia', 'update')
def update_erpia_settings(company_id):
    """ERPia 설정 업데이트"""
    data = request.get_json()
    
    for key, value in data.items():
        setting = ErpiaSettings.query.filter_by(
            company_id=company_id,
            setting_key=key
        ).first()
        
        if setting:
            setting.setting_value = str(value)
            setting.updated_at = datetime.utcnow()
        else:
            setting = ErpiaSettings(
                company_id=company_id,
                setting_key=key,
                setting_value=str(value)
            )
            db.session.add(setting)
    
    db.session.commit()
    
    # 스케줄러 업데이트
    scheduler = current_app.extensions['erpia_scheduler']
    scheduler.update_company_schedule(company_id)
    
    return jsonify({'success': True, 'message': '설정이 업데이트되었습니다.'})

@erpia_bp.route('/api/erpia/test-connection/<int:company_id>', methods=['POST'])
@login_required
def test_erpia_connection(company_id):
    """ERPia 연결 테스트"""
    try:
        client = ErpiaApiClient(company_id)
        
        # 간단한 API 호출로 연결 테스트
        today = datetime.now().strftime('%Y%m%d')
        result = client.fetch_sales_data(today, today)
        
        return jsonify({
            'success': True,
            'message': f'연결 성공! {len(result)}건의 데이터를 확인했습니다.',
            'data_count': len(result)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'연결 실패: {str(e)}'
        }), 400

@erpia_bp.route('/api/erpia/manual-batch/<int:company_id>', methods=['POST'])
@login_required
@permission_required('admin_erpia', 'execute')
def run_manual_batch(company_id):
    """수동 배치 실행"""
    data = request.get_json()
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    try:
        from app.services.erpia_batch_service import ErpiaBatchService
        
        batch_service = ErpiaBatchService(company_id)
        result = batch_service.collect_daily_sales(start_date, end_date)
        
        return jsonify({
            'success': True,
            'message': '배치가 성공적으로 실행되었습니다.',
            'result': result
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'배치 실행 실패: {str(e)}'
        }), 500
```

---

## ⚙️ 배치 스케줄링 웹 설정

### **1. ERPia 설정 모델**
```python
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from app.models.base import BaseModel

class ErpiaSettings(BaseModel):
    """ERPia 배치 설정 (웹 관리)"""
    __tablename__ = 'erpia_settings'
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    setting_key = Column(String(100), nullable=False)
    setting_value = Column(Text, nullable=False)
    setting_type = Column(String(50), nullable=False)  # time, number, boolean, text
    description = Column(Text)
    min_value = Column(Integer)
    max_value = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('company_id', 'setting_key'),
    )

# 기본 설정 데이터
DEFAULT_ERPIA_SETTINGS = [
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
    }
]
```

### **2. 웹 설정 화면**
```html
<!-- templates/admin/erpia_settings.html -->
<div class="card">
    <div class="card-header">
        <h5 class="card-title">
            <i class="bi bi-gear"></i> ERPia 배치 설정
        </h5>
    </div>
    <div class="card-body">
        <form id="erpiaSettingsForm">
            <!-- 배치 시간 설정 -->
            <div class="row mb-3">
                <label class="col-sm-3 col-form-label">일일 배치 실행 시간</label>
                <div class="col-sm-9">
                    <input type="time" class="form-control" name="schedule_time" value="02:00" required>
                    <div class="form-text">매일 자동으로 ERPia 데이터를 수집할 시간을 설정합니다.</div>
                </div>
            </div>
            
            <!-- API 호출 간격 -->
            <div class="row mb-3">
                <label class="col-sm-3 col-form-label">API 호출 간격 (초)</label>
                <div class="col-sm-9">
                    <input type="number" class="form-control" name="call_interval" value="3" min="1" max="60" required>
                    <div class="form-text">ERPia 서버 안정성을 위한 호출 간격입니다. (권장: 3초)</div>
                </div>
            </div>
            
            <!-- 페이지 크기 -->
            <div class="row mb-3">
                <label class="col-sm-3 col-form-label">페이지당 데이터 건수</label>
                <div class="col-sm-9">
                    <input type="number" class="form-control" name="page_size" value="30" min="1" max="30" required>
                    <div class="form-text">한 번에 가져올 데이터 건수입니다. (최대: 30건)</div>
                </div>
            </div>
            
            <!-- 자동 배치 활성화 -->
            <div class="row mb-3">
                <label class="col-sm-3 col-form-label">자동 배치</label>
                <div class="col-sm-9">
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" name="auto_batch_enabled" checked>
                        <label class="form-check-label">자동 배치 활성화</label>
                    </div>
                    <div class="form-text">매일 지정된 시간에 자동으로 배치를 실행합니다.</div>
                </div>
            </div>
            
            <!-- 사은품 자동 분류 -->
            <div class="row mb-3">
                <label class="col-sm-3 col-form-label">사은품 처리</label>
                <div class="col-sm-9">
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" name="auto_gift_classify" checked>
                        <label class="form-check-label">0원 상품 자동 사은품 분류</label>
                    </div>
                    <div class="form-text">공급가 0원인 상품을 자동으로 사은품으로 분류합니다.</div>
                </div>
            </div>
            
            <!-- 재시도 설정 -->
            <div class="row mb-3">
                <label class="col-sm-3 col-form-label">재시도 횟수</label>
                <div class="col-sm-9">
                    <input type="number" class="form-control" name="retry_count" value="3" min="1" max="10" required>
                    <div class="form-text">API 호출 실패 시 재시도할 횟수입니다.</div>
                </div>
            </div>
            
            <div class="d-flex justify-content-end">
                <button type="button" class="btn btn-outline-primary me-2" onclick="testConnection()">
                    <i class="bi bi-wifi"></i> 연결 테스트
                </button>
                <button type="submit" class="btn btn-primary">
                    <i class="bi bi-check-lg"></i> 설정 저장
                </button>
            </div>
        </form>
    </div>
</div>

<!-- 배치 상태 모니터링 -->
<div class="card mt-4">
    <div class="card-header">
        <h5 class="card-title">
            <i class="bi bi-activity"></i> 배치 실행 현황
        </h5>
    </div>
    <div class="card-body">
        <div id="batchStatus" class="table-responsive">
            <!-- 배치 실행 이력 테이블 -->
        </div>
        
        <div class="mt-3">
            <button type="button" class="btn btn-success" onclick="runManualBatch()">
                <i class="bi bi-play-fill"></i> 수동 배치 실행
            </button>
        </div>
    </div>
</div>

<script>
// ERPia 설정 관리 JavaScript
document.getElementById('erpiaSettingsForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const settings = {};
    
    for (let [key, value] of formData.entries()) {
        if (this.querySelector(`[name="${key}"]`).type === 'checkbox') {
            settings[key] = this.querySelector(`[name="${key}"]`).checked;
        } else {
            settings[key] = value;
        }
    }
    
    try {
        const response = await fetch(`/api/erpia/settings/${currentCompanyId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(settings)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('설정이 저장되었습니다.', 'success');
            loadBatchStatus(); // 상태 새로고침
        } else {
            showAlert('설정 저장에 실패했습니다.', 'error');
        }
    } catch (error) {
        showAlert('오류가 발생했습니다.', 'error');
    }
});

async function testConnection() {
    const button = event.target;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 테스트 중...';
    
    try {
        const response = await fetch(`/api/erpia/test-connection/${currentCompanyId}`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert(result.message, 'success');
        } else {
            showAlert(result.message, 'error');
        }
    } catch (error) {
        showAlert('연결 테스트 중 오류가 발생했습니다.', 'error');
    } finally {
        button.disabled = false;
        button.innerHTML = '<i class="bi bi-wifi"></i> 연결 테스트';
    }
}

async function runManualBatch() {
    const startDate = prompt('시작일을 입력하세요 (YYYYMMDD):', 
        new Date().toISOString().slice(0, 10).replace(/-/g, ''));
    
    if (!startDate) return;
    
    const endDate = prompt('종료일을 입력하세요 (YYYYMMDD):', startDate);
    if (!endDate) return;
    
    try {
        const response = await fetch(`/api/erpia/manual-batch/${currentCompanyId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                start_date: startDate,
                end_date: endDate
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('배치가 성공적으로 실행되었습니다.', 'success');
            loadBatchStatus();
        } else {
            showAlert(result.message, 'error');
        }
    } catch (error) {
        showAlert('배치 실행 중 오류가 발생했습니다.', 'error');
    }
}
</script>
```

---

## 🎁 사은품 처리 로직

### **1. 사은품 분류 규칙**
```python
class GiftClassifier:
    """사은품 분류 로직"""
    
    @staticmethod
    def classify_product(gong_amt: int, pan_amt: int, product_name: str, 
                        product_code: str, brand_code: str) -> Dict[str, Any]:
        """
        상품 분류 로직
        
        분류 기준:
        1. 공급가 0원 AND 판매가 0원 → 사은품
        2. 상품명에 '사은품', '증정품' 포함 → 사은품  
        3. 브랜드 코드가 'GIFT'로 시작 → 사은품
        4. 나머지 → 일반상품
        """
        
        # 기본 정보
        result = {
            'original_gong_amt': gong_amt,
            'original_pan_amt': pan_amt,
            'classification_reason': []
        }
        
        # 1. 0원 상품 체크 (우선순위 1)
        if gong_amt == 0 and pan_amt == 0:
            result.update({
                'product_type': 'GIFT',
                'is_revenue': False,
                'analysis_category': '사은품',
                'revenue_impact': 0,
                'gift_type': 'ZERO_PRICE',
                'include_in_quantity': True,    # 수량 집계에는 포함
                'include_in_revenue': False     # 매출 집계에서 제외
            })
            result['classification_reason'].append('공급가 0원')
            return result
        
        # 2. 상품명 기반 분류
        gift_keywords = ['사은품', '증정품', '무료', '샘플', '체험']
        product_name_lower = product_name.lower()
        
        for keyword in gift_keywords:
            if keyword in product_name_lower:
                result.update({
                    'product_type': 'GIFT',
                    'is_revenue': False,
                    'analysis_category': '사은품',
                    'revenue_impact': 0,
                    'gift_type': 'NAME_BASED',
                    'include_in_quantity': True,
                    'include_in_revenue': False
                })
                result['classification_reason'].append(f'상품명 키워드: {keyword}')
                return result
        
        # 3. 브랜드 코드 기반 분류
        if brand_code and brand_code.startswith('GIFT'):
            result.update({
                'product_type': 'GIFT',
                'is_revenue': False,
                'analysis_category': '사은품',
                'revenue_impact': 0,
                'gift_type': 'BRAND_BASED',
                'include_in_quantity': True,
                'include_in_revenue': False
            })
            result['classification_reason'].append('브랜드 코드: GIFT')
            return result
        
        # 4. 일반상품으로 분류
        result.update({
            'product_type': 'PRODUCT',
            'is_revenue': True,
            'analysis_category': '매출상품',
            'revenue_impact': gong_amt,
            'gift_type': None,
            'include_in_quantity': True,
            'include_in_revenue': True
        })
        result['classification_reason'].append('일반상품')
        
        return result

    @staticmethod
    def get_gift_summary_by_order(products: List[Dict]) -> Dict[str, Any]:
        """주문별 사은품 요약 정보"""
        total_products = len(products)
        gift_products = [p for p in products if p.get('product_type') == 'GIFT']
        revenue_products = [p for p in products if p.get('product_type') == 'PRODUCT']
        
        return {
            'total_product_count': total_products,
            'gift_product_count': len(gift_products),
            'revenue_product_count': len(revenue_products),
            'gift_ratio': len(gift_products) / total_products if total_products > 0 else 0,
            'total_revenue': sum(p.get('revenue_impact', 0) for p in revenue_products),
            'gift_products': [p['product_name'] for p in gift_products]
        }
```

### **2. 사은품 집계 및 분석**
```python
class GiftAnalytics:
    """사은품 분석 로직"""
    
    @staticmethod
    def generate_gift_report(start_date: str, end_date: str, company_id: int) -> Dict:
        """사은품 분석 리포트 생성"""
        from app.models.sales_analysis import SalesAnalysisMaster
        
        # 기간별 사은품 데이터 조회
        gift_data = SalesAnalysisMaster.query.filter(
            SalesAnalysisMaster.company_id == company_id,
            SalesAnalysisMaster.sale_date.between(start_date, end_date),
            SalesAnalysisMaster.product_type == 'GIFT'
        ).all()
        
        # 일반상품 데이터 조회
        product_data = SalesAnalysisMaster.query.filter(
            SalesAnalysisMaster.company_id == company_id,
            SalesAnalysisMaster.sale_date.between(start_date, end_date),
            SalesAnalysisMaster.product_type == 'PRODUCT'
        ).all()
        
        # 분석 결과
        analysis = {
            'period': {'start_date': start_date, 'end_date': end_date},
            'summary': {
                'total_orders': len(set([d.sales_no for d in gift_data + product_data])),
                'orders_with_gifts': len(set([d.sales_no for d in gift_data])),
                'total_gift_quantity': sum([d.quantity for d in gift_data]),
                'total_product_quantity': sum([d.quantity for d in product_data]),
                'gift_attachment_rate': 0  # 사은품 부착률
            },
            'gift_by_product': {},
            'gift_by_brand': {},
            'gift_by_channel': {},
            'top_gift_combinations': []
        }
        
        # 사은품 부착률 계산
        if analysis['summary']['total_orders'] > 0:
            analysis['summary']['gift_attachment_rate'] = (
                analysis['summary']['orders_with_gifts'] / 
                analysis['summary']['total_orders'] * 100
            )
        
        # 상품별 사은품 통계
        from collections import defaultdict
        
        gift_by_product = defaultdict(int)
        gift_by_brand = defaultdict(int)
        gift_by_channel = defaultdict(int)
        
        for gift in gift_data:
            gift_by_product[gift.product_name] += gift.quantity
            if gift.brand_name:
                gift_by_brand[gift.brand_name] += gift.quantity
            if gift.channel_type:
                gift_by_channel[gift.channel_type] += gift.quantity
        
        # 상위 10개 사은품
        analysis['gift_by_product'] = dict(
            sorted(gift_by_product.items(), key=lambda x: x[1], reverse=True)[:10]
        )
        analysis['gift_by_brand'] = dict(
            sorted(gift_by_brand.items(), key=lambda x: x[1], reverse=True)[:10]
        )
        analysis['gift_by_channel'] = dict(gift_by_channel)
        
        return analysis
    
    @staticmethod
    def get_gift_impact_on_sales(start_date: str, end_date: str, company_id: int) -> Dict:
        """사은품이 매출에 미치는 영향 분석"""
        
        # 사은품이 있는 주문 vs 없는 주문 비교
        orders_with_gifts = db.session.query(
            SalesAnalysisMaster.sales_no,
            func.sum(SalesAnalysisMaster.total_amount).label('total_amount')
        ).filter(
            SalesAnalysisMaster.company_id == company_id,
            SalesAnalysisMaster.sale_date.between(start_date, end_date),
            SalesAnalysisMaster.sales_no.in_(
                db.session.query(SalesAnalysisMaster.sales_no).filter(
                    SalesAnalysisMaster.product_type == 'GIFT'
                )
            )
        ).group_by(SalesAnalysisMaster.sales_no).all()
        
        orders_without_gifts = db.session.query(
            SalesAnalysisMaster.sales_no,
            func.sum(SalesAnalysisMaster.total_amount).label('total_amount')
        ).filter(
            SalesAnalysisMaster.company_id == company_id,
            SalesAnalysisMaster.sale_date.between(start_date, end_date),
            ~SalesAnalysisMaster.sales_no.in_(
                db.session.query(SalesAnalysisMaster.sales_no).filter(
                    SalesAnalysisMaster.product_type == 'GIFT'
                )
            )
        ).group_by(SalesAnalysisMaster.sales_no).all()
        
        # 평균 주문 금액 비교
        avg_with_gifts = (
            sum([o.total_amount for o in orders_with_gifts]) / len(orders_with_gifts)
            if orders_with_gifts else 0
        )
        
        avg_without_gifts = (
            sum([o.total_amount for o in orders_without_gifts]) / len(orders_without_gifts)
            if orders_without_gifts else 0
        )
        
        return {
            'orders_with_gifts': {
                'count': len(orders_with_gifts),
                'avg_amount': avg_with_gifts,
                'total_amount': sum([o.total_amount for o in orders_with_gifts])
            },
            'orders_without_gifts': {
                'count': len(orders_without_gifts),
                'avg_amount': avg_without_gifts,
                'total_amount': sum([o.total_amount for o in orders_without_gifts])
            },
            'impact_analysis': {
                'avg_amount_diff': avg_with_gifts - avg_without_gifts,
                'avg_amount_increase_rate': (
                    (avg_with_gifts - avg_without_gifts) / avg_without_gifts * 100
                    if avg_without_gifts > 0 else 0
                )
            }
        }
```

---

## 🏢 멀티테넌트 지원

### **회사별 ERPia 설정 관리**
```python
class CompanyErpiaConfig(BaseModel):
    """회사별 ERPia 연동 설정"""
    __tablename__ = 'company_erpia_configs'
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    admin_code = Column(String(100), nullable=False)
    password = Column(String(200), nullable=False)  # 암호화 저장
    api_url = Column(String(500), default='http://www.erpia.net/xml/xml.asp')
    is_active = Column(Boolean, default=True)
    last_sync_date = Column(DateTime)
    sync_error_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    company = relationship("Company", back_populates="erpia_config")
    
    def encrypt_password(self, password: str):
        """비밀번호 암호화"""
        from cryptography.fernet import Fernet
        key = current_app.config['ENCRYPTION_KEY']
        f = Fernet(key)
        self.password = f.encrypt(password.encode()).decode()
    
    def decrypt_password(self) -> str:
        """비밀번호 복호화"""
        from cryptography.fernet import Fernet
        key = current_app.config['ENCRYPTION_KEY']
        f = Fernet(key)
        return f.decrypt(self.password.encode()).decode()
```

---

## 📊 모니터링 및 로그

### **배치 실행 로그**
```python
class ErpiaBatchLog(BaseModel):
    """ERPia 배치 실행 로그"""
    __tablename__ = 'erpia_batch_logs'
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    batch_type = Column(String(50), nullable=False)  # daily_sales, manual, test
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    status = Column(String(20), nullable=False)  # RUNNING, SUCCESS, FAILED
    
    # 실행 결과
    total_pages = Column(Integer)
    processed_orders = Column(Integer)
    processed_products = Column(Integer)
    gift_products = Column(Integer)
    error_count = Column(Integer)
    
    # 상세 정보
    date_range = Column(String(50))  # 20250805-20250805
    error_message = Column(Text)
    execution_details = Column(Text)  # JSON 형태의 상세 정보
    
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

📅 **업데이트**: 2025-08-05  
📝 **버전**: v2.0  
🎯 **추가 기능**: 배치 웹 설정, 사은품 자동 분류 