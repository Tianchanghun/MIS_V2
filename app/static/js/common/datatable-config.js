/**
 * DataTables 공통 설정 및 헬퍼
 * 일관된 테이블 UI/UX 제공
 */
const DataTableConfig = {
    // 기본 옵션
    defaultOptions: {
        language: {
            emptyTable: "데이터가 없습니다",
            info: "_START_ - _END_ / _TOTAL_개",
            infoEmpty: "0 - 0 / 0개",
            infoFiltered: "(전체 _MAX_개에서 필터링)",
            lengthMenu: "_MENU_개씩 보기",
            loadingRecords: "로딩 중...",
            processing: "처리 중...",
            search: "검색:",
            zeroRecords: "검색 결과가 없습니다",
            paginate: {
                first: "처음",
                last: "마지막",
                next: "다음",
                previous: "이전"
            }
        },
        pageLength: 50,
        lengthMenu: [[10, 25, 50, 100], [10, 25, 50, 100]],
        responsive: true,
        processing: true,
        serverSide: false, // 기본적으로 클라이언트 사이드
        order: [[0, 'desc']],
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
             '<"row"<"col-sm-12"tr>>' +
             '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
        drawCallback: function() {
            // 테이블 그려진 후 툴팁 초기화
            $('[data-bs-toggle="tooltip"]').tooltip();
        }
    },

    // 상품 테이블 설정
    productTable: function(selector, options = {}) {
        const config = $.extend(true, {}, this.defaultOptions, {
            ajax: {
                url: '/product/api/list',
                type: 'GET',
                data: function(d) {
                    // 추가 검색 파라미터
                    d.search_term = $('#searchInput').val() || '';
                    d.company_filter = $('#companyFilter').val() || '';
                    d.brand_filter = $('#brandFilter').val() || '';
                    d.category_filter = $('#categoryFilter').val() || '';
                    d.status_filter = $('#statusFilter').val() || '';
                }
            },
            columns: [
                { 
                    data: 'id', 
                    title: 'ID',
                    width: '60px',
                    className: 'text-center'
                },
                { 
                    data: 'company_name', 
                    title: '회사',
                    width: '80px',
                    render: function(data, type, row) {
                        const badgeClass = row.company_id === 1 ? 'bg-primary' : 'bg-success';
                        return `<span class="badge ${badgeClass}">${data}</span>`;
                    }
                },
                { 
                    data: 'brand_name', 
                    title: '브랜드',
                    width: '100px'
                },
                { 
                    data: 'product_name', 
                    title: '상품명',
                    render: function(data, type, row) {
                        let html = `<strong>${data}</strong>`;
                        if (row.product_code) {
                            html += `<br><small class="text-muted">${row.product_code}</small>`;
                        }
                        return html;
                    }
                },
                { 
                    data: 'category_name', 
                    title: '품목',
                    width: '100px'
                },
                { 
                    data: 'type_name', 
                    title: '타입',
                    width: '100px'
                },
                { 
                    data: 'year_code_name', 
                    title: '년도',
                    width: '80px',
                    className: 'text-center'
                },
                { 
                    data: 'price', 
                    title: '가격',
                    width: '100px',
                    className: 'text-end',
                    render: function(data, type, row) {
                        return data ? new Intl.NumberFormat('ko-KR').format(data) + '원' : '-';
                    }
                },
                { 
                    data: 'is_active', 
                    title: '상태',
                    width: '80px',
                    className: 'text-center',
                    render: function(data, type, row) {
                        const statusClass = data ? 'success' : 'secondary';
                        const statusText = data ? '활성' : '비활성';
                        return `<span class="badge bg-${statusClass}">${statusText}</span>`;
                    }
                },
                { 
                    data: 'created_at', 
                    title: '등록일',
                    width: '100px',
                    className: 'text-center',
                    render: function(data, type, row) {
                        return data ? new Date(data).toLocaleDateString('ko-KR') : '-';
                    }
                },
                {
                    data: null,
                    title: '작업',
                    width: '120px',
                    orderable: false,
                    className: 'text-center',
                    render: function(data, type, row) {
                        return `
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-outline-primary" onclick="editProduct(${row.id})" 
                                        data-bs-toggle="tooltip" title="수정">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="btn btn-outline-info" onclick="viewProduct(${row.id})" 
                                        data-bs-toggle="tooltip" title="상세보기">
                                    <i class="fas fa-eye"></i>
                                </button>
                                <button class="btn btn-outline-danger" onclick="deleteProduct(${row.id})" 
                                        data-bs-toggle="tooltip" title="삭제">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        `;
                    }
                }
            ]
        }, options);

        return $(selector).DataTable(config);
    },

    // 코드 관리 테이블 설정
    codeTable: function(selector, options = {}) {
        const config = $.extend(true, {}, this.defaultOptions, {
            pageLength: 25,
            order: [[4, 'asc'], [5, 'asc']], // 깊이, 순서로 정렬
            columns: [
                { 
                    data: 'code', 
                    title: '코드',
                    width: '20%',
                    render: function(data, type, row) {
                        const indent = '&nbsp;'.repeat(row.depth * 4);
                        const icon = row.depth === 0 ? 'fas fa-folder' : 
                                    row.depth === 1 ? 'fas fa-folder-open' : 'fas fa-file';
                        return `${indent}<i class="${icon} me-2"></i><strong>${data}</strong>`;
                    }
                },
                { 
                    data: 'code_name', 
                    title: '코드명',
                    width: '25%'
                },
                { 
                    data: 'code_info', 
                    title: '설명',
                    width: '25%',
                    render: function(data, type, row) {
                        return data || '-';
                    }
                },
                { 
                    data: 'depth', 
                    title: '깊이',
                    width: '10%',
                    className: 'text-center'
                },
                { 
                    data: 'sort', 
                    title: '순서',
                    width: '10%',
                    className: 'text-center'
                },
                {
                    data: null,
                    title: '관리',
                    width: '10%',
                    orderable: false,
                    className: 'text-center',
                    render: function(data, type, row) {
                        let html = '<div class="btn-group btn-group-sm">';
                        
                        if (row.depth < 2) {
                            html += `<button class="btn btn-outline-success" onclick="addChildCode(${row.seq})" 
                                           data-bs-toggle="tooltip" title="하위코드 추가">
                                        <i class="fas fa-plus"></i>
                                    </button>`;
                        }
                        
                        html += `<button class="btn btn-outline-primary" onclick="editCode(${row.seq})" 
                                       data-bs-toggle="tooltip" title="수정">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="btn btn-outline-danger" onclick="deleteCode(${row.seq})" 
                                       data-bs-toggle="tooltip" title="삭제">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>`;
                        
                        return html;
                    }
                }
            ]
        }, options);

        return $(selector).DataTable(config);
    },

    // 일반 테이블 초기화 (DataTables 없이)
    simpleTable: function(selector, data, columns) {
        const $table = $(selector);
        const $tbody = $table.find('tbody');
        
        if (!data || data.length === 0) {
            UIHelper.showTableEmpty(selector);
            return;
        }

        let html = '';
        data.forEach(row => {
            html += '<tr>';
            columns.forEach(col => {
                let cellData = row[col.data] || '';
                if (col.render && typeof col.render === 'function') {
                    cellData = col.render(cellData, 'display', row);
                }
                html += `<td class="${col.className || ''}">${cellData}</td>`;
            });
            html += '</tr>';
        });
        
        $tbody.html(html);
        
        // 툴팁 초기화
        $table.find('[data-bs-toggle="tooltip"]').tooltip();
    },

    // 테이블 새로고침
    refresh: function(tableInstance) {
        if (tableInstance && typeof tableInstance.ajax === 'object') {
            tableInstance.ajax.reload(null, false); // 페이지 유지
        }
    },

    // 테이블 검색 필터 설정
    setupFilters: function(tableInstance, filterSelectors = {}) {
        // 검색 입력 필드
        if (filterSelectors.search) {
            $(filterSelectors.search).on('keyup', debounce(function() {
                tableInstance.ajax.reload();
            }, 300));
        }

        // 선택 필터들
        Object.keys(filterSelectors).forEach(key => {
            if (key !== 'search') {
                $(filterSelectors[key]).on('change', function() {
                    tableInstance.ajax.reload();
                });
            }
        });
    }
};

// 디바운스 함수
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
} 