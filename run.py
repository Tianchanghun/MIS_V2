#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIS v2 Flask 애플리케이션 실행 파일
새로운 모듈화된 구조 사용
"""

import os
from app import create_app

# Flask 애플리케이션 생성
app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # 개발 서버 실행
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_DEBUG', True)
    ) 