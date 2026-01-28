/**
 * AI SEO Auditor - Frontend JavaScript
 */

// =====  Configuration  =====
const API_BASE = 'http://localhost:8000/api/v1';
const POLL_INTERVAL = 2000; // 2 seconds

// ===== State =====
let currentJobId = null;
let pollTimer = null;
let auditData = null;

// ===== DOM Elements =====
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

// ===== Initialize =====
document.addEventListener('DOMContentLoaded', () => {
    initForm();
    initTabs();
    initFilters();
    initExport();
    initAdvancedOptions();
});

// ===== Form Handling =====
function initForm() {
    const form = $('#audit-form');
    const urlInput = $('#url-input');
    const submitBtn = $('#submit-btn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const url = urlInput.value.trim();
        if (!url) return;

        // Normalize URL
        let normalizedUrl = url;
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            normalizedUrl = 'https://' + url;
        }

        // Disable form
        submitBtn.disabled = true;
        $('.btn-text').style.display = 'none';
        $('.btn-loading').style.display = 'inline-block';

        try {
            await startAudit(normalizedUrl);
        } catch (error) {
            console.error('Audit failed:', error);
            alert('Failed to start audit: ' + error.message);
            resetForm();
        }
    });
}

function resetForm() {
    const submitBtn = $('#submit-btn');
    submitBtn.disabled = false;
    $('.btn-text').style.display = 'inline-block';
    $('.btn-loading').style.display = 'none';
}

// ===== API Calls =====
async function startAudit(url) {
    const includePerf = $('#include-perf').checked;

    try {
        const response = await fetch(`${API_BASE}/audit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                include_perf: includePerf
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API error');
        }

        const data = await response.json();

        // Start polling using the job_id
        startPolling(data.job_id);

    } catch (error) {
        console.error('API Error:', error);
        showToast('Audit failed: ' + error.message);
        resetForm();
    }
}

function startPolling(jobId) {
    pollTimer = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/audit/${jobId}`);

            if (response.ok) {
                const data = await response.json();

                if (data.status === 'completed') {
                    clearInterval(pollTimer);
                    auditData = data;
                    showResults(data);
                    resetForm();
                } else if (data.status === 'failed') {
                    clearInterval(pollTimer);
                    showToast('Audit failed: ' + (data.error || 'Unknown error'));
                    resetForm();
                }
                // If status is 'pending' or 'running', do nothing and wait for next poll
            }
        } catch (error) {
            console.error('Polling error:', error);
        }
    }, POLL_INTERVAL);
}

// Transform backend response to frontend format
function transformBackendResponse(data) {
    return {
        url: data.url,
        final_url: data.final_url,
        status: data.error ? 'failed' : 'completed',
        started_at: data.started_at,
        completed_at: data.completed_at,
        duration_seconds: data.duration_seconds,
        scores: {
            technical: data.scores?.technical || 0,
            content: data.scores?.content || 0,
            ai: data.scores?.ai || 0,
            overall: data.scores?.overall || 0
        },
        confidence: {
            level: data.confidence?.level || 'medium',
            score: data.confidence?.score || 50,
            missing: data.confidence?.missing || [],
            reason: data.confidence?.reason || 'Data collected'
        },
        caps_applied: data.caps_applied || [],
        labels: data.labels || [],
        checks: data.checks || [],
        scoring_version: data.scoring_version || '1.1',
        error: data.error
    };
}

// Keep mock function for offline demo mode only
async function fetchMockResults(url) {
    // For demonstration without backend
    const mockData = generateMockResults(url);
    auditData = mockData;
    showResults(mockData);
    resetForm();
}

function generateMockResults(url) {
    // Generate realistic mock data with v1.1 weights (35/35/30)
    const technical = Math.floor(Math.random() * 20) + 75;  // 75-95
    const content = Math.floor(Math.random() * 25) + 70;    // 70-95
    const ai = Math.floor(Math.random() * 30) + 60;         // 60-90
    // v1.1 weights: Technical 35%, Content 35%, AI 30%
    const overall = Math.floor((technical * 0.35) + (content * 0.35) + (ai * 0.30));

    return {
        url: url,
        final_url: url,
        status: 'completed',
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        duration_seconds: 5.2,
        scores: {
            technical: technical,
            content: content,
            ai: ai,
            overall: overall
        },
        confidence: {
            level: overall > 70 ? 'high' : overall > 50 ? 'medium' : 'low',
            score: 85,
            missing: ['performance'],
            reason: 'Most data sources available'
        },
        caps_applied: [],
        labels: [],
        checks: [
            // Technical checks - Crawlability
            { id: 'status_code', name: 'HTTP Status Code', category: 'crawlability', points_awarded: 10, points_possible: 10, status: 'pass', evidence: 'Status: 200', severity: 'P2' },
            { id: 'redirects', name: 'Redirect Chain', category: 'crawlability', points_awarded: 5, points_possible: 5, status: 'pass', evidence: 'No redirects', severity: 'P2' },
            { id: 'canonical', name: 'Canonical Tag', category: 'crawlability', points_awarded: 8, points_possible: 8, status: 'pass', evidence: 'Valid self-referencing canonical', severity: 'P2' },
            { id: 'meta_robots', name: 'Indexability', category: 'crawlability', points_awarded: 7, points_possible: 7, status: 'pass', evidence: 'Page is indexable', severity: 'P0' },
            { id: 'sitemap', name: 'Sitemap', category: 'crawlability', points_awarded: 5, points_possible: 5, status: 'pass', evidence: 'Sitemap found', severity: 'P2' },
            { id: 'robots_txt', name: 'robots.txt', category: 'crawlability', points_awarded: 5, points_possible: 5, status: 'pass', evidence: 'robots.txt found', severity: 'P2' },

            // Technical checks - Performance
            { id: 'performance', name: 'Performance Score', category: 'performance', points_awarded: 7, points_possible: 12, status: 'partial', evidence: 'Performance metrics not checked', severity: 'P2' },
            { id: 'mobile', name: 'Mobile Viewport', category: 'performance', points_awarded: 10, points_possible: 10, status: 'pass', evidence: 'Viewport meta tag present', severity: 'P1' },
            { id: 'https', name: 'HTTPS', category: 'performance', points_awarded: 8, points_possible: 8, status: 'pass', evidence: 'Site uses HTTPS', severity: 'P0' },

            // Technical checks - Hygiene
            { id: 'title', name: 'Title Tag', category: 'hygiene', points_awarded: 10, points_possible: 10, status: 'pass', evidence: 'Title length: 65 chars', severity: 'P1' },
            { id: 'meta_desc', name: 'Meta Description', category: 'hygiene', points_awarded: 8, points_possible: 8, status: 'pass', evidence: 'Description length: 145 chars', severity: 'P1' },
            { id: 'h1', name: 'H1 Tag', category: 'hygiene', points_awarded: 7, points_possible: 7, status: 'pass', evidence: 'Single H1 tag found', severity: 'P1' },
            { id: 'heading_hierarchy', name: 'Heading Hierarchy', category: 'hygiene', points_awarded: 5, points_possible: 5, status: 'pass', evidence: 'Valid heading hierarchy', severity: 'P2' },
            { id: 'charset', name: 'Charset Declaration', category: 'hygiene', points_awarded: 3, points_possible: 3, status: 'pass', evidence: 'Charset declared', severity: 'P2' },
            { id: 'html_lang', name: 'HTML Lang Attribute', category: 'hygiene', points_awarded: 3, points_possible: 3, status: 'pass', evidence: 'HTML lang attribute declared', severity: 'P2' },
            { id: 'image_alt', name: 'Image Alt Text', category: 'hygiene', points_awarded: 5, points_possible: 5, status: 'pass', evidence: '88/161 images have alt (55%)', severity: 'P2' },
            { id: 'internal_links', name: 'Internal Links', category: 'hygiene', points_awarded: 3, points_possible: 3, status: 'pass', evidence: '314 internal links', severity: 'P2' },

            // AI checks  
            { id: 'ai_access', name: 'AI Crawler Access', category: 'ai_access', points_awarded: 25, points_possible: 25, status: 'pass', evidence: 'AI crawlers allowed', severity: 'P0' },
            { id: 'llms_exists', name: 'llms.txt File', category: 'llms_txt', points_awarded: 2, points_possible: 5, status: 'partial', evidence: 'No llms.txt (optional)', how_to_fix: 'Create /llms.txt for enhanced AI discoverability', severity: 'P2' },
            { id: 'llms_quality', name: 'llms.txt Quality', category: 'llms_txt', points_awarded: 5, points_possible: 10, status: 'partial', evidence: 'llms.txt not present (optional)', severity: 'P2' },
            { id: 'schema_exists', name: 'JSON-LD Schema', category: 'schema', points_awarded: 12, points_possible: 12, status: 'pass', evidence: 'Schema types: Organization', severity: 'P1' },
            { id: 'schema_types', name: 'Schema Types', category: 'schema', points_awarded: 18, points_possible: 18, status: 'pass', evidence: 'Schema types: Organization', severity: 'P2' },
            { id: 'og_tags', name: 'Open Graph Tags', category: 'social', points_awarded: 8, points_possible: 8, status: 'pass', evidence: 'Open Graph tags present', severity: 'P2' },
            { id: 'twitter', name: 'Twitter Cards', category: 'social', points_awarded: 0, points_possible: 7, status: 'fail', evidence: 'Missing Twitter Card tags', how_to_fix: 'Add twitter:card, twitter:title, twitter:description meta tags', severity: 'P1' },
            { id: 'extractability', name: 'Content Extractability', category: 'extractability', points_awarded: 15, points_possible: 15, status: 'pass', evidence: 'Good extractable content', severity: 'P2' },

            // Content checks
            { id: 'clarity', name: 'Content Clarity', category: 'clarity', points_awarded: 25, points_possible: 25, status: 'pass', evidence: 'Clear purpose and audience defined', severity: 'P1' },
            { id: 'heading_structure', name: 'Heading Structure', category: 'structure', points_awarded: 10, points_possible: 10, status: 'pass', evidence: 'Good structure: 1 H1, 8 H2s', severity: 'P2' },
            { id: 'word_count', name: 'Content Length', category: 'structure', points_awarded: 10, points_possible: 10, status: 'pass', evidence: '2213 words', severity: 'P2' },
            { id: 'readability', name: 'Readability', category: 'structure', points_awarded: 5, points_possible: 5, status: 'pass', evidence: 'Good readability', severity: 'P2' },
            { id: 'trust', name: 'Trust Signals', category: 'completeness', points_awarded: 15, points_possible: 15, status: 'pass', evidence: 'Trust signals present', severity: 'P2' },
            { id: 'internal_links_content', name: 'Internal Links', category: 'completeness', points_awarded: 10, points_possible: 10, status: 'pass', evidence: '314 internal links', severity: 'P2' },
            { id: 'freshness', name: 'Content Freshness', category: 'freshness', points_awarded: 12, points_possible: 25, status: 'partial', evidence: 'No date found, but substantial content', how_to_fix: 'Add published or last-updated date', severity: 'P2' }
        ],
        scoring_version: '1.1'
    };
}

// ===== Display Results =====
function showResults(data) {
    // Hide hero, show results
    $('#hero-section').style.display = 'none';
    $('#results-section').style.display = 'block';

    // Update URL display
    const urlLink = $('#result-url');
    urlLink.href = data.final_url || data.url;
    urlLink.textContent = new URL(data.final_url || data.url).hostname;

    // Update scores with animation
    animateScore('overall', data.scores.overall);
    animateScore('technical', data.scores.technical);
    animateScore('content', data.scores.content);
    animateScore('ai', data.scores.ai);

    // Update confidence
    const confLevel = $('#confidence-level');
    confLevel.textContent = data.confidence.level.toUpperCase();
    confLevel.className = 'confidence-level ' + data.confidence.level;
    $('#confidence-reason').textContent = data.confidence.reason;

    // Show labels if any
    if (data.labels.length > 0) {
        const labelsSection = $('#labels-section');
        labelsSection.style.display = 'block';
        const labelsContainer = $('#labels');
        labelsContainer.innerHTML = data.labels.map(l =>
            `<span class="label">${l}</span>`
        ).join('');
    }

    // Populate issues (failed checks)
    populateIssues(data.checks);

    // Populate breakdown
    populateBreakdown(data.checks);
}

function animateScore(id, value) {
    const scoreEl = $(`#${id}-score`);
    const barEl = $(`#${id}-bar`);

    // Animate number
    let current = 0;
    const duration = 1000;
    const step = value / (duration / 16);

    const timer = setInterval(() => {
        current += step;
        if (current >= value) {
            current = value;
            clearInterval(timer);
        }
        scoreEl.textContent = Math.round(current);
    }, 16);

    // Update bar color based on score
    barEl.className = 'score-bar';
    if (value >= 80) barEl.classList.add('excellent');
    else if (value >= 60) barEl.classList.add('good');
    else if (value >= 40) barEl.classList.add('needs-work');
    else barEl.classList.add('poor');

    // Animate bar
    setTimeout(() => {
        barEl.style.width = value + '%';
    }, 100);
}

function populateIssues(checks) {
    const issues = checks.filter(c => c.status === 'fail' || c.status === 'partial');

    // Sort by severity
    const severityOrder = { 'P0': 0, 'P1': 1, 'P2': 2 };
    issues.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);

    const listEl = $('#issues-list');
    listEl.innerHTML = issues.map(issue => `
        <div class="issue-item ${issue.severity}" data-severity="${issue.severity}">
            <div class="issue-header">
                <span class="issue-name">${issue.name}</span>
                <span class="issue-severity ${issue.severity}">${issue.severity}</span>
            </div>
            <p class="issue-evidence">${issue.evidence}</p>
            ${issue.how_to_fix ? `<p class="issue-fix">💡 ${issue.how_to_fix}</p>` : ''}
        </div>
    `).join('');
}

function populateBreakdown(checks) {
    const categories = {
        technical: ['crawlability', 'performance', 'hygiene'],
        content: ['clarity', 'structure', 'completeness', 'freshness', 'trust_auth'],
        ai: ['ai_access', 'llms_txt', 'schema', 'social', 'extractability']
    };

    for (const [section, cats] of Object.entries(categories)) {
        const sectionChecks = checks.filter(c => cats.includes(c.category));
        const listEl = $(`#${section}-checks`);

        listEl.innerHTML = sectionChecks.map(check => `
            <div class="check-item">
                <div class="check-info">
                    <span class="check-status ${check.status}">${getStatusIcon(check.status)}</span>
                    <span class="check-name">${check.name}</span>
                </div>
                <span class="check-points">${check.points_awarded}/${check.points_possible}</span>
            </div>
        `).join('');
    }
}

function getStatusIcon(status) {
    switch (status) {
        case 'pass': return '✓';
        case 'partial': return '◐';
        case 'fail': return '✗';
        case 'skip': return '−';
        default: return '?';
    }
}

// ===== Tabs =====
function initTabs() {
    const tabs = $$('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Update active tab
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Show corresponding content
            const tabName = tab.dataset.tab;
            $$('.tab-content').forEach(content => {
                content.classList.remove('active');
                content.style.display = 'none';
            });
            $(`#${tabName}-tab`).classList.add('active');
            $(`#${tabName}-tab`).style.display = 'block';
        });
    });
}

// ===== Filters =====
function initFilters() {
    const filterBtns = $$('.filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Update active filter
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Filter issues
            const severity = btn.dataset.severity;
            $$('.issue-item').forEach(item => {
                if (severity === 'all' || item.dataset.severity === severity) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    });
}

// ===== Advanced Options =====
function initAdvancedOptions() {
    const toggle = $('#options-toggle');
    const options = $('#advanced-options');

    toggle.addEventListener('click', () => {
        toggle.classList.toggle('open');
        options.style.display = options.style.display === 'none' ? 'block' : 'none';
    });
}

// ===== Export =====
function initExport() {
    $('#export-pdf').addEventListener('click', async () => {
        if (!auditData) return;

        const btn = $('#export-pdf');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<span class="spinner"></span> Generating...';
        btn.disabled = true;

        try {
            const response = await fetch(`${API_BASE}/audit/${auditData.job_id}/pdf`);
            if (!response.ok) throw new Error('Failed to generate PDF');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `svata-audit-${new Date().toISOString().split('T')[0]}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            showToast('PDF Report downloaded!');

        } catch (error) {
            console.error('PDF Error:', error);
            showToast('PDF generation failed. Try again.');
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    });

    $('#export-json').addEventListener('click', () => {
        if (!auditData) return;

        const blob = new Blob([JSON.stringify(auditData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `seo-audit-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
    });

    $('#copy-link').addEventListener('click', () => {
        // For demo, just copy current URL
        const url = window.location.href;
        navigator.clipboard.writeText(url).then(() => {
            // Show toast instead of alert
            showToast('Link copied to clipboard!');
        });
    });

    // New Audit button
    $('#new-audit').addEventListener('click', () => {
        // Hide results, show hero
        $('#results-section').style.display = 'none';
        $('#hero-section').style.display = 'flex';
        $('#url-input').value = '';
        $('#url-input').focus();
    });
}

// ===== Toast Notification =====
function showToast(message) {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 24px;
        left: 50%;
        transform: translateX(-50%);
        padding: 12px 24px;
        background: var(--svata-card);
        border: 1px solid var(--svata-gold);
        border-radius: 8px;
        color: var(--svata-gold);
        font-size: 14px;
        z-index: 1000;
        animation: fadeIn 0.3s ease;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 2000);
}
