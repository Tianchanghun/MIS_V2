#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
인증 시스템 Blueprint
로그인, 로그아웃, 권한 관리
"""

# routes.py에서 정의된 auth_bp를 import
from app.auth.routes import auth_bp

# bp는 auth_bp의 별칭
bp = auth_bp 