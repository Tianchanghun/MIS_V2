/**
 * AJAX 헬퍼 라이브러리
 * 표준화된 AJAX 요청 처리
 */

const AjaxHelper = {
    /**
     * 기본 설정
     */
    defaults: {
        timeout: 30000,
        dataType: 'json',
        cache: false
    },

    /**
     * CSRF 토큰 가져오기
     */
    getCsrfToken: function() {
        return $('meta[name=csrf-token]').attr('content') || 
               $('input[name=csrf_token]').val() || '';
    },

    /**
     * 공통 헤더 설정
     */
    getCommonHeaders: function() {
        const headers = {
            'X-Requested-With': 'XMLHttpRequest'
        };
        
        const csrfToken = this.getCsrfToken();
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }
        
        return headers;
    },

    /**
     * 기본 AJAX 설정
     */
    getBaseConfig: function(options = {}) {
        return $.extend({}, this.defaults, {
            headers: this.getCommonHeaders(),
            beforeSend: function(xhr, settings) {
                // 기본 로딩 표시
                if (options.showLoading !== false) {
                    UIHelper.showLoading();
                }
                
                // 사용자 정의 beforeSend 콜백
                if (options.beforeSend) {
                    options.beforeSend(xhr, settings);
                }
            },
            complete: function(xhr, textStatus) {
                // 기본 로딩 숨김
                if (options.showLoading !== false) {
                    UIHelper.hideLoading();
                }
                
                // 사용자 정의 complete 콜백
                if (options.complete) {
                    options.complete(xhr, textStatus);
                }
            }
        }, options);
    },

    /**
     * GET 요청
     */
    get: function(url, data = {}, options = {}) {
        const config = this.getBaseConfig(options);
        config.url = url;
        config.type = 'GET';
        config.data = data;
        
        return new Promise((resolve, reject) => {
            $.ajax(config)
                .done((response) => {
                    this.handleResponse(response, resolve, reject);
                })
                .fail((xhr, textStatus, errorThrown) => {
                    this.handleError(xhr, textStatus, errorThrown, reject);
                });
        });
    },

    /**
     * POST 요청
     */
    post: function(url, data = {}, options = {}) {
        const config = this.getBaseConfig(options);
        config.url = url;
        config.type = 'POST';
        
        // FormData 처리
        if (data instanceof FormData) {
            config.data = data;
            config.processData = false;
            config.contentType = false;
        } else {
            config.data = data;
        }
        
        return new Promise((resolve, reject) => {
            $.ajax(config)
                .done((response) => {
                    this.handleResponse(response, resolve, reject);
                })
                .fail((xhr, textStatus, errorThrown) => {
                    this.handleError(xhr, textStatus, errorThrown, reject);
                });
        });
    },

    /**
     * PUT 요청
     */
    put: function(url, data = {}, options = {}) {
        const config = this.getBaseConfig(options);
        config.url = url;
        config.type = 'PUT';
        config.data = data;
        
        return new Promise((resolve, reject) => {
            $.ajax(config)
                .done((response) => {
                    this.handleResponse(response, resolve, reject);
                })
                .fail((xhr, textStatus, errorThrown) => {
                    this.handleError(xhr, textStatus, errorThrown, reject);
                });
        });
    },

    /**
     * DELETE 요청
     */
    delete: function(url, options = {}) {
        const config = this.getBaseConfig(options);
        config.url = url;
        config.type = 'DELETE';
        
        return new Promise((resolve, reject) => {
            $.ajax(config)
                .done((response) => {
                    this.handleResponse(response, resolve, reject);
                })
                .fail((xhr, textStatus, errorThrown) => {
                    this.handleError(xhr, textStatus, errorThrown, reject);
                });
        });
    },

    /**
     * 파일 업로드
     */
    upload: function(url, file, options = {}) {
        const formData = new FormData();
        formData.append('file', file);
        
        // 추가 데이터가 있으면 FormData에 추가
        if (options.data) {
            Object.keys(options.data).forEach(key => {
                formData.append(key, options.data[key]);
            });
        }
        
        const config = this.getBaseConfig(options);
        config.url = url;
        config.type = 'POST';
        config.data = formData;
        config.processData = false;
        config.contentType = false;
        
        // 업로드 진행률 표시
        if (options.progress) {
            config.xhr = function() {
                const xhr = new window.XMLHttpRequest();
                xhr.upload.addEventListener('progress', function(evt) {
                    if (evt.lengthComputable) {
                        const percentComplete = (evt.loaded / evt.total) * 100;
                        options.progress(percentComplete);
                    }
                });
                return xhr;
            };
        }
        
        return new Promise((resolve, reject) => {
            $.ajax(config)
                .done((response) => {
                    this.handleResponse(response, resolve, reject);
                })
                .fail((xhr, textStatus, errorThrown) => {
                    this.handleError(xhr, textStatus, errorThrown, reject);
                });
        });
    },

    /**
     * 응답 처리
     */
    handleResponse: function(response, resolve, reject) {
        // JSON 문자열인 경우 파싱
        if (typeof response === 'string') {
            try {
                response = JSON.parse(response);
            } catch (e) {
                // JSON이 아닌 경우 그대로 사용
            }
        }
        
        // 서버에서 에러 응답을 보낸 경우
        if (response && response.success === false) {
            console.warn('서버 에러:', response.message || '알 수 없는 오류');
            reject(new Error(response.message || '서버에서 오류가 발생했습니다'));
            return;
        }
        
        resolve(response);
    },

    /**
     * 에러 처리
     */
    handleError: function(xhr, textStatus, errorThrown, reject) {
        let errorMessage = '요청 처리 중 오류가 발생했습니다';
        
        // 🔥 상세한 오류 정보 로깅
        console.group('❌ AJAX 오류 상세 정보');
        console.log('HTTP Status:', xhr.status);
        console.log('Status Text:', xhr.statusText);
        console.log('Text Status:', textStatus);
        console.log('Error Thrown:', errorThrown);
        console.log('Response Text:', xhr.responseText);
        console.log('Ready State:', xhr.readyState);
        console.groupEnd();
        
        // HTTP 상태 코드별 메시지
        switch (xhr.status) {
            case 400:
                errorMessage = '잘못된 요청입니다';
                break;
            case 401:
                errorMessage = '인증이 필요합니다';
                window.location.href = '/auth/login';
                return;
            case 403:
                errorMessage = '접근 권한이 없습니다';
                break;
            case 404:
                errorMessage = '요청한 리소스를 찾을 수 없습니다';
                break;
            case 422:
                errorMessage = '입력 데이터가 올바르지 않습니다';
                break;
            case 500:
                errorMessage = '서버 내부 오류가 발생했습니다';
                break;
            case 502:
            case 503:
            case 504:
                errorMessage = '서버가 일시적으로 이용할 수 없습니다';
                break;
            default:
                if (textStatus === 'timeout') {
                    errorMessage = '요청 시간이 초과되었습니다';
                } else if (textStatus === 'abort') {
                    errorMessage = '요청이 취소되었습니다';
                } else if (textStatus === 'parsererror') {
                    errorMessage = '응답 데이터 형식이 올바르지 않습니다';
                }
        }
        
        // 서버에서 상세 에러 메시지를 보낸 경우
        try {
            const response = JSON.parse(xhr.responseText);
            if (response.message) {
                errorMessage = response.message;
            }
        } catch (e) {
            // JSON 파싱 실패 시 기본 메시지 사용
        }
        
        console.error('AJAX 오류:', {
            status: xhr.status,
            statusText: xhr.statusText,
            textStatus: textStatus,
            errorThrown: errorThrown,
            responseText: xhr.responseText
        });
        
        reject(new Error(errorMessage));
    },

    /**
     * 요청 취소를 위한 jqXHR 객체 반환
     */
    request: function(config) {
        const finalConfig = this.getBaseConfig(config);
        return $.ajax(finalConfig);
    }
};

// 전역 AJAX 설정
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        // CSRF 토큰 자동 추가
        const csrfToken = AjaxHelper.getCsrfToken();
        if (csrfToken && settings.type !== 'GET') {
            xhr.setRequestHeader('X-CSRFToken', csrfToken);
        }
    }
});

// jQuery AJAX 전역 에러 핸들러
$(document).ajaxError(function(event, xhr, settings, thrownError) {
    // 인증 오류 시 자동 로그인 페이지로 이동
    if (xhr.status === 401) {
        window.location.href = '/auth/login';
        return;
    }
    
    // 개발 환경에서만 콘솔에 상세 오류 출력
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        console.error('AJAX 전역 오류:', {
            url: settings.url,
            type: settings.type,
            status: xhr.status,
            error: thrownError,
            response: xhr.responseText
        });
    }
}); 