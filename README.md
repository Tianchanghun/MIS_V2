# 🚀 MIS v2 - PostgreSQL + Flask

> 레거시 ASP.NET MVC에서 PostgreSQL + Flask로 안전하게 전환

## 📋 **프로젝트 개요**

### **목표**
- ✅ **레거시 보호**: MS-SQL DB에 손상 없이 복제
- ✅ **안전한 테스트**: Docker 환경에서 격리된 개발
- ✅ **점진적 전환**: Phase별 단계적 구현

### **기술 스택**
- **Backend**: Python Flask 3.0
- **Database**: PostgreSQL 15
- **Frontend**: HTML5 + Bootstrap + jQuery
- **환경**: Docker + Docker Compose

## 🔧 **환경 구축**

### **1. Docker 환경 시작**
```bash
# Docker 컨테이너 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

### **2. 접속 정보**
- **PostgreSQL**: `localhost:5433`
- **pgAdmin**: `http://localhost:5051`
  - ID: `admin@mis.co.kr`
  - PW: `admin123!@#`
- **Flask App**: `http://localhost:5000`

### **3. 의존성 설치**
```bash
# Python 패키지 설치
pip install -r requirements.txt
```

## 📊 **데이터베이스 마이그레이션**

### **⚠️ 안전한 복제 과정**

#### **1단계: 스키마 생성**
```bash
# PostgreSQL 스키마 자동 생성
docker-compose up postgres
```
> `sql_scripts/01_create_schema.sql`이 자동 실행됩니다.

#### **2단계: 데이터 복제 (READ ONLY)**
```bash
# 레거시 DB에서 안전하게 복제 (재개 가능)
python db_migration_resumable.py

# 강제 재시작
python db_migration_resumable.py --restart
```

**📌 복제 특징:**
- ✅ **READ ONLY 모드**: 원본 DB 절대 손상 없음
- ✅ **재개 가능**: 중단된 지점부터 자동 재시작
- ✅ **배치 처리**: 500건씩 안전한 처리
- ✅ **스키마 자동 변환**: MS-SQL → PostgreSQL
- ✅ **데이터 검증**: 마이그레이션 후 자동 검증

#### **3단계: 복제 확인**
```bash
# pgAdmin에서 확인
http://localhost:5051

# 또는 직접 연결
psql -h localhost -p 5433 -U mis_user -d db_mis
```

## 🎯 **구현 우선순위**

### **Phase 1: 핵심 시스템 (필수)**
1. **시스템 관리** - 메뉴, 사용자, 권한
2. **제품 관리** - 제품 정보, 분류
3. **주문 관리** - SKU, 주문 처리
4. **무역 관리** - 발주, 시리얼 생성

### **Phase 2: 비즈니스 로직 (중요)**
5. **총판 관리** - 시리얼 검색, 초기화
6. **판매 리포트** - 매출 통계
7. **A/S 관리** - 고객 지원
8. **고객 관리** - 고객 정보

### **Phase 3: 운영 도구 (부가)**
9. **매장 관리** - 거래처 관리
10. **배치 관리** - 자동화 작업
11. **카탈로그 관리** - 마케팅 자료

## 🔍 **시리얼 번호 시스템**

### **구조 분석 완료 ✅**
```
브랜드(2) + 모델(2) + 주문회차(3) + 년도(1) + 색상(3) + 타입(4) + 랜덤(2) + 일련번호(4)
```

### **생성 방식**
1. **표준 시리얼**: 규칙 기반 자동 생성
2. **텍스트 조합**: 날짜+텍스트+번호
3. **엑셀 업로드**: 대량 생성

## 📁 **프로젝트 구조**

```
C:\mis_v2\
├── docker-compose.yml          # Docker 환경 설정
├── requirements.txt            # Python 의존성
├── db_migration_resumable.py   # 재개 가능한 DB 마이그레이션 도구
├── sql_scripts/               # PostgreSQL 초기화 스크립트
│   └── 01_create_schema.sql
├── docs/                      # 프로젝트 문서
├── app/                       # Flask 애플리케이션 (예정)
│   ├── __init__.py
│   ├── models/               # SQLAlchemy 모델
│   ├── views/                # 라우트 처리
│   ├── templates/            # HTML 템플릿
│   └── static/               # CSS, JS, 이미지
└── mis.aone.co.kr/           # 레거시 ASP.NET MVC (참조용, Git 제외)
```

## 🚨 **중요 사항**

### **데이터 안전성**
- ✅ **레거시 DB는 READ ONLY로만 접근**
- ✅ **원본 데이터 절대 수정 금지**
- ✅ **테스트는 복제본에서만 진행**

### **개발 원칙**
- ✅ **점진적 구현**: Phase별 단계적 접근
- ✅ **테스트 우선**: 로컬에서 충분한 검증 후 배포
- ✅ **문서화**: 모든 변경사항 기록

## 🎯 **다음 단계**

1. **환경 구축**: `docker-compose up -d`
2. **마이그레이션**: `python db_migration_resumable.py`
3. **Flask 앱 개발**: Phase 1부터 시작
4. **테스트**: 로컬 환경에서 검증
5. **배포**: 검증 완료 후 실서버 이전

---

**📞 문의사항이나 문제 발생시 언제든 연락주세요!** 🚀
