/* ================================================================
   IoT Control Center — main.js  (Complete Rebuild)
   ================================================================ */

'use strict';

const WS_URL = `ws://${window.location.host}/ws`;
let socket = null;
let isOpen = false;
let isRunning = false;

// ─── DOM References ───
const els = {
    statusDot:    document.getElementById('status-dot'),
    statusText:   document.getElementById('status-text'),
    btnOpen:      document.getElementById('btn-open'),
    btnStart:     document.getElementById('btn-start'),
    btnStop:      document.getElementById('btn-stop'),
    btnClose:     document.getElementById('btn-close'),
    btnSet:       document.getElementById('btn-set'),
    interval:     document.getElementById('interval'),
    logBox:       document.getElementById('log-box'),
    historyBody:  document.getElementById('history-body'),
    lastUpdate:   document.getElementById('last-update'),
    lightDot:     document.getElementById('light-dot'),
    lightText:    document.getElementById('light-text'),
    lightVal:     document.getElementById('light-val'),
    irBadge:      document.getElementById('ir-badge'),
    tempArc:      document.getElementById('temp-arc'),
    tempVal:      document.getElementById('temp-val'),
    tempBadge:    document.getElementById('temp-badge'),
    humArc:       document.getElementById('hum-arc'),
    humVal:       document.getElementById('hum-val'),
    humBadge:     document.getElementById('hum-badge'),
};

// ─── Logging ───
function log(msg, type) {
    const d = document.createElement('div');
    let cls = 'log-entry';
    if (type === 'ir') cls += ' log-entry--ir';
    else if (type === 'start') cls += ' log-entry--start';
    else if (type === 'stop') cls += ' log-entry--stop';
    d.className = cls;
    d.textContent = `[${new Date().toLocaleTimeString()}]  ${msg}`;
    els.logBox.prepend(d);
    while (els.logBox.children.length > 40) {
        els.logBox.removeChild(els.logBox.lastChild);
    }
}

// ─── UI State Sync ───
function syncUI(connected) {
    if (!connected) {
        els.statusDot.className  = 'dot dot--offline';
        els.statusText.textContent = 'Odpojené';
    } else if (isRunning) {
        els.statusDot.className  = 'dot dot--running';
        els.statusText.textContent = 'Monitorovanie aktívne';
    } else if (isOpen) {
        els.statusDot.className  = 'dot dot--online';
        els.statusText.textContent = 'Systém pripravený';
    } else {
        els.statusDot.className  = 'dot dot--offline';
        els.statusText.textContent = 'Pripojené — čaká na Open';
    }

    els.btnOpen.disabled  = !connected || isOpen;
    els.btnStart.disabled = !connected || !isOpen || isRunning;
    els.btnStop.disabled  = !connected || !isRunning;
    els.btnClose.disabled = !connected || !isOpen;
}

function send(payload) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(payload));
    }
}

// ─── SVG Gauge Logic (MISA style) ───
const ARC = 377;
const CIRC = 503;

function setGauge(arcEl, valEl, badgeEl, value, min, max, unit) {
    const pct = Math.max(0, Math.min(1, (value - min) / (max - min)));
    const filled = ARC * pct;
    const gap = CIRC - filled;
    arcEl.setAttribute('stroke-dasharray', `${filled.toFixed(1)} ${gap.toFixed(1)}`);
    valEl.textContent = value.toFixed(1);
    badgeEl.textContent = `${value.toFixed(1)} ${unit}`;
}

// ─── Chart.js (MISA style — Dual Y-Axis) ───
const MAX_CHART_POINTS = 30;
const chart = new Chart(document.getElementById('main-chart').getContext('2d'), {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'Teplota (°C)',
                data: [],
                borderColor: '#f97316',
                backgroundColor: 'rgba(249,115,22,0.08)',
                fill: true,
                tension: 0.35,
                pointRadius: 0,
                borderWidth: 2,
                yAxisID: 'yTemp',
            },
            {
                label: 'Vlhkosť (%)',
                data: [],
                borderColor: '#38bdf8',
                backgroundColor: 'rgba(56,189,248,0.08)',
                fill: true,
                tension: 0.35,
                pointRadius: 0,
                borderWidth: 2,
                yAxisID: 'yHum',
            },
        ],
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 400 },
        interaction: { mode: 'index', intersect: false },
        plugins: {
            legend: {
                labels: {
                    color: '#94a3b8',
                    font: { family: "'Outfit', sans-serif", size: 12 },
                    boxWidth: 10,
                    boxHeight: 10,
                    usePointStyle: true,
                    pointStyle: 'circle',
                }
            },
            tooltip: {
                backgroundColor: 'rgba(10,15,28,0.96)',
                borderColor: 'rgba(255,255,255,0.08)',
                borderWidth: 1,
                titleColor: '#64748b',
                bodyColor: '#f1f5f9',
                padding: 12,
                cornerRadius: 10,
                callbacks: {
                    label: ctx => {
                        const unit = ctx.datasetIndex === 0 ? ' °C' : ' %';
                        return ` ${ctx.dataset.label.split(' ')[0]}: ${ctx.parsed.y.toFixed(1)}${unit}`;
                    }
                }
            }
        },
        scales: {
            x: {
                grid: { color: 'rgba(255,255,255,0.04)' },
                ticks: {
                    color: '#475569',
                    maxTicksLimit: 8,
                    font: { family: "'Outfit', sans-serif", size: 11 },
                },
                border: { color: 'rgba(255,255,255,0.06)' },
            },
            yTemp: {
                position: 'left',
                grid: { color: 'rgba(255,255,255,0.04)' },
                border: { color: 'rgba(255,255,255,0.06)' },
                ticks: {
                    color: '#f97316',
                    font: { family: "'Outfit', sans-serif", size: 11 },
                    callback: v => v.toFixed(0) + ' °C',
                },
                suggestedMin: 15,
                suggestedMax: 40,
            },
            yHum: {
                position: 'right',
                grid: { drawOnChartArea: false },
                border: { color: 'rgba(255,255,255,0.06)' },
                ticks: {
                    color: '#38bdf8',
                    font: { family: "'Outfit', sans-serif", size: 11 },
                    callback: v => v.toFixed(0) + ' %',
                },
                suggestedMin: 20,
                suggestedMax: 80,
            },
        },
    },
});

function addChartPoint(label, temp, hum) {
    if (chart.data.labels.length >= MAX_CHART_POINTS) {
        chart.data.labels.shift();
        chart.data.datasets[0].data.shift();
        chart.data.datasets[1].data.shift();
    }
    chart.data.labels.push(label);
    chart.data.datasets[0].data.push(temp);
    chart.data.datasets[1].data.push(hum);
    chart.update('none');
}

// ─── Table Row ───
function addHistoryRow(ts, temp, hum, light) {
    const tr = els.historyBody.insertRow(0);
    const lightColor = light ? '#eab308' : '#64748b';
    const lightText = light ? '☀️ Priame' : '🌑 Tieň';
    tr.innerHTML = `<td>${ts}</td><td>${parseFloat(temp).toFixed(1)}</td><td>${parseFloat(hum).toFixed(1)}</td><td style="color:${lightColor}; font-weight:600; font-size:0.78rem">${lightText}</td>`;
    if (els.historyBody.rows.length > 50) els.historyBody.deleteRow(-1);
}

// ─── Light Indicator ───
function updateLight(light, lightVal) {
    if (light) {
        els.lightDot.className = 'light-dot light-dot--active';
        els.lightText.textContent = 'Priame svetlo';
        els.lightText.style.color = '#eab308';
    } else {
        els.lightDot.className = 'light-dot';
        els.lightText.textContent = 'Tieň';
        els.lightText.style.color = '';
    }
    els.lightVal.textContent = lightVal;
}

// ─── IR Badge ───
function updateIRBadge(trigger, action) {
    if (!trigger) return;
    const badge = els.irBadge;
    if (action === 'start') {
        badge.textContent = `▶ START — ${trigger}`;
        badge.className = 'ir-badge ir-badge--start';
    } else if (action === 'stop') {
        badge.textContent = `■ STOP — ${trigger}`;
        badge.className = 'ir-badge ir-badge--stop';
    }
}

// ─── WebSocket Message Handler ───
function handleMessage(event) {
    const msg = JSON.parse(event.data);

    if (msg.type === 'response') {
        const { status, message } = msg.data;
        log(message);
        if (status === 'success') {
            if (message.includes('initialized')) isOpen = true;
            if (message.includes('started')) isRunning = true;
            if (message.includes('stopped')) isRunning = false;
            if (message.includes('deactivated')) { isOpen = false; isRunning = false; }
        }
        syncUI(true);

    } else if (msg.type === 'status_update') {
        const { action, message, trigger, isRunning: runState, isOpen: openState } = msg.data;
        isOpen = openState;
        isRunning = runState;

        let logText = message;
        let logType = null;
        if (trigger) {
            logText += ` (cez ${trigger})`;
            logType = 'ir';
            updateIRBadge(trigger, action);
        }
        if (action === 'start') logType = logType || 'start';
        if (action === 'stop') logType = logType || 'stop';
        log(logText, logType);

        // Ak bolo zastavené cez IR, špeciálny status
        if (action === 'stop' && trigger) {
            els.statusDot.className = 'dot dot--stopped-ir';
            els.statusText.textContent = `Zastavené cez ${trigger}`;
        } else {
            syncUI(true);
        }

        // Pre non-IR eventy, sync normálne
        if (!trigger || action !== 'stop') {
            syncUI(true);
        }

    } else if (msg.type === 'sensor_data') {
        const { timestamp, temp, hum, light, light_val } = msg.data;

        // Ciferníky
        setGauge(els.tempArc, els.tempVal, els.tempBadge, temp, 0, 50, '°C');
        setGauge(els.humArc, els.humVal, els.humBadge, hum, 0, 100, '%');

        // Info karta
        els.lastUpdate.textContent = timestamp;
        updateLight(light, light_val);

        // Graf a tabuľka
        addChartPoint(timestamp.split(' ')[1], temp, hum);
        addHistoryRow(timestamp, temp, hum, light);
    }
}

// ─── WebSocket Connection ───
function connect() {
    socket = new WebSocket(WS_URL);
    socket.onopen = () => {
        log('Pripojené k serveru.');
        syncUI(true);
    };
    socket.onclose = () => {
        log('Odpojené. Opätovné pripájanie...');
        isOpen = false;
        isRunning = false;
        syncUI(false);
        setTimeout(connect, 3000);
    };
    socket.onmessage = handleMessage;
}

// ─── Load History from Database ───
async function loadHistory() {
    try {
        const res = await fetch('/api/history');
        if (res.ok) {
            const data = await res.json();
            const sortedData = [...data].reverse();

            // Vyčistenie
            chart.data.labels = [];
            chart.data.datasets[0].data = [];
            chart.data.datasets[1].data = [];
            els.historyBody.innerHTML = '';

            // Naplnenie grafu a tabuľky
            sortedData.forEach(d => {
                addChartPoint(d.timestamp.split(' ')[1], d.temp, d.hum);
                addHistoryRow(d.timestamp, d.temp, d.hum, d.light);
            });

            // Nastavenie ciferníkov podľa posledného záznamu
            if (data.length > 0) {
                const latest = data[0];
                setGauge(els.tempArc, els.tempVal, els.tempBadge, latest.temp, 0, 50, '°C');
                setGauge(els.humArc, els.humVal, els.humBadge, latest.hum, 0, 100, '%');
                els.lastUpdate.textContent = latest.timestamp;
                updateLight(latest.light, latest.light_val);
            }
        }
    } catch (e) {
        console.error('Chyba pri načítaní histórie:', e);
    }
}

// ─── Button Events ───
els.btnOpen.onclick  = () => send({ action: 'open' });
els.btnStart.onclick = () => send({ action: 'start' });
els.btnStop.onclick  = () => send({ action: 'stop' });
els.btnClose.onclick = () => send({ action: 'close' });
els.btnSet.onclick   = () => send({ action: 'set_params', interval: parseFloat(els.interval.value) });

// ─── Init ───
syncUI(false);
connect();
loadHistory();
