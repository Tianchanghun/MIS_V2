/**
 * UI 헬퍼 라이브러리
 * 공통 UI 컴포넌트 및 유틸리티 함수 제공
 */

const UIHelper = {
    /**
     * 로딩 표시
     */
    showLoading: function(message = '처리 중...') {
        // 기존 로딩 모달이 있으면 메시지만 업데이트
        if ($('#globalLoadingModal').length) {
            $('#loadingMessage').text(message);
            $('#globalLoadingModal').modal('show');
            return;
        }
        
        // 로딩 모달 생성
        const loadingModal = $(`
            <div class="modal fade" id="globalLoadingModal" tabindex="-1" data-bs-backdrop="static" data-bs-keyboard="false">
                <div class="modal-dialog modal-sm modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-body text-center py-4">
                            <div class="spinner-border text-primary mb-3" role="status">
                                <span class="visually-hidden">로딩 중...</span>
                            </div>
                            <div id="loadingMessage" class="text-muted">${message}</div>
                        </div>
                    </div>
                </div>
            </div>
        `);
        
        $('body').append(loadingModal);
        $('#globalLoadingModal').modal('show');
    },
    
    /**
     * 로딩 숨김
     */
    hideLoading: function() {
        try {
            // 모든 가능한 로딩 모달 숨김
            $('#globalLoadingModal').modal('hide');
            
            // 강제로 모달 제거 (혹시 숨겨지지 않는 경우)
            setTimeout(() => {
                $('#globalLoadingModal').remove();
                $('.modal-backdrop').remove();
                $('body').removeClass('modal-open');
                $('body').css('padding-right', '');
            }, 500);
            
            console.log('🔄 로딩 모달 숨김 처리 완료');
        } catch (error) {
            console.error('로딩 숨김 오류:', error);
            // 강제 제거
            $('#globalLoadingModal').remove();
            $('.modal-backdrop').remove();
            $('body').removeClass('modal-open');
            $('body').css('padding-right', '');
        }
    },
    
    /**
     * 알림 메시지 표시
     */
    showAlert: function(message, type = 'info', duration = 5000) {
        const alertClass = {
            'success': 'alert-success',
            'error': 'alert-danger',
            'danger': 'alert-danger',
            'warning': 'alert-warning',
            'info': 'alert-info',
            'primary': 'alert-primary'
        }[type] || 'alert-info';
        
        const iconClass = {
            'success': 'fas fa-check-circle',
            'error': 'fas fa-exclamation-triangle',
            'danger': 'fas fa-exclamation-triangle',
            'warning': 'fas fa-exclamation-circle',
            'info': 'fas fa-info-circle',
            'primary': 'fas fa-info-circle'
        }[type] || 'fas fa-info-circle';
        
        const alertId = 'alert_' + Date.now();
        const alert = $(`
            <div id="${alertId}" class="alert ${alertClass} alert-dismissible fade show position-fixed" 
                 style="top: 20px; right: 20px; z-index: 9999; min-width: 300px; max-width: 500px;">
                <i class="${iconClass} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `);
        
        $('body').append(alert);
        
        // 자동 제거
        if (duration > 0) {
            setTimeout(() => {
                $(`#${alertId}`).fadeOut(300, function() {
                    $(this).remove();
                });
            }, duration);
        }
        
        return alertId;
    },
    
    /**
     * 확인 다이얼로그
     */
    showConfirm: function(title, message, confirmCallback, cancelCallback) {
        return new Promise((resolve) => {
            // 기존 확인 모달 제거
            $('#globalConfirmModal').remove();
            
            const confirmModal = $(`
                <div class="modal fade" id="globalConfirmModal" tabindex="-1">
                    <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">
                                    <i class="fas fa-question-circle text-warning me-2"></i>
                                    ${title}
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                ${message}
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" id="confirmCancel">
                                    <i class="fas fa-times me-1"></i>취소
                                </button>
                                <button type="button" class="btn btn-primary" id="confirmOk">
                                    <i class="fas fa-check me-1"></i>확인
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `);
            
            $('body').append(confirmModal);
            
            // 이벤트 핸들러
            $('#confirmOk').on('click', function() {
                $('#globalConfirmModal').modal('hide');
                resolve(true);
                if (confirmCallback) confirmCallback();
            });
            
            $('#confirmCancel, #globalConfirmModal .btn-close').on('click', function() {
                $('#globalConfirmModal').modal('hide');
                resolve(false);
                if (cancelCallback) cancelCallback();
            });
            
            // 모달 표시
            $('#globalConfirmModal').modal('show');
            
            // 모달이 완전히 숨겨진 후 제거
            $('#globalConfirmModal').on('hidden.bs.modal', function() {
                $(this).remove();
            });
        });
    },
    
    /**
     * 토스트 메시지 (간단한 알림)
     */
    showToast: function(message, type = 'info', duration = 3000) {
        // 토스트 컨테이너가 없으면 생성
        if (!$('#toastContainer').length) {
            $('body').append(`
                <div id="toastContainer" class="toast-container position-fixed top-0 end-0 p-3" style="z-index: 9999;"></div>
            `);
        }
        
        const toastClass = {
            'success': 'text-bg-success',
            'error': 'text-bg-danger',
            'warning': 'text-bg-warning',
            'info': 'text-bg-info'
        }[type] || 'text-bg-info';
        
        const toastId = 'toast_' + Date.now();
        const toast = $(`
            <div id="${toastId}" class="toast ${toastClass}" role="alert">
                <div class="toast-body text-white">
                    ${message}
                    <button type="button" class="btn-close btn-close-white float-end" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `);
        
        $('#toastContainer').append(toast);
        
        // Bootstrap Toast 초기화 및 표시
        const bsToast = new bootstrap.Toast(toast[0], {
            autohide: true,
            delay: duration
        });
        bsToast.show();
        
        // 토스트가 숨겨진 후 제거
        toast.on('hidden.bs.toast', function() {
            $(this).remove();
        });
        
        return toastId;
    },
    
    /**
     * 입력 다이얼로그
     */
    showPrompt: function(title, message, defaultValue = '', placeholder = '') {
        return new Promise((resolve) => {
            // 기존 프롬프트 모달 제거
            $('#globalPromptModal').remove();
            
            const promptModal = $(`
                <div class="modal fade" id="globalPromptModal" tabindex="-1">
                    <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">
                                    <i class="fas fa-edit text-primary me-2"></i>
                                    ${title}
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <p>${message}</p>
                                <input type="text" class="form-control" id="promptInput" 
                                       value="${defaultValue}" placeholder="${placeholder}" />
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" id="promptCancel">
                                    <i class="fas fa-times me-1"></i>취소
                                </button>
                                <button type="button" class="btn btn-primary" id="promptOk">
                                    <i class="fas fa-check me-1"></i>확인
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `);
            
            $('body').append(promptModal);
            
            // 이벤트 핸들러
            $('#promptOk').on('click', function() {
                const value = $('#promptInput').val();
                $('#globalPromptModal').modal('hide');
                resolve(value);
            });
            
            $('#promptCancel, #globalPromptModal .btn-close').on('click', function() {
                $('#globalPromptModal').modal('hide');
                resolve(null);
            });
            
            // Enter 키로 확인
            $('#promptInput').on('keypress', function(e) {
                if (e.which === 13) {
                    $('#promptOk').click();
                }
            });
            
            // 모달 표시 및 입력 필드에 포커스
            $('#globalPromptModal').modal('show');
            $('#globalPromptModal').on('shown.bs.modal', function() {
                $('#promptInput').focus().select();
            });
            
            // 모달이 완전히 숨겨진 후 제거
            $('#globalPromptModal').on('hidden.bs.modal', function() {
                $(this).remove();
            });
        });
    },
    
    /**
     * 진행률 표시
     */
    showProgress: function(title, message = '') {
        // 기존 진행률 모달 제거
        $('#globalProgressModal').remove();
        
        const progressModal = $(`
            <div class="modal fade" id="globalProgressModal" tabindex="-1" data-bs-backdrop="static" data-bs-keyboard="false">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-tasks text-info me-2"></i>
                                ${title}
                            </h5>
                        </div>
                        <div class="modal-body">
                            <div id="progressMessage" class="mb-3">${message}</div>
                            <div class="progress">
                                <div id="progressBar" class="progress-bar progress-bar-striped progress-bar-animated" 
                                     role="progressbar" style="width: 0%">
                                    <span id="progressText">0%</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `);
        
        $('body').append(progressModal);
        $('#globalProgressModal').modal('show');
    },
    
    /**
     * 진행률 업데이트
     */
    updateProgress: function(percent, message = '') {
        if ($('#globalProgressModal').length) {
            $('#progressBar').css('width', percent + '%');
            $('#progressText').text(Math.round(percent) + '%');
            
            if (message) {
                $('#progressMessage').text(message);
            }
        }
    },
    
    /**
     * 진행률 숨김
     */
    hideProgress: function() {
        $('#globalProgressModal').modal('hide');
        setTimeout(() => {
            $('#globalProgressModal').remove();
        }, 300);
    },
    
    /**
     * 버튼 로딩 상태 설정
     */
    setButtonLoading: function(selector, loading, text = '처리 중...') {
        const $btn = $(selector);
        
        if (loading) {
            // 원래 텍스트 저장
            $btn.data('original-text', $btn.html());
            $btn.data('original-disabled', $btn.prop('disabled'));
            
            // 로딩 상태로 변경
            $btn.html(`<span class="spinner-border spinner-border-sm me-2"></span>${text}`)
                .prop('disabled', true);
        } else {
            // 원래 상태로 복원
            const originalText = $btn.data('original-text');
            const originalDisabled = $btn.data('original-disabled');
            
            if (originalText) {
                $btn.html(originalText);
            }
            
            $btn.prop('disabled', originalDisabled || false);
        }
    },
    
    /**
     * 툴팁 초기화
     */
    initTooltips: function(selector = '[data-bs-toggle="tooltip"]') {
        $(selector).each(function() {
            new bootstrap.Tooltip(this);
        });
    },
    
    /**
     * 팝오버 초기화
     */
    initPopovers: function(selector = '[data-bs-toggle="popover"]') {
        $(selector).each(function() {
            new bootstrap.Popover(this);
        });
    },
    
    /**
     * 폼 검증 표시
     */
    showValidationError: function(fieldId, message) {
        const $field = $('#' + fieldId);
        $field.addClass('is-invalid');
        
        // 기존 피드백 제거
        $field.siblings('.invalid-feedback').remove();
        
        // 새 피드백 추가
        $field.after(`<div class="invalid-feedback">${message}</div>`);
    },
    
    /**
     * 폼 검증 초기화
     */
    clearValidation: function(formSelector) {
        $(formSelector).find('.is-invalid').removeClass('is-invalid');
        $(formSelector).find('.invalid-feedback').remove();
    },
    
    /**
     * 숫자 콤마 포맷팅
     */
    formatNumber: function(number) {
        if (number === null || number === undefined || number === '') return '';
        return parseInt(number).toLocaleString();
    },
    
    /**
     * 날짜 포맷팅
     */
    formatDate: function(dateString, format = 'YYYY-MM-DD') {
        if (!dateString) return '';
        
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return '';
        
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        
        switch (format) {
            case 'YYYY-MM-DD':
                return `${year}-${month}-${day}`;
            case 'YYYY-MM-DD HH:mm':
                return `${year}-${month}-${day} ${hours}:${minutes}`;
            case 'MM/DD':
                return `${month}/${day}`;
            case 'Korean':
                return `${year}년 ${month}월 ${day}일`;
            default:
                return date.toLocaleDateString('ko-KR');
        }
    },
    
    /**
     * 디바운스 함수
     */
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func.apply(this, args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    /**
     * 스로틀 함수
     */
    throttle: function(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};

// 페이지 로드 완료 시 공통 초기화
$(document).ready(function() {
    // 툴팁 초기화
    UIHelper.initTooltips();
    
    // 팝오버 초기화
    UIHelper.initPopovers();
    
    console.log('✅ UI Helper 초기화 완료');
}); 