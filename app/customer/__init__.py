#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
고객 관리 모듈 (임시 껍데기)
"""

from flask import Blueprint, render_template, session, redirect, redirect, url_for
from flask_login import login_required

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

@customer_bp.route('/')
def index():
    """고객 목록"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    return render_template('customer/index.html')

@customer_bp.route('/analysis')
def analysis():
    """고객 분석"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    return render_template('customer/analysis.html')

@customer_bp.route('/carseat-change')
def carseat_change():
    if 'member_seq' not in session:
        return redirect('/auth/login')
    return "카시트 교환 관리 준비중"

@customer_bp.route('/serial-search')
def serial_search():
    if 'member_seq' not in session:
        return redirect('/auth/login')
    return "시리얼 검색 준비중"

@customer_bp.route('/serial-list')
def serial_list():
    if 'member_seq' not in session:
        return redirect('/auth/login')
    return "시리얼 목록 준비중"

@customer_bp.route('/targeting')
def targeting():
    if 'member_seq' not in session:
        return redirect('/auth/login')
    return "타겟팅 준비중"

@customer_bp.route('/send-log')
def send_log():
    if 'member_seq' not in session:
        return redirect('/auth/login')
    return "발송 내역 준비중"

@customer_bp.route('/as-list')
def as_list():
    if 'member_seq' not in session:
        return redirect('/auth/login')
    return "A/S 접수 내역 준비중"

@customer_bp.route('/store-management')
def store_management():
    if 'member_seq' not in session:
        return redirect('/auth/login')
    return "매장 관리 준비중"

@customer_bp.route('/send-sms', methods=['POST'])
def send_sms():
    if 'member_seq' not in session:
        return redirect('/auth/login')
    return "SMS 발송 준비중" 