/**
 * Unified Autonomous Mission Chat Client
 * =======================================
 * One single interface combining conversational intelligence and autonomous
 * repository engineering:
 *   - Unified SSE event stream (/api/v1/missions/{id}/stream)
 *   - Execution State Machine (IDLE, PLANNING, EXECUTING, TESTING, etc.)
 *   - Multimodal Screenshot Upload & Clipboard Paste (Ctrl+V / Cmd+V)
 *   - Interactive Multi-Stage Plan Approval ([Approve Plan], [Modify Plan])
 *   - Solution Selection (Option A, B, C with Tradeoffs)
 *   - Fine-Grained Permissions ([Allow Once], [Allow for Mission], [Deny])
 *   - Real-Time Streaming Terminal Output ($ pytest, npm, git)
 *   - Interactive Diff Review & Completion Reports
 *   - Slash Commands (/plan, /diff, /status, /permissions, /stop, !cmd)
 */

document.addEventListener('DOMContentLoaded', () => {
    // Mission State
    let currentMissionId = 'mission-' + Date.now();
    let isStreaming = false;
    let activeEventSource = null;
    let pendingAttachments = []; // Array of { id, filename, mime_type, base64 }
    let sessionTokens = 0;
    let sessionCost = 0.0;

    // DOM Elements
    const chatContainer = document.getElementById('chatContainer');
    const userInput = document.getElementById('userInput');
    const btnSend = document.getElementById('btnSend');
    const btnSendText = document.getElementById('btnSendText');
    const btnSendIcon = document.getElementById('btnSendIcon');
    const btnStopStream = document.getElementById('btnStopStream');
    const chkThinking = document.getElementById('chkThinking');
    const missionStatusBadge = document.getElementById('missionStatusBadge');
    const missionStatusText = document.getElementById('missionStatusText');
    const missionSelect = document.getElementById('missionSelect');
    const btnNewMission = document.getElementById('btnNewMission');
    const btnAttachImage = document.getElementById('btnAttachImage');
    const imageFileInput = document.getElementById('imageFileInput');
    const attachmentPreviewTray = document.getElementById('attachmentPreviewTray');

    // Telemetry Elements
    const statTokens = document.getElementById('statTokens');
    const statSpeed = document.getElementById('statSpeed');
    const statCost = document.getElementById('statCost');

    // Ledger Modal Elements
    const modalTotalMissions = document.getElementById('modalTotalMissions');
    const modalTotalTokens = document.getElementById('modalTotalTokens');
    const modalTotalCost = document.getElementById('modalTotalCost');
    const modalLedgerTableBody = document.getElementById('modalLedgerTableBody');

    // Initialize Missions Dropdown
    loadMissionList();

    // Auto-resize textarea
    function autoResizeTextarea() {
        userInput.style.height = 'auto';
        userInput.style.height = Math.min(userInput.scrollHeight, 180) + 'px';
    }
    userInput.addEventListener('input', autoResizeTextarea);

    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        } else if (e.key === 'Escape' && isStreaming) {
            e.preventDefault();
            stopStreaming();
        }
    });

    // Preset Prompt Helper (exposed globally)
    window.setPrompt = function(text) {
        userInput.value = text;
        autoResizeTextarea();
        userInput.focus();
    };

    // New Mission button
    btnNewMission.addEventListener('click', () => {
        currentMissionId = 'mission-' + Date.now();
        setMissionStatus('IDLE');
        chatContainer.innerHTML = '';
        appendAssistantNotice(
            'New Autonomous Mission Initialized',
            'Ready for instructions, questions, screenshots, or terminal commands.'
        );
        loadMissionList();
        userInput.focus();
    });

    // Mission Select change
    missionSelect.addEventListener('change', async (e) => {
        const val = e.target.value;
        if (val && val !== 'current') {
            currentMissionId = val;
            await loadMissionHistory(val);
        }
    });

    // Multimodal Image Attachment Triggers
    btnAttachImage.addEventListener('click', () => {
        imageFileInput.click();
    });

    imageFileInput.addEventListener('change', (e) => {
        const files = e.target.files;
        if (files && files[0]) {
            handleImageFile(files[0]);
        }
        imageFileInput.value = '';
    });

    // Clipboard Paste Listener for Screenshots (Ctrl+V / Cmd+V)
    userInput.addEventListener('paste', (e) => {
        const items = (e.clipboardData || e.originalEvent.clipboardData).items;
        for (let index = 0; index < items.length; index++) {
            const item = items[index];
            if (item.kind === 'file' && item.type.startsWith('image/')) {
                const blob = item.getAsFile();
                handleImageFile(blob);
                e.preventDefault();
                break;
            }
        }
    });

    function handleImageFile(file) {
        const reader = new FileReader();
        reader.onload = async (event) => {
            const b64 = event.target.result;
            try {
                // Upload to mission attachment endpoint
                const resp = await fetch(`/api/v1/missions/${currentMissionId}/upload`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        image_base64: b64,
                        filename: file.name || 'screenshot.png',
                        mime_type: file.type || 'image/png'
                    })
                });
                const resJson = await resp.json();
                const data = resJson.data || resJson;
                const attachId = data.attachment_id || 'att-' + Date.now();

                pendingAttachments.push({
                    id: attachId,
                    filename: data.filename || file.name || 'screenshot.png',
                    base64: b64
                });

                renderAttachmentPreviewTray();
            } catch (err) {
                console.warn('Failed to upload image attachment', err);
            }
        };
        reader.readAsDataURL(file);
    }

    function renderAttachmentPreviewTray() {
        if (pendingAttachments.length === 0) {
            attachmentPreviewTray.style.display = 'none';
            attachmentPreviewTray.innerHTML = '';
            return;
        }

        attachmentPreviewTray.style.display = 'flex';
        attachmentPreviewTray.innerHTML = pendingAttachments.map((att, idx) => `
            <div class="attachment-chip">
                <img src="${att.base64}" alt="${escapeHtml(att.filename)}">
                <span>${escapeHtml(att.filename)}</span>
                <button type="button" class="btn-remove-attachment" onclick="removeAttachment(${idx})">
                    <i class="bi bi-x-circle-fill"></i>
                </button>
            </div>
        `).join('');
    }

    window.removeAttachment = function(idx) {
        pendingAttachments.splice(idx, 1);
        renderAttachmentPreviewTray();
    };

    // Send and Stop actions
    btnSend.addEventListener('click', handleSubmit);
    btnStopStream.addEventListener('click', stopStreaming);

    function stopStreaming() {
        if (activeEventSource) {
            activeEventSource.close();
            activeEventSource = null;
        }
        // Send stop signal to mission
        fetch(`/api/v1/missions/${currentMissionId}/stop`, { method: 'POST' }).catch(() => {});
        setMissionStatus('CANCELLED');
        setStreamingState(false);
    }

    function setStreamingState(streaming) {
        isStreaming = streaming;
        btnSend.disabled = streaming;
        btnStopStream.style.display = streaming ? 'inline-flex' : 'none';
        if (!streaming) {
            userInput.focus();
        }
    }

    function setMissionStatus(state) {
        missionStatusBadge.className = `badge mission-badge mission-state-${state}`;
        missionStatusText.textContent = state.replace(/_/g, ' ');
    }

    // Message Rendering Helpers
    function appendUserMessage(text, attachments = []) {
        const row = document.createElement('div');
        row.className = 'msg-row msg-user d-flex justify-content-end gap-3 mb-3';
        
        let attachHtml = '';
        if (attachments && attachments.length > 0) {
            attachHtml = `
                <div class="d-flex flex-wrap gap-2 mt-2">
                    ${attachments.map(a => `<img src="${a.base64}" class="rounded border shadow-sm" style="max-height: 120px; object-fit: contain;">`).join('')}
                </div>
            `;
        }

        row.innerHTML = `
            <div class="msg-body-wrapper">
                <div class="bubble-user">
                    <div>${escapeHtml(text)}</div>
                    ${attachHtml}
                </div>
            </div>
            <div class="msg-avatar avatar-user">
                <i class="bi bi-person-fill"></i>
            </div>
        `;
        chatContainer.appendChild(row);
        scrollChatToBottom();
    }

    function appendAssistantNotice(title, subtitle) {
        const row = document.createElement('div');
        row.className = 'msg-row d-flex gap-3 mb-3';
        row.innerHTML = `
            <div class="msg-avatar avatar-nemotron">
                <i class="bi bi-cpu-fill"></i>
            </div>
            <div class="msg-body-wrapper flex-grow-1">
                <div class="bubble-assistant p-3 rounded-4">
                    <h6 class="fw-bold mb-1 text-dark d-flex align-items-center gap-2">
                        <span>${escapeHtml(title)}</span>
                        <span class="badge provider-badge badge-gemini">Ready</span>
                    </h6>
                    <p class="text-secondary small mb-0">${escapeHtml(subtitle)}</p>
                </div>
            </div>
        `;
        chatContainer.appendChild(row);
        scrollChatToBottom();
    }

    function createAssistantMessageSlot() {
        const row = document.createElement('div');
        row.className = 'msg-row d-flex gap-3 mb-3';
        const bubbleId = 'bubble-' + Date.now();
        const thoughtId = 'thought-' + Date.now();

        row.innerHTML = `
            <div class="msg-avatar avatar-nemotron">
                <i class="bi bi-cpu-fill"></i>
            </div>
            <div class="msg-body-wrapper flex-grow-1">
                <div class="bubble-assistant p-3 rounded-4 shadow-sm">
                    <div class="thought-container mb-3" id="${thoughtId}" style="display:none;">
                        <div class="thought-header d-flex align-items-center justify-content-between" onclick="toggleThought('${thoughtId}')">
                            <div class="thought-title">
                                <div class="pulse-dot"></div>
                                <span id="${thoughtId}-title">Nemotron 3 Ultra — Reasoning Stream</span>
                            </div>
                            <span class="badge bg-purple-subtle text-purple font-monospace small"><i class="bi bi-chevron-down me-1"></i>Thought Process</span>
                        </div>
                        <div class="thought-content" id="${thoughtId}-body"></div>
                    </div>
                    <div class="assistant-content markdown-body" id="${bubbleId}">
                        <div class="typing-indicator" id="${bubbleId}-typing">
                            <span class="typing-dot"></span>
                            <span class="typing-dot"></span>
                            <span class="typing-dot"></span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        chatContainer.appendChild(row);
        scrollChatToBottom();
        return {
            bubbleEl: document.getElementById(bubbleId),
            thoughtContainerEl: document.getElementById(thoughtId),
            thoughtBodyEl: document.getElementById(thoughtId + '-body'),
            thoughtId: thoughtId,
            bubbleId: bubbleId
        };
    }

    window.toggleThought = function(id) {
        const body = document.getElementById(id + '-body');
        if (body) {
            body.style.display = body.style.display === 'none' ? 'block' : 'none';
        }
    };

    // Main Mission Turn Dispatcher
    async function handleSubmit() {
        const text = userInput.value.trim();
        if ((!text && pendingAttachments.length === 0) || isStreaming) return;

        const attachmentsToSend = [...pendingAttachments];
        appendUserMessage(text, attachmentsToSend);

        userInput.value = '';
        pendingAttachments = [];
        renderAttachmentPreviewTray();
        autoResizeTextarea();
        setStreamingState(true);
        setMissionStatus('UNDERSTANDING');

        const slots = createAssistantMessageSlot();
        const t0 = performance.now();
        let tokenCount = 0;
        let thoughtAccumulator = "";
        let responseAccumulator = "";

        try {
            const attachmentIdsStr = attachmentsToSend.map(a => a.id).join(',');
            const sseUrl = `/api/v1/missions/${currentMissionId}/stream?goal=${encodeURIComponent(text)}&attachments=${encodeURIComponent(attachmentIdsStr)}`;
            activeEventSource = new EventSource(sseUrl);

            activeEventSource.onmessage = (e) => {
                try {
                    const eventData = JSON.parse(e.data);
                    const type = eventData.type;

                    if (type === 'state_change') {
                        setMissionStatus(eventData.current_state);
                    } else if (type === 'thought') {
                        if (chkThinking.checked) {
                            slots.thoughtContainerEl.style.display = 'block';
                            thoughtAccumulator += eventData.content;
                            slots.thoughtBodyEl.textContent = thoughtAccumulator;
                            slots.thoughtBodyEl.scrollTop = slots.thoughtBodyEl.scrollHeight;
                            tokenCount += 1;
                        }
                    } else if (type === 'token') {
                        removeTyping(slots.bubbleId);
                        responseAccumulator += eventData.content;
                        slots.bubbleEl.innerHTML = formatMarkdown(responseAccumulator);
                        tokenCount += 1;
                    } else if (type === 'plan_created' || type === 'plan_updated') {
                        removeTyping(slots.bubbleId);
                        renderPlanCard(slots.bubbleEl, eventData, currentMissionId);
                    } else if (type === 'option_selection_requested') {
                        removeTyping(slots.bubbleId);
                        renderSolutionOptionsCard(slots.bubbleEl, eventData, currentMissionId);
                    } else if (type === 'permission_requested') {
                        removeTyping(slots.bubbleId);
                        renderPermissionCard(slots.bubbleEl, eventData, currentMissionId);
                    } else if (type === 'terminal_start') {
                        removeTyping(slots.bubbleId);
                        appendTerminalBlock(slots.bubbleEl, eventData.command);
                    } else if (type === 'terminal_output') {
                        updateTerminalBlock(slots.bubbleEl, eventData);
                    } else if (type === 'diff_generated') {
                        renderDiffCard(slots.bubbleEl, eventData);
                    } else if (type === 'test_results') {
                        renderTestResultsBadge(slots.bubbleEl, eventData);
                    } else if (type === 'mission_completed') {
                        removeTyping(slots.bubbleId);
                        if (eventData.final_response && !responseAccumulator) {
                            slots.bubbleEl.innerHTML = formatMarkdown(eventData.final_response);
                        }
                        setMissionStatus('COMPLETED');
                        activeEventSource.close();
                        setStreamingState(false);
                        loadMissionList();
                    } else if (type === 'warning' || type === 'error') {
                        removeTyping(slots.bubbleId);
                        slots.bubbleEl.innerHTML += `<div class="alert alert-warning py-1 px-2 my-2 small">⚠️ ${escapeHtml(eventData.content || eventData.message || 'Warning')}</div>`;
                    }

                    updateLiveTelemetry(t0, tokenCount);
                    scrollChatToBottom();
                } catch (err) {
                    console.warn('SSE Parse err', err);
                }
            };

            activeEventSource.onerror = (err) => {
                activeEventSource.close();
                setStreamingState(false);
            };

        } catch (err) {
            removeTyping(slots.bubbleId);
            slots.bubbleEl.innerHTML = `<span class="text-danger">Mission Dispatch Error: ${escapeHtml(err.message)}</span>`;
            setStreamingState(false);
        }
    }

    function removeTyping(bubbleId) {
        const typingEl = document.getElementById(bubbleId + '-typing');
        if (typingEl) typingEl.remove();
    }

    // Interactive Plan Card Component
    function renderPlanCard(container, data, missionId) {
        let planCard = container.querySelector('.plan-card');
        if (!planCard) {
            planCard = document.createElement('div');
            planCard.className = 'plan-card';
            container.appendChild(planCard);
        }

        const steps = data.steps || [];
        const stepsHtml = steps.map(s => {
            let icon = '○';
            let iconClass = 'step-icon-pending';
            if (s.status === 'in_progress') {
                icon = '<i class="bi bi-arrow-repeat"></i>';
                iconClass = 'step-icon-in_progress';
            } else if (s.status === 'completed') {
                icon = '<i class="bi bi-check-circle-fill"></i>';
                iconClass = 'step-icon-completed';
            } else if (s.status === 'failed') {
                icon = '<i class="bi bi-x-circle-fill"></i>';
                iconClass = 'step-icon-failed';
            }
            return `
                <div class="plan-step-item">
                    <span class="${iconClass}">${icon}</span>
                    <div>
                        <strong>${escapeHtml(s.title)}</strong>
                        <div class="text-muted small">${escapeHtml(s.description || '')}</div>
                    </div>
                </div>
            `;
        }).join('');

        const buttonsHtml = data.requires_approval ? `
            <div class="d-flex align-items-center gap-2 mt-3 pt-2 border-top">
                <button type="button" class="btn btn-primary btn-sm rounded-pill px-3" onclick="approveMissionPlan('${missionId}', this)">
                    <i class="bi bi-check-lg me-1"></i> Approve Plan
                </button>
                <button type="button" class="btn btn-outline-secondary btn-sm rounded-pill px-3" onclick="setPrompt('/modify plan ')">
                    Modify Plan
                </button>
                <button type="button" class="btn btn-outline-danger btn-sm rounded-pill px-3" onclick="stopStreaming()">
                    Cancel
                </button>
            </div>
        ` : '';

        planCard.innerHTML = `
            <div class="plan-card-header">
                <span class="fw-bold text-dark font-monospace small"><i class="bi bi-list-task text-primary me-1"></i> MISSION EXECUTION PLAN</span>
                <span class="badge bg-primary-subtle text-primary font-monospace small">${steps.filter(s => s.status === 'completed').length}/${steps.length} Steps</span>
            </div>
            <div>${stepsHtml}</div>
            ${buttonsHtml}
        `;
    }

    window.approveMissionPlan = async function(missionId, btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Approving...';
        try {
            await fetch(`/api/v1/missions/${missionId}/plan/approve`, { method: 'POST' });
            btn.parentElement.innerHTML = '<span class="badge bg-success-subtle text-success py-1 px-3"><i class="bi bi-check2 me-1"></i> Plan Approved</span>';
        } catch (e) {
            btn.disabled = false;
        }
    };

    // Solution Selection Card Component
    function renderSolutionOptionsCard(container, data, missionId) {
        const card = document.createElement('div');
        card.className = 'solution-card-group my-3';

        const optionsHtml = (data.options || []).map(opt => `
            <div class="solution-card ${opt.recommended ? 'recommended' : ''}">
                <div class="d-flex align-items-center justify-content-between mb-1">
                    <h6 class="fw-bold mb-0 text-dark">${escapeHtml(opt.title)}</h6>
                    ${opt.recommended ? '<span class="badge bg-primary text-white small">Recommended</span>' : ''}
                </div>
                <p class="text-secondary small mb-2">${escapeHtml(opt.architecture || '')}</p>
                <div class="small mb-2">
                    <span class="text-success me-2">✓ ${escapeHtml(opt.advantages || '')}</span>
                    <span class="text-muted">⚠ ${escapeHtml(opt.tradeoffs || '')}</span>
                </div>
                <button type="button" class="btn btn-sm btn-outline-primary rounded-pill px-3" onclick="selectSolutionOption('${missionId}', '${data.selection_id}', '${opt.key}', this)">
                    Select Option ${opt.key}
                </button>
            </div>
        `).join('');

        card.innerHTML = `
            <div class="p-2 border-bottom fw-bold text-dark small"><i class="bi bi-diagram-3-fill text-primary me-1"></i> ${escapeHtml(data.prompt)}</div>
            ${optionsHtml}
        `;
        container.appendChild(card);
    }

    window.selectSolutionOption = async function(missionId, selectionId, optionKey, btn) {
        const group = btn.closest('.solution-card-group');
        group.querySelectorAll('button').forEach(b => b.disabled = true);
        btn.innerHTML = `<i class="bi bi-check-lg me-1"></i> Selected Option ${optionKey}`;
        btn.className = 'btn btn-sm btn-success rounded-pill px-3';

        await fetch(`/api/v1/missions/${missionId}/selection`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ selection_id: selectionId, selected_option: optionKey })
        });
    };

    // Permission Request Card Component
    function renderPermissionCard(container, data, missionId) {
        const card = document.createElement('div');
        card.className = 'permission-card';
        const risk = data.risk_level || 'LOW';

        card.innerHTML = `
            <div class="d-flex align-items-center justify-content-between mb-2">
                <span class="fw-bold text-dark small"><i class="bi bi-shield-exclamation text-warning me-1"></i> PERMISSION REQUIRED</span>
                <span class="risk-badge risk-badge-${risk}">${risk} RISK</span>
            </div>
            <div class="font-monospace small bg-white p-2 rounded border mb-2 text-dark">
                <code>$ ${escapeHtml(data.target)}</code>
            </div>
            <div class="small text-secondary mb-3">${escapeHtml(data.reason || 'Command requires explicit authorization.')}</div>
            <div class="d-flex align-items-center gap-2">
                <button type="button" class="btn btn-success btn-sm rounded-pill px-3" onclick="submitPermissionDecision('${missionId}', '${data.request_id}', 'ALLOW', 'ONCE', this)">
                    Allow Once
                </button>
                <button type="button" class="btn btn-outline-success btn-sm rounded-pill px-3" onclick="submitPermissionDecision('${missionId}', '${data.request_id}', 'ALLOW', 'MISSION', this)">
                    Allow for Mission
                </button>
                <button type="button" class="btn btn-outline-danger btn-sm rounded-pill px-3" onclick="submitPermissionDecision('${missionId}', '${data.request_id}', 'DENY', 'ONCE', this)">
                    Deny
                </button>
            </div>
        `;
        container.appendChild(card);
    }

    window.submitPermissionDecision = async function(missionId, requestId, action, scope, btn) {
        const card = btn.closest('.permission-card');
        card.querySelectorAll('button').forEach(b => b.disabled = true);
        btn.innerHTML = `<i class="bi bi-check2 me-1"></i> ${action === 'ALLOW' ? 'Authorized' : 'Denied'}`;

        await fetch(`/api/v1/missions/${missionId}/permissions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ request_id: requestId, action: action, scope: scope })
        });
    };

    // Terminal Block Component
    function appendTerminalBlock(container, command) {
        const term = document.createElement('div');
        term.className = 'terminal-card';
        term.innerHTML = `
            <div class="terminal-header">
                <div class="terminal-dots">
                    <span class="terminal-dot red"></span>
                    <span class="terminal-dot yellow"></span>
                    <span class="terminal-dot green"></span>
                </div>
                <span>SANDBOX TERMINAL</span>
                <span class="badge bg-secondary font-monospace small running-indicator">Running...</span>
            </div>
            <div class="terminal-body">
                <div class="terminal-prompt">$ ${escapeHtml(command)}</div>
                <div class="terminal-logs">Executing command inside repository sandbox...</div>
            </div>
        `;
        container.appendChild(term);
    }

    function updateTerminalBlock(container, data) {
        const term = container.querySelector('.terminal-card:last-child');
        if (!term) return;

        const badge = term.querySelector('.running-indicator');
        if (badge) {
            badge.className = data.exit_code === 0 ? 'badge bg-success font-monospace small' : 'badge bg-danger font-monospace small';
            badge.textContent = `Exit: ${data.exit_code}`;
        }

        const logs = term.querySelector('.terminal-logs');
        if (logs) {
            let output = data.stdout || '';
            if (data.stderr) output += '\n[stderr]: ' + data.stderr;
            logs.textContent = output;
        }
    }

    // Diff Card Component
    function renderDiffCard(container, data) {
        const card = document.createElement('div');
        card.className = 'code-block-container my-3';
        card.innerHTML = `
            <div class="code-block-header">
                <span><i class="bi bi-file-earmark-diff me-1"></i> DIFF REVIEW: ${escapeHtml(data.file_path || 'Repository Changes')}</span>
                <span class="badge bg-primary-subtle text-primary small">Review Ready</span>
            </div>
            <pre class="p-3 bg-dark text-light"><code>${escapeHtml(data.diff)}</code></pre>
            <div class="p-2 bg-light border-top d-flex gap-2">
                <button type="button" class="btn btn-sm btn-success rounded-pill px-3" onclick="this.disabled=true; this.textContent='Diff Accepted';">
                    <i class="bi bi-check2 me-1"></i> Accept Diff
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill px-3" onclick="setPrompt('/rollback')">
                    Revert
                </button>
            </div>
        `;
        container.appendChild(card);
    }

    function renderTestResultsBadge(container, data) {
        const badge = document.createElement('div');
        badge.className = `alert ${data.passed ? 'alert-success' : 'alert-danger'} py-2 px-3 my-2 small border rounded-3 d-flex align-items-center gap-2`;
        badge.innerHTML = `
            <i class="bi ${data.passed ? 'bi-check-circle-fill text-success' : 'bi-x-circle-fill text-danger'} fs-6"></i>
            <div><strong>Test Suite:</strong> ${escapeHtml(data.summary || (data.passed ? 'All tests passed' : 'Test failures detected'))}</div>
        `;
        container.appendChild(badge);
    }

    // Telemetry and Ledger
    function updateLiveTelemetry(startTimeMs, tokens) {
        const elapsedSec = Math.max(0.01, (performance.now() - startTimeMs) / 1000);
        const tps = Math.round(tokens / elapsedSec);
        sessionTokens += 1;
        sessionCost += 0.000003;

        statTokens.textContent = sessionTokens.toLocaleString();
        statSpeed.textContent = `${tps} t/s`;
        statCost.textContent = `$${sessionCost.toFixed(6)}`;
    }

    function scrollChatToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function escapeHtml(str) {
        return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    // Markdown Parser & Enhancer
    function formatMarkdown(text) {
        if (!text) return "";
        if (window.marked && typeof window.marked.parse === 'function') {
            let processed = text;
            const codeBlockMatches = processed.match(/```/g);
            if (codeBlockMatches && codeBlockMatches.length % 2 !== 0) {
                processed += "\n```";
            }
            try {
                let html = window.marked.parse(processed);
                return enhanceRenderedHtml(html);
            } catch (err) {
                console.warn('Marked parse error', err);
            }
        }
        return escapeHtml(text).replace(/\n/g, '<br>');
    }

    function enhanceRenderedHtml(html) {
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;

        tempDiv.querySelectorAll('pre').forEach(pre => {
            const code = pre.querySelector('code');
            let lang = 'CODE';
            if (code && code.className) {
                const match = code.className.match(/language-([a-zA-Z0-9_+-]+)/);
                if (match) lang = match[1].toUpperCase();
            }
            if (window.hljs && code) {
                try { window.hljs.highlightElement(code); } catch (e) {}
            }
            const wrapper = document.createElement('div');
            wrapper.className = 'code-block-container';
            wrapper.innerHTML = `
                <div class="code-block-header">
                    <span><i class="bi bi-file-earmark-code me-1"></i>${escapeHtml(lang)}</span>
                    <button type="button" class="btn-copy-code" onclick="copyCodeBlock(this)">
                        <i class="bi bi-clipboard me-1"></i><span>Copy</span>
                    </button>
                </div>
            `;
            pre.parentNode.insertBefore(wrapper, pre);
            wrapper.appendChild(pre);
        });

        tempDiv.querySelectorAll('table').forEach(table => {
            table.classList.add('table', 'table-sm', 'table-bordered', 'my-2');
        });

        return tempDiv.innerHTML;
    }

    window.copyCodeBlock = function(btn) {
        const container = btn.closest('.code-block-container');
        if (!container) return;
        const codeEl = container.querySelector('code');
        if (!codeEl) return;
        navigator.clipboard.writeText(codeEl.innerText || codeEl.textContent).then(() => {
            const originalHtml = btn.innerHTML;
            btn.innerHTML = '<i class="bi bi-check2 text-success me-1"></i><span class="text-success">Copied!</span>';
            setTimeout(() => { btn.innerHTML = originalHtml; }, 2000);
        });
    };

    // Load past missions in dropdown
    async function loadMissionList() {
        try {
            const resp = await fetch('/api/v1/missions?limit=15');
            if (resp.ok) {
                const missionsJson = await resp.json();
                const list = Array.isArray(missionsJson.data) ? missionsJson.data : (Array.isArray(missionsJson) ? missionsJson : []);
                if (list.length > 0) {
                    missionSelect.innerHTML = `
                        <option value="current">Current: ${currentMissionId.substring(0, 14)}...</option>
                        ${list.map(m => `
                            <option value="${escapeHtml(m.id)}">${escapeHtml(m.title || m.goal || m.id).substring(0, 30)}... (${m.status})</option>
                        `).join('')}
                    `;
                }
            }
        } catch (e) {}
    }

    async function loadMissionHistory(missionId) {
        try {
            const resp = await fetch(`/api/v1/missions/${missionId}`);
            if (resp.ok) {
                const json = await resp.json();
                const data = json.data || json;
                chatContainer.innerHTML = '';
                setMissionStatus(data.mission.status || 'IDLE');

                (data.messages || []).forEach(msg => {
                    if (msg.role === 'user') {
                        appendUserMessage(msg.content);
                    } else {
                        const slots = createAssistantMessageSlot();
                        removeTyping(slots.bubbleId);
                        slots.bubbleEl.innerHTML = formatMarkdown(msg.content);
                    }
                });
            }
        } catch (e) {}
    }

    // Modal Ledger fetch on opening
    const ledgerModal = document.getElementById('ledgerModal');
    if (ledgerModal) {
        ledgerModal.addEventListener('show.bs.modal', async () => {
            try {
                const [sumResp, ledgerResp] = await Promise.all([
                    fetch('/api/v1/agent/cost/summary'),
                    fetch('/api/v1/agent/cost/ledger?limit=10')
                ]);

                if (sumResp.ok) {
                    const sumJson = await sumResp.json();
                    const sum = sumJson.data || sumJson || {};
                    modalTotalMissions.textContent = sum.total_missions || 0;
                    modalTotalTokens.textContent = Number(sum.total_tokens || 0).toLocaleString();
                    modalTotalCost.textContent = `$${Number(sum.total_spend_usd ?? sum.total_cost_usd ?? 0.0).toFixed(6)}`;
                }

                if (ledgerResp.ok) {
                    const recordsJson = await ledgerResp.json();
                    const records = Array.isArray(recordsJson.data) ? recordsJson.data : (Array.isArray(recordsJson) ? recordsJson : []);
                    if (records.length === 0) {
                        modalLedgerTableBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">No recorded missions yet.</td></tr>';
                    } else {
                        modalLedgerTableBody.innerHTML = records.map(r => `
                            <tr>
                                <td><code>${escapeHtml((r.mission_id || 'unknown').substring(0, 8))}...</code></td>
                                <td>${Number(r.total_tokens || r.tokens_used || 0).toLocaleString()}</td>
                                <td class="text-success">$${Number(r.total_cost_usd ?? r.cost_usd ?? 0.0).toFixed(6)}</td>
                                <td>${Number(r.duration_seconds || 0).toFixed(1)}s</td>
                                <td><span class="badge bg-success-subtle text-success border border-success-subtle">Completed</span></td>
                            </tr>
                        `).join('');
                    }
                }
            } catch (err) {
                modalLedgerTableBody.innerHTML = `<tr><td colspan="5" class="text-danger py-2">Error loading ledger: ${escapeHtml(err.message)}</td></tr>`;
            }
        });
    }
});
