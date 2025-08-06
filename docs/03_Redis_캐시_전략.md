# 🚀 **MIS v2 Redis 캐시 전략**

## 📋 **목차**
1. [캐시 전략 개요](#캐시-전략-개요)
2. [Redis 구성](#redis-구성)
3. [캐시 데이터 분류](#캐시-데이터-분류)
4. [캐시 키 네이밍 규칙](#캐시-키-네이밍-규칙)
5. [TTL 설정 전략](#ttl-설정-전략)
6. [캐시 무효화 전략](#캐시-무효화-전략)
7. [구현 예제](#구현-예제)
8. [배치 시스템 캐시](#배치-시스템-캐시)
9. [사은품 분류 캐시](#사은품-분류-캐시)

---

## 🎯 **캐시 전략 개요**

### **캐시 사용 목적**
- **성능 향상**: DB 쿼리 부하 감소
- **세션 관리**: 사용자 세션 데이터 저장
- **임시 데이터**: 계산 결과, 중간 처리 데이터
- **권한 캐시**: 메뉴별 사용자 권한 정보
- **⚙️ 배치 관리**: 배치 설정, 실행 상태, 스케줄 정보 (신규)
- **🎁 사은품 분류**: 분류 규칙, 분석 결과, 통계 데이터 (신규)

### **캐시 패턴**
1. **Cache-Aside**: 애플리케이션에서 직접 캐시 관리
2. **Write-Through**: 데이터 저장 시 캐시도 함께 업데이트
3. **Write-Behind**: 캐시 우선 저장, 나중에 DB 동기화
4. **⚙️ Background Refresh**: 배치 실행 결과 백그라운드 캐시 갱신 (신규)
5. **🎁 Lazy Loading**: 사은품 분류 결과 지연 로딩 (신규)

---

## ⚙️ **Redis 구성**

### **Redis 설정** (업데이트)
```conf
# redis.conf
maxmemory 1gb                    # 1GB로 증가 (배치/사은품 데이터 고려)
maxmemory-policy allkeys-lru
timeout 300
tcp-keepalive 60
save 900 1
save 300 10
save 60 10000

# 배치 처리용 설정
client-output-buffer-limit normal 256mb 128mb 60
client-output-buffer-limit replica 512mb 256mb 60
```

### **Database 분리** (업데이트)
```python
# Redis DB 분리 전략
REDIS_DBS = {
    'session': 0,           # 사용자 세션
    'cache': 1,             # 일반 캐시
    'temp': 2,              # 임시 데이터
    'queue': 3,             # 작업 큐
    'batch': 4,             # 배치 관련 데이터 (신규)
    'gift': 5,              # 사은품 분류 데이터 (신규)
}
```

---

## 📊 **캐시 데이터 분류**

### **1. 세션 데이터** (DB 0)
```python
# 사용자 세션 정보
session:user:{user_id} = {
    'user_id': 123,
    'username': 'admin',
    'dept_id': 1,
    'current_company_id': 1,      # 멀티테넌트 지원 (신규)
    'permissions': {...},
    'last_activity': '2024-01-01T10:00:00Z'
}
# TTL: 24시간
```

### **2. 사용자 권한** (DB 1)
```python
# 메뉴별 사용자 권한
permissions:user:{user_id} = {
    'admin_user': {'create': True, 'read': True, 'update': True, 'delete': True},
    'admin_batch': {'create': False, 'read': True, 'update': True, 'delete': False},
    'admin_gift': {'create': True, 'read': True, 'update': True, 'delete': False},
    'trade_order': {'create': True, 'read': True, 'update': False, 'delete': False},
    'customer_info': {'create': False, 'read': True, 'update': False, 'delete': False}
}
# TTL: 1시간
```

### **3. 마스터 데이터** (DB 1)
```python
# 부서 목록 (자주 조회되는 마스터 데이터)
master:departments = [
    {'id': 1, 'name': '시스템관리', 'sort': 1},
    {'id': 2, 'name': '영업본부', 'sort': 2},
    {'id': 3, 'name': '무역팀', 'sort': 3}
]
# TTL: 6시간

# 브랜드 목록
master:brands = [
    {'id': 1, 'name': '리안', 'code': 'REAN'},
    {'id': 2, 'name': '조이', 'code': 'JOY'},
    {'id': 3, 'name': '뉴나', 'code': 'NUNA'}
]
# TTL: 6시간

# 회사 목록 (멀티테넌트 지원)
master:companies = [
    {'id': 1, 'code': 'AONE', 'name': '에이원'},
    {'id': 2, 'code': 'AONE_WORLD', 'name': '에이원 월드'}
]
# TTL: 12시간
```

### **4. 통계 데이터** (DB 1)
```python
# 일일 판매 통계 (무거운 쿼리 결과)
stats:daily_sales:{date} = {
    'total_amount': 1000000,
    'order_count': 150,
    'brand_stats': {...},
    'channel_stats': {...},
    'gift_stats': {              # 사은품 통계 추가 (신규)
        'gift_order_count': 85,
        'gift_attachment_rate': 56.7,
        'total_gift_cost': 125000
    }
}
# TTL: 12시간

# 시리얼 생성 카운트
stats:serial_count:{brand_code}:{date} = 1250
# TTL: 24시간
```

### **5. 임시 처리 데이터** (DB 2)
```python
# 엑셀 업로드 처리 상태
temp:excel_upload:{upload_id} = {
    'status': 'processing',
    'total_rows': 1000,
    'processed_rows': 500,
    'error_count': 5,
    'start_time': '2024-01-01T10:00:00Z'
}
# TTL: 1시간

# 대용량 리포트 생성 결과
temp:report:{report_id} = {
    'status': 'completed',
    'file_path': '/tmp/reports/sales_20240101.xlsx',
    'download_url': 'https://...'
}
# TTL: 30분
```

### **6. 배치 시스템 데이터** (DB 4) - 신규 추가
```python
# 회사별 배치 설정
batch:config:{company_id} = {
    'batch_enabled': True,
    'batch_hour': 2,
    'batch_minute': 0,
    'api_call_interval': 3,
    'page_size': 30,
    'retry_count': 3,
    'auto_gift_classify': True,
    'gift_keywords': ['사은품', '증정품', '무료'],
    'last_updated': '2024-01-01T10:00:00Z'
}
# TTL: 24시간

# 배치 실행 상태
batch:status:{company_id} = {
    'status': 'running',         # running, completed, failed
    'start_time': '2024-01-01T02:00:00Z',
    'current_step': 'data_collection',
    'progress': {
        'total_pages': 50,
        'processed_pages': 23,
        'total_records': 1500,
        'processed_records': 690,
        'classified_gifts': 125
    },
    'errors': []
}
# TTL: 1시간

# 배치 실행 이력
batch:history:{company_id}:{date} = {
    'execution_time': '2024-01-01T02:00:00Z',
    'duration_seconds': 180,
    'status': 'completed',
    'total_records': 1500,
    'gift_classified': 125,
    'errors': [],
    'summary': {
        'orders_processed': 450,
        'products_processed': 1500,
        'gifts_identified': 125,
        'revenue_products': 1375
    }
}
# TTL: 7일

# 배치 실행 락 (동시 실행 방지)
batch:lock:{company_id} = {
    'locked_by': 'scheduler_instance_1',
    'locked_at': '2024-01-01T02:00:00Z',
    'batch_id': 'batch_20240101_020000'
}
# TTL: 30분
```

### **7. 사은품 분류 데이터** (DB 5) - 신규 추가
```python
# 회사별 사은품 분류 규칙
gift:rules:{company_id} = {
    'auto_classify': True,
    'zero_price_rule': True,
    'keywords': ['사은품', '증정품', '무료', '샘플', '체험'],
    'exclude_from_revenue': True,
    'master_products': ['P001', 'P002', 'P003'],  # 사은품 마스터 등록 상품
    'last_updated': '2024-01-01T10:00:00Z'
}
# TTL: 6시간

# 사은품 분류 결과 캐시
gift:classification:{product_code}:{company_id} = {
    'product_type': 'GIFT',
    'gift_type': 'ZERO_PRICE',
    'classification_reason': '공급가 0원 (자동분류)',
    'is_revenue': False,
    'revenue_impact': 0,
    'classified_at': '2024-01-01T10:00:00Z'
}
# TTL: 4시간

# 사은품 분석 통계
gift:analytics:{company_id}:{date} = {
    'total_orders': 450,
    'orders_with_gifts': 255,
    'gift_attachment_rate': 56.7,
    'gift_products': {
        'P001': {'count': 85, 'name': '사은품 패드'},
        'P002': {'count': 42, 'name': '증정품 쿠션'},
        'P003': {'count': 18, 'name': '체험용 샘플'}
    },
    'gift_by_channel': {
        'online': {'orders': 180, 'gifts': 98},
        'offline': {'orders': 270, 'gifts': 157}
    },
    'revenue_impact': {
        'avg_order_with_gifts': 425000,
        'avg_order_without_gifts': 380000,
        'impact_rate': 11.8
    }
}
# TTL: 8시간

# 사은품 마스터 캐시
gift:master:{company_id} = [
    {
        'product_code': 'P001',
        'product_name': '사은품 패드',
        'brand_code': 'NUNA',
        'category': '샘플',
        'standard_cost': 15000,
        'is_active': True
    }
]
# TTL: 6시간
```

---

## 🏷️ **캐시 키 네이밍 규칙** (업데이트)

### **네이밍 패턴**
```
{prefix}:{category}:{identifier}:{sub_key}
```

### **예시** (신규 추가)
```python
# 세션
"session:user:123"
"session:temp:upload_abc123"

# 권한
"permissions:user:123"
"permissions:menu:admin_user"

# 마스터 데이터
"master:departments"
"master:brands"
"master:companies"
"master:products:category:1"

# 통계
"stats:daily_sales:20240101"
"stats:monthly_revenue:202401"

# 임시 데이터
"temp:excel_upload:abc123"
"temp:report_generation:def456"

# 배치 시스템 (신규)
"batch:config:1"                    # 회사 1의 배치 설정
"batch:status:1"                    # 회사 1의 배치 상태
"batch:history:1:20240101"          # 회사 1의 2024-01-01 배치 이력
"batch:lock:1"                      # 회사 1의 배치 실행 락

# 사은품 분류 (신규)
"gift:rules:1"                      # 회사 1의 사은품 분류 규칙
"gift:classification:P001:1"        # 회사 1의 P001 상품 분류 결과
"gift:analytics:1:20240101"         # 회사 1의 2024-01-01 사은품 분석
"gift:master:1"                     # 회사 1의 사은품 마스터

# 락 (동시 처리 방지)
"lock:serial_generation:REAN"
"lock:batch_process:daily_stats"
"lock:gift_classification:1"        # 회사 1의 사은품 분류 락 (신규)
```

---

## ⏰ **TTL 설정 전략** (업데이트)

### **TTL 기준**
| 데이터 유형 | TTL | 이유 |
|-------------|-----|------|
| 사용자 세션 | 24시간 | 하루 업무 주기 |
| 사용자 권한 | 1시간 | 권한 변경 반영 |
| 마스터 데이터 | 6시간 | 자주 변경되지 않음 |
| 통계 데이터 | 12시간 | 일 단위 업데이트 |
| 임시 데이터 | 30분-1시간 | 짧은 생명주기 |
| 락 데이터 | 5분 | 데드락 방지 |
| **배치 설정** | **24시간** | **설정 변경 빈도 낮음** |
| **배치 상태** | **1시간** | **실행 중 상태 추적** |
| **배치 이력** | **7일** | **일주일 이력 보관** |
| **사은품 규칙** | **6시간** | **정책 변경 반영** |
| **사은품 분류** | **4시간** | **분류 정확도 유지** |
| **사은품 분석** | **8시간** | **분석 결과 안정성** |

### **TTL 설정 코드** (업데이트)
```python
# app/utils/cache.py
class CacheConfig:
    TTL = {
        'session': 86400,           # 24시간
        'permissions': 3600,        # 1시간
        'master_data': 21600,       # 6시간
        'statistics': 43200,        # 12시간
        'temp_data': 1800,          # 30분
        'lock': 300,                # 5분
        
        # 배치 시스템 (신규)
        'batch_config': 86400,      # 24시간
        'batch_status': 3600,       # 1시간
        'batch_history': 604800,    # 7일
        'batch_lock': 1800,         # 30분
        
        # 사은품 분류 (신규)
        'gift_rules': 21600,        # 6시간
        'gift_classification': 14400, # 4시간
        'gift_analytics': 28800,    # 8시간
        'gift_master': 21600,       # 6시간
    }
```

---

## 🔄 **캐시 무효화 전략** (업데이트)

### **1. 수동 무효화** (즉시 반영 필요)
```python
# 사용자 권한 변경 시
def update_user_permissions(user_id, permissions):
    # DB 업데이트
    db.session.commit()
    
    # 캐시 삭제
    cache.delete(f"permissions:user:{user_id}")
    cache.delete(f"session:user:{user_id}")

# 배치 설정 변경 시 (신규)
def update_batch_config(company_id, config):
    # DB 업데이트
    db.session.commit()
    
    # 배치 관련 캐시 삭제
    cache.delete(f"batch:config:{company_id}", db=4)
    cache.delete(f"batch:status:{company_id}", db=4)

# 사은품 규칙 변경 시 (신규)
def update_gift_rules(company_id, rules):
    # DB 업데이트
    db.session.commit()
    
    # 사은품 관련 캐시 전체 삭제
    cache.delete(f"gift:rules:{company_id}", db=5)
    cache.delete_by_pattern(f"gift:classification:*:{company_id}", db=5)
    cache.delete_by_pattern(f"gift:analytics:{company_id}:*", db=5)
```

### **2. 태그 기반 무효화** (관련 데이터 일괄 삭제)
```python
# 브랜드 정보 변경 시 관련 캐시 모두 삭제
def update_brand_info(brand_id):
    # DB 업데이트
    db.session.commit()
    
    # 태그 기반 삭제
    cache.delete_by_pattern(f"master:brands*")
    cache.delete_by_pattern(f"stats:*:brand:{brand_id}*")
    
    # 사은품 분석에서 브랜드 관련 캐시도 삭제 (신규)
    cache.delete_by_pattern(f"gift:analytics:*", db=5)

# 회사 정보 변경 시 (신규)
def update_company_info(company_id):
    # DB 업데이트
    db.session.commit()
    
    # 해당 회사의 모든 캐시 삭제
    cache.delete_by_pattern(f"batch:*:{company_id}", db=4)
    cache.delete_by_pattern(f"gift:*:{company_id}", db=5)
    cache.delete_by_pattern(f"stats:*:{company_id}*", db=1)
```

### **3. 시간 기반 무효화** (스케줄러)
```python
# 매일 자정에 통계 캐시 삭제
@scheduler.task('cron', hour=0, minute=0)
def clear_daily_stats_cache():
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    cache.delete_by_pattern(f"stats:daily_*:{yesterday}")
    cache.delete_by_pattern(f"gift:analytics:*:{yesterday}", db=5)

# 배치 완료 후 관련 캐시 갱신 (신규)
@scheduler.task('cron', hour=3, minute=0)  # 배치 완료 후 1시간 뒤
def refresh_post_batch_cache():
    # 모든 활성 회사의 캐시 갱신
    for company in Company.query.filter_by(is_active=True).all():
        # 배치 상태 캐시 갱신
        cache.delete(f"batch:status:{company.id}", db=4)
        
        # 사은품 분석 캐시 갱신
        today = datetime.now().strftime('%Y%m%d')
        cache.delete(f"gift:analytics:{company.id}:{today}", db=5)
```

---

## 💻 **구현 예제** (업데이트)

### **1. 캐시 유틸리티 클래스** (확장)
```python
# app/utils/cache.py
import redis
import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional, List
from flask import current_app

class CacheManager:
    """Redis 캐시 관리자 (배치/사은품 지원)"""
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(
            current_app.config['REDIS_URL'],
            decode_responses=False
        )
        
    def set(self, key: str, value: Any, ttl: int = 3600, db: int = 1) -> bool:
        """캐시 데이터 저장"""
        try:
            self.redis_client.select(db)
            serialized_value = pickle.dumps(value)
            return self.redis_client.setex(key, ttl, serialized_value)
        except Exception as e:
            current_app.logger.error(f"Cache set error: {e}")
            return False
    
    def get(self, key: str, db: int = 1) -> Optional[Any]:
        """캐시 데이터 조회"""
        try:
            self.redis_client.select(db)
            value = self.redis_client.get(key)
            if value:
                return pickle.loads(value)
            return None
        except Exception as e:
            current_app.logger.error(f"Cache get error: {e}")
            return None
    
    def delete(self, key: str, db: int = 1) -> bool:
        """캐시 데이터 삭제"""
        try:
            self.redis_client.select(db)
            return self.redis_client.delete(key) > 0
        except Exception as e:
            current_app.logger.error(f"Cache delete error: {e}")
            return False
    
    def delete_by_pattern(self, pattern: str, db: int = 1) -> int:
        """패턴으로 캐시 데이터 일괄 삭제"""
        try:
            self.redis_client.select(db)
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            current_app.logger.error(f"Cache delete by pattern error: {e}")
            return 0
    
    def set_lock(self, key: str, value: str = "locked", ttl: int = 300, db: int = 1) -> bool:
        """락 설정 (배치 동시 실행 방지용)"""
        try:
            self.redis_client.select(db)
            return self.redis_client.set(key, value, nx=True, ex=ttl)
        except Exception as e:
            current_app.logger.error(f"Cache set lock error: {e}")
            return False
    
    def release_lock(self, key: str, db: int = 1) -> bool:
        """락 해제"""
        return self.delete(key, db)

# 전역 캐시 인스턴스
cache = CacheManager()
```

### **2. 배치 캐시 서비스** (신규)
```python
# app/services/batch_cache.py
from app.utils.cache import cache, CacheConfig
from app.models.company_erpia_config import CompanyErpiaConfig
from datetime import datetime

class BatchCache:
    """배치 시스템 캐시 서비스"""
    
    @staticmethod
    def get_batch_config(company_id: int) -> dict:
        """배치 설정 조회 (캐시 우선)"""
        cache_key = f"batch:config:{company_id}"
        
        # 캐시에서 먼저 조회
        config = cache.get(cache_key, db=4)
        if config:
            return config
        
        # 캐시 미스 시 DB 조회
        db_config = CompanyErpiaConfig.query.filter_by(company_id=company_id).first()
        if not db_config:
            return {}
        
        config = {
            'batch_enabled': db_config.batch_enabled,
            'batch_hour': db_config.batch_hour,
            'batch_minute': db_config.batch_minute,
            'api_call_interval': db_config.api_call_interval,
            'page_size': db_config.page_size,
            'retry_count': db_config.retry_count,
            'auto_gift_classify': db_config.auto_gift_classify,
            'gift_keywords': json.loads(db_config.gift_keywords) if db_config.gift_keywords else [],
            'last_updated': datetime.utcnow().isoformat()
        }
        
        # 캐시에 저장
        cache.set(cache_key, config, CacheConfig.TTL['batch_config'], db=4)
        
        return config
    
    @staticmethod
    def set_batch_status(company_id: int, status_data: dict):
        """배치 상태 저장"""
        cache_key = f"batch:status:{company_id}"
        cache.set(cache_key, status_data, CacheConfig.TTL['batch_status'], db=4)
    
    @staticmethod
    def get_batch_status(company_id: int) -> dict:
        """배치 상태 조회"""
        cache_key = f"batch:status:{company_id}"
        return cache.get(cache_key, db=4) or {}
    
    @staticmethod
    def set_batch_lock(company_id: int, batch_id: str) -> bool:
        """배치 실행 락 설정"""
        cache_key = f"batch:lock:{company_id}"
        lock_data = {
            'locked_by': f'batch_{batch_id}',
            'locked_at': datetime.utcnow().isoformat(),
            'batch_id': batch_id
        }
        return cache.set(cache_key, lock_data, CacheConfig.TTL['batch_lock'], db=4)
    
    @staticmethod
    def release_batch_lock(company_id: int) -> bool:
        """배치 실행 락 해제"""
        cache_key = f"batch:lock:{company_id}"
        return cache.delete(cache_key, db=4)
    
    @staticmethod
    def save_batch_history(company_id: int, date: str, history_data: dict):
        """배치 실행 이력 저장"""
        cache_key = f"batch:history:{company_id}:{date}"
        cache.set(cache_key, history_data, CacheConfig.TTL['batch_history'], db=4)
```

### **3. 사은품 캐시 서비스** (신규)
```python
# app/services/gift_cache.py
from app.utils.cache import cache, CacheConfig
from app.models.gift_master import GiftMaster
from app.models.company_erpia_config import CompanyErpiaConfig

class GiftCache:
    """사은품 분류 캐시 서비스"""
    
    @staticmethod
    def get_gift_rules(company_id: int) -> dict:
        """사은품 분류 규칙 조회 (캐시 우선)"""
        cache_key = f"gift:rules:{company_id}"
        
        # 캐시에서 먼저 조회
        rules = cache.get(cache_key, db=5)
        if rules:
            return rules
        
        # 캐시 미스 시 DB 조회
        config = CompanyErpiaConfig.query.filter_by(company_id=company_id).first()
        
        rules = {
            'auto_classify': config.auto_gift_classify if config else True,
            'zero_price_rule': True,
            'keywords': json.loads(config.gift_keywords) if config and config.gift_keywords else [],
            'exclude_from_revenue': config.gift_exclude_from_revenue if config else True,
            'master_products': [gm.product_code for gm in GiftMaster.query.filter_by(
                company_id=company_id, is_active=True
            ).all()],
            'last_updated': datetime.utcnow().isoformat()
        }
        
        # 캐시에 저장
        cache.set(cache_key, rules, CacheConfig.TTL['gift_rules'], db=5)
        
        return rules
    
    @staticmethod
    def cache_classification_result(product_code: str, company_id: int, 
                                  classification: dict):
        """상품 분류 결과 캐시"""
        cache_key = f"gift:classification:{product_code}:{company_id}"
        classification['classified_at'] = datetime.utcnow().isoformat()
        cache.set(cache_key, classification, CacheConfig.TTL['gift_classification'], db=5)
    
    @staticmethod
    def get_cached_classification(product_code: str, company_id: int) -> dict:
        """캐시된 분류 결과 조회"""
        cache_key = f"gift:classification:{product_code}:{company_id}"
        return cache.get(cache_key, db=5) or {}
    
    @staticmethod
    def save_gift_analytics(company_id: int, date: str, analytics_data: dict):
        """사은품 분석 결과 저장"""
        cache_key = f"gift:analytics:{company_id}:{date}"
        cache.set(cache_key, analytics_data, CacheConfig.TTL['gift_analytics'], db=5)
    
    @staticmethod
    def get_gift_analytics(company_id: int, date: str) -> dict:
        """사은품 분석 결과 조회"""
        cache_key = f"gift:analytics:{company_id}:{date}"
        return cache.get(cache_key, db=5) or {}
    
    @staticmethod
    def clear_company_gift_cache(company_id: int):
        """회사별 사은품 캐시 전체 삭제"""
        cache.delete_by_pattern(f"gift:*:{company_id}", db=5)
        cache.delete_by_pattern(f"gift:*:*:{company_id}", db=5)
```

---

## ⚙️ **배치 시스템 캐시** (신규 추가)

### **배치 실행 플로우와 캐시**
```python
# app/services/batch_executor.py
class BatchExecutor:
    """배치 실행기 (캐시 통합)"""
    
    def run_company_batch(self, company_id: int):
        """회사별 배치 실행 (캐시 활용)"""
        
        # 1. 배치 락 설정 (동시 실행 방지)
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if not BatchCache.set_batch_lock(company_id, batch_id):
            self.logger.warning(f"배치 이미 실행 중: 회사 {company_id}")
            return
        
        try:
            # 2. 배치 설정 로드 (캐시 우선)
            config = BatchCache.get_batch_config(company_id)
            if not config.get('batch_enabled', False):
                return
            
            # 3. 배치 상태 초기화
            BatchCache.set_batch_status(company_id, {
                'status': 'running',
                'start_time': datetime.utcnow().isoformat(),
                'batch_id': batch_id,
                'progress': {'total_pages': 0, 'processed_pages': 0}
            })
            
            # 4. ERPia 데이터 수집 및 사은품 분류
            result = self.collect_and_classify(company_id, config)
            
            # 5. 배치 완료 상태 업데이트
            BatchCache.set_batch_status(company_id, {
                'status': 'completed',
                'end_time': datetime.utcnow().isoformat(),
                'result': result
            })
            
            # 6. 배치 이력 저장
            today = datetime.now().strftime('%Y%m%d')
            BatchCache.save_batch_history(company_id, today, {
                'execution_time': datetime.utcnow().isoformat(),
                'duration_seconds': result['duration'],
                'status': 'completed',
                **result
            })
            
        except Exception as e:
            # 오류 상태 업데이트
            BatchCache.set_batch_status(company_id, {
                'status': 'failed',
                'error': str(e),
                'end_time': datetime.utcnow().isoformat()
            })
            raise
            
        finally:
            # 7. 배치 락 해제
            BatchCache.release_batch_lock(company_id)
```

---

## 🎁 **사은품 분류 캐시** (신규 추가)

### **사은품 분류 엔진과 캐시**
```python
# app/services/gift_classifier.py (캐시 통합)
class GiftClassifier:
    """사은품 분류 엔진 (캐시 최적화)"""
    
    def classify_product(self, product_data: dict, company_id: int) -> dict:
        """단일 상품 분류 (캐시 활용)"""
        
        product_code = product_data.get('product_code')
        
        # 1. 캐시된 분류 결과 확인
        cached_result = GiftCache.get_cached_classification(product_code, company_id)
        if cached_result:
            return cached_result
        
        # 2. 분류 규칙 로드 (캐시 우선)
        rules = GiftCache.get_gift_rules(company_id)
        
        # 3. 분류 로직 실행
        classification = self._apply_classification_logic(product_data, rules)
        
        # 4. 분류 결과 캐시
        GiftCache.cache_classification_result(product_code, company_id, classification)
        
        return classification
    
    def generate_daily_analytics(self, company_id: int, date: str) -> dict:
        """일일 사은품 분석 (캐시 활용)"""
        
        # 1. 캐시된 분석 결과 확인
        cached_analytics = GiftCache.get_gift_analytics(company_id, date)
        if cached_analytics:
            return cached_analytics
        
        # 2. 분석 데이터 생성 (무거운 쿼리)
        analytics = self._generate_heavy_analytics(company_id, date)
        
        # 3. 분석 결과 캐시
        GiftCache.save_gift_analytics(company_id, date, analytics)
        
        return analytics
```

---

## 🛡️ **캐시 모니터링** (업데이트)

### **캐시 히트율 추적**
```python
# app/utils/cache_monitor.py
class CacheMonitor:
    """캐시 성능 모니터링 (배치/사은품 포함)"""
    
    @staticmethod
    def log_cache_hit(key: str, db: int = 1):
        """캐시 히트 로그"""
        cache_type = CacheMonitor._get_cache_type(key, db)
        current_app.logger.info(f"Cache HIT [{cache_type}]: {key}")
    
    @staticmethod
    def log_cache_miss(key: str, db: int = 1):
        """캐시 미스 로그"""
        cache_type = CacheMonitor._get_cache_type(key, db)
        current_app.logger.info(f"Cache MISS [{cache_type}]: {key}")
    
    @staticmethod
    def _get_cache_type(key: str, db: int) -> str:
        """캐시 타입 식별"""
        db_types = {
            0: 'SESSION',
            1: 'GENERAL', 
            2: 'TEMP',
            3: 'QUEUE',
            4: 'BATCH',
            5: 'GIFT'
        }
        return db_types.get(db, 'UNKNOWN')
    
    @staticmethod
    def get_cache_stats() -> dict:
        """캐시 통계 정보 (DB별)"""
        stats = {}
        
        for db_num in range(6):  # 0-5번 DB
            cache.redis_client.select(db_num)
            info = cache.redis_client.info('memory')
            key_count = cache.redis_client.dbsize()
            
            db_type = CacheMonitor._get_cache_type('', db_num)
            stats[db_type] = {
                'key_count': key_count,
                'used_memory': info.get('used_memory_human'),
                'hit_rate': info.get('keyspace_hit_rate', 0)
            }
        
        return stats
    
    @staticmethod
    def get_batch_cache_health(company_id: int) -> dict:
        """배치 캐시 상태 확인"""
        config = BatchCache.get_batch_config(company_id)
        status = BatchCache.get_batch_status(company_id)
        
        return {
            'config_cached': bool(config),
            'status_cached': bool(status),
            'last_batch_time': status.get('start_time'),
            'cache_health': 'healthy' if config and status else 'partial'
        }
    
    @staticmethod
    def get_gift_cache_health(company_id: int) -> dict:
        """사은품 캐시 상태 확인"""
        rules = GiftCache.get_gift_rules(company_id)
        today = datetime.now().strftime('%Y%m%d')
        analytics = GiftCache.get_gift_analytics(company_id, today)
        
        return {
            'rules_cached': bool(rules),
            'analytics_cached': bool(analytics),
            'auto_classify': rules.get('auto_classify', False),
            'keyword_count': len(rules.get('keywords', [])),
            'cache_health': 'healthy' if rules else 'missing'
        }
```

---

**✅ 웹 기반 배치 시스템과 사은품 자동 분류가 완전히 반영된 Redis 캐시 전략 완료!**  
**📝 배치 설정/상태/이력과 사은품 분류/분석 데이터까지 포함한 종합적인 캐시 시스템으로 MIS v2의 성능을 극대화할 수 있습니다!** 