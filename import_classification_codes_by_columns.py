import pandas as pd
from app import create_app, db
from app.common.models import Code
import sys
import os
from datetime import datetime

app = create_app()

def import_classification_codes_by_columns():
    """Excel 파일의 각 컬럼별로 분류 코드를 생성"""
    
    try:
        with app.app_context():
            print("📊 Excel 컬럼별 분류 코드 가져오기 시작")
            print("="*60)
            
            excel_file = "분류 코드 추가.xlsx"
            
            if not os.path.exists(excel_file):
                print(f"❌ Excel 파일을 찾을 수 없습니다: {excel_file}")
                return
            
            # Excel 파일의 첫 번째 시트 읽기
            df = pd.read_excel(excel_file, sheet_name=0)
            
            print(f"📋 Excel 컬럼: {list(df.columns)}")
            print(f"📊 데이터 행 수: {len(df)}")
            
            # 컬럼별 분류 그룹 매핑
            column_mapping = {
                '제품군': ('제품군', 'PG', '제품군 분류'),
                '유형별': ('유형별', 'TP', '유형별 분류'),
                '아이템별': ('아이템별', 'IT', '아이템별 분류'),
                '아이템(상세)': ('아이템상세', 'ITD', '아이템 상세 분류'),
                '색상별': ('색상별', 'CB', '색상별 분류'),
                '제품타입': ('제품타입', 'PT', '제품타입 분류'),
                '제품구분': ('제품구분', 'PD', '제품구분 분류')
            }
            
            # 1. 분류 그룹 생성 (depth=0)
            print("\n🏗️ 컬럼별 분류 그룹 생성 중...")
            
            group_seqs = {}
            for col_name, (group_name, group_code, group_desc) in column_mapping.items():
                if col_name not in df.columns:
                    print(f"⚠️ 컬럼 '{col_name}'이 Excel에 없습니다.")
                    continue
                
                # 기존 그룹 확인
                existing_group = Code.query.filter_by(
                    code=group_code, 
                    depth=0
                ).first()
                
                if existing_group:
                    print(f"✅ {group_name} 그룹 이미 존재: {existing_group.seq}")
                    group_seqs[col_name] = existing_group.seq
                else:
                    # 새 그룹 생성
                    new_group = Code(
                        code_seq=None,
                        parent_seq=None,
                        depth=0,
                        sort=len(group_seqs) + 1,
                        code=group_code,
                        code_name=group_name,
                        code_info=group_desc,
                        ins_user='system',
                        ins_date=datetime.now()
                    )
                    db.session.add(new_group)
                    db.session.flush()  # seq 생성
                    
                    group_seqs[col_name] = new_group.seq
                    print(f"✅ {group_name} 그룹 생성: {new_group.seq}")
            
            # 2. 각 컬럼별로 고유 값 추출 및 코드 생성
            total_added = 0
            total_skipped = 0
            
            for col_name, parent_seq in group_seqs.items():
                print(f"\n📋 '{col_name}' 컬럼 처리 중...")
                
                # 해당 컬럼의 고유 값들 추출 (NaN 제외)
                unique_values = df[col_name].dropna().unique()
                print(f"📝 고유 값 개수: {len(unique_values)}개")
                
                added_count = 0
                skipped_count = 0
                
                for idx, value in enumerate(unique_values):
                    try:
                        # 값 정리
                        code_name = str(value).strip()
                        
                        if not code_name or code_name in ['', 'nan', 'NaN']:
                            continue
                        
                        # 코드값 생성 (컬럼명 약자 + 순번)
                        group_info = column_mapping[col_name]
                        code_val = f"{group_info[1]}{idx+1:03d}"
                        
                        # 중복 확인 (같은 부모 하위에서 코드명 중복 체크)
                        existing_code = Code.query.filter_by(
                            parent_seq=parent_seq,
                            code_name=code_name
                        ).first()
                        
                        if existing_code:
                            print(f"⚠️ 중복 건너뜀: {code_name}")
                            skipped_count += 1
                            continue
                        
                        # 새 코드 추가
                        new_code = Code(
                            code_seq=None,
                            parent_seq=parent_seq,
                            depth=1,
                            sort=added_count + 1,
                            code=code_val,
                            code_name=code_name,
                            code_info=f"{col_name}에서 추출된 값",
                            ins_user='system',
                            ins_date=datetime.now()
                        )
                        db.session.add(new_code)
                        added_count += 1
                        
                        print(f"✅ 추가: {code_name} ({code_val})")
                        
                    except Exception as e:
                        print(f"❌ 값 '{value}' 처리 오류: {e}")
                        continue
                
                print(f"📊 '{col_name}' 결과: 추가 {added_count}개, 건너뜀 {skipped_count}개")
                total_added += added_count
                total_skipped += skipped_count
            
            # 변경사항 저장
            if total_added > 0:
                db.session.commit()
                print(f"\n💾 총 {total_added}개 분류 코드 추가 완료!")
            else:
                print(f"\n📭 추가된 분류 코드가 없습니다.")
            
            print(f"\n📈 최종 결과:")
            print(f"  - 총 추가: {total_added}개")
            print(f"  - 총 건너뜀: {total_skipped}개")
            
            # 3. 추가된 분류 확인
            print(f"\n🔍 분류 그룹별 코드 개수:")
            for col_name, group_seq in group_seqs.items():
                count = Code.query.filter_by(parent_seq=group_seq).count()
                group_info = column_mapping[col_name]
                print(f"  - {group_info[0]}: {count}개")
            
            print("\n✅ 컬럼별 분류 코드 가져오기 완료!")
            
    except Exception as e:
        db.session.rollback()
        print(f"❌ 분류 코드 가져오기 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # pandas 설치 확인
    try:
        import pandas as pd
        print("✅ pandas 모듈 로드 성공")
    except ImportError:
        print("❌ pandas 모듈이 필요합니다. 설치: pip install pandas openpyxl")
        sys.exit(1)
    
    import_classification_codes_by_columns() 