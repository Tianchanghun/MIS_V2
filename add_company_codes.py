from app import create_app
from app.common.models import db, Code

app = create_app()

with app.app_context():
    try:
        # CB (회사/브랜드) 그룹 찾기
        cb_group = Code.query.filter_by(code='CB', depth=0).first()
        
        if not cb_group:
            print("❌ CB (회사/브랜드) 그룹을 찾을 수 없습니다.")
            exit(1)
        
        print(f"✅ CB 그룹 찾음: {cb_group.code_name} (SEQ: {cb_group.seq})")
        
        # 기존 하위 코드들 확인
        existing_codes = Code.query.filter_by(parent_seq=cb_group.seq).all()
        print(f"📋 기존 CB 하위 코드들:")
        for code in existing_codes:
            print(f"  - {code.code}: {code.code_name} (SEQ: {code.seq})")
        
        # 에이원 코드 확인/추가
        aiwan_code = Code.query.filter_by(parent_seq=cb_group.seq, code='AW1').first()
        if not aiwan_code:
            # 최대 sort 값 구하기
            max_sort = db.session.query(db.func.max(Code.sort)).filter_by(parent_seq=cb_group.seq).scalar() or 0
            
            aiwan_code = Code(
                code_seq=cb_group.seq,
                parent_seq=cb_group.seq,
                depth=1,
                sort=max_sort + 1,
                code='AW1',
                code_name='에이원',
                code_info='에이원 회사 코드',
                ins_user='admin'
            )
            db.session.add(aiwan_code)
            print("➕ 에이원 코드 추가됨")
        else:
            print(f"✅ 에이원 코드 이미 존재: {aiwan_code.code_name}")
        
        # 에이원 월드 코드 확인/추가
        aiwan_world_code = Code.query.filter_by(parent_seq=cb_group.seq, code='AW2').first()
        if not aiwan_world_code:
            # 최대 sort 값 구하기
            max_sort = db.session.query(db.func.max(Code.sort)).filter_by(parent_seq=cb_group.seq).scalar() or 0
            
            aiwan_world_code = Code(
                code_seq=cb_group.seq,
                parent_seq=cb_group.seq,
                depth=1,
                sort=max_sort + 2,
                code='AW2',
                code_name='에이원 월드',
                code_info='에이원 월드 회사 코드',
                ins_user='admin'
            )
            db.session.add(aiwan_world_code)
            print("➕ 에이원 월드 코드 추가됨")
        else:
            print(f"✅ 에이원 월드 코드 이미 존재: {aiwan_world_code.code_name}")
        
        db.session.commit()
        
        # 결과 확인
        print("\n🎉 완료! 현재 CB 하위 코드들:")
        updated_codes = Code.query.filter_by(parent_seq=cb_group.seq).order_by(Code.sort).all()
        for code in updated_codes:
            print(f"  - {code.code}: {code.code_name} (SEQ: {code.seq}, SORT: {code.sort})")
            
    except Exception as e:
        db.session.rollback()
        print(f"❌ 오류: {e}") 