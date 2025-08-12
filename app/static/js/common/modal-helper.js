/**
 * 🎨 AdminLTE 3 모달 헬퍼
 * 모든 시스템에서 통일된 모달 관리를 위한 유틸리티
 * 
 * @author MIS v2.0 Team
 * @version 1.0.0
 */

// 모달 헬퍼 클래스
class ModalHelper {
    /**
     * 통일된 모달 열기
     * @param {string} modalId - 모달 ID
     * @param {Object} options - 모달 옵션
     * @returns {bootstrap.Modal|null} 모달 인스턴스
     */
    static show(modalId, options = {}) {
        const modalElement = document.getElementById(modalId);
        if (!modalElement) {
            console.error(`❌ 모달을 찾을 수 없습니다: ${modalId}`);
            return null;
        }
        
        // 기존 인스턴스 정리
        const existingModal = bootstrap.Modal.getInstance(modalElement);
        if (existingModal) {
            existingModal.dispose();
        }
        
        // 새 인스턴스 생성
        const modal = new bootstrap.Modal(modalElement, {
            backdrop: options.backdrop || 'static',
            keyboard: options.keyboard || false,
            focus: options.focus !== false
        });
        
        // 이벤트 리스너 추가
        if (options.onShow) {
            modalElement.addEventListener('shown.bs.modal', options.onShow, { once: true });
        }
        if (options.onHide) {
            modalElement.addEventListener('hidden.bs.modal', options.onHide, { once: true });
        }
        
        // 모달 표시
        modal.show();
        
        console.log(`✅ 모달 열기 성공: ${modalId}`);
        return modal;
    }
    
    /**
     * 통일된 모달 닫기
     * @param {string} modalId - 모달 ID
     */
    static hide(modalId) {
        const modalElement = document.getElementById(modalId);
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) {
            modal.hide();
            console.log(`✅ 모달 닫기 성공: ${modalId}`);
        }
    }
    
    /**
     * 모달 제목 변경
     * @param {string} modalId - 모달 ID
     * @param {string} title - 새 제목
     * @param {string|null} icon - 아이콘 클래스
     */
    static setTitle(modalId, title, icon = null) {
        const titleElement = document.getElementById(`${modalId}Title`);
        if (titleElement) {
            let html = '';
            if (icon) {
                html += `<i class="${icon} me-2"></i>`;
            }
            html += title;
            titleElement.innerHTML = html;
        }
    }
    
    /**
     * 모달 바디 내용 변경
     * @param {string} modalId - 모달 ID
     * @param {string} content - HTML 내용
     */
    static setBody(modalId, content) {
        const modal = document.getElementById(modalId);
        const bodyElement = modal?.querySelector('.modal-body');
        if (bodyElement) {
            bodyElement.innerHTML = content;
        }
    }
    
    /**
     * 로딩 상태 표시
     * @param {string} modalId - 모달 ID
     * @param {string} message - 로딩 메시지
     */
    static showLoading(modalId, message = '처리 중...') {
        const modal = document.getElementById(modalId);
        const bodyElement = modal?.querySelector('.modal-body');
        const footerElement = modal?.querySelector('.modal-footer');
        
        if (bodyElement) {
            bodyElement.innerHTML = `
                <div class="text-center py-4">
                    <div class="spinner-border text-primary mb-3" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div class="text-muted">${message}</div>
                </div>
            `;
        }
        
        if (footerElement) {
            footerElement.style.display = 'none';
        }
    }
    
    /**
     * 에러 상태 표시
     * @param {string} modalId - 모달 ID
     * @param {string} message - 에러 메시지
     */
    static showError(modalId, message = '오류가 발생했습니다.') {
        const modal = document.getElementById(modalId);
        const bodyElement = modal?.querySelector('.modal-body');
        
        if (bodyElement) {
            bodyElement.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${message}
                </div>
            `;
        }
    }
    
    /**
     * 성공 메시지 표시
     * @param {string} modalId - 모달 ID
     * @param {string} message - 성공 메시지
     */
    static showSuccess(modalId, message = '성공적으로 처리되었습니다.') {
        const modal = document.getElementById(modalId);
        const bodyElement = modal?.querySelector('.modal-body');
        
        if (bodyElement) {
            bodyElement.innerHTML = `
                <div class="alert alert-success" role="alert">
                    <i class="fas fa-check-circle me-2"></i>
                    ${message}
                </div>
            `;
        }
    }
    
    /**
     * 확인 다이얼로그 표시
     * @param {Object} options - 옵션
     * @returns {Promise<boolean>} 사용자 선택 결과
     */
    static async confirm(options = {}) {
        const {
            title = '확인',
            message = '정말로 실행하시겠습니까?',
            confirmText = '확인',
            cancelText = '취소',
            icon = 'fas fa-question-circle',
            type = 'warning' // success, danger, warning, info
        } = options;
        
        return new Promise((resolve) => {
            // 확인 모달 HTML 생성
            const modalId = 'confirmModal';
            const modalHtml = `
                <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true" data-bs-backdrop="static">
                    <div class="modal-dialog modal-sm">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">
                                    <i class="${icon} me-2"></i>${title}
                                </h5>
                            </div>
                            <div class="modal-body">
                                <div class="alert alert-${type} mb-0">
                                    ${message}
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                    <i class="fas fa-times me-1"></i>${cancelText}
                                </button>
                                <button type="button" class="btn btn-${type === 'danger' ? 'danger' : 'primary'}" id="confirmBtn">
                                    <i class="fas fa-check me-1"></i>${confirmText}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // 기존 확인 모달 제거
            const existingModal = document.getElementById(modalId);
            if (existingModal) {
                existingModal.remove();
            }
            
            // 새 모달 추가
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            const modalElement = document.getElementById(modalId);
            
            // 이벤트 리스너 추가
            modalElement.querySelector('#confirmBtn').addEventListener('click', () => {
                bootstrap.Modal.getInstance(modalElement).hide();
                resolve(true);
            });
            
            modalElement.addEventListener('hidden.bs.modal', () => {
                modalElement.remove();
                resolve(false);
            });
            
            // 모달 표시
            new bootstrap.Modal(modalElement).show();
        });
    }
    
    /**
     * 알림 다이얼로그 표시
     * @param {string} message - 메시지
     * @param {string} type - 타입 (success, danger, warning, info)
     * @param {string} title - 제목
     */
    static alert(message, type = 'info', title = '알림') {
        const iconMap = {
            success: 'fas fa-check-circle',
            danger: 'fas fa-exclamation-triangle',
            warning: 'fas fa-exclamation',
            info: 'fas fa-info-circle'
        };
        
        const modalId = 'alertModal';
        const modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-sm">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="${iconMap[type]} me-2"></i>${title}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="alert alert-${type} mb-0">
                                ${message}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-primary" data-bs-dismiss="modal">
                                <i class="fas fa-check me-1"></i>확인
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 기존 알림 모달 제거
        const existingModal = document.getElementById(modalId);
        if (existingModal) {
            existingModal.remove();
        }
        
        // 새 모달 추가 및 표시
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modalElement = document.getElementById(modalId);
        
        modalElement.addEventListener('hidden.bs.modal', () => {
            modalElement.remove();
        });
        
        new bootstrap.Modal(modalElement).show();
    }
}

// 전역으로 등록
window.ModalHelper = ModalHelper;

// 편의 함수들
window.showModal = (modalId, options) => ModalHelper.show(modalId, options);
window.hideModal = (modalId) => ModalHelper.hide(modalId);
window.confirmModal = (options) => ModalHelper.confirm(options);
window.alertModal = (message, type, title) => ModalHelper.alert(message, type, title);

console.log('✅ AdminLTE 3 모달 헬퍼 로드 완료'); 