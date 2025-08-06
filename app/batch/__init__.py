#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
배치 관리 모듈
ERPia 자동 데이터 수집 및 배치 작업 관리
"""

from flask import Blueprint

# 배치 관리 Blueprint 생성
batch_bp = Blueprint(
    'batch',
    __name__,
    url_prefix='/batch',
    template_folder='templates',
    static_folder='static'
)

from . import routes 