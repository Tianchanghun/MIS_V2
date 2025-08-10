#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
현재 상품 데이터의 매핑 상태 확인
"""

import psycopg2

# PostgreSQL 설정
PG_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'mis_v2',
    'user': 'postgres',
    'password': 'password'
}

def check_product_mapping():
    """상품 매핑 상태 확인"""
    try:
        # PostgreSQL 연결
        conn = psycopg2.connect(**PG_CONFIG)
        cursor = conn.cursor()
        
        print("현재 상품 데이터 매핑 상태 확인")
        print("=" * 50)
        
        # 1. 전체 상품 개수
        cursor.execute("SELECT COUNT(*) FROM products WHERE company_id = 1")
        total_count = cursor.fetchone()[0]
        print(f"총 상품 개수: {total_count}개")
        
        # 2. 매핑 상태별 개수
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(brand_code_seq) as brand_mapped,
                COUNT(category_code_seq) as category_mapped,
                COUNT(type_code_seq) as type_mapped,
                COUNT(year_code_seq) as year_mapped
            FROM products 
            WHERE company_id = 1
        """)
        result = cursor.fetchone()
        total, brand_mapped, category_mapped, type_mapped, year_mapped = result
        
        print(f"\n매핑 상태:")
        print(f"  - 브랜드 매핑: {brand_mapped}/{total} ({brand_mapped/total*100:.1f}%)")
        print(f"  - 품목 매핑: {category_mapped}/{total} ({category_mapped/total*100:.1f}%)")
        print(f"  - 타입 매핑: {type_mapped}/{total} ({type_mapped/total*100:.1f}%)")
        print(f"  - 년도 매핑: {year_mapped}/{total} ({year_mapped/total*100:.1f}%)")
        
        # 3. 샘플 데이터 확인
        cursor.execute("""
            SELECT 
                p.id, p.product_name, p.legacy_seq,
                p.brand_code_seq, b.code_name as brand_name,
                p.category_code_seq, c.code_name as category_name,
                p.type_code_seq, t.code_name as type_name,
                p.year_code_seq, y.code_name as year_name
            FROM products p
            LEFT JOIN tbl_code b ON p.brand_code_seq = b.seq
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            LEFT JOIN tbl_code t ON p.type_code_seq = t.seq
            LEFT JOIN tbl_code y ON p.year_code_seq = y.seq
            WHERE p.company_id = 1
            ORDER BY p.id
            LIMIT 10
        """)
        
        samples = cursor.fetchall()
        print(f"\n샘플 데이터 (처음 10개):")
        for sample in samples:
            pid, pname, legacy_seq, brand_seq, brand_name, cat_seq, cat_name, type_seq, type_name, year_seq, year_name = sample
            print(f"  ID:{pid} {pname[:20]}...")
            print(f"    Legacy:{legacy_seq}")
            print(f"    브랜드: {brand_seq} -> {brand_name}")
            print(f"    품목: {cat_seq} -> {cat_name}")
            print(f"    타입: {type_seq} -> {type_name}")
            print(f"    년도: {year_seq} -> {year_name}")
            print()
        
        # 4. 코드 그룹별 사용 가능한 코드들 확인
        print("코드 그룹별 사용 가능한 코드:")
        
        code_groups = [
            ('브랜드', '브랜드'),
            ('제품구분', '품목'),
            ('타입', '타입'),
            ('년도', '년도')
        ]
        
        for group_name, display_name in code_groups:
            cursor.execute("""
                SELECT c.seq, c.code, c.code_name
                FROM tbl_code c
                WHERE c.parent_seq = (SELECT seq FROM tbl_code WHERE code_name = %s AND depth = 0)
                ORDER BY c.sort
                LIMIT 5
            """, (group_name,))
            codes = cursor.fetchall()
            
            print(f"  {display_name}: {len(codes)}개 사용 가능")
            for code in codes:
                seq, code_val, code_name = code
                print(f"    - Seq:{seq}, Code:{code_val}, Name:{code_name}")
        
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] 확인 실패: {e}")

if __name__ == '__main__':
    check_product_mapping() 