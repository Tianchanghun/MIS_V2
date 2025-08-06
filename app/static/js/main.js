/*!
 * MIS v2 공통 JavaScript
 */

// 전역 MIS 유틸리티 객체
window.MISUtils = {
    /**
     * 성공 메시지 표시
     */
    showSuccess: function(message) {
        this.showAlert(message, 'success');
    },
    
    /**
     * 에러 메시지 표시
     */
    showError: function(message) {
        this.showAlert(message, 'danger');
    },
    
    /**
     * 경고 메시지 표시
     */
    showWarning: function(message) {
        this.showAlert(message, 'warning');
    },
    
    /**
     * 정보 메시지 표시
     */
    showInfo: function(message) {
        this.showAlert(message, 'info');
    },
    
    /**
     * 알림 메시지 표시 (내부 함수)
     */
    showAlert: function(message, type) {
        // 기존 알림 제거
        $('.alert-dismissible').remove();
        
        // 새 알림 생성
        var alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert" style="position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        $('body').append(alertHtml);
        
        // 3초 후 자동 제거
        setTimeout(function() {
            $('.alert-dismissible').fadeOut(function() {
                $(this).remove();
            });
        }, 3000);
    },
    
    /**
     * 확인 대화상자
     */
    confirm: function(message, callback) {
        if (confirm(message)) {
            if (typeof callback === 'function') {
                callback();
            }
        }
    },
    
    /**
     * AJAX 요청 공통 설정
     */
    setupAjax: function() {
        // CSRF 토큰 설정 (필요시)
        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                    var token = $('meta[name=csrf-token]').attr('content');
                    if (token) {
                        xhr.setRequestHeader("X-CSRFToken", token);
                    }
                }
            }
        });
    },
    
    /**
     * 날짜 포맷팅
     */
    formatDate: function(date, format) {
        if (!date) return '-';
        
        var d = new Date(date);
        var year = d.getFullYear();
        var month = String(d.getMonth() + 1).padStart(2, '0');
        var day = String(d.getDate()).padStart(2, '0');
        var hour = String(d.getHours()).padStart(2, '0');
        var minute = String(d.getMinutes()).padStart(2, '0');
        var second = String(d.getSeconds()).padStart(2, '0');
        
        switch (format) {
            case 'YYYY-MM-DD':
                return `${year}-${month}-${day}`;
            case 'YYYY-MM-DD HH:mm':
                return `${year}-${month}-${day} ${hour}:${minute}`;
            case 'YYYY-MM-DD HH:mm:ss':
                return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
            default:
                return `${year}-${month}-${day}`;
        }
    },
    
    /**
     * 숫자 천단위 콤마 포맷팅
     */
    formatNumber: function(num) {
        if (!num && num !== 0) return '-';
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }
};

// ===============================
// 테이블 정렬 기능
// ===============================

/**
 * 테이블 정렬 초기화
 */
function initTableSorting() {
    // 정렬 가능한 테이블 헤더에 클릭 이벤트 추가
    document.querySelectorAll('.table thead th.sortable').forEach(header => {
        header.addEventListener('click', function() {
            sortTable(this);
        });
    });
}

/**
 * 테이블 정렬 실행
 */
function sortTable(header) {
    const table = header.closest('table');
    const tbody = table.querySelector('tbody');
    const columnIndex = Array.from(header.parentNode.children).indexOf(header);
    const isNumeric = header.dataset.type === 'number';
    const isDate = header.dataset.type === 'date';
    
    // 현재 정렬 상태 확인
    const currentSort = header.classList.contains('asc') ? 'asc' : 
                       header.classList.contains('desc') ? 'desc' : 'none';
    
    // 모든 헤더의 정렬 상태 초기화
    table.querySelectorAll('th.sortable').forEach(th => {
        th.classList.remove('asc', 'desc');
    });
    
    // 새로운 정렬 상태 설정
    let newSort;
    if (currentSort === 'none' || currentSort === 'desc') {
        newSort = 'asc';
        header.classList.add('asc');
    } else {
        newSort = 'desc';
        header.classList.add('desc');
    }
    
    // 행 정렬
    const rows = Array.from(tbody.querySelectorAll('tr'));
    rows.sort((a, b) => {
        const aCell = a.children[columnIndex];
        const bCell = b.children[columnIndex];
        
        let aValue = aCell.textContent.trim();
        let bValue = bCell.textContent.trim();
        
        // 데이터 타입별 처리
        if (isNumeric) {
            aValue = parseFloat(aValue.replace(/[^0-9.-]/g, '')) || 0;
            bValue = parseFloat(bValue.replace(/[^0-9.-]/g, '')) || 0;
        } else if (isDate) {
            aValue = new Date(aValue) || new Date(0);
            bValue = new Date(bValue) || new Date(0);
        } else {
            aValue = aValue.toLowerCase();
            bValue = bValue.toLowerCase();
        }
        
        if (newSort === 'asc') {
            return aValue > bValue ? 1 : -1;
        } else {
            return aValue < bValue ? 1 : -1;
        }
    });
    
    // 정렬된 행을 테이블에 다시 추가
    rows.forEach(row => tbody.appendChild(row));
}

/**
 * 테이블 검색/필터링
 */
function filterTable(searchInput, tableSelector) {
    const searchTerm = searchInput.value.toLowerCase();
    const table = document.querySelector(tableSelector);
    const tbody = table.querySelector('tbody');
    const rows = tbody.querySelectorAll('tr');
    
    let visibleCount = 0;
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        if (text.includes(searchTerm)) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
}

// DOM 로드 완료 후 실행
$(document).ready(function() {
    // AJAX 공통 설정
    MISUtils.setupAjax();
    
    // 모든 테이블에 부트스트랩 스타일 적용
    $('table').addClass('table table-striped table-hover');
    
    // 테이블 정렬 초기화
    initTableSorting();
    
    // 테이블 스타일 개선
    $('.table').each(function() {
        // 숫자 컬럼에 number 클래스 추가
        $(this).find('td').each(function() {
            const text = $(this).text().trim();
            if (text.match(/^\d+([,.]?\d+)*$/)) {
                $(this).addClass('number');
            }
        });
        
        // 날짜 컬럼에 date 클래스 추가
        $(this).find('td').each(function() {
            const text = $(this).text().trim();
            if (text.match(/^\d{4}-\d{2}-\d{2}/) || text.match(/^\d{2}\/\d{2}\/\d{4}/)) {
                $(this).addClass('date');
            }
        });
    });
    
    // 툴팁 활성화
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // 사이드바 토글 기능
    $('#sidebarToggle').on('click', function() {
        $('#sidebar').toggleClass('collapsed');
        $('#main-content').toggleClass('sidebar-collapsed');
    });
    
    // 검색 폼 엔터 키 지원
    $('input[type="search"], input[name="search"]').on('keypress', function(e) {
        if (e.which === 13) {
            $(this).closest('form').submit();
        }
    });
    
    // 전체 선택/해제 체크박스
    $('input[type="checkbox"][data-toggle="checkall"]').on('change', function() {
        var target = $(this).data('target');
        var checked = $(this).prop('checked');
        $(target).prop('checked', checked);
    });
    
    // 검색 입력 필드에 실시간 검색 적용
    $('input[data-table-search]').on('input', function() {
        const tableSelector = $(this).data('table-search');
        filterTable(this, tableSelector);
    });
});

// 배치 상태 모니터링 (실시간 업데이트)
window.BatchMonitor = {
    intervalId: null,
    
    start: function() {
        this.update();
        this.intervalId = setInterval(this.update, 5000); // 5초마다 업데이트
    },
    
    stop: function() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    },
    
    update: function() {
        $.get('/batch/status')
            .done(function(data) {
                $('#batch-status').html(data);
            })
            .fail(function() {
                console.log('배치 상태 업데이트 실패');
            });
    }
};

// 페이지별 초기화 함수들
window.PageInit = {
    // 메뉴 관리 페이지
    menuManagement: function() {
        console.log('메뉴 관리 페이지 초기화');
    },
    
    // 사용자 관리 페이지
    userManagement: function() {
        console.log('사용자 관리 페이지 초기화');
        
        // 전화번호 포맷팅
        $('input[name="mobile"]').on('input', function() {
            var value = $(this).val().replace(/[^0-9]/g, '');
            if (value.length >= 11) {
                value = value.replace(/(\d{3})(\d{4})(\d{4})/, '$1-$2-$3');
            } else if (value.length >= 7) {
                value = value.replace(/(\d{3})(\d{3,4})(\d{4})/, '$1-$2-$3');
            }
            $(this).val(value);
        });
    },
    
    // 부서 관리 페이지
    departmentManagement: function() {
        console.log('부서 관리 페이지 초기화');
    }
}; 

// ===============================
// 사용자 계정 관리 함수들
// ===============================

/**
 * 로그아웃 확인
 */
function confirmLogout() {
    if (confirm('정말 로그아웃하시겠습니까?')) {
        // 로딩 스피너 표시
        showLoading('로그아웃 중...');
        
        // 로그아웃 처리
        window.location.href = '/auth/logout';
    }
}

/**
 * 프로필 보기
 */
function showProfile() {
    alert('프로필 보기 기능을 구현 중입니다.');
}

/**
 * 설정 보기
 */
function showSettings() {
    alert('계정 설정 기능을 구현 중입니다.');
}

/**
 * 비밀번호 변경
 */
function changePassword() {
    const newPassword = prompt('새 비밀번호를 입력하세요:');
    if (newPassword && newPassword.length >= 6) {
        const confirmPassword = prompt('새 비밀번호를 다시 입력하세요:');
        if (newPassword === confirmPassword) {
            alert('비밀번호 변경 기능을 구현 중입니다.');
        } else {
            alert('비밀번호가 일치하지 않습니다.');
        }
    } else if (newPassword) {
        alert('비밀번호는 6자 이상이어야 합니다.');
    }
}

/**
 * 로딩 스피너 표시
 */
function showLoading(message = '처리 중...') {
    // 기존 로딩 제거
    hideLoading();
    
    const loadingHtml = `
        <div id="loading-overlay" style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        ">
            <div style="
                background: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            ">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div class="mt-2">${message}</div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', loadingHtml);
}

/**
 * 로딩 스피너 숨기기
 */
function hideLoading() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.remove();
    }
} 

// ===============================
// 키보드 단축키
// ===============================

document.addEventListener('keydown', function(e) {
    // Ctrl + Shift + L: 로그아웃
    if (e.ctrlKey && e.shiftKey && e.key === 'L') {
        e.preventDefault();
        confirmLogout();
    }
    
    // Esc: 모달 닫기
    if (e.key === 'Escape') {
        // 열려있는 모달이 있다면 닫기
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        });
        
        // 로딩 숨기기
        hideLoading();
    }
}); 