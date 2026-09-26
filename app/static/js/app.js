/**
 * Nemotron Agent Engine — Modern Interactive Client
 * Matches architecture and style of doc-processing-service
 */

document.addEventListener('DOMContentLoaded', () => {
    // State variables
    let currentMode = 'mission'; // 'mission' or 'chat'
    let isStreaming = false;
    let activeEventSource = null;
    let abortController = null;
    let sessionTokens = 0;
    let sessionCost = 0.0;
    let conversationHistory = [];

    // DOM Elements
    const chatContainer = document.getElementById('chatContainer');
    const userInput = document.getElementById('userInput');
    const btnSend = document.getElementById('btnSend');
    const btnSendText = document.getElementById('btnSendText');
    const btnSendIcon = document.getElementById('btnSendIcon');
    const btnStopStream = document.getElementById('btnStopStream');
    const btnModeMission = document.getElementById('btnModeMission');
    const btnModeChat = document.getElementById('btnModeChat');
    const chkThinking = document.getElementById('chkThinking');
    const modeIndicatorLabel = document.getElementById('modeIndicatorLabel');
    const statTokens = document.getElementById('statTokens');
    const statSpeed = document.getElementById('statSpeed');
    const statCost = document.getElementById('statCost');

    // Ledger Modal Elements
    const modalTotalMissions = document.getElementById('modalTotalMissions');
    const modalTotalTokens = document.getElementById('modalTotalTokens');
    const modalTotalCost = document.getElementById('modalTotalCost');
    const modalLedgerTableBody = document.getElementById('modalLedgerTableBody');

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
        }
    });

    // Preset Prompt Helper (exposed globally for onclick)
    window.setPrompt = function(text) {
        userInput.value = text;
        autoResizeTextarea();
        userInput.focus();
    };

    // Mode Switchers
    btnModeMission.addEventListener('click', () => {
        currentMode = 'mission';
        btnModeMission.classList.add('active');
        btnModeChat.classList.remove('active');
        modeIndicatorLabel.innerHTML = '<i class="bi bi-gear-wide-connected text-primary"></i> <span>Mode: Autonomous Mission (Tools Active)</span>';
        btnSendText.textContent = 'Dispatch';
        btnSendIcon.className = 'bi bi-lightning-charge-fill';
    });

    btnModeChat.addEventListener('click', () => {
        currentMode = 'chat';
        btnModeChat.classList.add('active');
        btnModeMission.classList.remove('active');
        modeIndicatorLabel.innerHTML = '<i class="bi bi-chat-left-dots text-primary"></i> <span>Mode: Direct Chat (Reasoning Only)</span>';
        btnSendText.textContent = 'Send Message';
        btnSendIcon.className = 'bi bi-send-fill';
    });

    btnSend.addEventListener('click', handleSubmit);
    btnStopStream.addEventListener('click', stopStreaming);

    function stopStreaming() {
        if (activeEventSource) {
            activeEventSource.close();
            activeEventSource = null;
        }
        if (abortController) {
            abortController.abort();
            abortController = null;
        }
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

    function appendUserMessage(text) {
        const row = document.createElement('div');
        row.className = 'msg-row msg-user d-flex justify-content-end gap-3 mb-3';
        row.innerHTML = `
            <div class="msg-body-wrapper">
                <div class="bubble-user">${escapeHtml(text)}</div>
            </div>
            <div class="msg-avatar avatar-user">
                <i class="bi bi-person-fill"></i>
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
                <div class="bubble-assistant p-3 rounded-4">
                    <div class="thought-container" id="${thoughtId}" style="display:none;">
                        <div class="thought-header" onclick="toggleThought('${thoughtId}')">
                            <div class="thought-title">
                                <div class="pulse-dot"></div>
                                <span>Nemotron 3 Ultra — Reasoning Stream</span>
                            </div>
                            <i class="bi bi-chevron-down text-muted small"></i>
                        </div>
                        <div class="thought-content" id="${thoughtId}-body"></div>
                    </div>
                    <div class="assistant-content" id="${bubbleId}"></div>
                </div>
            </div>
        `;
        chatContainer.appendChild(row);
        scrollChatToBottom();
        return {
            bubbleEl: document.getElementById(bubbleId),
            thoughtContainerEl: document.getElementById(thoughtId),
            thoughtBodyEl: document.getElementById(thoughtId + '-body')
        };
    }

    window.toggleThought = function(id) {
        const body = document.getElementById(id + '-body');
        if (body) {
            body.style.display = body.style.display === 'none' ? 'block' : 'none';
        }
    };

    async function handleSubmit() {
        const text = userInput.value.trim();
        if (!text || isStreaming) return;

        appendUserMessage(text);
        userInput.value = '';
        autoResizeTextarea();
        setStreamingState(true);

        const slots = createAssistantMessageSlot();
        const t0 = performance.now();
        let tokenCount = 0;
        let thoughtAccumulator = "";
        let responseAccumulator = "";

        if (currentMode === 'mission') {
            // Mode 1: Autonomous Agent Mission via SSE
            try {
                const initResp = await fetch('/api/v1/agent/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ goal: text, max_iterations: 15 })
                });
                const initData = await initResp.json();
                const missionId = initData.mission_id || Date.now();

                const sseUrl = `/api/v1/agent/stream/${missionId}?goal=${encodeURIComponent(text)}`;
                activeEventSource = new EventSource(sseUrl);

                activeEventSource.onmessage = (e) => {
                    try {
                        const eventData = JSON.parse(e.data);
                        const type = eventData.type;

                        if (type === 'thought') {
                            slots.thoughtContainerEl.style.display = 'block';
                            thoughtAccumulator += eventData.content;
                            slots.thoughtBodyEl.textContent = thoughtAccumulator;
                            slots.thoughtBodyEl.scrollTop = slots.thoughtBodyEl.scrollHeight;
                            tokenCount += 1;
                        } else if (type === 'token') {
                            responseAccumulator += eventData.content;
                            slots.bubbleEl.innerHTML = formatMarkdown(responseAccumulator);
                            tokenCount += 1;
                        } else if (type === 'tool_start') {
                            const card = document.createElement('div');
                            card.className = 'tool-step-card';
                            card.innerHTML = `
                                <div class="tool-step-title"><i class="bi bi-gear-fill me-1"></i> Tool Executing: ${escapeHtml(eventData.tool)}</div>
                                <div class="tool-step-obs">Args: ${escapeHtml(JSON.stringify(eventData.arguments))}</div>
                            `;
                            slots.bubbleEl.appendChild(card);
                        } else if (type === 'tool_observation') {
                            const obsDiv = document.createElement('div');
                            obsDiv.className = 'tool-step-card';
                            obsDiv.innerHTML = `
                                <div class="tool-step-title text-success"><i class="bi bi-check-circle-fill me-1"></i> Observation: ${escapeHtml(eventData.tool)}</div>
                                <div class="tool-step-obs">${escapeHtml(JSON.stringify(eventData.observation))}</div>
                            `;
                            slots.bubbleEl.appendChild(obsDiv);
                        } else if (type === 'mission_completed') {
                            if (eventData.final_response) {
                                slots.bubbleEl.innerHTML = formatMarkdown(eventData.final_response);
                            }
                            activeEventSource.close();
                            setStreamingState(false);
                        } else if (type === 'warning' || type === 'error') {
                            slots.bubbleEl.innerHTML += `<div class="alert alert-warning py-1 px-2 my-2 small">⚠️ ${escapeHtml(eventData.content)}</div>`;
                        }

                        updateLiveTelemetry(t0, tokenCount);
                        scrollChatToBottom();
                    } catch (err) {
                        console.warn('SSE Parse err', err);
                    }
                };

                activeEventSource.onerror = (err) => {
                    console.warn('SSE closed', err);
                    activeEventSource.close();
                    setStreamingState(false);
                };

            } catch (err) {
                slots.bubbleEl.innerHTML = `<span class="text-danger">Error dispatching mission: ${escapeHtml(err.message)}</span>`;
                setStreamingState(false);
            }

        } else {
            // Mode 2: Direct Conversational Chat
            conversationHistory.push({ role: 'user', content: text });
            abortController = new AbortController();

            try {
                const resp = await fetch('/api/v1/agent/chat/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        messages: conversationHistory,
                        temperature: 0.6,
                        enable_thinking: chkThinking.checked
                    }),
                    signal: abortController.signal
                });

                const reader = resp.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop();

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const dataStr = line.slice(6).trim();
                            if (!dataStr || dataStr === '[DONE]') continue;
                            try {
                                const chunk = JSON.parse(dataStr);
                                if (chunk.type === 'thought') {
                                    slots.thoughtContainerEl.style.display = 'block';
                                    thoughtAccumulator += chunk.content;
                                    slots.thoughtBodyEl.textContent = thoughtAccumulator;
                                    slots.thoughtBodyEl.scrollTop = slots.thoughtBodyEl.scrollHeight;
                                    tokenCount += 1;
                                } else if (chunk.type === 'token') {
                                    responseAccumulator += chunk.content;
                                    slots.bubbleEl.innerHTML = formatMarkdown(responseAccumulator);
                                    tokenCount += 1;
                                } else if (chunk.type === 'warning' || chunk.type === 'error') {
                                    slots.bubbleEl.innerHTML += `<div class="alert alert-warning py-1 px-2 my-2 small">⚠️ ${escapeHtml(chunk.content)}</div>`;
                                }
                                updateLiveTelemetry(t0, tokenCount);
                                scrollChatToBottom();
                            } catch (e) {
                                // Ignore chunk parse error
                            }
                        }
                    }
                }

                conversationHistory.push({ role: 'assistant', content: responseAccumulator });
            } catch (err) {
                if (err.name !== 'AbortError') {
                    slots.bubbleEl.innerHTML = `<span class="text-danger">Chat Error: ${escapeHtml(err.message)}</span>`;
                }
            } finally {
                setStreamingState(false);
            }
        }
    }

    function updateLiveTelemetry(startTimeMs, tokens) {
        const elapsedSec = Math.max(0.01, (performance.now() - startTimeMs) / 1000);
        const tps = Math.round(tokens / elapsedSec);
        sessionTokens += 1;
        sessionCost += 0.000003; // GCP Spot amortized rate

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

    function formatMarkdown(text) {
        if (!text) return "";
        let html = text;

        // Fenced code blocks
        html = html.replace(/```([a-zA-Z0-9_+-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
            const langLabel = lang ? lang.toUpperCase() : "CODE";
            return `<pre class="p-3 my-2 rounded-3 bg-dark text-light position-relative">` +
                   `<div class="d-flex justify-content-between text-muted small pb-1 mb-2 border-bottom border-secondary">` +
                   `<span><i class="bi bi-file-earmark-code me-1"></i>${langLabel}</span></div>` +
                   `<code>${escapeHtml(code)}</code></pre>`;
        });

        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code class="bg-light px-1 py-0.5 rounded border text-primary font-monospace">$1</code>');

        // Headers
        html = html.replace(/^### (.*$)/gim, '<h6 class="fw-bold mt-3 mb-1 text-dark">$1</h6>');
        html = html.replace(/^## (.*$)/gim, '<h5 class="fw-bold mt-3 mb-2 text-dark">$1</h5>');
        html = html.replace(/^# (.*$)/gim, '<h4 class="fw-bold mt-3 mb-2 text-dark">$1</h4>');

        // Bold & Italic
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

        // Bullet lists
        html = html.replace(/^\s*-\s+(.*$)/gim, '<li class="ms-3 mb-1">$1</li>');

        // Line breaks
        html = html.replace(/\n/g, '<br>');

        return html;
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
                    const tokens = sum.total_tokens || 0;
                    modalTotalTokens.textContent = Number(tokens).toLocaleString();
                    const cost = sum.total_spend_usd ?? sum.total_cost_usd ?? 0.0;
                    modalTotalCost.textContent = `$${Number(cost).toFixed(6)}`;
                }

                if (ledgerResp.ok) {
                    const recordsJson = await ledgerResp.json();
                    const records = Array.isArray(recordsJson.data)
                        ? recordsJson.data
                        : (Array.isArray(recordsJson) ? recordsJson : []);

                    if (records.length === 0) {
                        modalLedgerTableBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">No recorded missions yet.</td></tr>';
                    } else {
                        modalLedgerTableBody.innerHTML = records.map(r => {
                            const missionId = r.mission_id || 'unknown';
                            const tokens = (r.usage && r.usage.total_tokens !== undefined)
                                ? r.usage.total_tokens
                                : (r.tokens_used || 0);
                            const cost = r.total_cost_usd ?? r.cost_usd ?? 0.0;
                            const duration = r.duration_seconds || 0.0;
                            return `
                                <tr>
                                    <td><code title="${escapeHtml(missionId)}">${escapeHtml(missionId.substring(0, 8))}...</code></td>
                                    <td>${Number(tokens).toLocaleString()}</td>
                                    <td class="text-success">$${Number(cost).toFixed(6)}</td>
                                    <td>${Number(duration).toFixed(1)}s</td>
                                    <td><span class="badge bg-success-subtle text-success border border-success-subtle">Completed</span></td>
                                </tr>
                            `;
                        }).join('');
                    }
                }
            } catch (err) {
                modalLedgerTableBody.innerHTML = `<tr><td colspan="5" class="text-danger py-2">Error loading ledger: ${escapeHtml(err.message)}</td></tr>`;
            }
        });
    }
});

