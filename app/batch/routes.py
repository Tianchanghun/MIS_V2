#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
배치 관리 웹 UI 라우트
ERPia 자동 배치 시스템의 웹 인터페이스
"""

from flask import render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json
import logging

from . import batch_bp
from app.services.batch_scheduler import batch_scheduler, BatchJobConfig, BatchExecutionResult
from app.services.erpia_client import ErpiaApiClient
from app.services.gift_classifier import GiftClassifier
from app.common.models import db

logger = logging.getLogger(__name__)

@batch_bp.route('/')
@login_required
def index():
    """배치 관리 메인 페이지"""
    try:
        # 등록된 배치 작업 목록 조회
        jobs = batch_scheduler.get_jobs()
        
        # 최근 실행 결과 조회 (최근 10건)
        recent_executions = []
        
        # 스케줄러 상태 확인
        scheduler_status = {
            'running': batch_scheduler.is_running,
            'job_count': len(jobs),
            'last_check': datetime.now()
        }
        
        return render_template(
            'batch/index.html',
            jobs=jobs,
            recent_executions=recent_executions,
            scheduler_status=scheduler_status,
            current_user=current_user
        )
        
    except Exception as e:
        logger.error(f"❌ 배치 관리 페이지 로드 실패: {e}")
        flash(f'페이지 로드 중 오류가 발생했습니다: {str(e)}', 'error')
        return render_template('batch/index.html', jobs=[], recent_executions=[], scheduler_status={})

@batch_bp.route('/jobs')
@login_required
def job_list():
    """배치 작업 목록 페이지"""
    try:
        jobs = batch_scheduler.get_jobs()
        
        # 작업별 최근 실행 결과 조회
        job_details = []
        for job in jobs:
            job_details.append({
                'job': job,
                'last_execution': None
            })
        
        return render_template(
            'batch/job_list.html',
            job_details=job_details,
            current_user=current_user
        )
        
    except Exception as e:
        logger.error(f"❌ 작업 목록 페이지 로드 실패: {e}")
        flash(f'작업 목록 로드 중 오류가 발생했습니다: {str(e)}', 'error')
        return render_template('batch/job_list.html', job_details=[])

@batch_bp.route('/jobs/add', methods=['GET', 'POST'])
@login_required
def add_job():
    """배치 작업 추가"""
    if request.method == 'GET':
        # 작업 추가 폼 페이지
        job_types = [
            ('DAILY_COLLECTION', '일일 ERPia 데이터 수집'),
            ('CUSTOMER_SYNC', '고객 정보 동기화'),
            ('GIFT_CLASSIFY', '사은품 자동 분류'),
            ('REPORT_GENERATE', '보고서 생성'),
            ('DATA_CLEANUP', '데이터 정리')
        ]
        
        return render_template(
            'batch/add_job.html',
            job_types=job_types,
            current_user=current_user
        )
    
    elif request.method == 'POST':
        try:
            # 폼 데이터 추출
            job_data = {
                'job_id': request.form.get('job_id'),
                'name': request.form.get('name'),
                'job_type': request.form.get('job_type'),
                'company_id': current_user.company_id,
                'enabled': request.form.get('enabled') == 'on',
                'schedule_type': request.form.get('schedule_type', 'cron'),
                'cron_expression': request.form.get('cron_expression', '0 2 * * *'),
                'interval_minutes': int(request.form.get('interval_minutes', 60)),
                'max_instances': int(request.form.get('max_instances', 1)),
                'parameters': {}
            }
            
            # 배치 작업 설정 생성
            job_config = BatchJobConfig(**job_data)
            
            # 작업 등록
            if batch_scheduler.add_job(job_config):
                flash(f'배치 작업 "{job_data["name"]}"이 성공적으로 등록되었습니다.', 'success')
                return redirect(url_for('batch.job_list'))
            else:
                flash('배치 작업 등록에 실패했습니다.', 'error')
                
        except Exception as e:
            logger.error(f"❌ 배치 작업 추가 실패: {e}")
            flash(f'작업 추가 중 오류가 발생했습니다: {str(e)}', 'error')
        
        return redirect(url_for('batch.add_job'))

@batch_bp.route('/jobs/<job_id>/run', methods=['POST'])
@login_required
def run_job(job_id):
    """배치 작업 즉시 실행"""
    try:
        if batch_scheduler.run_job_now(job_id):
            return jsonify({
                'success': True,
                'message': f'작업 {job_id}이 즉시 실행되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'작업 {job_id} 실행에 실패했습니다.'
            }), 400
            
    except Exception as e:
        logger.error(f"❌ 작업 즉시 실행 실패 ({job_id}): {e}")
        return jsonify({
            'success': False,
            'message': f'작업 실행 중 오류가 발생했습니다: {str(e)}'
        }), 500

@batch_bp.route('/erpia/test', methods=['GET', 'POST'])
@login_required
def test_erpia_connection():
    """ERPia API 연결 테스트"""
    try:
        erpia_client = ErpiaApiClient(company_id=current_user.company_id)
        test_result = erpia_client.test_connection()
        
        return jsonify(test_result)
        
    except Exception as e:
        logger.error(f"❌ ERPia 연결 테스트 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'연결 테스트 중 오류가 발생했습니다: {str(e)}',
            'company_id': current_user.company_id
        }), 500

@batch_bp.route('/gift/classify', methods=['POST'])
@login_required
def manual_gift_classify():
    """사은품 수동 분류"""
    try:
        days_back = int(request.json.get('days_back', 7))
        
        gift_classifier = GiftClassifier(company_id=current_user.company_id)
        classified_count = gift_classifier.auto_classify_recent_products(
            company_id=current_user.company_id,
            days_back=days_back
        )
        
        return jsonify({
            'success': True,
            'message': f'최근 {days_back}일간 사은품 분류 완료',
            'data': {
                'classified_count': classified_count,
                'days_back': days_back
            }
        })
        
    except Exception as e:
        logger.error(f"❌ 사은품 수동 분류 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'사은품 분류 중 오류가 발생했습니다: {str(e)}'
        }), 500

@batch_bp.route('/gift/statistics')
@login_required
def gift_statistics():
    """사은품 분류 통계"""
    try:
        start_date = request.args.get('start_date', '2024-01-01')
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        # 임시 통계 데이터
        stats = {
            'total_products': 1000,
            'gift_products': 150,
            'revenue_products': 850,
            'zero_price_gifts': 80,
            'keyword_gifts': 70,
            'pattern_gifts': 0,
            'master_gifts': 0,
            'total_revenue_impact': 5000000,
            'accuracy_rate': 95.5
        }
        
        return jsonify({
            'success': True,
            'data': {
                'total_products': stats['total_products'],
                'gift_products': stats['gift_products'],
                'revenue_products': stats['revenue_products'],
                'zero_price_gifts': stats['zero_price_gifts'],
                'keyword_gifts': stats['keyword_gifts'],
                'pattern_gifts': stats['pattern_gifts'],
                'master_gifts': stats['master_gifts'],
                'total_revenue_impact': stats['total_revenue_impact'],
                'accuracy_rate': stats['accuracy_rate'],
                'gift_ratio': stats['gift_products'] / stats['total_products'] if stats['total_products'] > 0 else 0
            }
        })
        
    except Exception as e:
        logger.error(f"❌ 사은품 통계 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'사은품 통계 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

@batch_bp.route('/dashboard/data')
@login_required  
def dashboard_data():
    """대시보드 데이터 API"""
    try:
        # 스케줄러 상태
        scheduler_status = {
            'running': batch_scheduler.is_running,
            'job_count': len(batch_scheduler.get_jobs()),
            'last_check': datetime.now().isoformat()
        }
        
        # 최근 7일간 실행 통계 (임시로 하드코딩)
        total_executions = 10
        successful_executions = 8
        failed_executions = 2
        
        # 일별 통계 (임시)
        daily_stats = {
            '2025-01-27': {'success': 3, 'failed': 1},
            '2025-01-28': {'success': 5, 'failed': 1}
        }
        
        return jsonify({
            'success': True,
            'data': {
                'scheduler_status': scheduler_status,
                'execution_stats': {
                    'total': total_executions,
                    'successful': successful_executions,
                    'failed': failed_executions,
                    'success_rate': successful_executions / total_executions if total_executions > 0 else 0
                },
                'daily_stats': daily_stats,
                'last_updated': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"❌ 대시보드 데이터 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'대시보드 데이터 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

@batch_bp.route('/scheduler/start', methods=['POST'])
@login_required
def start_scheduler():
    """스케줄러 시작"""
    try:
        if not batch_scheduler.is_running:
            batch_scheduler.start()
            return jsonify({
                'success': True,
                'message': '스케줄러가 시작되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '스케줄러가 이미 실행 중입니다.'
            }), 400
            
    except Exception as e:
        logger.error(f"❌ 스케줄러 시작 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'스케줄러 시작 중 오류가 발생했습니다: {str(e)}'
        }), 500

@batch_bp.route('/scheduler/stop', methods=['POST'])
@login_required
def stop_scheduler():
    """스케줄러 중지"""
    try:
        if batch_scheduler.is_running:
            batch_scheduler.stop()
            return jsonify({
                'success': True,
                'message': '스케줄러가 중지되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '스케줄러가 이미 중지되어 있습니다.'
            }), 400
            
    except Exception as e:
        logger.error(f"❌ 스케줄러 중지 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'스케줄러 중지 중 오류가 발생했습니다: {str(e)}'
        }), 500 

@batch_bp.route('/settings')
@login_required
def settings():
    """배치 설정 페이지"""
    try:
        # 현재 배치 설정 조회
        current_settings = {
            'auto_start': True,
            'default_schedule': '0 2 * * *',  # 매일 새벽 2시
            'max_concurrent_jobs': 3,
            'retry_attempts': 3,
            'email_notifications': True,
            'log_retention_days': 30
        }
        
        return render_template(
            'batch/settings.html',
            settings=current_settings,
            current_user=current_user
        )
        
    except Exception as e:
        logger.error(f"❌ 배치 설정 페이지 로드 실패: {e}")
        flash(f'설정 페이지 로드 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('batch.index'))

@batch_bp.route('/api/status')
@login_required
def api_status():
    """시스템 상태 API"""
    try:
        jobs = batch_scheduler.get_jobs()
        
        # ERPia 연결 테스트
        erpia_connected = False
        try:
            from app.services.erpia_client import ErpiaApiClient
            erpia = ErpiaApiClient()
            test_result = erpia.test_connection()
            erpia_connected = test_result.get('success', False)
        except:
            erpia_connected = False
        
        return jsonify({
            'success': True,
            'scheduler_running': batch_scheduler.is_running,
            'job_count': len(jobs),
            'erpia_connected': erpia_connected,
            'last_update': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@batch_bp.route('/api/scheduler/start', methods=['POST'])
@login_required
def api_start_scheduler():
    """스케줄러 시작 API"""
    try:
        if not batch_scheduler.is_running:
            batch_scheduler.start()
            logger.info("🚀 배치 스케줄러 시작됨")
            return jsonify({'success': True, 'message': '스케줄러가 시작되었습니다.'})
        else:
            return jsonify({'success': True, 'message': '스케줄러가 이미 실행 중입니다.'})
    except Exception as e:
        logger.error(f"❌ 스케줄러 시작 실패: {e}")
        return jsonify({'success': False, 'message': str(e)})

@batch_bp.route('/api/scheduler/stop', methods=['POST'])
@login_required
def api_stop_scheduler():
    """스케줄러 중지 API"""
    try:
        if batch_scheduler.is_running:
            batch_scheduler.shutdown()
            logger.info("⏹️ 배치 스케줄러 중지됨")
            return jsonify({'success': True, 'message': '스케줄러가 중지되었습니다.'})
        else:
            return jsonify({'success': True, 'message': '스케줄러가 이미 중지되어 있습니다.'})
    except Exception as e:
        logger.error(f"❌ 스케줄러 중지 실패: {e}")
        return jsonify({'success': False, 'message': str(e)})

@batch_bp.route('/api/run-erpia', methods=['POST'])
@login_required
def api_run_erpia():
    """ERPia 배치 실행 API"""
    try:
        data_type = request.form.get('type', 'all')
        
        from app.services.erpia_client import ErpiaApiClient
        erpia = ErpiaApiClient()
        
        message = ""
        if data_type == 'orders' or data_type == 'all':
            # 주문 데이터 수집
            orders = erpia.get_order_list()
            message += f"주문 {len(orders)}건 수집 완료. "
            
        if data_type == 'products' or data_type == 'all':
            # 상품 데이터 수집
            products = erpia.get_product_list()
            message += f"상품 {len(products)}건 수집 완료. "
            
        if data_type == 'customers' or data_type == 'all':
            # 고객 데이터 수집
            customers = erpia.get_customer_list()
            message += f"고객 {len(customers)}건 수집 완료. "
        
        return jsonify({'success': True, 'message': message.strip()})
        
    except Exception as e:
        logger.error(f"❌ ERPia 배치 실행 실패: {e}")
        return jsonify({'success': False, 'message': str(e)})

@batch_bp.route('/api/run-gift-classification', methods=['POST'])
@login_required
def api_run_gift_classification():
    """사은품 분류 실행 API"""
    try:
        from app.services.gift_classifier import GiftClassifier
        classifier = GiftClassifier()
        
        # 최근 30일 데이터를 대상으로 분류
        result = classifier.classify_recent_orders(days_back=30)
        
        return jsonify({
            'success': True, 
            'message': f"사은품 분류 완료: {result.get('classified_count', 0)}건 분류됨"
        })
        
    except Exception as e:
        logger.error(f"❌ 사은품 분류 실행 실패: {e}")
        return jsonify({'success': False, 'message': str(e)})

@batch_bp.route('/api/job/run/<job_id>', methods=['POST'])
@login_required
def api_run_job(job_id):
    """작업 즉시 실행 API"""
    try:
        job = batch_scheduler.get_job(job_id)
        if job:
            job.modify(next_run_time=datetime.now())
            return jsonify({'success': True, 'message': '작업이 실행되었습니다.'})
        else:
            return jsonify({'success': False, 'message': '작업을 찾을 수 없습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@batch_bp.route('/api/job/pause/<job_id>', methods=['POST'])
@login_required
def api_pause_job(job_id):
    """작업 일시정지 API"""
    try:
        job = batch_scheduler.get_job(job_id)
        if job:
            batch_scheduler.pause_job(job_id)
            return jsonify({'success': True, 'message': '작업이 일시정지되었습니다.'})
        else:
            return jsonify({'success': False, 'message': '작업을 찾을 수 없습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@batch_bp.route('/api/job/remove/<job_id>', methods=['POST'])
@login_required
def api_remove_job(job_id):
    """작업 삭제 API"""
    try:
        job = batch_scheduler.get_job(job_id)
        if job:
            batch_scheduler.remove_job(job_id)
            return jsonify({'success': True, 'message': '작업이 삭제되었습니다.'})
        else:
            return jsonify({'success': False, 'message': '작업을 찾을 수 없습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}) 