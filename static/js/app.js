// static/js/app.js - Nationwide Income & Housing Statistics Analytics Dashboard

let currentData = null;
let currentType = '아파트';
let currentSido = '전체';
let currentSort = 'nat_income_rank';
let selectedLocation = '서울 강남구';
let quadrantChart = null;
let rankingChart = null;

// 로딩 멘트 순환 타이머
let loadingInterval = null;
const loadingMessages = [
    "Gemini 3.5 모델이 국세청 연말정산 전국 소득과 부동산 가격지수를 대조 중입니다...",
    "전국 시·군·구 단위에서 소득 지수와 부동산 괴리율(Mismatch Ratio)을 계산하고 있습니다...",
    "수도권과 지방 대도시 간의 자산·소득 4분면 경제적 특성을 도출하고 있습니다...",
    "조별 보고서 및 과제에 바로 인용할 수 있는 학술 심층 진단을 작성하는 중입니다..."
];

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    setupEventListeners();
    await loadDashboardData(currentType, currentSido);
}

function setupEventListeners() {
    // Quick select dropdown
    const quickSelect = document.getElementById('quickGuSelect');
    quickSelect.addEventListener('change', (e) => {
        if (e.target.value) {
            selectedLocation = e.target.value;
            highlightTableRow(selectedLocation);
            document.getElementById('aiTargetBadge').innerText = `선택: ${selectedLocation}`;
        }
    });

    // Run AI Button
    document.getElementById('btnRunAi').addEventListener('click', () => {
        const target = quickSelect.value || selectedLocation || '서울 강남구';
        triggerAiAnalysis(target);
    });

    // Sort buttons
    document.querySelectorAll('.sort-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentSort = e.target.getAttribute('data-sort');
            renderTable();
        });
    });

    // Copy Report Button
    document.getElementById('btnCopyReport').addEventListener('click', copyReportToClipboard);

    // Download Report Button
    document.getElementById('btnDownloadReport').addEventListener('click', downloadReportMarkdown);
}

// 1. Load Data from Backend API
async function loadDashboardData(type, sido) {
    try {
        const response = await fetch(`/api/data?type=${encodeURIComponent(type)}&sido=${encodeURIComponent(sido)}`);
        const json = await response.json();
        if (json.status !== 'success') throw new Error(json.message);

        currentData = json.data;
        currentType = type;
        currentSido = sido;

        renderSidoButtons();
        renderTypeButtons();
        renderKPIs();
        populateGuDropdown();
        renderCharts();
        renderTable();

        if (!selectedLocation && currentData.districts.length > 0) {
            selectedLocation = currentData.districts[0].full_name;
        }
        document.getElementById('aiTargetBadge').innerText = `선택: ${selectedLocation}`;

    } catch (err) {
        console.error("데이터 로드 실패:", err);
        alert("데이터를 불러오지 못했습니다: " + err.message);
    }
}

// 2. Render Sido Filter Buttons
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

// 3. Render Housing Type Buttons
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

// 4. Render Nationwide KPI Summary
function renderKPIs() {
    const nat = currentData.nat_summary;
    const districts = currentData.districts;

    document.getElementById('kpiSeoulIncome').innerText = `${nat.avg_income_manwon.toLocaleString()} 만원`;
    document.getElementById('kpiSeoulGrowth').innerText = `+${nat.price_growth_rate}%`;

    // 1위 연봉 지역 (전국 기준)
    const topIncome = [...districts].sort((a, b) => b.avg_income_manwon - a.avg_income_manwon)[0];
    if (topIncome) {
        document.getElementById('kpiTopIncomeGu').innerText = topIncome.full_name;
        document.getElementById('kpiTopIncomeVal').innerText = `평균 ${topIncome.avg_income_manwon.toLocaleString()}만 원 (전국 1위)`;
    }

    // 1위 괴리율 지역 (소득 대비 주거부담 극대화)
    const topMismatch = [...districts].sort((a, b) => b.mismatch_ratio - a.mismatch_ratio)[0];
    if (topMismatch) {
        document.getElementById('kpiTopMismatchGu').innerText = topMismatch.full_name;
        document.getElementById('kpiTopMismatchVal').innerText = `괴리율 ${topMismatch.mismatch_ratio}% (연봉 ${topMismatch.avg_income_manwon}만)`;
    }

    // Update Section titles
    const regionName = currentSido === '전체' ? '대한민국 전국' : currentSido;
    document.getElementById('quadrantTitle').innerText = `📊 ${regionName} 4분면 매트릭스: 소득 수준 vs 부동산 상승률`;
    document.getElementById('rankingTitle').innerText = `🏆 ${regionName} 소득 순위 vs 주거부담 괴리율 (전국 100 기준)`;
    document.getElementById('tableSectionTitle').innerText = `📋 ${regionName} 시·군·구 종합 통계 데이터 시트 (${districts.length}개 지역)`;
}

// 5. Populate Gu Dropdown
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

// 6. Render 4-Quadrant Scatter Chart & Ranking Chart
function renderCharts() {
    const districts = currentData.districts;

    // 6-1. Quadrant Scatter Chart
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

    // 6-2. Ranking Bar Chart (최대 상위 25개 표시)
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

// 7. Render Data Table
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
    document.getElementById('quickGuSelect').value = location;
    document.getElementById('aiTargetBadge').innerText = `선택: ${location}`;
    highlightTableRow(location);
    triggerAiAnalysis(location);
}

// 8. Gemini AI 심층 진단 호출
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

// 9. Render AI Report Content
let lastReportData = null;

function renderAiReport(data) {
    lastReportData = data;
    const report = data.report;
    const stats = data.stats;
    const nat = data.nat_summary;

    document.getElementById('aiLoading').style.display = 'none';
    document.getElementById('aiResult').style.display = 'flex';

    // Headline
    document.getElementById('reportHeadlineText').innerText = report.headline;

    // Mini Stats
    document.getElementById('rIncomeVal').innerText = `${stats.avg_income_manwon.toLocaleString()}만 원`;
    document.getElementById('rIncomeRank').innerText = `${stats.nat_income_rank}위 / ${nat.total_nationwide}개`;
    document.getElementById('rPriceVal').innerText = `${stats.price_index_latest} (${stats.growth_rate >= 0 ? '+' : ''}${stats.growth_rate}%)`;
    document.getElementById('rMismatchVal').innerText = `${stats.mismatch_ratio}% (${stats.quadrant_label.split(' ')[0]})`;

    // Sections
    document.getElementById('reportIncomeText').innerText = report.income_summary;
    document.getElementById('reportHousingText').innerText = report.housing_summary;
    document.getElementById('reportMismatchText').innerText = report.mismatch_analysis;
    document.getElementById('reportPolicyText').innerText = report.policy_implication;
}

// 10. Clipboard & Markdown Export
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
