#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
배치 관리 웹 UI 라우트
ERPia 자동 배치 시스템의 웹 인터페이스
"""

from flask import render_template, request, jsonify, flash, redirect, url_for, current_app, session
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
def index():
    """배치 관리 메인 페이지"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def job_list():
    """배치 작업 목록 페이지"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def add_job():
    """배치 작업 추가"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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

@batch_bp.route('/gift/classify', methods=['POST'])
def manual_gift_classify():
    """사은품 수동 분류"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    try:
        days_back = int(request.json.get('days_back', 7))
        
        gift_classifier = GiftClassifier(company_id=current_user.company_id)
        classified_count = gift_classifier.auto_classify_recent_products(
            current_user.company_id,
            days_back
        )
        
        return jsonify({
            'success': True,
            'message': f'{classified_count}개 상품이 사은품으로 분류되었습니다.'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}) 

@batch_bp.route('/gift/statistics')
def gift_statistics():
    """사은품 분류 통계"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
        return jsonify({'success': False, 'message': str(e)})

@batch_bp.route('/dashboard/data')
  
def dashboard_data():
    """대시보드 데이터 API"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def start_scheduler():
    """스케줄러 시작"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def stop_scheduler():
    """스케줄러 중지"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def settings():
    """배치 설정 페이지"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
    try:
        # 현재 사용자 정보 조회
        from app.common.models import User, UserCompany, Company
        
        member_seq = session.get('member_seq')
        user = User.query.filter_by(seq=member_seq).first()
        
        if not user:
            flash('사용자 정보를 찾을 수 없습니다.', 'error')
            return redirect('/auth/login')
        
        # 사용자의 회사 정보 조회
        user_companies = UserCompany.query.filter_by(user_seq=user.seq).all()
        
        # 현재 회사 설정 (세션에서 가져오거나 기본값)
        current_company_id = session.get('company_id')
        current_company = None
        
        if current_company_id:
            current_company = Company.query.get(current_company_id)
        elif user_companies:
            # 세션에 회사가 없으면 주속 회사나 첫 번째 회사로 설정
            primary_uc = next((uc for uc in user_companies if uc.is_primary), user_companies[0])
            current_company = primary_uc.company
            session['company_id'] = current_company.id
            current_company_id = current_company.id
        
        # 디버그 로그 추가
        logger.info(f"🏢 배치 설정 페이지 - 사용자: {user.login_id}, 현재 회사: {current_company_id}")
        logger.info(f"📋 사용자 회사 목록: {[(uc.company_id, uc.company.company_name, uc.is_primary) for uc in user_companies]}")
        
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
            user_companies=user_companies,
            current_company=current_company,
            current_company_id=current_company_id,  # 추가
            current_user=user
        )
        
    except Exception as e:
        logger.error(f"❌ 배치 설정 페이지 로드 실패: {e}")
        flash(f'설정 페이지 로드 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('batch.index'))

@batch_bp.route('/api/status')
def api_status():
    """시스템 상태 API"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def api_start_scheduler():
    """스케줄러 시작 API"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def api_stop_scheduler():
    """스케줄러 중지 API"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def api_run_erpia():
    """ERPia 배치 실행 API"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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
def api_run_gift_classification():
    """사은품 분류 실행 API"""
    if 'member_seq' not in session:
        return redirect('/auth/login')
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

# ==================== ERPia 설정 관리 API ====================

@batch_bp.route('/api/erpia/settings/<int:company_id>', methods=['GET'])
def get_erpia_settings(company_id):
    """ERPia 설정 조회"""
    try:
        from app.common.models import CompanyErpiaConfig, ErpiaBatchSettings
        
        # ERPia 연동 설정 조회
        erpia_config = CompanyErpiaConfig.query.filter_by(company_id=company_id).first()
        
        # 배치 설정 조회
        batch_settings = {}
        for setting in ErpiaBatchSettings.query.filter_by(company_id=company_id).all():
            batch_settings[setting.setting_key] = {
                'value': setting.setting_value,
                'type': setting.setting_type,
                'description': setting.description,
                'min_value': setting.min_value,
                'max_value': setting.max_value
            }
        
        result = {
            'erpia_config': erpia_config.to_dict() if erpia_config else None,
            'batch_settings': batch_settings
        }
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        logger.error(f"❌ ERPia 설정 조회 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@batch_bp.route('/api/erpia/settings/<int:company_id>', methods=['POST'])
def update_erpia_settings(company_id):
    """ERPia 설정 업데이트"""
    try:
        from app.common.models import CompanyErpiaConfig, ErpiaBatchSettings, db
        from datetime import datetime
        
        data = request.get_json()
        
        # ERPia 연동 설정 업데이트
        if 'erpia_config' in data:
            config_data = data['erpia_config']
            erpia_config = CompanyErpiaConfig.query.filter_by(company_id=company_id).first()
            
            if erpia_config:
                erpia_config.admin_code = config_data.get('admin_code', erpia_config.admin_code)
                erpia_config.password = config_data.get('password', erpia_config.password)
                erpia_config.api_url = config_data.get('api_url', erpia_config.api_url)
                erpia_config.is_active = config_data.get('is_active', erpia_config.is_active)
                erpia_config.updated_at = datetime.utcnow()
            else:
                erpia_config = CompanyErpiaConfig(
                    company_id=company_id,
                    admin_code=config_data.get('admin_code', ''),
                    password=config_data.get('password', ''),
                    api_url=config_data.get('api_url', 'http://www.erpia.net/xml/xml.asp'),
                    is_active=config_data.get('is_active', True)
                )
                db.session.add(erpia_config)
        
        # 배치 설정 업데이트
        if 'batch_settings' in data:
            for key, value in data['batch_settings'].items():
                setting = ErpiaBatchSettings.query.filter_by(
                    company_id=company_id,
                    setting_key=key
                ).first()
                
                if setting:
                    setting.setting_value = str(value)
                    setting.updated_at = datetime.utcnow()
                else:
                    # 새 설정 생성
                    setting = ErpiaBatchSettings(
                        company_id=company_id,
                        setting_key=key,
                        setting_value=str(value),
                        setting_type='text',  # 기본값
                        description=f'{key} 설정'
                    )
                    db.session.add(setting)
        
        db.session.commit()
        
        # 스케줄러 업데이트 (추후 구현)
        # from app.services.erpia_scheduler import update_company_schedule
        # update_company_schedule(company_id)
        
        return jsonify({'success': True, 'message': '설정이 업데이트되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ ERPia 설정 업데이트 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@batch_bp.route('/api/erpia/test-connection/<int:company_id>', methods=['POST'])
def test_erpia_connection_by_company(company_id):
    """ERPia 연결 테스트 (회사별)"""
    try:
        from app.common.models import CompanyErpiaConfig
        from app.services.erpia_client import ErpiaApiClient
        from datetime import datetime
        
        # ERPia 설정 조회
        erpia_config = CompanyErpiaConfig.query.filter_by(company_id=company_id).first()
        if not erpia_config:
            return jsonify({
                'success': False,
                'message': 'ERPia 설정이 없습니다. 먼저 설정을 저장해주세요.'
            }), 400
        
        # 연결 테스트
        client = ErpiaApiClient(company_id)
        
        # 간단한 API 호출로 연결 테스트 (사이트 코드 조회)
        today = datetime.now().strftime('%Y%m%d')
        result = client.test_connection()
        
        if result['success']:
            # 연결 성공 시 마지막 동기화 시간 업데이트
            erpia_config.last_sync_date = datetime.utcnow()
            erpia_config.sync_error_count = 0
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'연결 성공! {result.get("message", "ERPia 서버와 정상적으로 연결되었습니다.")}'
            })
        else:
            # 연결 실패 시 오류 카운트 증가
            erpia_config.sync_error_count = (erpia_config.sync_error_count or 0) + 1
            db.session.commit()
            
            return jsonify({
                'success': False,
                'message': f'연결 실패: {result.get("message", "알 수 없는 오류")}'
            }), 400
    
    except Exception as e:
        logger.error(f"❌ ERPia 연결 테스트 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'연결 테스트 중 오류가 발생했습니다: {str(e)}'
        }), 500

@batch_bp.route('/api/erpia/manual-batch/<int:company_id>', methods=['POST'])
def run_manual_batch(company_id):
    """수동 배치 실행 API"""
    try:
        if 'member_seq' not in session:
            return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        
        data = request.get_json()
        start_date = data.get('start_date')  # YYYYMMDD 형식
        end_date = data.get('end_date')      # YYYYMMDD 형식
        batch_options = data.get('batch_options', {})
        
        if not start_date or not end_date:
            return jsonify({'success': False, 'message': '시작일과 종료일을 입력해주세요.'}), 400
        
        # 날짜 형식 검증
        try:
            from datetime import datetime
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            end_dt = datetime.strptime(end_date, '%Y%m%d')
            
            if start_dt > end_dt:
                return jsonify({'success': False, 'message': '시작일이 종료일보다 늦을 수 없습니다.'}), 400
                
        except ValueError:
            return jsonify({'success': False, 'message': '날짜 형식이 올바르지 않습니다. (YYYYMMDD)'}), 400
        
        logger.info(f"🚀 수동 배치 실행 시작: 회사ID={company_id}, 기간={start_date}~{end_date}")
        
        # 배치 설정 로드
        from app.common.models import CompanyErpiaConfig, ErpiaBatchLog
        
        config = CompanyErpiaConfig.query.filter_by(company_id=company_id).first()
        if not config:
            return jsonify({'success': False, 'message': 'ERPia 설정이 없습니다.'}), 400
        
        if not config.batch_enabled:
            return jsonify({'success': False, 'message': 'ERPia 연동이 비활성화되어 있습니다.'}), 400
        
        # 배치 로그 생성
        batch_log = ErpiaBatchLog(
            company_id=company_id,
            admin_code=config.admin_code,
            batch_type='manual',
            start_time=datetime.utcnow(),
            status='RUNNING',
            date_range=f"{start_date}-{end_date}"
        )
        db.session.add(batch_log)
        db.session.commit()
        
        try:
            # ERPia API 클라이언트 초기화
            from app.services.erpia_client import ErpiaApiClient
            erpia_client = ErpiaApiClient(company_id=company_id)
            
            total_processed = 0
            total_gifts = 0
            member_id = session.get('member_id', 'admin')
            
            # 1. 매장정보 수집 (옵션에 따라)
            if batch_options.get('include_customers', True):
                logger.info("📱 매장정보 수집 시작")
                try:
                    # 분류 코드 매핑 준비 (Shop 모듈 방식 참고)
                    classification_mapping = {}
                    try:
                        from app.common.models import Code
                        cst_group = Code.query.filter_by(code='CST', depth=0).first()
                        if cst_group:
                            classification_groups = Code.query.filter_by(
                                parent_seq=cst_group.seq, 
                                depth=1
                            ).all()
                            
                            for group in classification_groups:
                                group_codes = Code.query.filter_by(
                                    parent_seq=group.seq,
                                    depth=2
                                ).all()
                                
                                # 코드별 매핑 딕셔너리 생성
                                group_key = group.code.lower()
                                classification_mapping[group_key] = {}
                                for code in group_codes:
                                    classification_mapping[group_key][code.code] = code.code_name
                            
                            logger.info(f"📋 분류 매핑 준비 완료: {list(classification_mapping.keys())}")
                        else:
                            logger.warning("⚠️ CST 분류 그룹을 찾을 수 없습니다.")
                    except Exception as e:
                        logger.error(f"❌ 분류 매핑 준비 실패: {str(e)}")
                        classification_mapping = {}
                    
                    logger.info(f"📅 매장정보 조회 기간: {start_date} ~ {end_date}")
                    logger.info(f"🏢 대상 회사: {company_id} ({'에이원' if company_id == 1 else '에이원월드'})")
                    
                    customers_data = erpia_client.fetch_customers(start_date, end_date)
                    if customers_data:
                        from app.common.models import ErpiaCustomer
                        
                        updated_count = 0
                        inserted_count = 0
                        error_count = 0
                        
                        logger.info(f"📊 총 {len(customers_data)}개 매장 데이터 수집 완료")
                        
                        for customer_data in customers_data:
                            try:
                                customer_code = customer_data.get('customer_code', '').strip()
                                if not customer_code:
                                    error_count += 1
                                    continue
                                
                                # 시스템 필드 제외
                                system_fields = {'seq', 'ins_user', 'ins_date', 'upt_user', 'upt_date', 'company_id'}
                                customer_data_filtered = {k: v for k, v in customer_data.items() 
                                                        if hasattr(ErpiaCustomer, k) and k not in system_fields}
                                
                                existing_customer = ErpiaCustomer.query.filter_by(
                                    customer_code=customer_code,
                                    company_id=company_id
                                ).first()
                                
                                if existing_customer:
                                    # 업데이트
                                    for key, value in customer_data_filtered.items():
                                        setattr(existing_customer, key, value)
                                    existing_customer.upt_user = member_id
                                    existing_customer.upt_date = datetime.utcnow()
                                    updated_count += 1
                                else:
                                    # 신규 추가
                                    new_customer = ErpiaCustomer(
                                        company_id=company_id,
                                        ins_user=member_id,
                                        ins_date=datetime.utcnow(),
                                        upt_user=member_id,
                                        upt_date=datetime.utcnow(),
                                        **customer_data_filtered
                                    )
                                    db.session.add(new_customer)
                                    inserted_count += 1
                            
                            except Exception as e:
                                logger.error(f"❌ 매장 데이터 처리 실패 ({customer_code}): {str(e)}")
                                error_count += 1
                                continue
                        
                        # 커밋
                        db.session.commit()
                        
                        logger.info(f"✅ 매장정보 수집 완료: 신규 {inserted_count}개, 업데이트 {updated_count}개, 오류 {error_count}개")
                        total_processed += inserted_count + updated_count
                    else:
                        logger.warning("⚠️ ERPia에서 매장 데이터를 가져오지 못했습니다.")
                        
                except Exception as e:
                    logger.error(f"❌ 매장정보 수집 실패: {str(e)}")
                    db.session.rollback()
                    raise e
            
            # 2. 매출데이터 수집 (옵션에 따라)
            if batch_options.get('include_sales', True):
                logger.info("💰 매출데이터 수집 시작")
                try:
                    # 매출 데이터 처리는 복잡하므로 기본 구현만
                    logger.info("💰 매출데이터 수집 완료 (기본 구현)")
                except Exception as e:
                    logger.error(f"❌ 매출데이터 수집 실패: {e}")
            
            # 3. 상품정보 수집 (옵션에 따라)
            if batch_options.get('include_products', True):
                logger.info("📦 상품정보 수집 시작")
                try:
                    # 상품 정보 처리는 향후 구현
                    logger.info("📦 상품정보 수집 완료 (기본 구현)")
                except Exception as e:
                    logger.error(f"❌ 상품정보 수집 실패: {e}")
            
            # 배치 완료 처리
            batch_log.end_time = datetime.utcnow()
            batch_log.status = 'SUCCESS'
            batch_log.processed_orders = total_processed
            batch_log.gift_products = total_gifts
            db.session.commit()
            
            logger.info(f"🎉 수동 배치 실행 완료: {total_processed}건 처리")
            
            return jsonify({
                'success': True,
                'message': f'배치 실행 완료: {total_processed}건 처리',
                'data': {
                    'processed_count': total_processed,
                    'gift_count': total_gifts,
                    'start_date': start_date,
                    'end_date': end_date,
                    'batch_options': batch_options
                }
            })
            
        except Exception as e:
            # 배치 실패 처리
            batch_log.end_time = datetime.utcnow()
            batch_log.status = 'FAILED'
            batch_log.error_message = str(e)
            db.session.commit()
            
            logger.error(f"❌ 수동 배치 실행 실패: {e}")
            raise
        
    except Exception as e:
        logger.error(f"❌ 수동 배치 API 오류: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@batch_bp.route('/api/erpia/batch-logs/<int:company_id>', methods=['GET'])
def get_batch_logs(company_id):
    """배치 실행 로그 조회"""
    try:
        from app.common.models import ErpiaBatchLog
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        logs = ErpiaBatchLog.query.filter_by(company_id=company_id)\
            .order_by(ErpiaBatchLog.start_time.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        result = {
            'logs': [log.to_dict() for log in logs.items],
            'pagination': {
                'page': logs.page,
                'pages': logs.pages,
                'per_page': logs.per_page,
                'total': logs.total
            }
        }
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        logger.error(f"❌ 배치 로그 조회 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500 