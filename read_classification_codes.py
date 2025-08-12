#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
분류 코드 추가1.xlsx 파일을 읽어서 새로운 분류 코드들을 확인하는 스크립트
"""

import pandas as pd
import os

def read_classification_codes():
    """엑셀 파일에서 분류 코드들을 읽어서 출력"""
    
    excel_file = "분류 코드 추가1.xlsx"
    
    if not os.path.exists(excel_file):
        print(f"❌ 파일을 찾을 수 없습니다: {excel_file}")
        return
    
    try:
        # 엑셀 파일 읽기
        print(f"📁 엑셀 파일 읽는 중: {excel_file}")
        
        # 모든 시트 확인
        excel_data = pd.ExcelFile(excel_file)
        print(f"📊 시트 목록: {excel_data.sheet_names}")
        
        for sheet_name in excel_data.sheet_names:
            print(f"\n=== 시트: {sheet_name} ===")
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            print(f"행 수: {len(df)}")
            print(f"열 수: {len(df.columns)}")
            print(f"컬럼명: {list(df.columns)}")
            
            # 처음 10개 행 출력
            print("\n--- 데이터 샘플 (처음 10개 행) ---")
            print(df.head(10))
            
            # 각 컬럼별 고유값 개수 확인
            print("\n--- 각 컬럼별 고유값 개수 ---")
            for col in df.columns:
                unique_count = df[col].nunique()
                print(f"  {col}: {unique_count}개 고유값")
                
                # 고유값이 50개 이하면 실제 값들도 출력
                if unique_count <= 50:
                    unique_values = df[col].dropna().unique()
                    print(f"    값들: {list(unique_values)}")
                    
    except Exception as e:
        print(f"❌ 엑셀 파일 읽기 실패: {e}")

if __name__ == "__main__":
    read_classification_codes() 