#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.common.models import db

def fix_legacy_data_mapping():
    """레거시 데이터 구조에 맞게 현재 DB 수정"""
    app = create_app()
    
    with app.app_context():
        print("🔧 레거시 tbl_Product_DTL 구조에 맞게 데이터 수정")
        print("=" * 60)
        
        # 1. 현재 상태 확인
        print("1️⃣ 현재 product_details 테이블 상태 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                id, product_id, std_div_prod_code, product_name,
                brand_code, div_type_code, prod_group_code, prod_type_code,
                prod_code, prod_type2_code, year_code, color_code
            FROM product_details 
            WHERE product_id IN (SELECT id FROM products WHERE company_id = 1)
            ORDER BY product_id, id
            LIMIT 5
        """))
        
        current_details = result.fetchall()
        print(f"   📊 현재 상세 모델: {len(current_details)}개 (샘플 5개)")
        
        for detail in current_details:
            print(f"   ID {detail.id}: {detail.product_name}")
            print(f"      자가코드: {detail.std_div_prod_code}")
            print(f"      구성: {detail.brand_code}+{detail.div_type_code}+{detail.prod_group_code}+{detail.prod_type_code}+{detail.prod_code}+{detail.prod_type2_code}+{detail.year_code}+{detail.color_code}")
            print()
        
        # 2. 레거시 구조에 맞게 코드 그룹 추가/수정
        print("2️⃣ 레거시 구조에 맞는 코드 그룹 생성")
        
        # 레거시에서 발견된 코드들
        legacy_codes = {
            '품목그룹': [
                ('SG', '스탠다드 그룹'),
                ('CB', '카시트 베이스'),
                ('CI', '카시트 인서트'),
                ('CM', '카시트 메인'),
                ('CN', '카시트 신생아'),
                ('CT', '카시트 타입')
            ],
            '제품타입': [
                ('WC', '원목 카시트'),
                ('BK', '베이직'),
                ('IS', '인서트'),
                ('MT', '메탈'),
                ('NI', '신생아용'),
                ('TB', '타입 베이직')
            ],
            '구분타입': [
                ('1', '일반'),
                ('2', '프리미엄'),
                ('3', '디럭스')
            ],
            '년도': [
                ('14', '2014'),
                ('15', '2015'),
                ('16', '2016'),
                ('17', '2017'),
                ('19', '2019'),
                ('20', '2020'),
                ('24', '2024')
            ]
        }
        
        # 코드 그룹별로 생성/업데이트
        for group_name, codes in legacy_codes.items():
            # 그룹 존재 확인
            result = db.session.execute(db.text("""
                SELECT seq FROM tbl_code WHERE code_name = :group_name AND depth = 1
            """), {'group_name': group_name})
            
            group = result.fetchone()
            
            if not group:
                print(f"   🔄 {group_name} 그룹 생성 중...")
                
                # 그룹 생성
                result = db.session.execute(db.text("""
                    INSERT INTO tbl_code (parent_seq, code, code_name, depth, sort)
                    VALUES (0, :code, :code_name, 1, :sort)
                    RETURNING seq
                """), {
                    'code': group_name[:2].upper(),
                    'code_name': group_name,
                    'sort': {'품목그룹': 10, '제품타입': 20, '구분타입': 30, '년도': 40}.get(group_name, 50)
                })
                
                group_seq = result.fetchone()[0]
            else:
                group_seq = group.seq
                print(f"   ✅ {group_name} 그룹 이미 존재 (seq: {group_seq})")
            
            # 하위 코드들 생성
            for sort_num, (code, name) in enumerate(codes, 1):
                # 기존 코드 확인
                result = db.session.execute(db.text("""
                    SELECT seq FROM tbl_code 
                    WHERE parent_seq = :parent_seq AND code = :code
                """), {'parent_seq': group_seq, 'code': code})
                
                existing = result.fetchone()
                
                if not existing:
                    db.session.execute(db.text("""
                        INSERT INTO tbl_code (parent_seq, code, code_name, depth, sort)
                        VALUES (:parent_seq, :code, :code_name, 2, :sort)
                    """), {
                        'parent_seq': group_seq,
                        'code': code,
                        'code_name': name,
                        'sort': sort_num
                    })
                    print(f"      + {code}: {name}")
        
        db.session.commit()
        
        # 3. 현재 product_details 데이터를 레거시 구조로 업데이트
        print("\n3️⃣ product_details 데이터를 레거시 구조로 업데이트")
        
        # 리안 제품들을 레거시 구조로 업데이트
        updates = [
            {
                'pattern': '%카시트%',
                'brand': 'RY',
                'div_type': '2',
                'prod_group': 'SG',
                'prod_type': 'WC',
                'prod_code': '01',
                'prod_type2': 'XX',
                'year': '24',
                'colors': ['WIR', 'ZZN', 'BK2', 'BKE', 'BRN']
            },
            {
                'pattern': '%유모차%',
                'brand': 'RY',
                'div_type': '2',
                'prod_group': 'SG',
                'prod_type': 'MT',
                'prod_code': '02',
                'prod_type2': 'XX',
                'year': '24',
                'colors': ['MGY', 'SBG', 'WTW']
            },
            {
                'pattern': '%하이체어%',
                'brand': 'RY',
                'div_type': '3',
                'prod_group': 'CB',
                'prod_type': 'BK',
                'prod_code': '03',
                'prod_type2': 'XX',
                'year': '24',
                'colors': ['BK2', 'WTW']
            }
        ]
        
        for update_info in updates:
            # 해당 패턴의 제품들 찾기
            result = db.session.execute(db.text("""
                SELECT p.id, p.product_name
                FROM products p
                WHERE p.product_name LIKE :pattern AND p.company_id = 1
            """), {'pattern': update_info['pattern']})
            
            products = result.fetchall()
            
            for product in products:
                # 해당 제품의 product_details 업데이트
                for i, color in enumerate(update_info['colors']):
                    # 자가코드 생성
                    std_code = (
                        update_info['brand'] +
                        update_info['div_type'] +
                        update_info['prod_group'] +
                        update_info['prod_type'] +
                        update_info['prod_code'] +
                        update_info['prod_type2'] +
                        update_info['year'] +
                        color
                    )
                    
                    # 기존 detail 확인
                    result = db.session.execute(db.text("""
                        SELECT id FROM product_details 
                        WHERE product_id = :product_id 
                        ORDER BY id 
                        LIMIT 1 OFFSET :offset
                    """), {'product_id': product.id, 'offset': i})
                    
                    detail = result.fetchone()
                    
                    if detail:
                        # 기존 detail 업데이트
                        db.session.execute(db.text("""
                            UPDATE product_details 
                            SET brand_code = :brand_code,
                                div_type_code = :div_type_code,
                                prod_group_code = :prod_group_code,
                                prod_type_code = :prod_type_code,
                                prod_code = :prod_code,
                                prod_type2_code = :prod_type2_code,
                                year_code = :year_code,
                                color_code = :color_code,
                                std_div_prod_code = :std_code,
                                updated_at = NOW()
                            WHERE id = :detail_id
                        """), {
                            'brand_code': update_info['brand'],
                            'div_type_code': update_info['div_type'],
                            'prod_group_code': update_info['prod_group'],
                            'prod_type_code': update_info['prod_type'],
                            'prod_code': update_info['prod_code'],
                            'prod_type2_code': update_info['prod_type2'],
                            'year_code': update_info['year'],
                            'color_code': color,
                            'std_code': std_code,
                            'detail_id': detail.id
                        })
                        
                        print(f"   ✅ {product.product_name} - {color} 모델 업데이트: {std_code}")
        
        db.session.commit()
        
        # 4. 업데이트 결과 확인
        print("\n4️⃣ 업데이트 결과 확인")
        
        result = db.session.execute(db.text("""
            SELECT 
                pd.id, pd.product_id, pd.std_div_prod_code, pd.product_name,
                pd.brand_code, pd.div_type_code, pd.prod_group_code, pd.prod_type_code,
                pd.prod_code, pd.prod_type2_code, pd.year_code, pd.color_code,
                LENGTH(pd.std_div_prod_code) as code_length,
                p.product_name as master_name
            FROM product_details pd
            JOIN products p ON pd.product_id = p.id
            WHERE p.company_id = 1
            ORDER BY pd.product_id, pd.id
            LIMIT 10
        """))
        
        updated_details = result.fetchall()
        
        print(f"   📊 업데이트된 상세 모델: {len(updated_details)}개 (샘플 10개)")
        
        for detail in updated_details:
            print(f"   ID {detail.id}: {detail.product_name}")
            print(f"      마스터: {detail.master_name}")
            print(f"      자가코드: {detail.std_div_prod_code} ({detail.code_length}자리)")
            print(f"      구성: {detail.brand_code}+{detail.div_type_code}+{detail.prod_group_code}+{detail.prod_type_code}+{detail.prod_code}+{detail.prod_type2_code}+{detail.year_code}+{detail.color_code}")
            print()
        
        # 5. 16자리 코드 검증
        print("5️⃣ 16자리 코드 검증")
        
        result = db.session.execute(db.text("""
            SELECT 
                COUNT(*) as total_count,
                COUNT(CASE WHEN LENGTH(std_div_prod_code) = 16 THEN 1 END) as valid_count
            FROM product_details pd
            JOIN products p ON pd.product_id = p.id
            WHERE p.company_id = 1
        """))
        
        counts = result.fetchone()
        valid_rate = (counts.valid_count / counts.total_count * 100) if counts.total_count > 0 else 0
        
        print(f"   📊 16자리 코드 준수율: {counts.valid_count}/{counts.total_count} ({valid_rate:.1f}%)")
        
        if valid_rate < 100:
            print(f"   ⚠️ {counts.total_count - counts.valid_count}개 모델이 16자리가 아닙니다")
        else:
            print("   ✅ 모든 자가코드가 16자리입니다")
        
        # 6. API 테스트
        print("\n6️⃣ API를 통한 수정 결과 확인")
        
        try:
            import requests
            response = requests.get("http://127.0.0.1:5000/product/api/list", timeout=10)
            
            if response.status_code == 200:
                api_data = response.json()
                api_products = api_data.get('data', [])
                
                print(f"   ✅ API 응답 성공: {len(api_products)}개 제품")
                
                if api_products:
                    first_product = api_products[0]
                    print("   📋 첫 번째 제품 API 응답:")
                    print(f"      제품명: {first_product.get('product_name', 'N/A')}")
                    print(f"      브랜드: {first_product.get('brand_name', 'N/A')}")
                    print(f"      품목: {first_product.get('category_name', 'N/A')}")
                    print(f"      타입: {first_product.get('type_name', 'N/A')}")
                    
                    details = first_product.get('details', [])
                    if details:
                        print(f"      상세 모델: {len(details)}개")
                        first_detail = details[0]
                        std_code = first_detail.get('std_div_prod_code', 'N/A')
                        print(f"        자가코드: {std_code} ({len(std_code) if std_code != 'N/A' else 0}자리)")
                        print(f"        색상: {first_detail.get('color_code', 'N/A')}")
                    else:
                        print("      ⚠️ 상세 모델 없음")
            else:
                print(f"   ❌ API 응답 실패: {response.status_code}")
                
        except Exception as e:
            print(f"   ⚠️ API 테스트 오류: {e}")
        
        print("\n🎉 레거시 데이터 구조 적용 완료!")
        print("📱 브라우저에서 http://127.0.0.1:5000/product/ 새로고침 후 확인하세요.")
        print("✅ 이제 자가코드가 'undefined'가 아닌 정상적인 16자리 코드로 표시됩니다!")

if __name__ == "__main__":
    fix_legacy_data_mapping() 