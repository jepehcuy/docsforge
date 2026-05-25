/* DocsForge — Frontend Application Logic */

(function () {
    'use strict';

    // ---- State ----
    let currentTab = 'path';
    let isGenerating = false;
    let activeDocs = null;

    // ---- Init ----
    document.addEventListener('DOMContentLoaded', () => {
        loadHealth();
        loadHistory();
    });

    // ---- Tab Switching ----
    window.switchTab = function (tab) {
        currentTab = tab;
        document.querySelectorAll('.tab').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });
        document.querySelectorAll('.tab-content').forEach(c => {
            c.classList.toggle('active', c.id === tab + 'Input');
        });
    };

    // ---- Health Check ----
    async function loadHealth() {
        try {
            const resp = await fetch('/api/health');
            const data = await resp.json();
            document.getElementById('modelBadge').textContent = data.model || 'unknown';
        } catch {
            document.getElementById('modelBadge').textContent = 'offline';
        }
    }

    // ---- History ----
    async function loadHistory() {
        const container = document.getElementById('historyList');
        try {
            const resp = await fetch('/api/history');
            const data = await resp.json();
            const runs = data.runs || [];

            if (runs.length === 0) {
                container.innerHTML = '<div class="empty-state">No runs yet. Generate documentation above.</div>';
                return;
            }

            container.innerHTML = runs.map(run => {
                const date = new Date(run.created_at).toLocaleDateString('en-US', {
                    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                });
                const path = run.root_path || '';
                const displayPath = path.length > 50 ? '...' + path.slice(-47) : path;
                return `
                    <div class="history-item">
                        <div class="history-left">
                            <span class="history-id">#${run.id}</span>
                            <span class="history-path">${escapeHtml(displayPath)}</span>
                        </div>
                        <div class="history-meta">
                            <span class="history-score">${run.quality_score ?? '--'}</span>
                            <span class="history-files">${run.total_files ?? 0} files</span>
                            <span class="history-date">${date}</span>
                        </div>
                    </div>
                `;
            }).join('');
        } catch {
            container.innerHTML = '<div class="empty-state">Failed to load history.</div>';
        }
    }

    // ---- Generation ----
    window.startGeneration = async function () {
        if (isGenerating) return;

        let payload = {};
        if (currentTab === 'path') {
            const path = document.getElementById('pathField').value.trim();
            if (!path) return;
            payload = { path };
        } else {
            const code = document.getElementById('codeField').value.trim();
            const language = document.getElementById('langSelect').value;
            if (!code) return;
            payload = { code, language };
        }

        isGenerating = true;
        const btn = document.getElementById('generateBtn');
        btn.disabled = true;
        btn.textContent = 'Generating...';

        // Show progress section, hide results
        document.getElementById('progressSection').style.display = '';
        document.getElementById('resultsSection').style.display = 'none';
        resetAgentCards();
        setStage('scanning');

        try {
            const resp = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data:')) {
                        const jsonStr = line.slice(5).trim();
                        if (!jsonStr) continue;
                        try {
                            const event = JSON.parse(jsonStr);
                            handleSSE(event);
                        } catch {
                            // skip malformed
                        }
                    }
                }
            }
        } catch (err) {
            setStage('Error: ' + err.message);
        } finally {
            isGenerating = false;
            btn.disabled = false;
            btn.textContent = 'Generate Documentation';
        }
    };

    function handleSSE(event) {
        switch (event.type) {
            case 'progress':
                setStage(event.stage);
                break;
            case 'scan_complete':
                setStage('Scanned ' + event.total_files + ' files in ' + event.duration + 's');
                break;
            case 'agent_complete':
                markAgentDone(event.agent, event.duration, event.confidence);
                break;
            case 'complete':
                showResults(event);
                break;
            case 'error':
                setStage('Error: ' + (event.error || 'Unknown error'));
                break;
        }
    }

    // ---- Agent Cards ----
    function resetAgentCards() {
        const agents = ['ArchitectureAgent', 'APIAgent', 'ExamplesAgent', 'ChangelogAgent', 'ConfigAgent'];
        agents.forEach(name => {
            const card = document.getElementById('agent-' + name);
            if (!card) return;
            card.className = 'agent-card';
            card.querySelector('.agent-status').textContent = 'Waiting';
            card.querySelector('.agent-duration').textContent = '';
        });
    }

    function markAgentDone(name, duration, confidence) {
        const card = document.getElementById('agent-' + name);
        if (!card) return;

        // Briefly show running state then done
        card.className = 'agent-card running';
        setTimeout(() => {
            card.className = 'agent-card done';
            card.querySelector('.agent-status').textContent = 'Done';
            card.querySelector('.agent-duration').textContent = duration + 's';
        }, 300);

        // Mark next agent as running
        const agents = ['ArchitectureAgent', 'APIAgent', 'ExamplesAgent', 'ChangelogAgent', 'ConfigAgent'];
        const idx = agents.indexOf(name);
        if (idx < agents.length - 1) {
            const next = document.getElementById('agent-' + agents[idx + 1]);
            if (next && !next.classList.contains('done')) {
                next.className = 'agent-card running';
                next.querySelector('.agent-status').textContent = 'Running...';
            }
        }
    }

    function setStage(text) {
        const el = document.getElementById('stageText');
        if (el) el.textContent = text;

        // Mark first agent as running at agent stage
        if (text === 'agents') {
            const first = document.getElementById('agent-ArchitectureAgent');
            if (first) {
                first.className = 'agent-card running';
                first.querySelector('.agent-status').textContent = 'Running...';
            }
        }
    }

    // ---- Results ----
    function showResults(event) {
        document.getElementById('resultsSection').style.display = '';
        setStage('Complete');

        // Quality score
        const score = event.quality;
        const scoreNum = document.getElementById('scoreNumber');
        animateNumber(scoreNum, 0, score.overall, 800);
        document.getElementById('scoreReasoning').textContent = score.reasoning || '';

        // Score bars
        const dims = ['completeness', 'accuracy', 'clarity', 'structure', 'usefulness'];
        const barsEl = document.getElementById('scoreBars');
        barsEl.innerHTML = dims.map(dim => `
            <div class="score-bar-row">
                <span class="score-bar-label">${dim}</span>
                <div class="score-bar-track">
                    <div class="score-bar-fill" style="width: 0%" data-target="${score[dim]}"></div>
                </div>
                <span class="score-bar-value">${score[dim]}</span>
            </div>
        `).join('');

        // Animate bars
        requestAnimationFrame(() => {
            setTimeout(() => {
                barsEl.querySelectorAll('.score-bar-fill').forEach(bar => {
                    bar.style.width = bar.dataset.target + '%';
                });
            }, 100);
        });

        // Recommendations
        const recsEl = document.getElementById('scoreRecommendations');
        if (score.recommendations && score.recommendations.length > 0) {
            recsEl.innerHTML = score.recommendations.map(r =>
                `<div class="score-rec-item">${escapeHtml(r)}</div>`
            ).join('');
        }

        // Token stats
        const tokens = event.tokens;
        document.getElementById('statsGrid').innerHTML = `
            <div class="stat-row">
                <span class="stat-label">Total tokens</span>
                <span class="stat-value">${formatNumber(tokens.total_tokens)}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Prompt tokens</span>
                <span class="stat-value">${formatNumber(tokens.total_prompt_tokens)}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Completion tokens</span>
                <span class="stat-value">${formatNumber(tokens.total_completion_tokens)}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">API calls</span>
                <span class="stat-value">${tokens.num_calls}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Total duration</span>
                <span class="stat-value">${(tokens.total_duration_ms / 1000).toFixed(1)}s</span>
            </div>
        `;

        // Scan info
        const scan = event.scan;
        document.getElementById('scanGrid').innerHTML = `
            <div class="scan-row">
                <span class="scan-label">Files scanned</span>
                <span class="scan-value">${scan.total_files}</span>
            </div>
            <div class="scan-row">
                <span class="scan-label">Lines of code</span>
                <span class="scan-value">${formatNumber(scan.total_lines)}</span>
            </div>
            ${Object.entries(scan.languages || {}).map(([lang, count]) => `
                <div class="scan-row">
                    <span class="scan-label">${lang}</span>
                    <span class="scan-value">${count} files</span>
                </div>
            `).join('')}
        `;

        // Docs tabs
        const pages = event.pages || [];
        const tabsEl = document.getElementById('docsTabs');
        tabsEl.innerHTML = pages.map((p, i) =>
            `<button class="docs-tab ${i === 0 ? 'active' : ''}" onclick="loadDocPage(${event.run_id}, '${p}', this)">${p.replace('.md', '')}</button>`
        ).join('');

        // Load docs
        activeDocs = null;
        loadDocPage(event.run_id, pages[0] || 'index.md', tabsEl.querySelector('.docs-tab'));

        // Refresh history
        loadHistory();
    }

    window.loadDocPage = async function (runId, pageName, btnEl) {
        // Update active tab
        if (btnEl) {
            btnEl.parentElement.querySelectorAll('.docs-tab').forEach(t => t.classList.remove('active'));
            btnEl.classList.add('active');
        }

        const body = document.getElementById('docsBody');

        // Check in-memory cache
        if (activeDocs && activeDocs.run_id === runId && activeDocs.pages[pageName]) {
            body.innerHTML = marked.parse(activeDocs.pages[pageName]);
            return;
        }

        body.innerHTML = '<div class="skeleton-block"></div>';

        try {
            const resp = await fetch('/api/docs/' + runId);
            const data = await resp.json();
            activeDocs = data;

            if (data.pages && data.pages[pageName]) {
                body.innerHTML = marked.parse(data.pages[pageName]);
            } else {
                body.innerHTML = '<div class="empty-state">Page not found.</div>';
            }
        } catch {
            body.innerHTML = '<div class="empty-state">Failed to load documentation.</div>';
        }
    };

    // ---- Helpers ----
    function animateNumber(el, from, to, duration) {
        const start = performance.now();
        function tick(now) {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = Math.round(from + (to - from) * eased);
            if (progress < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    }

    function formatNumber(n) {
        if (n == null) return '--';
        return n.toLocaleString();
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

})();
