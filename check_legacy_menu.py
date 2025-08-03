#!/usr/bin/env python3
"""
레거시 DB 메뉴 구조 조회
"""

import pyodbc
import pandas as pd

def check_legacy_menu():
    # MS-SQL 연결
    conn_string = '''DRIVER={ODBC Driver 17 for SQL Server};
SERVER=210.109.96.74,2521;
DATABASE=db_mis;
UID=user_mis;
PWD=user_mis!@12;
ApplicationIntent=ReadOnly;'''

    try:
        conn = pyodbc.connect(conn_string)
        
        # 실제 메뉴 구조 조회
        query = '''
        SELECT 
            MenuSeq, ParentSeq, Depth, Sort, Name, Url, UseWebYn
        FROM tbl_category 
        WHERE UseWebYn = 'Y'
        ORDER BY MenuSeq, Depth, Sort
        '''
        
        df = pd.read_sql(query, conn)
        print('=== 레거시 DB 실제 메뉴 구조 ===')
        
        # 메뉴 구조 출력
        for menu_seq in sorted(df['MenuSeq'].unique()):
            menu_data = df[df['MenuSeq'] == menu_seq]
            root_menu = menu_data[menu_data['Depth'] == 0]
            
            if not root_menu.empty:
                print(f'\n{menu_seq}. {root_menu.iloc[0]["Name"]} ({root_menu.iloc[0]["Url"]})')
                
                # 하위 메뉴
                sub_menus = menu_data[menu_data['Depth'] > 0].sort_values('Sort')
                for _, sub in sub_menus.iterrows():
                    indent = '  ' * sub['Depth']
                    print(f'{indent}- {sub["Name"]} ({sub["Url"]})')
        
        conn.close()
        print('\n메뉴 조회 완료!')
        
        return df
        
    except Exception as e:
        print(f'연결 실패: {e}')
        return None

if __name__ == "__main__":
    check_legacy_menu() 