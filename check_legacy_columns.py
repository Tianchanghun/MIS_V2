import pyodbc

print("🔍 레거시 DB 테이블 구조 확인")

try:
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=210.109.96.74,2521;"
        "DATABASE=db_mis;"
        "UID=user_mis;"
        "PWD=user_mis!@12;"
        "ApplicationIntent=ReadOnly;",
        timeout=30
    )
    print("✅ 연결 성공")
    
    cursor = conn.cursor()
    
    # tbl_Product 테이블 구조 확인
    print("\n📋 tbl_Product 컬럼 구조:")
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'tbl_Product' 
        ORDER BY ORDINAL_POSITION
    """)
    
    columns = cursor.fetchall()
    for col in columns:
        col_name, data_type, nullable, max_length = col
        length_info = f"({max_length})" if max_length else ""
        nullable_info = "NULL" if nullable == "YES" else "NOT NULL"
        print(f"  - {col_name}: {data_type}{length_info} {nullable_info}")
    
    # 가격 관련 컬럼 확인
    print("\n💰 가격 관련 컬럼 데이터 확인:")
    cursor.execute("SELECT TOP 3 seq, ProdTagAmt FROM tbl_Product WHERE ProdTagAmt > 0")
    rows = cursor.fetchall()
    for row in rows:
        print(f"  SEQ: {row[0]}, ProdTagAmt: {row[1]:,}원")
    
    conn.close()
    print("\n✅ 확인 완료")
    
except Exception as e:
    print(f"❌ 오류: {e}")
    import traceback
    traceback.print_exc() 