#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def fix_ui_display_comprehensive():
    """UI 정보 표시 문제 종합 해결"""
    print("🔧 UI 정보 표시 문제 종합 해결")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        # 1. 검색 기능 500 오류 먼저 해결 (가장 중요)
        print("1️⃣ 검색 기능 500 오류 해결")
        print("   ❌ 현재 ilike_op 함수 오류 발생 중")
        print("   ✅ routes.py 수정 필요 - 검색 쿼리 구문 교체")
        
        # 2. 제품-코드 매핑 문제 진단
        print(f"\n2️⃣ 제품-코드 매핑 문제 진단")
        
        # 샘플 제품들의 매핑 상태 확인
        result = db.session.execute(db.text("""
            SELECT 
                p.id,
                p.product_name,
                p.brand_code_seq,
                p.category_code_seq,
                p.type_code_seq,
                b.code_name as current_brand,
                c.code_name as current_category,
                t.code_name as current_type,
                pd.std_div_prod_code
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
        print(f"   📋 샘플 제품 매핑 상태:")
        print(f"      {'제품명':25} | {'브랜드':10} | {'품목':10} | {'타입':10} | {'자가코드':16}")
        print(f"      {'-'*25} | {'-'*10} | {'-'*10} | {'-'*10} | {'-'*16}")
        
        missing_brand = 0
        missing_category = 0
        missing_type = 0
        missing_code = 0
        
        for sample in samples:
            brand = sample.current_brand or "❌없음"
            category = sample.current_category or "❌없음"
            type_name = sample.current_type or "❌없음"
            code = sample.std_div_prod_code or "❌없음"
            
            if not sample.current_brand:
                missing_brand += 1
            if not sample.current_category:
                missing_category += 1
            if not sample.current_type:
                missing_type += 1
            if not sample.std_div_prod_code:
                missing_code += 1
                
            print(f"      {sample.product_name[:25]:25} | {brand[:10]:10} | {category[:10]:10} | {type_name[:10]:10} | {code[:16]:16}")
        
        print(f"\n   📊 문제 통계 (샘플 10개 기준):")
        print(f"      브랜드 누락: {missing_brand}개")
        print(f"      품목 누락: {missing_category}개") 
        print(f"      타입 누락: {missing_type}개")
        print(f"      자가코드 누락: {missing_code}개")
        
        # 3. 브랜드 매핑 수정 (가장 중요)
        print(f"\n3️⃣ 브랜드 매핑 수정")
        
        # 실제 제품명에서 브랜드 추출해서 매핑
        brand_patterns = [
            ('조이', 'JI', 'JOIE'),
            ('JOIE', 'JI', 'JOIE'),
            ('스핀', 'JI', 'JOIE'),  # 스핀은 JOIE 제품
            ('아이앵커', 'JI', 'JOIE'),  # 아이앵커도 JOIE
            ('아이스테이지', 'JI', 'JOIE'),  # 아이스테이지도 JOIE
            ('뉴나', 'NU', 'NUNA'),
            ('NUNA', 'NU', 'NUNA'),
            ('리안', 'LI', 'LIAN'),
            ('LIAN', 'LI', 'LIAN'),
            ('라이언', 'RY', 'RYAN'),
            ('RYAN', 'RY', 'RYAN'),
            ('프로그', 'RY', 'RYAN'),  # 프로그는 RYAN 제품
            ('듀얼', 'RY', 'RYAN'),   # 듀얼도 RYAN
            ('트릴로', 'RY', 'RYAN'), # 트릴로도 RYAN
            ('나니아', 'NA', 'NANIA'),
            ('NANIA', 'NA', 'NANIA'),
            ('페라리', 'FR', 'FERRARI'),
            ('FERRARI', 'FR', 'FERRARI'),
            ('팀텍스', 'TT', 'TEAMTEX'),
            ('TEAMTEX', 'TT', 'TEAMTEX')
        ]
        
        brand_updated = 0
        for pattern, code, name in brand_patterns:
            # 해당 코드의 seq 찾기
            result = db.session.execute(db.text("""
                SELECT c.seq
                FROM tbl_code p
                JOIN tbl_code c ON p.seq = c.parent_seq
                WHERE p.code_name = '브랜드' AND c.code = :brand_code
            """), {'brand_code': code})
            
            brand_seq = result.fetchone()
            if not brand_seq:
                continue
                
            # 제품명에 패턴이 포함된 제품들 업데이트
            result = db.session.execute(db.text("""
                UPDATE products 
                SET brand_code_seq = :brand_seq, updated_at = NOW()
                WHERE company_id = 1 AND product_name ILIKE :pattern 
                AND (brand_code_seq IS NULL OR brand_code_seq != :brand_seq)
            """), {
                'brand_seq': brand_seq.seq,
                'pattern': f'%{pattern}%'
            })
            
            if result.rowcount > 0:
                brand_updated += result.rowcount
                print(f"      ✅ '{pattern}' → {name}: {result.rowcount}개 업데이트")
        
        # 4. 품목(카테고리) 매핑 수정
        print(f"\n4️⃣ 품목 매핑 수정")
        
        category_patterns = [
            ('카시트', 'CS', '카시트'),
            ('스핀', 'CS', '카시트'),     # 스핀은 카시트
            ('아이앵커', 'CS', '카시트'),   # 아이앵커는 카시트
            ('아이스테이지', 'CS', '카시트'), # 아이스테이지는 카시트
            ('듀얼', 'CS', '카시트'),     # 듀얼은 카시트
            ('유모차', 'ST', '유모차'),
            ('스토리', 'ST', '유모차'),
            ('프로그', 'ST', '유모차'),   # 프로그는 유모차
            ('하이체어', 'CH', '하이체어'),
            ('체어', 'CH', '하이체어'),
            ('트릴로', 'ST', '유모차'),   # 트릴로는 유모차
            ('커버', 'AC', '액세서리'),
            ('시트', 'AC', '액세서리'),
            ('가드', 'AC', '액세서리'),
            ('토이', 'TY', '토이'),
            ('인형', 'TY', '토이')
        ]
        
        category_updated = 0
        for pattern, code, name in category_patterns:
            # 해당 코드의 seq 찾기
            result = db.session.execute(db.text("""
                SELECT c.seq
                FROM tbl_code p
                JOIN tbl_code c ON p.seq = c.parent_seq
                WHERE p.code_name = '품목' AND c.code = :category_code
            """), {'category_code': code})
            
            category_seq = result.fetchone()
            if not category_seq:
                continue
                
            # 제품명에 패턴이 포함된 제품들 업데이트
            result = db.session.execute(db.text("""
                UPDATE products 
                SET category_code_seq = :category_seq, updated_at = NOW()
                WHERE company_id = 1 AND product_name ILIKE :pattern 
                AND (category_code_seq IS NULL OR category_code_seq != :category_seq)
            """), {
                'category_seq': category_seq.seq,
                'pattern': f'%{pattern}%'
            })
            
            if result.rowcount > 0:
                category_updated += result.rowcount
                print(f"      ✅ '{pattern}' → {name}: {result.rowcount}개 업데이트")
        
        # 5. 타입 매핑 수정
        print(f"\n5️⃣ 타입 매핑 수정")
        
        type_patterns = [
            ('360', 'CV', '컨버터블'),    # 스핀 360은 컨버터블
            ('클래식', 'CL', '클래식'),
            ('스테이지', 'ST', '스테이지'),
            ('프리미엄', 'PR', '프리미엄'),
            ('에코', 'EC', '에코'),
            ('듀얼', 'DL', '듀얼'),
            ('스탠다드', 'ST', '스탠다드'),
            ('일반', 'ST', '스탠다드'),
            ('베이직', 'BK', '베이직'),
            ('디럭스', 'DL', '디럭스'),
            ('액세서리', 'AC', '액세서리'),
            ('토이', 'TY', '토이')
        ]
        
        type_updated = 0
        for pattern, code, name in type_patterns:
            # 해당 코드의 seq 찾기
            result = db.session.execute(db.text("""
                SELECT c.seq
                FROM tbl_code p
                JOIN tbl_code c ON p.seq = c.parent_seq
                WHERE p.code_name = '타입' AND c.code = :type_code
            """), {'type_code': code})
            
            type_seq = result.fetchone()
            if not type_seq:
                # 타입이 없으면 생성
                result = db.session.execute(db.text("""
                    SELECT seq FROM tbl_code WHERE code_name = '타입' AND parent_seq = 0
                """))
                type_group = result.fetchone()
                
                if type_group:
                    db.session.execute(db.text("""
                        INSERT INTO tbl_code (parent_seq, code, code_name, depth, sort)
                        VALUES (:parent_seq, :code, :code_name, 2, 99) RETURNING seq
                    """), {
                        'parent_seq': type_group.seq,
                        'code': code,
                        'code_name': name
                    })
                    
                    result = db.session.execute(db.text("""
                        SELECT c.seq
                        FROM tbl_code p
                        JOIN tbl_code c ON p.seq = c.parent_seq
                        WHERE p.code_name = '타입' AND c.code = :type_code
                    """), {'type_code': code})
                    type_seq = result.fetchone()
                    print(f"      ✅ 타입 코드 생성: {code} - {name}")
            
            if type_seq:
                # 제품명에 패턴이 포함된 제품들 업데이트
                result = db.session.execute(db.text("""
                    UPDATE products 
                    SET type_code_seq = :type_seq, updated_at = NOW()
                    WHERE company_id = 1 AND product_name ILIKE :pattern 
                    AND (type_code_seq IS NULL OR type_code_seq != :type_seq)
                """), {
                    'type_seq': type_seq.seq,
                    'pattern': f'%{pattern}%'
                })
                
                if result.rowcount > 0:
                    type_updated += result.rowcount
                    print(f"      ✅ '{pattern}' → {name}: {result.rowcount}개 업데이트")
        
        db.session.commit()
        
        # 6. 수정 후 상태 확인
        print(f"\n6️⃣ 수정 후 상태 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(*) as total_products,
                COUNT(CASE WHEN p.brand_code_seq IS NOT NULL AND b.code_name IS NOT NULL THEN 1 END) as good_brand,
                COUNT(CASE WHEN p.category_code_seq IS NOT NULL AND c.code_name IS NOT NULL THEN 1 END) as good_category,
                COUNT(CASE WHEN p.type_code_seq IS NOT NULL AND t.code_name IS NOT NULL THEN 1 END) as good_type,
                COUNT(CASE WHEN pd.std_div_prod_code IS NOT NULL AND LENGTH(pd.std_div_prod_code) = 16 THEN 1 END) as good_code
            FROM products p
            LEFT JOIN tbl_code b ON p.brand_code_seq = b.seq
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            LEFT JOIN tbl_code t ON p.type_code_seq = t.seq
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1 AND p.use_yn = 'Y'
        """))
        
        final_stats = result.fetchone()
        print(f"   📊 최종 매핑 상태 (활성 제품):")
        print(f"      총 제품: {final_stats.total_products}개")
        print(f"      브랜드 완료: {final_stats.good_brand}개 ({final_stats.good_brand/final_stats.total_products*100:.1f}%)")
        print(f"      품목 완료: {final_stats.good_category}개 ({final_stats.good_category/final_stats.total_products*100:.1f}%)")
        print(f"      타입 완료: {final_stats.good_type}개 ({final_stats.good_type/final_stats.total_products*100:.1f}%)")
        print(f"      자가코드 완료: {final_stats.good_code}개")
        
        # 7. 개선된 샘플 확인
        print(f"\n7️⃣ 개선된 샘플 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                p.product_name,
                b.code_name as brand_name,
                c.code_name as category_name,
                t.code_name as type_name,
                p.price,
                pd.std_div_prod_code
            FROM products p
            LEFT JOIN tbl_code b ON p.brand_code_seq = b.seq
            LEFT JOIN tbl_code c ON p.category_code_seq = c.seq
            LEFT JOIN tbl_code t ON p.type_code_seq = t.seq
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.company_id = 1 AND p.use_yn = 'Y'
            ORDER BY p.id
            LIMIT 15
        """))
        
        improved_samples = result.fetchall()
        print(f"   📋 개선된 샘플 데이터:")
        print(f"      {'제품명':25} | {'브랜드':8} | {'품목':8} | {'타입':8} | {'가격':10} | {'자가코드':16}")
        print(f"      {'-'*25} | {'-'*8} | {'-'*8} | {'-'*8} | {'-'*10} | {'-'*16}")
        
        for sample in improved_samples:
            brand = sample.brand_name or "❌미지정"
            category = sample.category_name or "❌미지정"
            type_name = sample.type_name or "❌미지정"
            price = f"{sample.price:,}" if sample.price else "0"
            code = sample.std_div_prod_code or "❌미지정"
            
            print(f"      {sample.product_name[:25]:25} | {brand[:8]:8} | {category[:8]:8} | {type_name[:8]:8} | {price:>10} | {code[:16]:16}")
        
        print(f"\n🎉 UI 표시 문제 대폭 개선 완료!")
        print(f"✅ 브랜드 매핑: {brand_updated}개 업데이트")
        print(f"✅ 품목 매핑: {category_updated}개 업데이트")
        print(f"✅ 타입 매핑: {type_updated}개 업데이트")
        print(f"⚠️ 검색 기능 500 오류는 routes.py 수정 필요")
        print(f"📱 http://127.0.0.1:5000/product/ 에서 개선된 결과 확인!")

if __name__ == "__main__":
    fix_ui_display_comprehensive() 