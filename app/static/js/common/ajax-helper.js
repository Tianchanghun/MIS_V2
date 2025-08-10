/**
 * AJAX 헬퍼 함수들
 * 모든 AJAX 요청을 표준화하고 일관된 에러 처리를 제공
 */
const AjaxHelper = {
    // 기본 설정
    defaults: {
        dataType: 'json',
        timeout: 30000,
        cache: false
    },

    // CSRF 토큰 가져오기
    getCSRFToken: function() {
        return $('meta[name=csrf-token]').attr('content') || '';
    },

    // 표준 GET 요청
    get: function(url, data = {}, options = {}) {
        const config = $.extend({}, this.defaults, {
            url: url,
            type: 'GET',
            data: data,
            beforeSend: function() {
                if (options.showLoading !== false) {
                    UIHelper.showLoading(options.loadingMessage);
                }
            },
            complete: function() {
                if (options.showLoading !== false) {
                    UIHelper.hideLoading();
                }
            }
        }, options);

        return $.ajax(config)
            .fail(function(xhr, status, error) {
                AjaxHelper.handleError(xhr, status, error);
            });
    },

    // 표준 POST 요청
    post: function(url, data = {}, options = {}) {
        const config = $.extend({}, this.defaults, {
            url: url,
            type: 'POST',
            data: data,
            headers: {
                'X-CSRFToken': this.getCSRFToken()
            },
            beforeSend: function() {
                if (options.showLoading !== false) {
                    UIHelper.showLoading(options.loadingMessage);
                }
            },
            complete: function() {
                if (options.showLoading !== false) {
                    UIHelper.hideLoading();
                }
            }
        }, options);

        return $.ajax(config)
            .fail(function(xhr, status, error) {
                AjaxHelper.handleError(xhr, status, error);
            });
    },

    // PUT 요청
    put: function(url, data = {}, options = {}) {
        return this.post(url, data, $.extend({type: 'PUT'}, options));
    },

    // DELETE 요청
    delete: function(url, data = {}, options = {}) {
        return this.post(url, data, $.extend({type: 'DELETE'}, options));
    },

    // 파일 업로드 (FormData)
    upload: function(url, formData, options = {}) {
        const config = $.extend({}, {
            url: url,
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            headers: {
                'X-CSRFToken': this.getCSRFToken()
            },
            beforeSend: function() {
                UIHelper.showLoading('파일 업로드 중...');
            },
            complete: function() {
                UIHelper.hideLoading();
            }
        }, options);

        return $.ajax(config)
            .fail(function(xhr, status, error) {
                AjaxHelper.handleError(xhr, status, error);
            });
    },

    // 공통 에러 처리
    handleError: function(xhr, status, error) {
        console.error('AJAX 요청 실패:', {xhr, status, error});
        
        let message = '요청 처리 중 오류가 발생했습니다.';
        
        if (xhr.status === 0) {
            message = '네트워크 연결을 확인해주세요.';
        } else if (xhr.status === 404) {
            message = '요청한 페이지를 찾을 수 없습니다.';
        } else if (xhr.status === 500) {
            message = '서버 내부 오류가 발생했습니다.';
        } else if (xhr.status === 403) {
            message = '접근 권한이 없습니다.';
        } else if (xhr.responseJSON && xhr.responseJSON.message) {
            message = xhr.responseJSON.message;
        }

        UIHelper.showAlert(message, 'error');
    }
}; 