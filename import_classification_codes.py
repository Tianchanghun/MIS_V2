import pandas as pd
from app import create_app, db
from app.common.models import Code
import sys
import os
from datetime import datetime

app = create_app()

def import_classification_codes():
    """Excel 파일에서 분류 코드를 읽어서 tbl_code에 추가"""
    
    try:
        with app.app_context():
            print("📊 Excel 파일에서 분류 코드 가져오기 시작")
            print("="*60)
            
            excel_file = "분류 코드 추가.xlsx"
            
            if not os.path.exists(excel_file):
                print(f"❌ Excel 파일을 찾을 수 없습니다: {excel_file}")
                return
            
            # Excel 파일 읽기 (모든 시트)
            excel_data = pd.read_excel(excel_file, sheet_name=None)
            
            print(f"📋 발견된 시트: {list(excel_data.keys())}")
            
            # 분류 그룹 생성을 위한 매핑
            classification_groups = [
                ("분류1", "CL1", "제품 분류1"),
                ("분류2", "CL2", "제품 분류2"), 
                ("분류3", "CL3", "제품 분류3"),
                ("분류4", "CL4", "제품 분류4"),
                ("분류5", "CL5", "제품 분류5")
            ]
            
            # 1. 분류 그룹 생성 (depth=0)
            print("\n🏗️ 분류 그룹 생성 중...")
            
            group_seqs = {}
            for group_name, group_code, group_desc in classification_groups:
                # 기존 그룹 확인
                existing_group = Code.query.filter_by(
                    code=group_code, 
                    depth=0
                ).first()
                
                if existing_group:
                    print(f"✅ {group_name} 그룹 이미 존재: {existing_group.seq}")
                    group_seqs[group_name] = existing_group.seq
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
                    
                    group_seqs[group_name] = new_group.seq
                    print(f"✅ {group_name} 그룹 생성: {new_group.seq}")
            
            # 2. Excel 시트별로 분류 코드 처리
            total_added = 0
            total_skipped = 0
            
            for sheet_name, df in excel_data.items():
                print(f"\n📋 시트 '{sheet_name}' 처리 중...")
                
                if df.empty:
                    print(f"⚠️ 시트 '{sheet_name}'이 비어있습니다.")
                    continue
                
                # 컬럼명 확인 및 정리
                print(f"📝 컬럼: {list(df.columns)}")
                
                # 첫 번째 컬럼을 코드명으로, 두 번째 컬럼을 코드값으로 가정
                if len(df.columns) >= 2:
                    code_name_col = df.columns[0]
                    code_val_col = df.columns[1]
                elif len(df.columns) >= 1:
                    code_name_col = df.columns[0]
                    code_val_col = df.columns[0]  # 같은 컬럼 사용
                else:
                    print(f"❌ 시트 '{sheet_name}': 유효한 컬럼이 없습니다.")
                    continue
                
                # 시트명을 기반으로 분류 그룹 매핑
                target_group = None
                for group_name, _, _ in classification_groups:
                    if group_name in sheet_name or sheet_name in group_name:
                        target_group = group_name
                        break
                
                # 매핑되지 않으면 첫 번째 분류로 기본 설정
                if not target_group:
                    target_group = "분류1"
                    print(f"⚠️ 시트 '{sheet_name}' -> {target_group}로 매핑")
                
                parent_seq = group_seqs[target_group]
                added_count = 0
                skipped_count = 0
                
                # 데이터 행 처리
                for idx, row in df.iterrows():
                    try:
                        # NaN 값 처리
                        code_name = str(row[code_name_col]).strip() if pd.notna(row[code_name_col]) else ""
                        code_val = str(row[code_val_col]).strip() if pd.notna(row[code_val_col]) else ""
                        
                        if not code_name or code_name in ['', 'nan', 'NaN']:
                            continue
                        
                        # 코드값이 없으면 코드명 기반으로 생성
                        if not code_val or code_val in ['', 'nan', 'NaN']:
                            # 한글이면 초성 추출 또는 일련번호
                            code_val = f"CL{idx+1:03d}"
                        
                        # 중복 확인
                        existing_code = Code.query.filter_by(
                            parent_seq=parent_seq,
                            code=code_val
                        ).first()
                        
                        if existing_code:
                            print(f"⚠️ 중복 건너뜀: {code_name} ({code_val})")
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
                            code_info=f"{target_group} - {sheet_name}에서 가져옴",
                            ins_user='system',
                            ins_date=datetime.now()
                        )
                        db.session.add(new_code)
                        added_count += 1
                        
                        print(f"✅ 추가: {code_name} ({code_val}) -> {target_group}")
                        
                    except Exception as e:
                        print(f"❌ 행 {idx} 처리 오류: {e}")
                        continue
                
                print(f"📊 시트 '{sheet_name}' 결과: 추가 {added_count}개, 건너뜀 {skipped_count}개")
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
            for group_name, group_seq in group_seqs.items():
                count = Code.query.filter_by(parent_seq=group_seq).count()
                print(f"  - {group_name}: {count}개")
            
            print("\n✅ 분류 코드 가져오기 완료!")
            
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
    
    import_classification_codes() 