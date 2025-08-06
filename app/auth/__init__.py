#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
인증 시스템 Blueprint
로그인, 로그아웃, 권한 관리
"""

from flask import Blueprint

bp = Blueprint('auth', __name__)

# 라우트 파일 import (순환 import 방지를 위해 Blueprint 생성 후 import)
from app.auth import routes 