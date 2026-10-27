// static/js/app.js - Nationwide Income & Housing Statistics Analytics Dashboard
// Multi-Dimensional Intelligence Engine: Districts, Quintiles, Macro Regions, Housing Types, and AI Table Q&A

let currentData = null;
let currentType = '아파트';
let currentSido = '전체';
let currentSort = 'nat_income_rank';
let selectedLocation = '서울 강남구';

// Chart.js Instances
let quadrantChart = null;
let rankingChart = null;
let quintileCompareChart = null;
let quintileMismatchChart = null;
let macroRegionsChart = null;
let macroGrowthChart = null;
let housingGrowthChart = null;

// 로딩 멘트 순환 타이머
let loadingInterval = null;
const loadingMessages = [
    "Gemini 3.5 모델이 국세청 연말정산 전국 소득과 부동산 가격지수를 대조 중입니다...",
    "전국 시·군·구 단위에서 소득 지수와 부동산 괴리율(Mismatch Ratio)을 계산하고 있습니다...",
    "수도권과 지방 대도시 간의 자산·소득 4분면 경제적 특성을 도출하고 있습니다...",
    "조별 보고서 및 과제에 바로 인용할 수 있는 학술 심층 진단을 작성하는 중입니다..."
];

const chatLoadingMessages = [
    "Gemini 3.5 모델이 148개 전국 시·군·구 공식 통계를 검색하고 있습니다...",
    "질문 조건에 부합하는 지역들을 필터링 및 대조하고 있습니다...",
    "질문 맞춤형 통계 비교 표(Table)를 생성하고 있습니다...",
    "수치 검증 및 경제적 인사이트 요약을 정리하는 중입니다..."
];

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    setupTabNavigation();
    setupEventListeners();
    setupChatEventListeners();
    await loadDashboardData(currentType, currentSido);
}

// ============================================================================
// 0. Tab Navigation Controller
// ============================================================================
function setupTabNavigation() {
    const tabBtns = document.querySelectorAll('.nav-tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const targetBtn = e.currentTarget;
            const targetTabId = targetBtn.getAttribute('data-tab');

            tabBtns.forEach(b => b.classList.remove('active'));
            targetBtn.classList.add('active');

            document.querySelectorAll('.tab-content-panel').forEach(panel => {
                panel.classList.remove('active');
            });

            const activePanel = document.getElementById(targetTabId);
            if (activePanel) {
                activePanel.classList.add('active');
            }

            // Trigger chart resize after tab becomes visible
            setTimeout(resizeAllCharts, 80);
        });
    });
}

function resizeAllCharts() {
    const charts = [
        quadrantChart, rankingChart,
        quintileCompareChart, quintileMismatchChart,
        macroRegionsChart, macroGrowthChart,
        housingGrowthChart
    ];
    charts.forEach(c => {
        if (c) c.resize();
    });
}

// ============================================================================
// 1. Event Listeners for District Filters & Single AI Report
// ============================================================================
function setupEventListeners() {
    const quickSelect = document.getElementById('quickGuSelect');
    quickSelect.addEventListener('change', (e) => {
        if (e.target.value) {
            selectedLocation = e.target.value;
            highlightTableRow(selectedLocation);
            document.getElementById('aiTargetBadge').innerText = `선택: ${selectedLocation}`;
        }
    });

    document.getElementById('btnRunAi').addEventListener('click', () => {
        const target = quickSelect.value || selectedLocation || '서울 강남구';
        triggerAiAnalysis(target);
    });

    document.querySelectorAll('.sort-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentSort = e.target.getAttribute('data-sort');
            renderTable();
        });
    });

    document.getElementById('btnCopyReport').addEventListener('click', copyReportToClipboard);
    document.getElementById('btnDownloadReport').addEventListener('click', downloadReportMarkdown);
}

// ============================================================================
// 2. Chat Q&A & Custom Table Event Listeners
// ============================================================================
function setupChatEventListeners() {
    const chatInput = document.getElementById('chatInputText');
    const submitBtn = document.getElementById('btnSubmitChat');

    submitBtn.addEventListener('click', () => {
        const q = chatInput.value.trim();
        if (q) executeChatQuery(q);
    });

    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            const q = chatInput.value.trim();
            if (q) executeChatQuery(q);
        }
    });

    document.querySelectorAll('.chip-btn').forEach(chip => {
        chip.addEventListener('click', () => {
            const q = chip.getAttribute('data-q');
            chatInput.value = q;
            executeChatQuery(q);
        });
    });

    document.getElementById('btnCopyCustomTable').addEventListener('click', copyCustomTableToClipboard);
    document.getElementById('btnDownloadCustomCsv').addEventListener('click', downloadCustomTableCsv);
}

// ============================================================================
// 3. Load Main Data from Backend API
// ============================================================================
async function loadDashboardData(type, sido) {
    try {
        const response = await fetch(`/api/data?type=${encodeURIComponent(type)}&sido=${encodeURIComponent(sido)}`);
        const json = await response.json();
        if (json.status !== 'success') throw new Error(json.message);

        currentData = json.data;
        currentType = type;
        currentSido = sido;

        // Tab 1 Data Rendering
        renderSidoButtons();
        renderTypeButtons();
        renderKPIs();
        populateGuDropdown();
        renderDistrictCharts();
        renderTable();

        // Multi-dimensional Tabs Rendering
        renderQuintilesTab();
        renderMacroRegionsTab();
        renderHousingTypesTab();

        if (!selectedLocation && currentData.districts.length > 0) {
            selectedLocation = currentData.districts[0].full_name;
        }
        document.getElementById('aiTargetBadge').innerText = `선택: ${selectedLocation}`;

    } catch (err) {
        console.error("데이터 로드 실패:", err);
        alert("데이터를 불러오지 못했습니다: " + err.message);
    }
}

// ============================================================================
// 4. Render Sido & Type Filters
// ============================================================================
function renderSidoButtons() {
    const container = document.getElementById('sidoButtons');
    container.innerHTML = '';

    currentData.available_sidos.forEach(s => {
        const btn = document.createElement('button');
        btn.className = `sido-btn ${s === currentSido ? 'active' : ''}`;
        btn.innerText = s;
        btn.addEventListener('click', () => {
            if (s !== currentSido) {
                loadDashboardData(currentType, s);
            }
        });
        container.appendChild(btn);
    });
}

function renderTypeButtons() {
    const container = document.getElementById('typeButtons');
    container.innerHTML = '';

    currentData.available_types.forEach(t => {
        const btn = document.createElement('button');
        btn.className = `type-btn ${t === currentType ? 'active' : ''}`;
        btn.innerText = t;
        btn.addEventListener('click', () => {
            if (t !== currentType) {
                loadDashboardData(t, currentSido);
            }
        });
        container.appendChild(btn);
    });
}

function renderKPIs() {
    const nat = currentData.nat_summary;
    const districts = currentData.districts;

    document.getElementById('kpiSeoulIncome').innerText = `${nat.avg_income_manwon.toLocaleString()} 만원`;
    document.getElementById('kpiSeoulGrowth').innerText = `+${nat.price_growth_rate}%`;

    const topIncome = [...districts].sort((a, b) => b.avg_income_manwon - a.avg_income_manwon)[0];
    if (topIncome) {
        document.getElementById('kpiTopIncomeGu').innerText = topIncome.full_name;
        document.getElementById('kpiTopIncomeVal').innerText = `평균 ${topIncome.avg_income_manwon.toLocaleString()}만 원 (전국 1위)`;
    }

    const topMismatch = [...districts].sort((a, b) => b.mismatch_ratio - a.mismatch_ratio)[0];
    if (topMismatch) {
        document.getElementById('kpiTopMismatchGu').innerText = topMismatch.full_name;
        document.getElementById('kpiTopMismatchVal').innerText = `괴리율 ${topMismatch.mismatch_ratio}% (연봉 ${topMismatch.avg_income_manwon}만)`;
    }

    const regionName = currentSido === '전체' ? '대한민국 전국' : currentSido;
    document.getElementById('quadrantTitle').innerText = `📊 ${regionName} 4분면 매트릭스: 소득 수준 vs 부동산 상승률`;
    document.getElementById('rankingTitle').innerText = `🏆 ${regionName} 소득 순위 vs 주거부담 괴리율 (전국 100 기준)`;
    document.getElementById('tableSectionTitle').innerText = `📋 ${regionName} 시·군·구 종합 통계 데이터 시트 (${districts.length}개 지역)`;
}

function populateGuDropdown() {
    const select = document.getElementById('quickGuSelect');
    select.innerHTML = '';
    
    currentData.districts.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d.full_name;
        opt.innerText = `${d.full_name} (전국 ${d.nat_income_rank}위, ${d.avg_income_manwon}만)`;
        if (d.full_name === selectedLocation) opt.selected = true;
        select.appendChild(opt);
    });
}

// ============================================================================
// 5. TAB 1: 4분면 매트릭스 & 순위 바 차트
// ============================================================================
function renderDistrictCharts() {
    const districts = currentData.districts;

    // 5-1. Quadrant Scatter Chart
    const ctxQuadrant = document.getElementById('quadrantChart').getContext('2d');
    if (quadrantChart) quadrantChart.destroy();

    const quadrantColors = {
        'Q1_프리미엄안정': '#c084fc',
        'Q2_주거부담경보': '#fb923c',
        'Q3_서민안정': '#38bdf8',
        'Q4_신흥성장': '#34d399'
    };

    const scatterData = districts.map(d => ({
        x: d.income_index,
        y: d.growth_rate,
        fullName: d.full_name,
        name: d.name,
        avg_income: d.avg_income_manwon,
        mismatch: d.mismatch_ratio,
        quadrant: d.quadrant,
        quadrantLabel: d.quadrant_label,
        rank: d.nat_income_rank
    }));

    quadrantChart = new Chart(ctxQuadrant, {
        type: 'scatter',
        data: {
            datasets: [{
                label: '지역 위치',
                data: scatterData,
                backgroundColor: (context) => {
                    const raw = context.raw;
                    return raw ? (quadrantColors[raw.quadrant] || '#38bdf8') : '#38bdf8';
                },
                pointRadius: 6,
                pointHoverRadius: 9,
                borderColor: '#ffffff',
                borderWidth: 1.2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: '#38bdf8',
                    bodyColor: '#f8fafc',
                    borderColor: '#1e293b',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label: (ctx) => {
                            const d = ctx.raw;
                            return [
                                `📍 ${d.fullName} (전국 ${d.rank}위 | ${d.quadrantLabel})`,
                                `💰 1인당 연봉: ${d.avg_income.toLocaleString()}만 원 (전국대비: ${d.x}%)`,
                                `📈 최근 상승률: ${d.y}%`,
                                `⚖️ 소득대비 괴리율: ${d.mismatch}%`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '소득 지수 (대한민국 전국 평균 = 100 기준)',
                        color: '#94a3b8',
                        font: { size: 12, weight: 'bold' }
                    },
                    grid: { color: 'rgba(255, 255, 255, 0.06)' },
                    ticks: { color: '#94a3b8' }
                },
                y: {
                    title: {
                        display: true,
                        text: '최근 6개월 가격 변동률 (%)',
                        color: '#94a3b8',
                        font: { size: 12, weight: 'bold' }
                    },
                    grid: { color: 'rgba(255, 255, 255, 0.06)' },
                    ticks: { color: '#94a3b8' }
                }
            },
            onClick: (e, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const clickedTarget = scatterData[index].fullName;
                    selectAndAnalyzeLocation(clickedTarget);
                }
            }
        }
    });

    // 5-2. Ranking Bar Chart (상위 25개 표시)
    const ctxBar = document.getElementById('rankingChart').getContext('2d');
    if (rankingChart) rankingChart.destroy();

    const displayDistricts = districts.slice(0, 25);
    const labels = displayDistricts.map(d => d.name);
    const incomeIndices = displayDistricts.map(d => d.income_index);
    const mismatchRatios = displayDistricts.map(d => d.mismatch_ratio);

    rankingChart = new Chart(ctxBar, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '소득 지수 (전국=100)',
                    data: incomeIndices,
                    backgroundColor: 'rgba(56, 189, 248, 0.8)',
                    borderRadius: 4
                },
                {
                    label: '주거부담 괴리율 (100 초과 시 부담 가중)',
                    data: mismatchRatios,
                    backgroundColor: 'rgba(251, 146, 60, 0.8)',
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#94a3b8', font: { size: 11, weight: 'bold' } }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    padding: 10
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { size: 10 }, maxRotation: 45, minRotation: 45 }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.06)' },
                    ticks: { color: '#94a3b8' }
                }
            },
            onClick: (e, elements) => {
                if (elements.length > 0) {
                    const idx = elements[0].index;
                    const clickedTarget = displayDistricts[idx].full_name;
                    selectAndAnalyzeLocation(clickedTarget);
                }
            }
        }
    });
}

// ============================================================================
// 6. TAB 1: 전국 시·군·구 테이블 렌더링
// ============================================================================
function renderTable() {
    const tbody = document.getElementById('dataTableBody');
    tbody.innerHTML = '';

    let items = [...currentData.districts];

    if (currentSort === 'nat_income_rank') {
        items.sort((a, b) => a.nat_income_rank - b.nat_income_rank);
    } else if (currentSort === 'mismatch_ratio') {
        items.sort((a, b) => b.mismatch_ratio - a.mismatch_ratio);
    } else if (currentSort === 'growth_rate') {
        items.sort((a, b) => b.growth_rate - a.growth_rate);
    } else if (currentSort === 'price_index_latest') {
        items.sort((a, b) => b.price_index_latest - a.price_index_latest);
    }

    const badgeMap = {
        'Q1_프리미엄안정': { cls: 'badge-q1', text: '자산집중' },
        'Q2_주거부담경보': { cls: 'badge-q2', text: '주거부담경보' },
        'Q3_서민안정': { cls: 'badge-q3', text: '서민안정' },
        'Q4_신흥성장': { cls: 'badge-q4', text: '신흥성장' }
    };

    items.forEach(d => {
        const tr = document.createElement('tr');
        if (d.full_name === selectedLocation) tr.classList.add('selected');

        const bInfo = badgeMap[d.quadrant] || { cls: 'badge-q3', text: '일반' };
        const growthColor = d.growth_rate >= 0 ? '#f87171' : '#38bdf8';
        const growthPrefix = d.growth_rate >= 0 ? '+' : '';

        tr.innerHTML = `
            <td><strong>#${d.nat_income_rank}</strong></td>
            <td><span style="color:#94a3b8;">${d.sido}</span></td>
            <td><strong>${d.name}</strong></td>
            <td>${d.avg_income_manwon.toLocaleString()}만 원</td>
            <td>${d.income_index}</td>
            <td>${d.price_index_base}</td>
            <td>${d.price_index_latest}</td>
            <td style="color:${growthColor}; font-weight:700;">${growthPrefix}${d.growth_rate}%</td>
            <td><strong class="text-warning">${d.mismatch_ratio}%</strong></td>
            <td><span class="table-badge ${bInfo.cls}">${bInfo.text}</span></td>
            <td><button class="btn-table-ai" onclick="selectAndAnalyzeLocation('${d.full_name}')">🤖 진단</button></td>
        `;

        tr.addEventListener('click', (e) => {
            if (e.target.tagName !== 'BUTTON') {
                selectAndAnalyzeLocation(d.full_name);
            }
        });

        tbody.appendChild(tr);
    });
}

function highlightTableRow(location) {
    document.querySelectorAll('#dataTableBody tr').forEach(tr => {
        tr.classList.remove('selected');
        const sido = tr.children[1] ? tr.children[1].innerText : '';
        const name = tr.children[2] ? tr.children[2].innerText : '';
        if (`${sido} ${name}`.trim() === location.trim()) {
            tr.classList.add('selected');
        }
    });
}

function selectAndAnalyzeLocation(location) {
    selectedLocation = location;
    const select = document.getElementById('quickGuSelect');
    if (select) select.value = location;
    document.getElementById('aiTargetBadge').innerText = `선택: ${location}`;
    highlightTableRow(location);
    triggerAiAnalysis(location);
}

// ============================================================================
// 7. TAB 2: 소득 5분위 계층 분석 (Quintiles)
// ============================================================================
function renderQuintilesTab() {
    if (!currentData || !currentData.quintiles) return;
    const quintiles = currentData.quintiles;
    const nat = currentData.nat_summary;

    // 7-1. Quintile Cards Grid
    const cardsGrid = document.getElementById('quintileCardsGrid');
    cardsGrid.innerHTML = '';

    const tierColorMap = {
        1: { cls: 'q1-bg', badge: '1분위 (하위 20%)', color: '#fb923c' },
        2: { cls: 'q2-bg', badge: '2분위 (소득 20~40%)', color: '#f87171' },
        3: { cls: 'q3-bg', badge: '3분위 (중위 소득)', color: '#38bdf8' },
        4: { cls: 'q4-bg', badge: '4분위 (소득 60~80%)', color: '#34d399' },
        5: { cls: 'q5-bg', badge: '5분위 (최상위 20%)', color: '#c084fc' }
    };

    quintiles.forEach(q => {
        const info = tierColorMap[q.tier] || { cls: 'q3-bg', badge: `${q.tier}분위`, color: '#38bdf8' };
        const card = document.createElement('div');
        card.className = 'quintile-card';
        card.innerHTML = `
            <div class="q-tier-header">
                <span class="q-badge ${info.cls}">${info.badge}</span>
                <span style="font-size: 0.78rem; color: #94a3b8;">${q.count}개 자치구</span>
            </div>
            <div style="margin: 8px 0 4px;">
                <span style="font-size: 0.76rem; color: #94a3b8;">평균 1인 연봉</span>
                <div class="q-income-val" style="color: ${info.color};">${q.avg_income_manwon.toLocaleString()} <span style="font-size: 0.85rem; font-weight: normal; color: #94a3b8;">만원</span></div>
            </div>
            <div class="q-detail-row">
                <span>소득 구간</span>
                <strong style="color: #cbd5e1;">${q.income_min.toLocaleString()} ~ ${q.income_max.toLocaleString()}만</strong>
            </div>
            <div class="q-detail-row">
                <span>평균 가격지수</span>
                <strong style="color: #cbd5e1;">${q.avg_price_index}</strong>
            </div>
            <div class="q-detail-row">
                <span>주거부담 괴리율</span>
                <strong style="color: ${q.avg_mismatch_ratio >= 100 ? '#f87171' : '#34d399'}; font-weight: 700;">${q.avg_mismatch_ratio}%</strong>
            </div>
            <div class="q-detail-row">
                <span>최근 6개월 변동률</span>
                <strong style="color: ${q.avg_growth_rate >= 0 ? '#f87171' : '#38bdf8'};">${q.avg_growth_rate >= 0 ? '+' : ''}${q.avg_growth_rate}%</strong>
            </div>
            <div style="margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.06); font-size: 0.75rem; color: #94a3b8;">
                <span style="color: #64748b;">대표:</span> ${(q.sample_districts || []).join(', ')}
            </div>
        `;
        cardsGrid.appendChild(card);
    });

    // 7-2. Chart: Quintile Compare (Income vs Price Index)
    const ctxCompare = document.getElementById('chartQuintileCompare').getContext('2d');
    if (quintileCompareChart) quintileCompareChart.destroy();

    const labels = quintiles.map(q => `${q.tier}분위`);
    const incomes = quintiles.map(q => q.avg_income_manwon);
    const priceIndices = quintiles.map(q => q.avg_price_index);

    quintileCompareChart = new Chart(ctxCompare, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '평균 연봉 (만원)',
                    data: incomes,
                    backgroundColor: 'rgba(56, 189, 248, 0.85)',
                    borderRadius: 6,
                    yAxisID: 'y'
                },
                {
                    label: '평균 주택가격지수',
                    data: priceIndices,
                    backgroundColor: 'rgba(192, 132, 252, 0.85)',
                    borderRadius: 6,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#94a3b8', font: { size: 11, weight: 'bold' } } },
                tooltip: { backgroundColor: 'rgba(15, 23, 42, 0.95)', padding: 10 }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8' }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: { display: true, text: '평균 연봉 (만 원)', color: '#38bdf8' },
                    grid: { color: 'rgba(255, 255, 255, 0.06)' },
                    ticks: { color: '#94a3b8' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: { display: true, text: '가격 지수 (최신)', color: '#c084fc' },
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });

    // 7-3. Chart: Quintile Mismatch Ratio Curve
    const ctxMismatch = document.getElementById('chartQuintileMismatch').getContext('2d');
    if (quintileMismatchChart) quintileMismatchChart.destroy();

    const mismatches = quintiles.map(q => q.avg_mismatch_ratio);

    quintileMismatchChart = new Chart(ctxMismatch, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: '주거부담 괴리율 (%)',
                data: mismatches,
                borderColor: '#fb923c',
                backgroundColor: 'rgba(251, 146, 60, 0.15)',
                pointBackgroundColor: '#fb923c',
                pointRadius: 6,
                pointHoverRadius: 9,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#94a3b8', font: { size: 11, weight: 'bold' } } },
                tooltip: { backgroundColor: 'rgba(15, 23, 42, 0.95)', padding: 10 }
            },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#94a3b8' } },
                y: {
                    title: { display: true, text: '주거부담 괴리율 (%) - 100 초과 시 부담 가중', color: '#fb923c' },
                    grid: { color: 'rgba(255, 255, 255, 0.06)' },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });

    // 7-4. Quintiles Table Body
    const tbody = document.getElementById('quintileTableBody');
    tbody.innerHTML = '';
    quintiles.forEach(q => {
        const info = tierColorMap[q.tier];
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong style="color: ${info.color};">${q.tier}분위</strong></td>
            <td><span class="q-badge ${info.cls}">${info.badge}</span></td>
            <td>${q.count}개</td>
            <td>${q.income_min.toLocaleString()}만 ~ ${q.income_max.toLocaleString()}만 원</td>
            <td><strong>${q.avg_income_manwon.toLocaleString()}만 원</strong></td>
            <td>${q.avg_income_index}</td>
            <td>${q.avg_price_index}</td>
            <td style="color: ${q.avg_growth_rate >= 0 ? '#f87171' : '#38bdf8'}; font-weight: 700;">${q.avg_growth_rate >= 0 ? '+' : ''}${q.avg_growth_rate}%</td>
            <td><strong class="text-warning">${q.avg_mismatch_ratio}%</strong></td>
            <td style="color: #94a3b8; font-size: 0.82rem;">${(q.sample_districts || []).join(', ')}</td>
        `;
        tbody.appendChild(tr);
    });

    // 7-5. Academic Insight Dynamic Text
    const q1 = quintiles[0];
    const q5 = quintiles[quintiles.length - 1];
    if (q1 && q5) {
        document.getElementById('quintileInsightText').innerHTML = `
            전국 148개 자치구 분석 결과, 최상위 5분위(평균 <strong>${q5.avg_income_manwon.toLocaleString()}만원</strong>)와 최하위 1분위(평균 <strong>${q1.avg_income_manwon.toLocaleString()}만원</strong>)의 소득 5분위 배율은 <strong>약 ${nat.income_gap_ratio}배</strong> 수준입니다. 
            그러나 가격지수에 대한 체감 주거부담 괴리율은 1분위(<strong>${q1.avg_mismatch_ratio}%</strong>)가 5분위(<strong>${q5.avg_mismatch_ratio}%</strong>) 대비 <strong>${nat.mismatch_gap_ratio}배 높아</strong>, 
            소득이 취약할수록 주택 가격 지수에 대한 체감 주거비 압박을 심하게 겪는 <strong>'주거 부담 역진성(Regressive Housing Burden)'</strong> 현상이 통계적으로 명확히 입증됩니다.
        `;
    }
}

// ============================================================================
// 8. TAB 3: 6대 권역별 주거 부담 비교 (Macro Regions)
// ============================================================================
function renderMacroRegionsTab() {
    if (!currentData || !currentData.macro_regions) return;
    const regions = currentData.macro_regions;

    // 8-1. Chart: Macro Regions Income vs Price Index
    const ctxMacro = document.getElementById('chartMacroRegions').getContext('2d');
    if (macroRegionsChart) macroRegionsChart.destroy();

    const labels = regions.map(r => r.region_name);
    const incomes = regions.map(r => r.avg_income_manwon);
    const prices = regions.map(r => r.avg_price_index);

    macroRegionsChart = new Chart(ctxMacro, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '권역 평균 연봉 (만원)',
                    data: incomes,
                    backgroundColor: 'rgba(56, 189, 248, 0.85)',
                    borderRadius: 6
                },
                {
                    label: '권역 평균 가격지수',
                    data: prices,
                    backgroundColor: 'rgba(99, 102, 241, 0.85)',
                    borderRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#94a3b8', font: { size: 11, weight: 'bold' } } },
                tooltip: { backgroundColor: 'rgba(15, 23, 42, 0.95)', padding: 10 }
            },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#94a3b8' } },
                y: { grid: { color: 'rgba(255, 255, 255, 0.06)' }, ticks: { color: '#94a3b8' } }
            }
        }
    });

    // 8-2. Chart: Macro Regions Growth Rate
    const ctxGrowth = document.getElementById('chartMacroGrowth').getContext('2d');
    if (macroGrowthChart) macroGrowthChart.destroy();

    const growths = regions.map(r => r.avg_growth_rate);

    macroGrowthChart = new Chart(ctxGrowth, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '최근 6개월 가격 변동률 (%)',
                data: growths,
                backgroundColor: growths.map(g => g >= 0 ? 'rgba(248, 113, 113, 0.85)' : 'rgba(56, 189, 248, 0.85)'),
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#94a3b8', font: { size: 11, weight: 'bold' } } },
                tooltip: { backgroundColor: 'rgba(15, 23, 42, 0.95)', padding: 10 }
            },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#94a3b8' } },
                y: {
                    title: { display: true, text: '변동률 (%)', color: '#94a3b8' },
                    grid: { color: 'rgba(255, 255, 255, 0.06)' },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });

    // 8-3. Macro Regions Table
    const tbody = document.getElementById('macroTableBody');
    tbody.innerHTML = '';
    regions.forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${r.region_name}</strong></td>
            <td style="color: #94a3b8;">${r.sidos.join(', ')}</td>
            <td>${r.count}개 자치구</td>
            <td><strong>${r.avg_income_manwon.toLocaleString()}만 원</strong></td>
            <td>${r.avg_price_index}</td>
            <td style="color: ${r.avg_growth_rate >= 0 ? '#f87171' : '#38bdf8'}; font-weight: 700;">${r.avg_growth_rate >= 0 ? '+' : ''}${r.avg_growth_rate}%</td>
            <td><strong class="text-warning">${r.avg_mismatch_ratio}%</strong></td>
            <td><span class="table-badge badge-q1">${r.top_income_gu}</span></td>
            <td><span class="table-badge badge-q2">${r.top_mismatch_gu}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

// ============================================================================
// 9. TAB 4: 주택 유형별 격차 (Housing Types)
// ============================================================================
function renderHousingTypesTab() {
    if (!currentData || !currentData.housing_types_summary) return;
    const summaries = currentData.housing_types_summary;

    // 9-1. Cards Grid
    const cardsGrid = document.getElementById('housingTypeCardsGrid');
    cardsGrid.innerHTML = '';

    const iconMap = {
        '아파트': '🏢',
        '종합': '🏘️',
        '연립다세대': '🏠',
        '단독주택': '🏡'
    };

    summaries.forEach(h => {
        const icon = iconMap[h.type] || '🏠';
        const card = document.createElement('div');
        card.className = 'housing-type-card';
        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 1.15rem; font-weight: 700; color: #fff;">${icon} ${h.type}</span>
                <span class="table-badge badge-q3">공식 지표</span>
            </div>
            <p style="font-size: 0.8rem; color: #94a3b8; margin: 4px 0 10px;">${h.desc}</p>
            <div class="q-detail-row">
                <span>전국 최신 지수</span>
                <strong>${h.nat_latest_index}</strong>
            </div>
            <div class="q-detail-row">
                <span>전국 최근 변동률</span>
                <strong style="color: ${h.nat_growth_rate >= 0 ? '#f87171' : '#38bdf8'};">${h.nat_growth_rate >= 0 ? '+' : ''}${h.nat_growth_rate}%</strong>
            </div>
            <div class="q-detail-row" style="margin-top: 6px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.06);">
                <span>서울 최신 지수</span>
                <strong>${h.seoul_latest_index}</strong>
            </div>
            <div class="q-detail-row">
                <span>서울 최근 변동률</span>
                <strong style="color: ${h.seoul_growth_rate >= 0 ? '#f87171' : '#38bdf8'}; font-weight: 700;">${h.seoul_growth_rate >= 0 ? '+' : ''}${h.seoul_growth_rate}%</strong>
            </div>
        `;
        cardsGrid.appendChild(card);
    });

    // 9-2. Chart: Housing Types Growth (Nationwide vs Seoul)
    const ctxHousing = document.getElementById('chartHousingTypesGrowth').getContext('2d');
    if (housingGrowthChart) housingGrowthChart.destroy();

    const labels = summaries.map(h => h.type);
    const natGrowths = summaries.map(h => h.nat_growth_rate);
    const seoulGrowths = summaries.map(h => h.seoul_growth_rate);

    housingGrowthChart = new Chart(ctxHousing, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '대한민국 전국 최근 변동률 (%)',
                    data: natGrowths,
                    backgroundColor: 'rgba(56, 189, 248, 0.8)',
                    borderRadius: 6
                },
                {
                    label: '서울특별시 최근 변동률 (%)',
                    data: seoulGrowths,
                    backgroundColor: 'rgba(248, 113, 113, 0.85)',
                    borderRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#94a3b8', font: { size: 11, weight: 'bold' } } },
                tooltip: { backgroundColor: 'rgba(15, 23, 42, 0.95)', padding: 10 }
            },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#94a3b8' } },
                y: {
                    title: { display: true, text: '최근 6개월 변동률 (%)', color: '#94a3b8' },
                    grid: { color: 'rgba(255, 255, 255, 0.06)' },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });

    // 9-3. Housing Types Table
    const tbody = document.getElementById('housingTypeTableBody');
    tbody.innerHTML = '';
    summaries.forEach(h => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${h.type}</strong></td>
            <td style="color: #94a3b8;">${h.desc}</td>
            <td>${h.nat_latest_index}</td>
            <td style="color: ${h.nat_growth_rate >= 0 ? '#f87171' : '#38bdf8'}; font-weight: 700;">${h.nat_growth_rate >= 0 ? '+' : ''}${h.nat_growth_rate}%</td>
            <td><strong>${h.seoul_latest_index}</strong></td>
            <td style="color: ${h.seoul_growth_rate >= 0 ? '#f87171' : '#38bdf8'}; font-weight: 700;">${h.seoul_growth_rate >= 0 ? '+' : ''}${h.seoul_growth_rate}%</td>
        `;
        tbody.appendChild(tr);
    });
}

// ============================================================================
// 10. Gemini AI Single District Report
// ============================================================================
async function triggerAiAnalysis(location) {
    const placeholder = document.getElementById('aiPlaceholder');
    const loading = document.getElementById('aiLoading');
    const result = document.getElementById('aiResult');
    const loadingMsg = document.getElementById('loadingMsg');

    placeholder.style.display = 'none';
    result.style.display = 'none';
    loading.style.display = 'block';

    let msgIdx = 0;
    loadingMsg.innerText = loadingMessages[0];
    clearInterval(loadingInterval);
    loadingInterval = setInterval(() => {
        msgIdx = (msgIdx + 1) % loadingMessages.length;
        loadingMsg.innerText = loadingMessages[msgIdx];
    }, 2200);

    try {
        const res = await fetch('/api/ai-analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_name: location, type: currentType, sido: currentSido })
        });

        const data = await res.json();
        clearInterval(loadingInterval);

        if (data.status !== 'success') {
            throw new Error(data.message || 'AI 분석 응답 실패');
        }

        renderAiReport(data);

    } catch (err) {
        clearInterval(loadingInterval);
        loading.style.display = 'none';
        placeholder.style.display = 'block';
        alert("AI 분석 생성 중 오류 발생: " + err.message);
    }
}

let lastReportData = null;

function renderAiReport(data) {
    lastReportData = data;
    const report = data.report;
    const stats = data.stats;
    const nat = data.nat_summary;

    document.getElementById('aiLoading').style.display = 'none';
    document.getElementById('aiResult').style.display = 'flex';

    document.getElementById('reportHeadlineText').innerText = report.headline;
    document.getElementById('rIncomeVal').innerText = `${stats.avg_income_manwon.toLocaleString()}만 원`;
    document.getElementById('rIncomeRank').innerText = `${stats.nat_income_rank}위 / ${nat.total_nationwide}개`;
    document.getElementById('rPriceVal').innerText = `${stats.price_index_latest} (${stats.growth_rate >= 0 ? '+' : ''}${stats.growth_rate}%)`;
    document.getElementById('rMismatchVal').innerText = `${stats.mismatch_ratio}% (${stats.quadrant_label.split(' ')[0]})`;

    document.getElementById('reportIncomeText').innerText = report.income_summary;
    document.getElementById('reportHousingText').innerText = report.housing_summary;
    document.getElementById('reportMismatchText').innerText = report.mismatch_analysis;
    document.getElementById('reportPolicyText').innerText = report.policy_implication;
}

// ============================================================================
// 11. TAB 5: AI Free Chat Query & Custom Table Generation
// ============================================================================
let lastChatResult = null;

async function executeChatQuery(question) {
    const loadingBox = document.getElementById('chatLoading');
    const resultBox = document.getElementById('chatResultBox');
    const loadingMsg = document.getElementById('chatLoadingMsg');

    resultBox.style.display = 'none';
    loadingBox.style.display = 'block';

    let msgIdx = 0;
    loadingMsg.innerText = chatLoadingMessages[0];
    clearInterval(loadingInterval);
    loadingInterval = setInterval(() => {
        msgIdx = (msgIdx + 1) % chatLoadingMessages.length;
        loadingMsg.innerText = chatLoadingMessages[msgIdx];
    }, 2000);

    try {
        const res = await fetch('/api/chat-query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: question,
                type: currentType,
                sido: currentSido
            })
        });

        const data = await res.json();
        clearInterval(loadingInterval);
        loadingBox.style.display = 'none';

        if (data.status !== 'success') {
            throw new Error(data.message || 'AI 질의응답 실패');
        }

        lastChatResult = data.result;
        renderChatResult(data.question, data.result);

    } catch (err) {
        clearInterval(loadingInterval);
        loadingBox.style.display = 'none';
        alert("AI 질의응답 중 오류 발생: " + err.message);
    }
}

function renderChatResult(question, result) {
    const resultBox = document.getElementById('chatResultBox');
    resultBox.style.display = 'flex';

    document.getElementById('chatDisplayQuestion').innerText = question;
    document.getElementById('chatAnswerText').innerText = result.answer;

    const kpContainer = document.getElementById('chatKeyPoints');
    kpContainer.innerHTML = '';
    if (result.key_points && Array.isArray(result.key_points)) {
        result.key_points.forEach(pt => {
            const span = document.createElement('span');
            span.className = 'key-point-pill';
            span.innerText = `📌 ${pt}`;
            kpContainer.appendChild(span);
        });
    }

    const tableData = result.table;
    if (tableData) {
        document.getElementById('customTableTitle').innerText = `📊 ${tableData.title || 'AI 맞춤 추출 결과 표'}`;
        document.getElementById('customTableRowCount').innerText = `${tableData.rows ? tableData.rows.length : 0}개 지역 도출`;

        const thead = document.getElementById('customTableHead');
        thead.innerHTML = '';
        const trH = document.createElement('tr');
        (tableData.headers || []).forEach(h => {
            const th = document.createElement('th');
            th.innerText = h;
            trH.appendChild(th);
        });
        thead.appendChild(trH);

        const tbody = document.getElementById('customTableBody');
        tbody.innerHTML = '';
        (tableData.rows || []).forEach(row => {
            const tr = document.createElement('tr');
            row.forEach((cell, idx) => {
                const td = document.createElement('td');
                td.innerText = cell;
                if (idx === 0) td.style.fontWeight = '700';
                if (String(cell).includes('%') && (String(cell).includes('+') || String(cell).includes('-'))) {
                    td.style.color = String(cell).includes('+') ? '#f87171' : '#38bdf8';
                    td.style.fontWeight = '700';
                }
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
    }

    resultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function copyCustomTableToClipboard() {
    if (!lastChatResult || !lastChatResult.table) return;

    const t = lastChatResult.table;
    let md = `### ${t.title}\n\n`;
    md += `| ${t.headers.join(' | ')} |\n`;
    md += `| ${t.headers.map(() => '---').join(' | ')} |\n`;
    t.rows.forEach(r => {
        md += `| ${r.join(' | ')} |\n`;
    });

    navigator.clipboard.writeText(md).then(() => {
        const btn = document.getElementById('btnCopyCustomTable');
        const orig = btn.innerText;
        btn.innerText = "✅ 복사 완료!";
        setTimeout(() => { btn.innerText = orig; }, 1800);
    }).catch(err => {
        alert("복사 실패: " + err);
    });
}

function downloadCustomTableCsv() {
    if (!lastChatResult || !lastChatResult.table) return;

    const t = lastChatResult.table;
    let csv = '\uFEFF';
    csv += t.headers.join(',') + '\n';
    t.rows.forEach(r => {
        csv += r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',') + '\n';
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(t.title || 'AI_맞춤_통계표').replace(/\s+/g, '_')}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ============================================================================
// 12. Single District Report Export (Markdown & Clipboard)
// ============================================================================
function generateMarkdownReport() {
    if (!lastReportData) return "";
    const r = lastReportData.report;
    const s = lastReportData.stats;
    const nat = lastReportData.nat_summary;

    return `# [AI 거시경제·부동산 통계 진단] ${s.full_name} 소득 수준 vs 부동산 가격 심층 분석

> **분석 기준**: 국세청 근로소득 연말정산 신고현황 & 한국부동산원 전국 매매가격지수 (${currentType})  
> **분석 모델**: Google Gemini 3.5 Flash Lite

---

## 📌 핵심 총평 (Headline)
> "${r.headline}"

---

## 📊 ${s.full_name} 공식 통계 지표 요약 (대한민국 전국 기준)
* **1인당 평균 근로소득**: ${s.avg_income_manwon.toLocaleString()}만 원 (전국 ${nat.total_nationwide}개 시·군·구 중 **${s.nat_income_rank}위**)
* **대한민국 전국 평균 대비 소득 지수**: ${s.income_index} (전국 평균: ${nat.avg_income_manwon.toLocaleString()}만 원 = 100 기준)
* **주택 매매가격지수**: ${s.price_index_latest} (최근 6개월 변동률: **${s.growth_rate >= 0 ? '+' : ''}${s.growth_rate}%**, 전국 평균: +${nat.price_growth_rate}%)
* **소득 대비 주거부담 괴리율**: **${s.mismatch_ratio}%**
* **4분면 특성 분류**: ${s.quadrant_label}

---

## 💼 1. 근로소득 구조 해석
${r.income_summary}

## 🏠 2. 부동산 가격 및 상승 동향
${r.housing_summary}

## ⚖️ 3. 소득 vs 부동산 불균형 괴리율 진단
${r.mismatch_analysis}

## 🎓 4. 학술 보고서 및 조별 과제 인용 시사점
${r.policy_implication}

---
*Generated by AI Study - Nationwide Income & Housing Statistics Analyzer*
`;
}

function copyReportToClipboard() {
    const md = generateMarkdownReport();
    if (!md) return;

    navigator.clipboard.writeText(md).then(() => {
        const btn = document.getElementById('btnCopyReport');
        const orig = btn.innerText;
        btn.innerText = "✅ 복사 완료!";
        setTimeout(() => { btn.innerText = orig; }, 1800);
    }).catch(err => {
        alert("클립보드 복사 실패: " + err);
    });
}

function downloadReportMarkdown() {
    const md = generateMarkdownReport();
    if (!md) return;

    const loc = lastReportData.stats.full_name.replace(' ', '_');
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${loc}_소득_부동산_심층진단리포트.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
