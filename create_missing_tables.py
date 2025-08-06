#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
누락된 데이터베이스 테이블 생성 스크립트
"""

import sys
import os

# Flask 앱 컨텍스트 필요
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

def create_missing_tables():
    """누락된 테이블들 생성"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔧 누락된 테이블을 생성합니다...")
            
            # 1. tbl_department 테이블 생성
            create_department_table()
            
            # 2. tbl_menu 테이블 생성
            create_menu_table()
            
            # 3. tbl_dept_auth 테이블 생성
            create_dept_auth_table()
            
            # 4. 추가 테이블들 생성
            create_additional_tables()
            
            print("✅ 모든 테이블이 성공적으로 생성되었습니다!")
            
        except Exception as e:
            print(f"❌ 오류 발생: {e}")

def create_department_table():
    """부서 테이블 생성"""
    sql = """
    CREATE TABLE IF NOT EXISTS tbl_department (
        seq SERIAL PRIMARY KEY,
        dept_name VARCHAR(100) NOT NULL,
        dept_code VARCHAR(20),
        use_yn CHAR(1) DEFAULT 'Y',
        report_yn CHAR(1) DEFAULT 'Y',
        sort INTEGER DEFAULT 0,
        company_id INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    db.session.execute(sql)
    db.session.commit()
    print("   ✅ tbl_department 테이블 생성 완료")

def create_menu_table():
    """메뉴 테이블 생성"""
    sql = """
    CREATE TABLE IF NOT EXISTS tbl_menu (
        seq SERIAL PRIMARY KEY,
        menu_name VARCHAR(100) NOT NULL,
        menu_url VARCHAR(200),
        parent_seq INTEGER REFERENCES tbl_menu(seq),
        depth INTEGER DEFAULT 1,
        sort INTEGER DEFAULT 0,
        use_yn CHAR(1) DEFAULT 'Y',
        icon VARCHAR(50),
        company_id INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    db.session.execute(sql)
    db.session.commit()
    print("   ✅ tbl_menu 테이블 생성 완료")

def create_dept_auth_table():
    """부서 권한 테이블 생성"""
    sql = """
    CREATE TABLE IF NOT EXISTS tbl_dept_auth (
        seq SERIAL PRIMARY KEY,
        dept_seq INTEGER REFERENCES tbl_department(seq),
        menu_seq INTEGER REFERENCES tbl_menu(seq),
        auth_c CHAR(1) DEFAULT 'N',
        auth_r CHAR(1) DEFAULT 'N',
        auth_u CHAR(1) DEFAULT 'N',
        auth_d CHAR(1) DEFAULT 'N',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(dept_seq, menu_seq)
    );
    """
    
    db.session.execute(sql)
    db.session.commit()
    print("   ✅ tbl_dept_auth 테이블 생성 완료")

def create_additional_tables():
    """추가 필요 테이블들 생성"""
    
    # 배치 로그 테이블
    sql_batch_log = """
    CREATE TABLE IF NOT EXISTS tbl_batchlog (
        seq SERIAL PRIMARY KEY,
        batch_name VARCHAR(100),
        batch_type VARCHAR(50),
        status VARCHAR(20),
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMP,
        message TEXT,
        processed_count INTEGER DEFAULT 0,
        error_count INTEGER DEFAULT 0,
        company_id INTEGER DEFAULT 1
    );
    """
    
    # 배치 스케줄 테이블
    sql_batch_schedule = """
    CREATE TABLE IF NOT EXISTS tbl_batch_schedule (
        seq SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        schedule_type VARCHAR(20) DEFAULT 'daily',
        cron_expression VARCHAR(100),
        enabled BOOLEAN DEFAULT TRUE,
        last_run TIMESTAMP,
        next_run TIMESTAMP,
        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        company_id INTEGER DEFAULT 1
    );
    """
    
    # 사은품 키워드 테이블
    sql_gift_keyword = """
    CREATE TABLE IF NOT EXISTS tbl_gift_keyword (
        seq SERIAL PRIMARY KEY,
        keyword VARCHAR(100) NOT NULL,
        keyword_type VARCHAR(20) DEFAULT 'include',
        priority INTEGER DEFAULT 1,
        enabled BOOLEAN DEFAULT TRUE,
        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        company_id INTEGER DEFAULT 1
    );
    """
    
    # 사은품 분류 로그 테이블
    sql_gift_classify_log = """
    CREATE TABLE IF NOT EXISTS tbl_gift_classify_log (
        seq SERIAL PRIMARY KEY,
        order_seq INTEGER REFERENCES tbl_sales_orderinfo(seq),
        classify_type VARCHAR(20),
        classify_reason VARCHAR(200),
        before_is_gift BOOLEAN,
        after_is_gift BOOLEAN,
        classified_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        classified_by VARCHAR(50),
        company_id INTEGER DEFAULT 1
    );
    """
    
    # ERPia 고객 테이블
    sql_erpia_customer = """
    CREATE TABLE IF NOT EXISTS tbl_erpia_customer (
        seq SERIAL PRIMARY KEY,
        g_code VARCHAR(50) UNIQUE,
        g_name VARCHAR(200),
        g_tel VARCHAR(50),
        g_email VARCHAR(100),
        g_addr VARCHAR(500),
        g_manager VARCHAR(100),
        region VARCHAR(100),
        channel VARCHAR(50),
        use_yn CHAR(1) DEFAULT 'Y',
        sync_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        company_id INTEGER DEFAULT 1
    );
    """
    
    tables = [
        (sql_batch_log, "tbl_batchlog"),
        (sql_batch_schedule, "tbl_batch_schedule"),
        (sql_gift_keyword, "tbl_gift_keyword"),
        (sql_gift_classify_log, "tbl_gift_classify_log"),
        (sql_erpia_customer, "tbl_erpia_customer")
    ]
    
    for sql, table_name in tables:
        try:
            db.session.execute(sql)
            db.session.commit()
            print(f"   ✅ {table_name} 테이블 생성 완료")
        except Exception as e:
            print(f"   ⚠️ {table_name} 테이블: {e}")
            db.session.rollback()

if __name__ == '__main__':
    create_missing_tables() 