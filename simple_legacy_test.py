print("🚀 레거시 DB 연결 테스트 시작")

try:
    import pyodbc
    print("✅ pyodbc 모듈 로드 성공")
    
    conn_string = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=210.109.96.74,2521;DATABASE=db_mis;UID=user_mis;PWD=user_mis!@12;ApplicationIntent=ReadOnly;"
    print("🔄 DB 연결 시도 중...")
    
    conn = pyodbc.connect(conn_string, timeout=30)
    print("✅ 연결 성공!")
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tbl_Product WHERE ProdTagAmt > 0")
    count = cursor.fetchone()[0]
    print(f"📊 가격이 있는 상품: {count}개")
    
    cursor.execute("SELECT TOP 3 seq, ProdNm, ProdTagAmt FROM tbl_Product WHERE ProdTagAmt > 0")
    rows = cursor.fetchall()
    
    print("📋 샘플 데이터:")
    for row in rows:
        print(f"  SEQ: {row[0]}, 이름: {row[1][:20]}, 가격: {row[2]:,}원")
    
    conn.close()
    print("✅ 테스트 완료")
    
except Exception as e:
    print(f"❌ 오류: {e}")
    import traceback
    traceback.print_exc() 