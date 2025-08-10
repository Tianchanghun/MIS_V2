#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
레거시 DB의 코드 체계 확인
"""

import pyodbc
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db, Code

app = create_app()

# 레거시 DB 설정
LEGACY_DB_CONFIG = {
    'server': '210.109.96.74,2521',
    'database': 'db_mis',
    'username': 'user_mis',
    'password': 'user_mis!@12'
}

def get_legacy_connection():
    """레거시 DB 연결"""
    connection_string = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={LEGACY_DB_CONFIG['server']};"
        f"DATABASE={LEGACY_DB_CONFIG['database']};"
        f"UID={LEGACY_DB_CONFIG['username']};"
        f"PWD={LEGACY_DB_CONFIG['password']};"
        f"ApplicationIntent=ReadOnly;"
    )
    
    try:
        connection = pyodbc.connect(connection_string, timeout=10)
        print(f"✅ 레거시 DB 연결 성공")
        return connection
    except Exception as e:
        print(f"❌ 레거시 DB 연결 실패: {e}")
        return None

def check_legacy_codes():
    """레거시 tbl_Code 테이블 확인"""
    legacy_conn = get_legacy_connection()
    if not legacy_conn:
        return
    
    try:
        cursor = legacy_conn.cursor()
        
        # 1. tbl_Code 테이블 구조 확인
        print(f"\n📋 tbl_Code 테이블 구조:")
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'tbl_Code' 
            ORDER BY ORDINAL_POSITION
        """)
        columns = cursor.fetchall()
        for col in columns:
            col_name, data_type, nullable, max_length = col
            length_info = f"({max_length})" if max_length else ""
            nullable_info = "NULL" if nullable == "YES" else "NOT NULL"
            print(f"  - {col_name}: {data_type}{length_info} {nullable_info}")
        
        # 2. 코드 그룹 확인
        print(f"\n📊 레거시 코드 그룹 확인 (Depth=0):")
        cursor.execute("SELECT * FROM tbl_Code WHERE Depth = 0 ORDER BY Sort, CodeName")
        groups = cursor.fetchall()
        
        print(f"총 {len(groups)}개 그룹:")
        for group in groups:
            print(f"  - Seq:{group[0]}, Code:{group[4]}, Name:{group[5]}")
        
        # 3. 특정 그룹의 하위 코드들 확인
        target_groups = ['BRAND', 'PRT', 'TP', 'YR']
        for group_code in target_groups:
            print(f"\n🔍 '{group_code}' 그룹의 하위 코드들:")
            
            # 먼저 그룹 찾기
            cursor.execute("SELECT Seq, CodeName FROM tbl_Code WHERE Code = ? AND Depth = 0", group_code)
            group = cursor.fetchone()
            
            if group:
                group_seq, group_name = group
                print(f"  📦 그룹: {group_name} (Seq: {group_seq})")
                
                # 하위 코드들 조회
                cursor.execute("SELECT Seq, Code, CodeName FROM tbl_Code WHERE ParentSeq = ? ORDER BY Sort", group_seq)
                child_codes = cursor.fetchall()
                
                print(f"  📋 하위 코드 {len(child_codes)}개:")
                for code in child_codes[:10]:  # 처음 10개만
                    seq, code_val, code_name = code
                    print(f"    - Seq:{seq}, Code:{code_val}, Name:{code_name}")
            else:
                print(f"  ❌ '{group_code}' 그룹을 찾을 수 없습니다.")
        
        # 4. tbl_Brand 테이블도 확인
        print(f"\n📊 tbl_Brand 테이블 확인:")
        try:
            cursor.execute("SELECT COUNT(*) FROM tbl_Brand")
            brand_count = cursor.fetchone()[0]
            print(f"총 {brand_count}개 브랜드")
            
            cursor.execute("SELECT TOP 10 Seq, BrandCode, BrandName FROM tbl_Brand ORDER BY Seq")
            brands = cursor.fetchall()
            for brand in brands:
                seq, code, name = brand
                print(f"  - Seq:{seq}, Code:{code}, Name:{name}")
                
        except Exception as e:
            print(f"❌ tbl_Brand 확인 실패: {e}")
            
    except Exception as e:
        print(f"❌ 코드 확인 실패: {e}")
    finally:
        legacy_conn.close()

def check_current_codes():
    """현재 PostgreSQL의 코드 체계 확인"""
    with app.app_context():
        print(f"\n📊 현재 PostgreSQL tbl_code 현황:")
        
        # Depth 0 그룹들
        groups = Code.query.filter_by(depth=0).order_by(Code.sort.asc()).all()
        print(f"총 {len(groups)}개 그룹:")
        for group in groups:
            print(f"  - Seq:{group.seq}, Code:{group.code}, Name:{group.code_name}")
            
            # 각 그룹의 하위 코드 개수
            child_count = Code.query.filter_by(parent_seq=group.seq).count()
            print(f"    📋 하위 코드: {child_count}개")

if __name__ == '__main__':
    print("🚀 레거시 & 현재 코드 체계 비교 분석")
    print("=" * 60)
    
    # 1. 레거시 코드 확인
    check_legacy_codes()
    
    # 2. 현재 코드 확인
    check_current_codes()
    
    print(f"\n🎉 코드 체계 분석 완료!") 