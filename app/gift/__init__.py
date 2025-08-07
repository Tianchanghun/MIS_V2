#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사은품 관리 모듈 (임시 껍데기)
"""

from flask import Blueprint, render_template, session, redirect, redirect, url_for
from flask_login import login_required

gift_bp = Blueprint('gift', __name__, url_prefix='/gift')

@gift_bp.route('/')
def index():
    """사은품 분류 관리"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    return render_template('gift/index.html')

@gift_bp.route('/settings')
  
def settings():
    """분류 설정"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    return render_template('gift/settings.html') 