/**
 * UI 컴포넌트 헬퍼 함수들
 * 일관된 UI 경험을 제공하는 공통 컴포넌트들
 */
const UIHelper = {
    // 전역 로딩 모달 표시
    showLoading: function(message = '처리 중...') {
        // 기존 로딩 모달 제거
        $('#globalLoadingModal').remove();
        
        const loadingModal = $(`
            <div class="modal fade" id="globalLoadingModal" tabindex="-1" data-bs-backdrop="static" data-bs-keyboard="false">
                <div class="modal-dialog modal-sm modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-body text-center py-4">
                            <div class="spinner-border text-primary mb-3" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <div id="globalLoadingMessage">${message}</div>
                        </div>
                    </div>
                </div>
            </div>
        `);
        
        $('body').append(loadingModal);
        $('#globalLoadingModal').modal('show');
    },

    // 로딩 모달 숨김
    hideLoading: function() {
        $('#globalLoadingModal').modal('hide');
        setTimeout(() => $('#globalLoadingModal').remove(), 300);
    },

    // 로딩 메시지 업데이트
    updateLoadingMessage: function(message) {
        $('#globalLoadingMessage').text(message);
    },

    // 표준 알림 표시
    showAlert: function(message, type = 'info', autoHide = true) {
        // 알림 컨테이너 확인 및 생성
        if (!$('#alertContainer').length) {
            $('body').prepend('<div id="alertContainer" style="position: fixed; top: 20px; right: 20px; z-index: 10000; width: 350px;"></div>');
        }

        const alertClass = {
            'success': 'alert-success',
            'error': 'alert-danger',
            'warning': 'alert-warning',
            'info': 'alert-info'
        }[type] || 'alert-info';

        const alertIcon = {
            'success': 'fas fa-check-circle',
            'error': 'fas fa-exclamation-triangle',
            'warning': 'fas fa-exclamation-circle',
            'info': 'fas fa-info-circle'
        }[type] || 'fas fa-info-circle';

        const alert = $(`
            <div class="alert ${alertClass} alert-dismissible fade show shadow" role="alert">
                <i class="${alertIcon} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `);

        $('#alertContainer').append(alert);

        // 자동 숨김
        if (autoHide) {
            setTimeout(() => {
                alert.alert('close');
            }, type === 'error' ? 8000 : 5000);
        }

        return alert;
    },

    // 확인 대화상자
    showConfirm: function(title, message, callback, options = {}) {
        const modalId = 'confirmModal_' + Date.now();
        const modal = $(`
            <div class="modal fade" id="${modalId}" tabindex="-1">
                <div class="modal-dialog ${options.size || 'modal-sm'}">
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
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                ${options.cancelText || '취소'}
                            </button>
                            <button type="button" class="btn btn-primary confirm-yes">
                                ${options.confirmText || '확인'}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `);

        $('body').append(modal);
        
        modal.find('.confirm-yes').on('click', function() {
            modal.modal('hide');
            if (callback) callback(true);
        });

        modal.on('hidden.bs.modal', function() {
            $(this).remove();
        });

        modal.modal('show');
    },

    // 입력 대화상자
    showPrompt: function(title, message, callback, options = {}) {
        const modalId = 'promptModal_' + Date.now();
        const modal = $(`
            <div class="modal fade" id="${modalId}" tabindex="-1">
                <div class="modal-dialog">
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
                                   placeholder="${options.placeholder || ''}" 
                                   value="${options.defaultValue || ''}">
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">취소</button>
                            <button type="button" class="btn btn-primary prompt-ok">확인</button>
                        </div>
                    </div>
                </div>
            </div>
        `);

        $('body').append(modal);
        
        modal.find('.prompt-ok').on('click', function() {
            const value = modal.find('#promptInput').val();
            modal.modal('hide');
            if (callback) callback(value);
        });

        modal.on('shown.bs.modal', function() {
            modal.find('#promptInput').focus();
        });

        modal.on('hidden.bs.modal', function() {
            $(this).remove();
        });

        modal.modal('show');
    },

    // 테이블 로딩 상태
    showTableLoading: function(tableSelector, message = '데이터를 불러오는 중...') {
        const $table = $(tableSelector);
        const $tbody = $table.find('tbody');
        const colCount = $table.find('thead th').length;
        
        $tbody.html(`
            <tr>
                <td colspan="${colCount}" class="text-center py-4">
                    <div class="spinner-border text-primary mb-2" role="status"></div>
                    <div>${message}</div>
                </td>
            </tr>
        `);
    },

    // 테이블 빈 상태
    showTableEmpty: function(tableSelector, message = '데이터가 없습니다.') {
        const $table = $(tableSelector);
        const $tbody = $table.find('tbody');
        const colCount = $table.find('thead th').length;
        
        $tbody.html(`
            <tr>
                <td colspan="${colCount}" class="text-center py-4 text-muted">
                    <i class="fas fa-inbox fa-2x mb-2"></i>
                    <div>${message}</div>
                </td>
            </tr>
        `);
    },

    // 폼 비활성화/활성화
    toggleForm: function(formSelector, disabled = true) {
        const $form = $(formSelector);
        $form.find('input, select, textarea, button').prop('disabled', disabled);
        
        if (disabled) {
            $form.addClass('form-disabled');
        } else {
            $form.removeClass('form-disabled');
        }
    },

    // 버튼 로딩 상태
    setButtonLoading: function(buttonSelector, loading = true, text = '처리 중...') {
        const $btn = $(buttonSelector);
        
        if (loading) {
            $btn.data('original-text', $btn.html());
            $btn.html(`<span class="spinner-border spinner-border-sm me-2"></span>${text}`);
            $btn.prop('disabled', true);
        } else {
            $btn.html($btn.data('original-text') || $btn.html());
            $btn.prop('disabled', false);
        }
    }
}; 