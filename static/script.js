// =========================================
// CONFIG & STATE
// =========================================
const API_BASE = 'http://localhost:8000';

// --- 🔐 API KEY (Must match your .env API_KEY) ---
// For local development, store it here. In production, use a secure backend proxy.
const API_KEY = 'awvJVdB9T_RAcXOzT47WPhgPPssgH7Hjf49eVjXNVtM';  // <-- REPLACE with your actual key from .env

let currentEmail = 'test@example.com';
let currentReply = '';

// =========================================
// DOM REFS
// =========================================
const emailInput = document.getElementById('emailInput');
const nameInput = document.getElementById('nameInput');
const questionInput = document.getElementById('questionInput');
const submitBtn = document.getElementById('submitBtn');
const responseArea = document.getElementById('responseArea');
const replyContent = document.getElementById('replyContent');
const historyList = document.getElementById('historyList');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');
const backendStatusText = document.getElementById('backendStatusText');
const judgeStatusText = document.getElementById('judgeStatusText');
const statusBadge = document.getElementById('statusBadge');

// Step elements
const step1 = document.getElementById('step1');
const step2 = document.getElementById('step2');
const step3 = document.getElementById('step3');

// Metrics
const metricTime = document.getElementById('metricTime');
const metricWords = document.getElementById('metricWords');
const metricLength = document.getElementById('metricLength');

// Raw Inspector
const inspectorCard = document.getElementById('inspectorCard');
const inspectorHeader = document.getElementById('inspectorHeader');
const inspectorContent = document.getElementById('inspectorContent');

// =========================================
// UTILITY: Step progress indicators
// =========================================
function setStep(step, state) {
    const dot = step.querySelector('.dot');
    dot.className = 'dot';
    if (state === 'active') {
        dot.classList.add('active');
        step.className = 'step active-text';
    } else if (state === 'done') {
        dot.classList.add('done');
        step.className = 'step done-text';
    } else {
        dot.classList.add('waiting');
        step.className = 'step';
    }
}

function resetSteps() {
    setStep(step1, 'waiting');
    setStep(step2, 'waiting');
    setStep(step3, 'waiting');
}

function showProgress(step) {
    if (step === 1) {
        setStep(step1, 'active');
        setStep(step2, 'waiting');
        setStep(step3, 'waiting');
    } else if (step === 2) {
        setStep(step1, 'done');
        setStep(step2, 'active');
        setStep(step3, 'waiting');
    } else if (step === 3) {
        setStep(step1, 'done');
        setStep(step2, 'done');
        setStep(step3, 'active');
    } else if (step === 'done') {
        setStep(step1, 'done');
        setStep(step2, 'done');
        setStep(step3, 'done');
    }
}

// =========================================
// 🔐 HELPER: Get headers with API Key
// =========================================
function getHeaders(extraHeaders = {}) {
    return {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,  // <-- CRITICAL: Authentication
        ...extraHeaders
    };
}

// =========================================
// API SERVICES
// =========================================
async function checkHealth() {
    try {
        const res = await fetch(`${API_BASE}/health`);
        if (res.ok) {
            backendStatusText.textContent = 'Online';
            backendStatusText.style.color = 'var(--success)';
            statusBadge.textContent = '● Online';
            statusBadge.className = 'badge badge-online';
            return true;
        }
        throw new Error('Unhealthy');
    } catch {
        backendStatusText.textContent = 'Offline';
        backendStatusText.style.color = 'var(--error)';
        statusBadge.textContent = '● Offline';
        statusBadge.className = 'badge badge-offline';
        return false;
    }
}

async function fetchJudgeStatus() {
    try {
        const res = await fetch(`${API_BASE}/api/hitl/status`);
        if (res.ok) {
            const data = await res.json();
            if (data.mode) {
                judgeStatusText.textContent = 'Manual Approval';
                judgeStatusText.className = 'badge-judge manual';
            } else {
                judgeStatusText.textContent = 'Auto-Send';
                judgeStatusText.className = 'badge-judge auto';
            }
            return;
        }
        judgeStatusText.textContent = 'Unknown';
        judgeStatusText.className = 'badge-judge auto';
    } catch {
        judgeStatusText.textContent = 'Offline';
        judgeStatusText.className = 'badge-judge auto';
    }
}

async function sendMessage(email, message) {
    const payload = { email, message };
    const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: getHeaders(),  // <-- Includes API Key
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(120000),
    });
    if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Server Error: ${res.status} - ${errText}`);
    }
    return await res.json();
}

async function clearHistory(email) {
    try {
        const res = await fetch(`${API_BASE}/clear_history/${encodeURIComponent(email)}`, {
            method: 'POST',
            headers: getHeaders(),  // <-- Includes API Key
        });
        return res.ok;
    } catch {
        return false;
    }
}

// =========================================
// UI CONTROLS & RENDER
// =========================================
function renderHistory(history) {
    historyList.innerHTML = '';
    if (!history || history.length === 0) {
        historyList.innerHTML = '<p class="empty-history">No conversations yet.</p>';
        return;
    }

    const items = history.slice(-5).reverse();
    items.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = 'history-item';
        const questionText = typeof item === 'object' ? item.question : item[0];
        div.textContent = `• ${questionText.substring(0, 30)}${questionText.length > 30 ? '...' : ''}`;
        div.title = "Click to load this history details";
        
        div.addEventListener('click', () => {
            loadHistoryItem(item);
        });
        historyList.appendChild(div);
    });
}

function loadHistoryItem(item) {
    if (!item) return;
    
    let questionText = "";
    let replyText = "";
    let elapsed = 0.0;
    
    if (typeof item === 'object') {
        questionText = item.question;
        replyText = item.reply;
        elapsed = item.elapsed || 0.0;
    } else {
        questionText = item[0];
        replyText = item[1];
    }
    
    questionInput.value = questionText;
    currentReply = replyText;
    replyContent.textContent = currentReply;
    
    metricTime.textContent = typeof elapsed === 'number' ? `${elapsed.toFixed(1)}s` : elapsed;
    metricWords.textContent = replyText.split(/\s+/).filter(Boolean).length;
    metricLength.textContent = questionText.split(/\s+/).filter(Boolean).length;
    
    inspectorContent.textContent = JSON.stringify({ question: questionText, reply: replyText }, null, 2);
    
    responseArea.style.display = 'block';
    showProgress('done');
    responseArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showReply(data, elapsed, question) {
    currentReply = data.reply || 'No reply generated.';
    replyContent.textContent = currentReply;

    metricTime.textContent = `${elapsed.toFixed(1)}s`;
    metricWords.textContent = currentReply.split(/\s+/).filter(Boolean).length;
    metricLength.textContent = question.split(/\s+/).filter(Boolean).length;

    inspectorContent.textContent = JSON.stringify(data, null, 2);

    responseArea.style.display = 'block';
    responseArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// =========================================
// HANDLERS
// =========================================
async function handleSubmit(e) {
    e.preventDefault();

    const email = emailInput.value.trim();
    const question = questionInput.value.trim();

    if (!email) { alert('Please enter an email.'); return; }
    if (!question) { alert('Please describe your issue.'); return; }

    currentEmail = email;

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating reply...';
    responseArea.style.display = 'none';
    resetSteps();

    showProgress(1);
    const startTime = performance.now();

    try {
        setTimeout(() => showProgress(2), 500);

        const data = await sendMessage(email, question);
        const elapsed = (performance.now() - startTime) / 1000;

        showProgress(3);
        setTimeout(() => showProgress('done'), 500);

        let history = JSON.parse(localStorage.getItem('chat_history') || '[]');
        history.push({
            question: question,
            reply: data.reply,
            elapsed: elapsed,
            timestamp: new Date().toISOString()
        });
        localStorage.setItem('chat_history', JSON.stringify(history));
        renderHistory(history);

        showReply(data, elapsed, question);
    } catch (err) {
        alert(`❌ Error: ${err.message}`);
        resetSteps();
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Generate Draft Reply';
    }
}

function handleClearHistory() {
    if (!confirm('Are you sure you want to clear all chat history?')) return;
    clearHistory(currentEmail);
    localStorage.removeItem('chat_history');
    renderHistory([]);
    responseArea.style.display = 'none';
}

function handleExampleClick(e) {
    const query = e.currentTarget.getAttribute('data-query');
    questionInput.value = query;
    questionInput.focus();
}

function handleDownload() {
    if (!currentReply) return;
    const blob = new Blob([currentReply], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `reply_${currentEmail.split('@')[0]}_${new Date().toISOString().slice(0,10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
}

function handleCopy() {
    if (!currentReply) return;
    navigator.clipboard.writeText(currentReply).then(() => {
        const btn = document.getElementById('copyBtn');
        const orig = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
        setTimeout(() => btn.innerHTML = orig, 2000);
    });
}

function toggleInspector() {
    inspectorCard.classList.toggle('open');
}

// =========================================
// INIT
// =========================================
async function init() {
    function updateClock() {
        const now = new Date();
        const hrs = now.getHours().toString().padStart(2, '0');
        const mins = now.getMinutes().toString().padStart(2, '0');
        document.getElementById('headerTime').textContent = `🕒 ${hrs}:${mins}`;
    }
    updateClock();
    setInterval(updateClock, 15000);

    const online = await checkHealth();
    if (online) await fetchJudgeStatus();

    const saved = JSON.parse(localStorage.getItem('chat_history') || '[]');
    renderHistory(saved);

    document.getElementById('chatForm').addEventListener('submit', handleSubmit);
    document.getElementById('clearFormBtn').addEventListener('click', () => {
        questionInput.value = '';
        responseArea.style.display = 'none';
    });
    clearHistoryBtn.addEventListener('click', handleClearHistory);
    document.querySelectorAll('.example-btn').forEach(btn => {
        btn.addEventListener('click', handleExampleClick);
    });
    document.getElementById('downloadBtn').addEventListener('click', handleDownload);
    document.getElementById('copyBtn').addEventListener('click', handleCopy);
    inspectorHeader.addEventListener('click', toggleInspector);

    const params = new URLSearchParams(window.location.search);
    const queryParam = params.get('query');
    if (queryParam) {
        questionInput.value = queryParam;
        handleSubmit(new Event('submit'));
    }
}

document.addEventListener('DOMContentLoaded', init);