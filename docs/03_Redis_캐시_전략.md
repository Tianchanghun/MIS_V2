# 🚀 **MIS v2 Redis 캐시 전략**

## 📋 **목차**
1. [캐시 전략 개요](#캐시-전략-개요)
2. [Redis 구성](#redis-구성)
3. [캐시 데이터 분류](#캐시-데이터-분류)
4. [캐시 키 네이밍 규칙](#캐시-키-네이밍-규칙)
5. [TTL 설정 전략](#ttl-설정-전략)
6. [캐시 무효화 전략](#캐시-무효화-전략)
7. [구현 예제](#구현-예제)

---

## 🎯 **캐시 전략 개요**

### **캐시 사용 목적**
- **성능 향상**: DB 쿼리 부하 감소
- **세션 관리**: 사용자 세션 데이터 저장
- **임시 데이터**: 계산 결과, 중간 처리 데이터
- **권한 캐시**: 메뉴별 사용자 권한 정보

### **캐시 패턴**
1. **Cache-Aside**: 애플리케이션에서 직접 캐시 관리
2. **Write-Through**: 데이터 저장 시 캐시도 함께 업데이트
3. **Write-Behind**: 캐시 우선 저장, 나중에 DB 동기화

---

## ⚙️ **Redis 구성**

### **Redis 설정**
```conf
# redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
timeout 300
tcp-keepalive 60
save 900 1
save 300 10
save 60 10000
```

### **Database 분리**
```python
# Redis DB 분리 전략
REDIS_DBS = {
    'session': 0,      # 사용자 세션
    'cache': 1,        # 일반 캐시
    'temp': 2,         # 임시 데이터
    'queue': 3,        # 작업 큐
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
```

### **4. 통계 데이터** (DB 1)
```python
# 일일 판매 통계 (무거운 쿼리 결과)
stats:daily_sales:{date} = {
    'total_amount': 1000000,
    'order_count': 150,
    'brand_stats': {...},
    'channel_stats': {...}
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

---

## 🏷️ **캐시 키 네이밍 규칙**

### **네이밍 패턴**
```
{prefix}:{category}:{identifier}:{sub_key}
```

### **예시**
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
"master:products:category:1"

# 통계
"stats:daily_sales:20240101"
"stats:monthly_revenue:202401"

# 임시 데이터
"temp:excel_upload:abc123"
"temp:report_generation:def456"

# 락 (동시 처리 방지)
"lock:serial_generation:REAN"
"lock:batch_process:daily_stats"
```

---

## ⏰ **TTL 설정 전략**

### **TTL 기준**
| 데이터 유형 | TTL | 이유 |
|-------------|-----|------|
| 사용자 세션 | 24시간 | 하루 업무 주기 |
| 사용자 권한 | 1시간 | 권한 변경 반영 |
| 마스터 데이터 | 6시간 | 자주 변경되지 않음 |
| 통계 데이터 | 12시간 | 일 단위 업데이트 |
| 임시 데이터 | 30분-1시간 | 짧은 생명주기 |
| 락 데이터 | 5분 | 데드락 방지 |

### **TTL 설정 코드**
```python
# app/utils/cache.py
class CacheConfig:
    TTL = {
        'session': 86400,        # 24시간
        'permissions': 3600,     # 1시간
        'master_data': 21600,    # 6시간
        'statistics': 43200,     # 12시간
        'temp_data': 1800,       # 30분
        'lock': 300,             # 5분
    }
```

---

## 🔄 **캐시 무효화 전략**

### **1. 수동 무효화** (즉시 반영 필요)
```python
# 사용자 권한 변경 시
def update_user_permissions(user_id, permissions):
    # DB 업데이트
    db.session.commit()
    
    # 캐시 삭제
    cache.delete(f"permissions:user:{user_id}")
    cache.delete(f"session:user:{user_id}")
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
```

### **3. 시간 기반 무효화** (스케줄러)
```python
# 매일 자정에 통계 캐시 삭제
@scheduler.task('cron', hour=0, minute=0)
def clear_daily_stats_cache():
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    cache.delete_by_pattern(f"stats:daily_*:{yesterday}")
```

---

## 💻 **구현 예제**

### **1. 캐시 유틸리티 클래스**
```python
# app/utils/cache.py
import redis
import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional, List
from flask import current_app

class CacheManager:
    """Redis 캐시 관리자"""
    
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

# 전역 캐시 인스턴스
cache = CacheManager()
```

### **2. 권한 캐시 서비스**
```python
# app/services/permission_cache.py
from app.utils.cache import cache, CacheConfig
from app.models.user import User
from app.models.user_auth import UserAuth

class PermissionCache:
    """사용자 권한 캐시 서비스"""
    
    @staticmethod
    def get_user_permissions(user_id: int) -> dict:
        """사용자 권한 조회 (캐시 우선)"""
        cache_key = f"permissions:user:{user_id}"
        
        # 캐시에서 먼저 조회
        permissions = cache.get(cache_key, db=1)
        if permissions:
            return permissions
        
        # 캐시 미스 시 DB 조회
        user = User.query.get(user_id)
        if not user:
            return {}
        
        # DB에서 권한 정보 조회
        auth_list = UserAuth.query.filter_by(user_id=user_id, use_yn='Y').all()
        permissions = {}
        
        for auth in auth_list:
            menu_code = auth.menu.code if auth.menu else 'unknown'
            permissions[menu_code] = {
                'create': auth.create_yn == 'Y',
                'read': auth.read_yn == 'Y',
                'update': auth.update_yn == 'Y',
                'delete': auth.delete_yn == 'Y'
            }
        
        # 캐시에 저장
        cache.set(cache_key, permissions, CacheConfig.TTL['permissions'], db=1)
        
        return permissions
    
    @staticmethod
    def clear_user_permissions(user_id: int):
        """사용자 권한 캐시 삭제"""
        cache_key = f"permissions:user:{user_id}"
        cache.delete(cache_key, db=1)
```

### **3. 마스터 데이터 캐시**
```python
# app/services/master_cache.py
from app.utils.cache import cache, CacheConfig
from app.models.department import Department
from app.models.brand import Brand

class MasterDataCache:
    """마스터 데이터 캐시 서비스"""
    
    @staticmethod
    def get_departments() -> list:
        """부서 목록 조회"""
        cache_key = "master:departments"
        
        departments = cache.get(cache_key, db=1)
        if departments:
            return departments
        
        # DB 조회
        dept_list = Department.query.filter_by(use_yn='Y').order_by(Department.sort).all()
        departments = [
            {
                'id': dept.dept_id,
                'name': dept.dept_name,
                'sort': dept.sort
            }
            for dept in dept_list
        ]
        
        # 캐시 저장
        cache.set(cache_key, departments, CacheConfig.TTL['master_data'], db=1)
        
        return departments
    
    @staticmethod
    def get_brands() -> list:
        """브랜드 목록 조회"""
        cache_key = "master:brands"
        
        brands = cache.get(cache_key, db=1)
        if brands:
            return brands
        
        # DB 조회
        brand_list = Brand.query.filter_by(use_yn='Y').order_by(Brand.sort).all()
        brands = [
            {
                'id': brand.brand_id,
                'name': brand.brand_name,
                'code': brand.brand_code
            }
            for brand in brand_list
        ]
        
        # 캐시 저장
        cache.set(cache_key, brands, CacheConfig.TTL['master_data'], db=1)
        
        return brands
```

### **4. 통계 캐시 서비스**
```python
# app/services/stats_cache.py
from datetime import datetime, timedelta
from app.utils.cache import cache, CacheConfig
from app.models.trade_order import TradeOrder

class StatsCache:
    """통계 데이터 캐시 서비스"""
    
    @staticmethod
    def get_daily_sales_stats(date: str) -> dict:
        """일일 판매 통계"""
        cache_key = f"stats:daily_sales:{date}"
        
        stats = cache.get(cache_key, db=1)
        if stats:
            return stats
        
        # 무거운 통계 쿼리 실행
        stats = {
            'total_amount': 0,
            'order_count': 0,
            'brand_stats': {},
            'channel_stats': {}
        }
        
        # ... 복잡한 통계 계산 로직 ...
        
        # 캐시 저장 (12시간)
        cache.set(cache_key, stats, CacheConfig.TTL['statistics'], db=1)
        
        return stats
```

---

## 🛡️ **캐시 모니터링**

### **캐시 히트율 추적**
```python
# app/utils/cache_monitor.py
class CacheMonitor:
    """캐시 성능 모니터링"""
    
    @staticmethod
    def log_cache_hit(key: str):
        """캐시 히트 로그"""
        current_app.logger.info(f"Cache HIT: {key}")
    
    @staticmethod
    def log_cache_miss(key: str):
        """캐시 미스 로그"""
        current_app.logger.info(f"Cache MISS: {key}")
    
    @staticmethod
    def get_cache_stats() -> dict:
        """캐시 통계 정보"""
        info = cache.redis_client.info('memory')
        return {
            'used_memory': info.get('used_memory_human'),
            'hit_rate': info.get('keyspace_hit_rate', 0),
            'evicted_keys': info.get('evicted_keys', 0)
        }
```

---

**✅ Redis 캐시 전략 완성!**  
**📝 이 전략으로 MIS v2의 성능을 크게 향상시킬 수 있습니다!** 