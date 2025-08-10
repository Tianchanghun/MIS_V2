"""
레거시 DB에서 코드 데이터 가져오기
"""
import pyodbc
from app import create_app
from app.common.models import db, Code

# 레거시 DB 연결 정보
LEGACY_DB_CONNECTION = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=210.109.96.74,2521;DATABASE=db_mis;UID=user_mis;PWD=user_mis!@12;ApplicationIntent=ReadOnly;"

def import_codes_from_legacy():
    """레거시 DB에서 코드 데이터 가져오기"""
    app = create_app()
    
    with app.app_context():
        try:
            # 레거시 DB 연결
            print("🔗 레거시 DB 연결 중...")
            legacy_conn = pyodbc.connect(LEGACY_DB_CONNECTION)
            legacy_cursor = legacy_conn.cursor()
            
            # 먼저 ST와 관련 그룹들의 CodeSeq 확인
            print("📋 CodeSeq=4 그룹 조회 중...")
            legacy_cursor.execute("SELECT Seq, CodeSeq, ParentSeq, Depth, Sort, Code, CodeName FROM tbl_Code WHERE CodeSeq='4' ORDER BY Sort, Seq")
            group_codes = legacy_cursor.fetchall()
            
            print(f"📦 CodeSeq=4 그룹에서 {len(group_codes)}개 코드 발견:")
            for row in group_codes:
                seq, code_seq, parent_seq, depth, sort, code, code_name = row
                print(f"  - {code}: {code_name} (SEQ: {seq}, Depth: {depth})")
            
            # ST 그룹과 하위 코드들 가져오기
            print("\n📋 ST 그룹과 하위 코드들 조회 중...")
            query = """
            SELECT Seq, CodeSeq, ParentSeq, Depth, Sort, Code, CodeName, CodeInfo, 
                   InsUser, InsDate, UptUser, UptDate
            FROM tbl_Code 
            WHERE Code IN ('ST', 'CS', 'FT', 'SG', 'CG', 'FG', 'TO', 'AC', 'ZG', 'BS', 'PE', 'ACC')
               OR ParentSeq IN (
                   SELECT Seq FROM tbl_Code 
                   WHERE Code IN ('ST', 'CS', 'FT', 'SG', 'CG', 'FG', 'TO', 'AC', 'ZG', 'BS', 'PE', 'ACC')
               )
            ORDER BY Depth, Sort, Seq
            """
            
            legacy_cursor.execute(query)
            legacy_codes = legacy_cursor.fetchall()
            
            print(f"📦 레거시에서 {len(legacy_codes)}개 코드 발견")
            
            # 기존 코드와 중복 체크 및 추가
            imported_count = 0
            updated_count = 0
            
            for row in legacy_codes:
                seq, code_seq, parent_seq, depth, sort, code, code_name, code_info, ins_user, ins_date, upt_user, upt_date = row
                
                # 기존 코드 확인 (seq 기준)
                existing_code = Code.query.filter_by(seq=seq).first()
                
                if existing_code:
                    # 업데이트
                    existing_code.code_seq = code_seq
                    existing_code.parent_seq = parent_seq
                    existing_code.depth = depth
                    existing_code.sort = sort
                    existing_code.code = code
                    existing_code.code_name = code_name
                    existing_code.code_info = code_info
                    existing_code.upt_user = upt_user
                    existing_code.upt_date = upt_date
                    updated_count += 1
                    print(f"🔄 업데이트: {code} - {code_name}")
                else:
                    # 새로 추가
                    new_code = Code(
                        seq=seq,
                        code_seq=code_seq,
                        parent_seq=parent_seq,
                        depth=depth,
                        sort=sort,
                        code=code,
                        code_name=code_name,
                        code_info=code_info,
                        ins_user=ins_user,
                        ins_date=ins_date,
                        upt_user=upt_user,
                        upt_date=upt_date
                    )
                    db.session.add(new_code)
                    imported_count += 1
                    print(f"➕ 추가: {code} - {code_name}")
            
            # 커밋
            db.session.commit()
            legacy_conn.close()
            
            print(f"\n✅ 레거시 코드 가져오기 완료!")
            print(f"   - 새로 추가: {imported_count}개")
            print(f"   - 업데이트: {updated_count}개")
            
            # ST 그룹 하위 코드 확인
            st_group = Code.query.filter_by(code='ST', depth=0).first()
            if st_group:
                st_children = Code.query.filter_by(parent_seq=st_group.seq).order_by(Code.sort).all()
                print(f"\n🎯 ST 그룹 하위 코드: {len(st_children)}개")
                for child in st_children:
                    print(f"   - {child.code}: {child.code_name}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 레거시 DB 가져오기 실패: {e}")
            raise

if __name__ == "__main__":
    import_codes_from_legacy() 