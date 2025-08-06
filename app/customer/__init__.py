#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
고객 관리 모듈 (임시 껍데기)
"""

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

@customer_bp.route('/')
@login_required
def index():
    """고객 목록"""
    return render_template('customer/index.html')

@customer_bp.route('/analysis')
@login_required
def analysis():
    """고객 분석"""
    return render_template('customer/analysis.html')

@customer_bp.route('/carseat-change')
def carseat_change():
    return "카시트 교환 관리 준비중"

@customer_bp.route('/serial-search')
def serial_search():
    return "시리얼 검색 준비중"

@customer_bp.route('/serial-list')
def serial_list():
    return "시리얼 목록 준비중"

@customer_bp.route('/targeting')
def targeting():
    return "타겟팅 준비중"

@customer_bp.route('/send-log')
def send_log():
    return "발송 내역 준비중"

@customer_bp.route('/as-list')
def as_list():
    return "A/S 접수 내역 준비중"

@customer_bp.route('/store-management')
def store_management():
    return "매장 관리 준비중"

@customer_bp.route('/send-sms', methods=['POST'])
def send_sms():
    return "SMS 발송 준비중" 