#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIS v2 Flask 애플리케이션 메인 실행 파일
"""

import os
from flask import Flask

def create_app():
    """Flask 애플리케이션 팩토리"""
    app = Flask(__name__)
    
    # 기본 설정
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL')
    app.config['REDIS_URL'] = os.environ.get('REDIS_URL')
    
    # 간단한 헬스체크 라우트
    @app.route('/')
    def health_check():
        return {
            'status': 'healthy',
            'message': 'MIS v2 Flask 애플리케이션이 정상 작동 중입니다.',
            'version': '2.0.0'
        }
    
    @app.route('/health')
    def health():
        return {'status': 'ok'}
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_DEBUG', False)
    ) 