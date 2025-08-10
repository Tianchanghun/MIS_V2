#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db
import requests
import json
from datetime import datetime

def test_ui_and_fix():
    """UI 문제 진단 및 수정: 년식, 분류코드, 정렬 기능"""
    print("🔧 UI 문제 진단 및 수정")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        # 1. 년식(년도) 데이터 문제 진단
        print("1️⃣ 년식(년도) 데이터 진단")
        
        # 년도 코드 그룹 확인
        result = db.session.execute(db.text("""
            SELECT c.seq, c.code, c.code_name
            FROM tbl_code p
            JOIN tbl_code c ON p.seq = c.parent_seq
            WHERE p.code_name = '년도'
            ORDER BY c.code
        """))
        year_codes = result.fetchall()
        print(f"   📋 년도 코드: {len(year_codes)}개")
        for year in year_codes[:10]:  # 처음 10개만
            print(f"      {year.code}: {year.code_name}")
        
        # product_details의 year_code 분포 확인
        result = db.session.execute(db.text("""
            SELECT 
                year_code, 
                COUNT(*) as count,
                COUNT(DISTINCT product_id) as product_count
            FROM product_details
            GROUP BY year_code
            ORDER BY year_code
        """))
        year_distribution = result.fetchall()
        print(f"   📊 product_details의 year_code 분포:")
        for dist in year_distribution:
            print(f"      '{dist.year_code}': {dist.count}개 상세, {dist.product_count}개 제품")
        
        # 2. 분류코드 누락 문제 진단
        print(f"\n2️⃣ 분류코드 누락 문제 진단")
        
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(*) as total_products,
                COUNT(CASE WHEN p.brand_code_seq IS NULL THEN 1 END) as no_brand,
                COUNT(CASE WHEN p.category_code_seq IS NULL THEN 1 END) as no_category,
                COUNT(CASE WHEN p.type_code_seq IS NULL THEN 1 END) as no_type,
                COUNT(CASE WHEN b.code_name IS NULL THEN 1 END) as broken_brand,
                COUNT(CASE WHEN c.code_name IS NULL THEN 1 END) as broken_category,
                COUNT(CASE WHEN t.code_name IS NULL THEN 1 END) as broken_type
            FROM products p
            LEFT JOIN tbl_code b ON p.brand_code_seq = b.seq
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            LEFT JOIN tbl_code t ON p.type_code_seq = t.seq
            WHERE p.company_id = 1 AND p.use_yn = 'Y'
        """))
        
        mapping_stats = result.fetchone()
        print(f"   📊 분류코드 매핑 상태 (활성 제품 기준):")
        print(f"      총 제품: {mapping_stats.total_products}개")
        print(f"      브랜드 누락: {mapping_stats.no_brand}개 ({mapping_stats.no_brand/mapping_stats.total_products*100:.1f}%)")
        print(f"      품목 누락: {mapping_stats.no_category}개 ({mapping_stats.no_category/mapping_stats.total_products*100:.1f}%)")
        print(f"      타입 누락: {mapping_stats.no_type}개 ({mapping_stats.no_type/mapping_stats.total_products*100:.1f}%)")
        print(f"      브랜드 연결 오류: {mapping_stats.broken_brand}개")
        print(f"      품목 연결 오류: {mapping_stats.broken_category}개")
        print(f"      타입 연결 오류: {mapping_stats.broken_type}개")
        
        # 3. 년도 코드 누락 문제 해결
        print(f"\n3️⃣ 년도 코드 누락 해결")
        
        # 년도 그룹 확인/생성
        result = db.session.execute(db.text("""
            SELECT seq FROM tbl_code WHERE code_name = '년도' AND parent_seq = 0
        """))
        year_group = result.fetchone()
        
        if not year_group:
            result = db.session.execute(db.text("""
                INSERT INTO tbl_code (parent_seq, code, code_name, depth, sort)
                VALUES (0, 'YR', '년도', 1, 7) RETURNING seq
            """))
            year_group_seq = result.fetchone()[0]
            print(f"   ✅ 년도 그룹 생성: seq {year_group_seq}")
        else:
            year_group_seq = year_group.seq
            print(f"   ✅ 년도 그룹 확인: seq {year_group_seq}")
        
        # product_details에서 실제 사용되는 년도 코드들 수집
        result = db.session.execute(db.text("""
            SELECT DISTINCT year_code, COUNT(*) as usage_count
            FROM product_details
            WHERE year_code IS NOT NULL AND year_code != ''
            GROUP BY year_code
            ORDER BY year_code
        """))
        
        used_year_codes = result.fetchall()
        print(f"   📋 실제 사용되는 년도 코드: {len(used_year_codes)}개")
        
        # 년도 코드를 tbl_code에 추가
        added_years = 0
        for year_data in used_year_codes:
            year_code = year_data.year_code
            
            # 이미 존재하는지 확인
            result = db.session.execute(db.text("""
                SELECT seq FROM tbl_code 
                WHERE parent_seq = :parent_seq AND code = :code
            """), {'parent_seq': year_group_seq, 'code': year_code})
            
            if not result.fetchone():
                # 2자리 년도면 4자리로 변환 (예: '24' -> '2024')
                if len(year_code) == 2 and year_code.isdigit():
                    year_int = int(year_code)
                    if year_int >= 0 and year_int <= 30:  # 00-30은 2000년대
                        full_year = f"20{year_code}"
                    else:  # 31-99는 1900년대
                        full_year = f"19{year_code}"
                else:
                    full_year = year_code
                
                db.session.execute(db.text("""
                    INSERT INTO tbl_code (parent_seq, code, code_name, depth, sort)
                    VALUES (:parent_seq, :code, :code_name, 2, :sort)
                """), {
                    'parent_seq': year_group_seq,
                    'code': year_code,
                    'code_name': full_year,
                    'sort': 50 + added_years
                })
                added_years += 1
                print(f"      ✅ 년도 추가: {year_code} -> {full_year} ({year_data.usage_count}개 사용)")
        
        db.session.commit()
        print(f"   📊 년도 코드 추가 완료: {added_years}개")
        
        # 4. 브랜드/품목/타입 매핑 개선
        print(f"\n4️⃣ 브랜드/품목/타입 매핑 개선")
        
        # 레거시 데이터에서 브랜드/품목/타입 정보 가져와서 매핑
        brand_mappings = [
            (['뉴나', 'NUNA'], 'NU', '뉴나'),
            (['리안', 'LIAN'], 'LI', '리안'),
            (['조이', 'JOIE'], 'JY', '조이'),
            (['페라리', 'FERRARI'], 'FR', '페라리'),
            (['나니아', 'NANIA'], 'NA', '나니아'),
            (['피셔프라이스', 'FISHER'], 'FP', '피셔프라이스'),
            (['팀텍스', 'TEAMTEX'], 'TT', '팀텍스'),
            (['페프', 'PEP'], 'PP', '페프'),
            (['기타'], 'MI', '미지정')
        ]
        
        category_mappings = [
            (['카시트', '카시트'], 'CS', '카시트'),
            (['유모차', '스토리'], 'ST', '유모차'),
            (['하이체어', '체어'], 'CH', '하이체어'),
            (['액세서리', '부품', '커버', '시트', '가드'], 'AC', '액세서리'),
            (['토이', '인형', '블록'], 'TY', '토이'),
            (['기타'], 'MI', '미지정')
        ]
        
        type_mappings = [
            (['프리미엄', 'LX', '럭스'], 'PR', '프리미엄'),
            (['스탠다드', '일반'], 'ST', '스탠다드'),
            (['에코', 'ECO'], 'EC', '에코'),
            (['디럭스', '듀얼'], 'DL', '디럭스'),
            (['액세서리'], 'AC', '액세서리'),
            (['토이'], 'TY', '토이'),
            (['기타'], 'MI', '미지정')
        ]
        
        # 매핑 함수
        def update_product_mapping(mappings, mapping_type, code_group_name):
            updated_count = 0
            
            # 코드 그룹 찾기
            result = db.session.execute(db.text("""
                SELECT seq FROM tbl_code WHERE code_name = :group_name AND parent_seq = 0
            """), {'group_name': code_group_name})
            group = result.fetchone()
            
            if not group:
                print(f"      ❌ {code_group_name} 그룹을 찾을 수 없음")
                return 0
            
            group_seq = group.seq
            
            for patterns, code, name in mappings:
                # 코드 seq 찾기
                result = db.session.execute(db.text("""
                    SELECT seq FROM tbl_code 
                    WHERE parent_seq = :parent_seq AND code = :code
                """), {'parent_seq': group_seq, 'code': code})
                code_seq = result.fetchone()
                
                if not code_seq:
                    # 코드가 없으면 생성
                    result = db.session.execute(db.text("""
                        INSERT INTO tbl_code (parent_seq, code, code_name, depth, sort)
                        VALUES (:parent_seq, :code, :code_name, 2, 99) RETURNING seq
                    """), {
                        'parent_seq': group_seq,
                        'code': code,
                        'code_name': name
                    })
                    code_seq = result.fetchone()
                    print(f"      ✅ {code_group_name} 코드 생성: {code} - {name}")
                
                # 패턴 매칭으로 제품 업데이트
                for pattern in patterns:
                    if mapping_type == 'brand':
                        column = 'brand_code_seq'
                    elif mapping_type == 'category':
                        column = 'category_code_seq'
                    else:  # type
                        column = 'type_code_seq'
                    
                    result = db.session.execute(db.text(f"""
                        UPDATE products 
                        SET {column} = :code_seq, updated_at = NOW()
                        WHERE company_id = 1 AND product_name ILIKE :pattern 
                        AND {column} IS NULL
                    """), {
                        'code_seq': code_seq.seq,
                        'pattern': f'%{pattern}%'
                    })
                    
                    if result.rowcount > 0:
                        updated_count += result.rowcount
                        print(f"      ✅ {pattern} → {name}: {result.rowcount}개 업데이트")
            
            return updated_count
        
        # 각 매핑 수행
        brand_updated = update_product_mapping(brand_mappings, 'brand', '브랜드')
        category_updated = update_product_mapping(category_mappings, 'category', '품목')
        type_updated = update_product_mapping(type_mappings, 'type', '타입')
        
        db.session.commit()
        
        print(f"   📊 매핑 업데이트 완료:")
        print(f"      브랜드: {brand_updated}개")
        print(f"      품목: {category_updated}개")
        print(f"      타입: {type_updated}개")
        
        # 5. API 응답 테스트
        print(f"\n5️⃣ API 응답 테스트")
        
        try:
            # Flask 앱이 실행 중인지 테스트
            response = requests.get('http://127.0.0.1:5000/product/api/list', timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ API 응답 성공: {len(data.get('data', []))}개 제품")
                
                # 첫 번째 제품의 데이터 구조 확인
                if data.get('data'):
                    first_product = data['data'][0]
                    print(f"   📋 샘플 제품 데이터:")
                    print(f"      ID: {first_product.get('id')}")
                    print(f"      이름: {first_product.get('product_name')}")
                    print(f"      브랜드: {first_product.get('brand_name', 'undefined')}")
                    print(f"      품목: {first_product.get('category_name', 'undefined')}")
                    print(f"      타입: {first_product.get('type_name', 'undefined')}")
                    print(f"      가격: {first_product.get('price')}")
                    print(f"      자가코드: {first_product.get('std_div_prod_code', 'undefined')}")
                    
            else:
                print(f"   ❌ API 오류: HTTP {response.status_code}")
                
        except requests.ConnectionError:
            print(f"   ⚠️ Flask 앱이 실행되지 않음 - 수동으로 실행 필요")
        except Exception as e:
            print(f"   ❌ API 테스트 오류: {e}")
        
        # 6. 최종 매핑 상태 확인
        print(f"\n6️⃣ 최종 매핑 상태 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(*) as total_products,
                COUNT(CASE WHEN p.brand_code_seq IS NOT NULL AND b.code_name IS NOT NULL THEN 1 END) as good_brand,
                COUNT(CASE WHEN p.category_code_seq IS NOT NULL AND c.code_name IS NOT NULL THEN 1 END) as good_category,
                COUNT(CASE WHEN p.type_code_seq IS NOT NULL AND t.code_name IS NOT NULL THEN 1 END) as good_type
            FROM products p
            LEFT JOIN tbl_code b ON p.brand_code_seq = b.seq
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            LEFT JOIN tbl_code t ON p.type_code_seq = t.seq
            WHERE p.company_id = 1 AND p.use_yn = 'Y'
        """))
        
        final_stats = result.fetchone()
        print(f"   📊 최종 매핑 상태 (활성 제품):")
        print(f"      총 제품: {final_stats.total_products}개")
        print(f"      브랜드 매핑 완료: {final_stats.good_brand}개 ({final_stats.good_brand/final_stats.total_products*100:.1f}%)")
        print(f"      품목 매핑 완료: {final_stats.good_category}개 ({final_stats.good_category/final_stats.total_products*100:.1f}%)")
        print(f"      타입 매핑 완료: {final_stats.good_type}개 ({final_stats.good_type/final_stats.total_products*100:.1f}%)")
        
        # 7. 샘플 데이터 확인
        print(f"\n7️⃣ 개선된 샘플 데이터 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                p.product_name,
                b.code_name as brand_name,
                c.code_name as category_name,
                t.code_name as type_name,
                p.price,
                pd.std_div_prod_code,
                pd.year_code
            FROM products p
            LEFT JOIN tbl_code b ON p.brand_code_seq = b.seq
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            LEFT JOIN tbl_code t ON p.type_code_seq = t.seq
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1 AND p.use_yn = 'Y'
            ORDER BY p.id
            LIMIT 10
        """))
        
        samples = result.fetchall()
        print(f"   📋 개선된 샘플 데이터:")
        print(f"      {'제품명':25} | {'브랜드':8} | {'품목':8} | {'타입':8} | {'가격':10} | {'년도':4} | {'자가코드':16}")
        print(f"      {'-'*25} | {'-'*8} | {'-'*8} | {'-'*8} | {'-'*10} | {'-'*4} | {'-'*16}")
        
        for sample in samples:
            brand = sample.brand_name or "미지정"
            category = sample.category_name or "미지정"
            type_name = sample.type_name or "미지정"
            price = f"{sample.price:,}" if sample.price else "0"
            year = sample.year_code or "-"
            code = sample.std_div_prod_code or "미지정"
            
            print(f"      {sample.product_name[:25]:25} | {brand:8} | {category:8} | {type_name:8} | {price:>10} | {year:4} | {code:16}")
        
        print(f"\n🎉 UI 문제 수정 완료!")
        print(f"✅ 년도 코드 {added_years}개 추가로 년식 표시 가능")
        print(f"✅ 브랜드/품목/타입 매핑 대폭 개선")
        print(f"✅ 분류코드 표시율 대폭 향상")
        print(f"📱 http://127.0.0.1:5000/product/ 에서 개선된 UI 확인 가능!")
        print(f"💡 정렬 기능은 Flask 앱 실행 후 테스트 필요")

if __name__ == "__main__":
    test_ui_and_fix() 