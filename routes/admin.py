#!/usr/bin/env python3
"""
관리자 화면 라우트 - ERPia API 설정 관리
- ERPia API 설정값 조회/수정
- 동기화 로그 확인
- 수동 동기화 실행
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
from models.erpia_settings import ErpiaSettings, ErpiaSyncLog
from services.erpia_api_client import ErpiaApiClient
from app import db
from datetime import datetime, timedelta
import logging

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
logger = logging.getLogger(__name__)

@admin_bp.route('/erpia_settings')
@login_required
def erpia_settings():
    """ERPia API 설정 페이지"""
    try:
        # 모든 설정값 조회
        settings = ErpiaSettings.query.filter_by(is_active=True).all()
        
        # 설정값을 딕셔너리로 변환
        settings_dict = {}
        for setting in settings:
            if setting.setting_type == 'int':
                settings_dict[setting.setting_key] = int(setting.setting_value)
            elif setting.setting_type == 'float':
                settings_dict[setting.setting_key] = float(setting.setting_value)
            elif setting.setting_type == 'bool':
                settings_dict[setting.setting_key] = setting.setting_value.lower() in ('true', '1', 'yes', 'on')
            else:
                settings_dict[setting.setting_key] = setting.setting_value
        
        # 최근 동기화 로그 조회
        recent_logs = ErpiaSyncLog.query.order_by(ErpiaSyncLog.start_time.desc()).limit(10).all()
        
        return render_template('admin/erpia_settings.html', 
                             settings=settings,
                             settings_dict=settings_dict,
                             recent_logs=recent_logs)
    
    except Exception as e:
        logger.error(f"ERPia 설정 페이지 로드 실패: {e}")
        flash('ERPia 설정을 불러오는 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('main.index'))

@admin_bp.route('/erpia_settings/update', methods=['POST'])
@login_required
def update_erpia_settings():
    """ERPia API 설정 업데이트"""
    try:
        # 폼 데이터 받기
        page_size = int(request.form.get('page_size', 30))
        call_interval = int(request.form.get('call_interval', 3))
        timeout = int(request.form.get('timeout', 30))
        retry_count = int(request.form.get('retry_count', 3))
        auto_sync_enabled = request.form.get('auto_sync_enabled') == 'on'
        sync_schedule_daily = request.form.get('sync_schedule_daily', '02:00')
        sync_schedule_weekly = request.form.get('sync_schedule_weekly', 'sunday')
        
        # 유효성 검증
        if not (1 <= page_size <= 30):
            flash('페이징 크기는 1~30 사이의 값이어야 합니다.', 'error')
            return redirect(url_for('admin.erpia_settings'))
        
        if not (1 <= call_interval <= 10):
            flash('호출 간격은 1~10초 사이의 값이어야 합니다.', 'error')
            return redirect(url_for('admin.erpia_settings'))
        
        if not (10 <= timeout <= 120):
            flash('타임아웃은 10~120초 사이의 값이어야 합니다.', 'error')
            return redirect(url_for('admin.erpia_settings'))
        
        if not (1 <= retry_count <= 5):
            flash('재시도 횟수는 1~5회 사이의 값이어야 합니다.', 'error')
            return redirect(url_for('admin.erpia_settings'))
        
        # 설정값 업데이트
        ErpiaSettings.set_setting('page_size', page_size, 'int', 
                                'ERPia API 페이징 크기 (최대 30건 권장)', 1, 30)
        
        ErpiaSettings.set_setting('call_interval', call_interval, 'int', 
                                'ERPia API 호출 간격 (초)', 1, 10)
        
        ErpiaSettings.set_setting('timeout', timeout, 'int', 
                                'ERPia API 요청 타임아웃 (초)', 10, 120)
        
        ErpiaSettings.set_setting('retry_count', retry_count, 'int', 
                                'ERPia API 재시도 횟수', 1, 5)
        
        ErpiaSettings.set_setting('auto_sync_enabled', auto_sync_enabled, 'bool', 
                                'ERPia 자동 동기화 활성화 여부')
        
        ErpiaSettings.set_setting('sync_schedule_daily', sync_schedule_daily, 'string', 
                                '일일 동기화 시간 (HH:MM 형식)')
        
        ErpiaSettings.set_setting('sync_schedule_weekly', sync_schedule_weekly, 'string', 
                                '주간 동기화 요일 (monday~sunday)')
        
        logger.info(f"ERPia 설정 업데이트됨 - 페이지크기: {page_size}, 호출간격: {call_interval}초")
        flash('ERPia API 설정이 성공적으로 업데이트되었습니다.', 'success')
        
    except ValueError as e:
        logger.error(f"ERPia 설정 업데이트 실패 (값 오류): {e}")
        flash('잘못된 설정값입니다. 올바른 숫자를 입력해주세요.', 'error')
    
    except Exception as e:
        logger.error(f"ERPia 설정 업데이트 실패: {e}")
        flash('설정 업데이트 중 오류가 발생했습니다.', 'error')
    
    return redirect(url_for('admin.erpia_settings'))

@admin_bp.route('/erpia_settings/reset', methods=['POST'])
@login_required
def reset_erpia_settings():
    """ERPia API 설정 초기화"""
    try:
        # 기본 설정값으로 초기화
        ErpiaSettings.initialize_default_settings()
        
        logger.info("ERPia 설정이 기본값으로 초기화됨")
        flash('ERPia API 설정이 기본값으로 초기화되었습니다.', 'success')
        
    except Exception as e:
        logger.error(f"ERPia 설정 초기화 실패: {e}")
        flash('설정 초기화 중 오류가 발생했습니다.', 'error')
    
    return redirect(url_for('admin.erpia_settings'))

@admin_bp.route('/erpia_sync/test')
@login_required
def test_erpia_sync():
    """ERPia API 연결 테스트"""
    try:
        # API 클라이언트 생성 및 설정 로드
        client = ErpiaApiClient()
        
        # 마켓코드 조회 테스트 (가장 간단한 API)
        markets = client.get_market_codes()
        
        if markets:
            result = {
                'success': True,
                'message': f'ERPia API 연결 성공! (마켓코드 {len(markets)}건 조회됨)',
                'data': {
                    'market_count': len(markets),
                    'page_size': client.page_size,
                    'call_interval': client.call_interval,
                    'timeout': client.timeout,
                    'retry_count': client.retry_count
                }
            }
            logger.info(f"ERPia API 연결 테스트 성공 - 마켓코드 {len(markets)}건")
        else:
            result = {
                'success': False,
                'message': 'ERPia API 연결 실패 또는 데이터 없음',
                'data': None
            }
            logger.warning("ERPia API 연결 테스트 실패")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"ERPia API 연결 테스트 오류: {e}")
        return jsonify({
            'success': False,
            'message': f'ERPia API 연결 테스트 중 오류 발생: {str(e)}',
            'data': None
        })

@admin_bp.route('/erpia_sync/codes')
@login_required
def sync_erpia_codes():
    """ERPia 코드 수동 동기화"""
    try:
        # 동기화 로그 생성
        sync_log = ErpiaSyncLog(
            sync_type='codes',
            sync_mode='manual',
            status='running'
        )
        db.session.add(sync_log)
        db.session.commit()
        
        # API 클라이언트 생성
        client = ErpiaApiClient()
        
        # 코드 동기화 수행
        results = {}
        total_records = 0
        processed_records = 0
        
        try:
            # 1. 마켓코드 동기화
            markets = client.get_market_codes()
            results['markets'] = len(markets)
            total_records += len(markets)
            processed_records += len(markets)
            
            # 2. 사이트코드 동기화
            sites = client.get_site_codes()
            results['sites'] = len(sites)
            total_records += len(sites)
            processed_records += len(sites)
            
            # 3. 창고코드 동기화
            warehouses = client.get_warehouse_codes()
            results['warehouses'] = len(warehouses)
            total_records += len(warehouses)
            processed_records += len(warehouses)
            
            # 4. 브랜드코드 동기화
            brands = client.get_brand_codes(status='0')
            results['brands'] = len(brands)
            total_records += len(brands)
            processed_records += len(brands)
            
            # 5. 택배사코드 동기화
            companies = client.get_delivery_companies()
            results['companies'] = len(companies)
            total_records += len(companies)
            processed_records += len(companies)
            
            # 동기화 로그 업데이트
            sync_log.total_records = total_records
            sync_log.processed_records = processed_records
            sync_log.complete_sync('success')
            
            logger.info(f"ERPia 코드 동기화 완료 - 총 {processed_records}건")
            
            return jsonify({
                'success': True,
                'message': f'ERPia 코드 동기화 완료! (총 {processed_records}건)',
                'data': results
            })
            
        except Exception as e:
            sync_log.complete_sync('failed', str(e))
            raise e
            
    except Exception as e:
        logger.error(f"ERPia 코드 동기화 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'ERPia 코드 동기화 실패: {str(e)}',
            'data': None
        })

@admin_bp.route('/erpia_sync/customers')
@login_required
def sync_erpia_customers():
    """ERPia 거래처 수동 동기화"""
    try:
        # 동기화 기간 설정 (최근 7일)
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
        
        # 동기화 로그 생성
        sync_log = ErpiaSyncLog(
            sync_type='customers',
            sync_mode='manual',
            status='running'
        )
        db.session.add(sync_log)
        db.session.commit()
        
        # API 클라이언트 생성
        client = ErpiaApiClient()
        
        try:
            # 거래처 동기화 수행
            customers = client.get_customers_paginated(start_date, end_date)
            
            # 동기화 로그 업데이트
            sync_log.total_records = len(customers)
            sync_log.processed_records = len(customers)
            sync_log.complete_sync('success')
            
            logger.info(f"ERPia 거래처 동기화 완료 - {len(customers)}건")
            
            return jsonify({
                'success': True,
                'message': f'ERPia 거래처 동기화 완료! ({len(customers)}건, {start_date}~{end_date})',
                'data': {
                    'customer_count': len(customers),
                    'start_date': start_date,
                    'end_date': end_date
                }
            })
            
        except Exception as e:
            sync_log.complete_sync('failed', str(e))
            raise e
            
    except Exception as e:
        logger.error(f"ERPia 거래처 동기화 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'ERPia 거래처 동기화 실패: {str(e)}',
            'data': None
        })

@admin_bp.route('/erpia_logs')
@login_required
def erpia_logs():
    """ERPia 동기화 로그 조회"""
    try:
        # 페이지 파라미터
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # 필터 파라미터
        sync_type = request.args.get('sync_type', '')
        status = request.args.get('status', '')
        
        # 쿼리 빌드
        query = ErpiaSyncLog.query
        
        if sync_type:
            query = query.filter(ErpiaSyncLog.sync_type == sync_type)
        
        if status:
            query = query.filter(ErpiaSyncLog.status == status)
        
        # 페이징 처리
        logs = query.order_by(ErpiaSyncLog.start_time.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 통계 정보
        total_logs = ErpiaSyncLog.query.count()
        success_logs = ErpiaSyncLog.query.filter_by(status='success').count()
        failed_logs = ErpiaSyncLog.query.filter_by(status='failed').count()
        
        stats = {
            'total': total_logs,
            'success': success_logs,
            'failed': failed_logs,
            'success_rate': round((success_logs / total_logs * 100) if total_logs > 0 else 0, 2)
        }
        
        return render_template('admin/erpia_logs.html', 
                             logs=logs, 
                             stats=stats,
                             sync_type=sync_type,
                             status=status)
        
    except Exception as e:
        logger.error(f"ERPia 로그 조회 실패: {e}")
        flash('동기화 로그를 불러오는 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('admin.erpia_settings'))

@admin_bp.route('/erpia_logs/<int:log_id>')
@login_required
def erpia_log_detail(log_id):
    """ERPia 동기화 로그 상세 조회"""
    try:
        log = ErpiaSyncLog.query.get_or_404(log_id)
        return render_template('admin/erpia_log_detail.html', log=log)
        
    except Exception as e:
        logger.error(f"ERPia 로그 상세 조회 실패: {e}")
        flash('로그 상세 정보를 불러오는 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('admin.erpia_logs'))

# JSON API 엔드포인트
@admin_bp.route('/api/erpia_settings')
@login_required
def api_erpia_settings():
    """ERPia API 설정 JSON 조회"""
    try:
        settings = {}
        settings['page_size'] = ErpiaSettings.get_page_size()
        settings['call_interval'] = ErpiaSettings.get_call_interval()
        settings['timeout'] = ErpiaSettings.get_timeout()
        settings['retry_count'] = ErpiaSettings.get_retry_count()
        settings['auto_sync_enabled'] = ErpiaSettings.get_setting('auto_sync_enabled', False)
        settings['sync_schedule_daily'] = ErpiaSettings.get_setting('sync_schedule_daily', '02:00')
        settings['sync_schedule_weekly'] = ErpiaSettings.get_setting('sync_schedule_weekly', 'sunday')
        
        return jsonify({
            'success': True,
            'data': settings
        })
        
    except Exception as e:
        logger.error(f"ERPia 설정 API 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@admin_bp.route('/api/erpia_logs/recent')
@login_required
def api_recent_erpia_logs():
    """최근 ERPia 동기화 로그 JSON 조회"""
    try:
        logs = ErpiaSyncLog.query.order_by(ErpiaSyncLog.start_time.desc()).limit(5).all()
        
        logs_data = []
        for log in logs:
            logs_data.append({
                'id': log.id,
                'sync_type': log.sync_type,
                'sync_mode': log.sync_mode,
                'status': log.status,
                'total_records': log.total_records,
                'processed_records': log.processed_records,
                'success_rate': log.success_rate,
                'start_time': log.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration_seconds': log.duration_seconds
            })
        
        return jsonify({
            'success': True,
            'data': logs_data
        })
        
    except Exception as e:
        logger.error(f"최근 ERPia 로그 API 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }) 