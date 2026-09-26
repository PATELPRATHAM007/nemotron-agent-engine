"""
Interactive Web UI & Mission Control Dashboard
==============================================
Serves a state-of-the-art dark-mode glassmorphic interface for chatting directly
with NVIDIA Nemotron 3 Ultra, streaming chain-of-thought reasoning tokens in real-time,
dispatching autonomous coding missions, and monitoring token/cost analytics.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["UI"])

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NVIDIA Nemotron 3 Ultra — Autonomous Agent Engine</title>
  <meta name="description" content="Production-Grade Autonomous Coding & Repository Intelligence Agent powered by NVIDIA Nemotron 3 Ultra (550B LatentMoE).">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-base: #080C14;
      --bg-surface: #0E1524;
      --bg-surface-elevated: #162036;
      --bg-glass: rgba(14, 21, 36, 0.72);
      --border-subtle: rgba(255, 255, 255, 0.08);
      --border-glow: rgba(118, 185, 0, 0.35);
      --nvidia-green: #76B900;
      --nvidia-glow: #8CE300;
      --cyber-cyan: #00F2FE;
      --neon-violet: #8A2BE2;
      --neon-purple: #B800FF;
      --text-primary: #F3F4F6;
      --text-secondary: #9CA3AF;
      --text-muted: #6B7280;
      --font-ui: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-code: 'JetBrains Mono', monospace;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--bg-base);
      color: var(--text-primary);
      font-family: var(--font-ui);
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      background-image: 
        radial-gradient(circle at 15% 15%, rgba(118, 185, 0, 0.08) 0%, transparent 40%),
        radial-gradient(circle at 85% 20%, rgba(138, 43, 226, 0.07) 0%, transparent 45%),
        radial-gradient(circle at 50% 85%, rgba(0, 242, 254, 0.05) 0%, transparent 50%);
    }

    /* Top Navigation Bar */
    header {
      background: var(--bg-glass);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--border-subtle);
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      z-index: 100;
    }

    .brand-section {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .logo-badge {
      width: 40px;
      height: 40px;
      background: linear-gradient(135deg, #76B900, #407A00);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 20px;
      color: #000;
      box-shadow: 0 0 20px rgba(118, 185, 0, 0.4);
      letter-spacing: -1px;
    }

    .brand-title {
      display: flex;
      flex-direction: column;
    }

    .brand-title h1 {
      font-size: 17px;
      font-weight: 700;
      letter-spacing: 0.3px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .badge-chip {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 6px;
      background: rgba(118, 185, 0, 0.15);
      border: 1px solid rgba(118, 185, 0, 0.4);
      color: var(--nvidia-glow);
      font-family: var(--font-code);
      font-weight: 600;
    }

    .brand-subtitle {
      font-size: 12px;
      color: var(--text-secondary);
      font-family: var(--font-code);
    }

    /* Live Analytics Stats Pill Bar */
    .metrics-bar {
      display: flex;
      align-items: center;
      gap: 18px;
      background: rgba(22, 32, 54, 0.6);
      border: 1px solid var(--border-subtle);
      border-radius: 30px;
      padding: 6px 18px;
    }

    .metric-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
    }

    .metric-label {
      color: var(--text-muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .metric-val {
      font-family: var(--font-code);
      font-weight: 700;
      color: var(--text-primary);
    }

    .val-cost { color: #10B981; }
    .val-speed { color: var(--cyber-cyan); }
    .val-tokens { color: var(--nvidia-glow); }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .btn-secondary {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-subtle);
      color: var(--text-secondary);
      padding: 7px 14px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s ease;
    }

    .btn-secondary:hover {
      background: rgba(255, 255, 255, 0.1);
      color: var(--text-primary);
      border-color: rgba(255, 255, 255, 0.2);
    }

    /* Main Container */
    main {
      flex: 1;
      display: flex;
      flex-direction: column;
      max-width: 1200px;
      width: 100%;
      margin: 0 auto;
      padding: 16px 24px;
      overflow: hidden;
    }

    /* Mode Selector & Quick Prompts */
    .control-ribbon {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;
      flex-wrap: wrap;
    }

    .mode-switch-group {
      display: flex;
      background: rgba(14, 21, 36, 0.8);
      border: 1px solid var(--border-subtle);
      border-radius: 10px;
      padding: 3px;
      gap: 4px;
    }

    .mode-btn {
      background: transparent;
      border: none;
      color: var(--text-secondary);
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s;
    }

    .mode-btn.active {
      background: rgba(118, 185, 0, 0.15);
      color: var(--nvidia-glow);
      border: 1px solid rgba(118, 185, 0, 0.4);
      box-shadow: 0 0 12px rgba(118, 185, 0, 0.2);
    }

    .toggle-group {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .switch-label {
      font-size: 13px;
      color: var(--text-secondary);
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
    }

    .switch-checkbox {
      appearance: none;
      width: 36px;
      height: 20px;
      background: #2D3748;
      border-radius: 20px;
      position: relative;
      cursor: pointer;
      outline: none;
      transition: background 0.3s;
    }

    .switch-checkbox::after {
      content: '';
      position: absolute;
      top: 2px;
      left: 2px;
      width: 16px;
      height: 16px;
      background: #FFF;
      border-radius: 50%;
      transition: transform 0.3s;
    }

    .switch-checkbox:checked {
      background: var(--nvidia-green);
    }

    .switch-checkbox:checked::after {
      transform: translateX(16px);
    }

    /* Preset Quick Prompts */
    .quick-prompts-bar {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding-bottom: 4px;
      scrollbar-width: none;
    }

    .quick-pill {
      background: rgba(22, 32, 54, 0.5);
      border: 1px solid var(--border-subtle);
      border-radius: 20px;
      padding: 5px 12px;
      font-size: 12px;
      color: var(--text-secondary);
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }

    .quick-pill:hover {
      background: rgba(118, 185, 0, 0.1);
      color: var(--text-primary);
      border-color: rgba(118, 185, 0, 0.3);
    }

    /* Chat Messages Stream Area */
    .chat-scroll-container {
      flex: 1;
      overflow-y: auto;
      padding: 12px 6px;
      display: flex;
      flex-direction: column;
      gap: 18px;
      scrollbar-width: thin;
      scrollbar-color: rgba(255, 255, 255, 0.1) transparent;
    }

    .chat-scroll-container::-webkit-scrollbar {
      width: 6px;
    }
    .chat-scroll-container::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.1);
      border-radius: 3px;
    }

    /* Message Bubbles */
    .msg-row {
      display: flex;
      gap: 14px;
      animation: fadeIn 0.3s ease-out;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .msg-user {
      justify-content: flex-end;
    }

    .msg-avatar {
      width: 36px;
      height: 36px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      flex-shrink: 0;
    }

    .avatar-nemotron {
      background: linear-gradient(135deg, #76B900, #2E5800);
      box-shadow: 0 0 15px rgba(118, 185, 0, 0.35);
      color: #000;
      font-weight: 800;
    }

    .avatar-user {
      background: linear-gradient(135deg, #3B82F6, #1D4ED8);
      color: #FFF;
    }

    .msg-body-wrapper {
      max-width: 85%;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .bubble-user {
      background: linear-gradient(135deg, #1E3A8A, #1E293B);
      border: 1px solid rgba(59, 130, 246, 0.3);
      padding: 12px 18px;
      border-radius: 16px 16px 4px 16px;
      color: #FFF;
      font-size: 14px;
      line-height: 1.5;
    }

    .bubble-assistant {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 16px 16px 16px 4px;
      padding: 16px 20px;
      color: var(--text-primary);
      font-size: 14px;
      line-height: 1.6;
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
    }

    /* Deep Thought Box (Chain-of-Thought Stream) */
    .thought-container {
      background: rgba(138, 43, 226, 0.08);
      border: 1px solid rgba(138, 43, 226, 0.25);
      border-radius: 10px;
      padding: 10px 14px;
      margin-bottom: 12px;
      transition: all 0.3s ease;
    }

    .thought-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      cursor: pointer;
      user-select: none;
    }

    .thought-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      font-weight: 700;
      color: #C084FC;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      font-family: var(--font-code);
    }

    .pulse-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #C084FC;
      box-shadow: 0 0 10px #C084FC;
      animation: pulse 1.5s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 0.4; transform: scale(0.9); }
      50% { opacity: 1; transform: scale(1.1); }
    }

    .thought-content {
      margin-top: 8px;
      font-family: var(--font-code);
      font-size: 12px;
      color: #D8B4FE;
      line-height: 1.5;
      white-space: pre-wrap;
      max-height: 220px;
      overflow-y: auto;
      border-top: 1px dashed rgba(138, 43, 226, 0.2);
      padding-top: 8px;
    }

    /* Tool Call Steps */
    .tool-step-card {
      background: rgba(0, 242, 254, 0.05);
      border: 1px solid rgba(0, 242, 254, 0.2);
      border-radius: 8px;
      padding: 8px 12px;
      margin: 8px 0;
      font-family: var(--font-code);
      font-size: 12px;
    }

    .tool-step-title {
      color: var(--cyber-cyan);
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .tool-step-obs {
      color: var(--text-secondary);
      margin-top: 4px;
      font-size: 11px;
      background: rgba(0, 0, 0, 0.3);
      padding: 6px;
      border-radius: 4px;
      max-height: 120px;
      overflow-y: auto;
    }

    /* Markdown Formatted Elements */
    .bubble-assistant pre {
      background: #060910;
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 12px;
      margin: 10px 0;
      overflow-x: auto;
      position: relative;
    }

    .bubble-assistant code {
      font-family: var(--font-code);
      font-size: 13px;
      color: #E2E8F0;
    }

    .bubble-assistant p {
      margin-bottom: 10px;
    }

    .bubble-assistant p:last-child {
      margin-bottom: 0;
    }

    .bubble-assistant ul, .bubble-assistant ol {
      margin-left: 20px;
      margin-bottom: 10px;
    }

    .bubble-assistant h1, .bubble-assistant h2, .bubble-assistant h3 {
      margin-top: 14px;
      margin-bottom: 6px;
      color: #FFF;
    }

    /* Bottom Input Dock */
    .input-dock {
      background: var(--bg-glass);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid var(--border-subtle);
      border-radius: 16px;
      padding: 12px 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
      margin-top: 8px;
    }

    .input-dock:focus-within {
      border-color: var(--border-glow);
      box-shadow: 0 0 25px rgba(118, 185, 0, 0.15);
    }

    .input-textarea {
      background: transparent;
      border: none;
      color: var(--text-primary);
      font-family: var(--font-ui);
      font-size: 14px;
      resize: none;
      height: 48px;
      max-height: 160px;
      outline: none;
      line-height: 1.5;
    }

    .input-textarea::placeholder {
      color: var(--text-muted);
    }

    .input-actions-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
      padding-top: 8px;
    }

    .input-hints {
      font-size: 11px;
      color: var(--text-muted);
      font-family: var(--font-code);
    }

    .action-buttons {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .btn-stop {
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.4);
      color: #F87171;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: none;
    }

    .btn-send {
      background: linear-gradient(135deg, #76B900, #558A00);
      border: none;
      color: #000;
      padding: 8px 20px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      box-shadow: 0 0 15px rgba(118, 185, 0, 0.3);
      transition: all 0.2s;
    }

    .btn-send:hover {
      background: linear-gradient(135deg, #8CE300, #76B900);
      transform: translateY(-1px);
      box-shadow: 0 0 20px rgba(118, 185, 0, 0.5);
    }

    .btn-send:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      transform: none;
    }

    /* Modal / Drawer for Cost Ledger */
    .ledger-modal-backdrop {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(8px);
      display: none;
      justify-content: flex-end;
      z-index: 200;
    }

    .ledger-drawer {
      width: 520px;
      max-width: 90vw;
      background: var(--bg-surface);
      border-left: 1px solid var(--border-subtle);
      height: 100%;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      overflow-y: auto;
    }

    .drawer-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--border-subtle);
      padding-bottom: 12px;
    }

    .drawer-title {
      font-size: 18px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .btn-close {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 20px;
      cursor: pointer;
    }

    .ledger-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      font-family: var(--font-code);
    }

    .ledger-table th, .ledger-table td {
      padding: 8px 10px;
      text-align: left;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }

    .ledger-table th {
      color: var(--text-muted);
      text-transform: uppercase;
      font-size: 10px;
    }
  </style>
</head>
<body>

  <!-- Top Navigation Header -->
  <header>
    <div class="brand-section">
      <div class="logo-badge" id="appLogo">⚡</div>
      <div class="brand-title">
        <h1>NVIDIA Nemotron 3 Ultra <span class="badge-chip" id="clusterStatusBadge">550B LatentMoE</span></h1>
        <div class="brand-subtitle" id="remoteEndpointText">vLLM Inference Engine: http://localhost:8000/v1</div>
      </div>
    </div>

    <!-- Live Telemetry Bar -->
    <div class="metrics-bar" id="metricsBar">
      <div class="metric-item">
        <span class="metric-label">Tokens</span>
        <span class="metric-val val-tokens" id="statTokens">0</span>
      </div>
      <div class="metric-item">
        <span class="metric-label">Speed</span>
        <span class="metric-val val-speed" id="statSpeed">0 t/s</span>
      </div>
      <div class="metric-item">
        <span class="metric-label">GCP Spot Cost</span>
        <span class="metric-val val-cost" id="statCost">$0.000000</span>
      </div>
    </div>

    <div class="header-actions">
      <button class="btn-secondary" id="btnOpenLedger">
        <span>📊</span> Cost Ledger
      </button>
      <a href="/docs" target="_blank" class="btn-secondary" style="text-decoration:none;">
        <span>📖</span> API Docs
      </a>
    </div>
  </header>

  <!-- Main Chat / Mission Workspace -->
  <main>
    <!-- Ribbon: Mode & Fast Presets -->
    <div class="control-ribbon">
      <div class="mode-switch-group">
        <button class="mode-btn active" id="btnModeMission">
          <span>🚀</span> Autonomous Mission
        </button>
        <button class="mode-btn" id="btnModeChat">
          <span>💬</span> Direct Chat
        </button>
      </div>

      <div class="toggle-group">
        <label class="switch-label" title="Enable Chain-of-Thought thinking stream from Nemotron">
          <input type="checkbox" class="switch-checkbox" id="chkThinking" checked>
          <span>Deep Reasoning Stream</span>
        </label>
      </div>

      <div class="quick-prompts-bar">
        <div class="quick-pill" onclick="setPrompt('Audit repository database queries for N+1 anti-patterns and suggest selectinload fixes.')">🔍 Audit SQL N+1</div>
        <div class="quick-pill" onclick="setPrompt('Inspect repository AST and verify clean 4-tier layer boundaries (Gate 4).')">📐 Verify Architecture</div>
        <div class="quick-pill" onclick="setPrompt('Run repository verification gates 1 through 5 and auto-debugger.')">🧪 Run Gates 1-5</div>
        <div class="quick-pill" onclick="setPrompt('Verify Alembic migration reversible rules and Level 5 approval gates.')">🛡️ Database Safety</div>
      </div>
    </div>

    <!-- Chat & Reasoning Scroll Area -->
    <div class="chat-scroll-container" id="chatContainer">
      <div class="msg-row">
        <div class="msg-avatar avatar-nemotron">⚡</div>
        <div class="msg-body-wrapper">
          <div class="bubble-assistant">
            <strong>Welcome to the NVIDIA Nemotron 3 Ultra Autonomous Agent Engine!</strong>
            <p style="margin-top:6px; color: var(--text-secondary);">
              This interface is directly connected to the reasoning loop. In <strong>Autonomous Mission Mode</strong>, the agent reasons deeply, writes code, queries AST graphs, checks database safety, and self-corrects using verification gates. In <strong>Direct Chat Mode</strong>, you can converse directly with the 550B model.
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Input Dock -->
    <div class="input-dock">
      <textarea 
        class="input-textarea" 
        id="userInput" 
        placeholder="Type a coding mission or question... (Enter to send, Shift+Enter for newline)"
        rows="1"
      ></textarea>
      
      <div class="input-actions-bar">
        <div class="input-hints">
          <span id="modeIndicatorLabel">Mode: Autonomous Multi-Turn Mission (Tools Active)</span>
        </div>
        <div class="action-buttons">
          <button class="btn-stop" id="btnStopStream">⏹ Stop</button>
          <button class="btn-send" id="btnSend">
            <span>Dispatch</span> ⚡
          </button>
        </div>
      </div>
    </div>
  </main>

  <!-- Cost Ledger Drawer Modal -->
  <div class="ledger-modal-backdrop" id="ledgerModal">
    <div class="ledger-drawer">
      <div class="drawer-header">
        <div class="drawer-title">
          <span>📊</span> Mission Cost & Token Ledger
        </div>
        <button class="btn-close" id="btnCloseLedger">&times;</button>
      </div>
      <div id="ledgerSummaryBox" style="background:rgba(255,255,255,0.03); border:1px solid var(--border-subtle); border-radius:8px; padding:12px; font-size:13px; font-family:var(--font-code);">
        Loading metrics...
      </div>
      <h3 style="font-size:14px; color:var(--text-secondary); margin-top:8px;">Recent Missions</h3>
      <div style="overflow-x:auto;">
        <table class="ledger-table">
          <thead>
            <tr>
              <th>Mission ID</th>
              <th>Tokens</th>
              <th>Cost ($)</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody id="ledgerTableBody">
            <tr><td colspan="4" style="text-align:center; color:var(--text-muted);">Fetching history...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    // State Variables
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
    const btnStopStream = document.getElementById('btnStopStream');
    const btnModeMission = document.getElementById('btnModeMission');
    const btnModeChat = document.getElementById('btnModeChat');
    const chkThinking = document.getElementById('chkThinking');
    const modeIndicatorLabel = document.getElementById('modeIndicatorLabel');
    const statTokens = document.getElementById('statTokens');
    const statSpeed = document.getElementById('statSpeed');
    const statCost = document.getElementById('statCost');
    const remoteEndpointText = document.getElementById('remoteEndpointText');
    const clusterStatusBadge = document.getElementById('clusterStatusBadge');

    // Ledger Modal Elements
    const ledgerModal = document.getElementById('ledgerModal');
    const btnOpenLedger = document.getElementById('btnOpenLedger');
    const btnCloseLedger = document.getElementById('btnCloseLedger');
    const ledgerSummaryBox = document.getElementById('ledgerSummaryBox');
    const ledgerTableBody = document.getElementById('ledgerTableBody');

    // Load initial config from server
    async function loadAgentConfig() {
      try {
        const resp = await fetch('/api/v1/agent/config');
        if (resp.ok) {
          const cfg = await resp.json();
          remoteEndpointText.textContent = `vLLM Endpoint: ${cfg.nemotron_api_base} | Model: ${cfg.nemotron_model}`;
        }
      } catch (err) {
        console.warn('Failed to load agent config:', err);
      }
    }
    loadAgentConfig();

    // Mode Switchers
    btnModeMission.addEventListener('click', () => {
      currentMode = 'mission';
      btnModeMission.classList.add('active');
      btnModeChat.classList.remove('active');
      modeIndicatorLabel.textContent = 'Mode: Autonomous Multi-Turn Mission (Tools Active)';
      btnSend.innerHTML = '<span>Dispatch</span> ⚡';
    });

    btnModeChat.addEventListener('click', () => {
      currentMode = 'chat';
      btnModeChat.classList.add('active');
      btnModeMission.classList.remove('active');
      modeIndicatorLabel.textContent = 'Mode: Direct Conversational Chat (Reasoning Only)';
      btnSend.innerHTML = '<span>Send Message</span> 💬';
    });

    function setPrompt(text) {
      userInput.value = text;
      autoResizeTextarea();
      userInput.focus();
    }

    function autoResizeTextarea() {
      userInput.style.height = 'auto';
      userInput.style.height = Math.min(userInput.scrollHeight, 160) + 'px';
    }
    userInput.addEventListener('input', autoResizeTextarea);

    userInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
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
      btnStopStream.style.display = streaming ? 'block' : 'none';
      if (!streaming) {
        userInput.focus();
      }
    }

    function appendUserMessage(text) {
      const row = document.createElement('div');
      row.className = 'msg-row msg-user';
      row.innerHTML = `
        <div class="msg-body-wrapper">
          <div class="bubble-user">${escapeHtml(text)}</div>
        </div>
        <div class="msg-avatar avatar-user">👤</div>
      `;
      chatContainer.appendChild(row);
      scrollChatToBottom();
    }

    function createAssistantMessageSlot() {
      const row = document.createElement('div');
      row.className = 'msg-row';
      const bubbleId = 'bubble-' + Date.now();
      const thoughtId = 'thought-' + Date.now();

      row.innerHTML = `
        <div class="msg-avatar avatar-nemotron">⚡</div>
        <div class="msg-body-wrapper">
          <div class="bubble-assistant">
            <div class="thought-container" id="${thoughtId}" style="display:none;">
              <div class="thought-header" onclick="toggleThought('${thoughtId}')">
                <div class="thought-title">
                  <div class="pulse-dot"></div>
                  <span>Nemotron 3 Ultra — Reasoning Process</span>
                </div>
                <span style="font-size:11px; color:#A855F7;">▾</span>
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

    function toggleThought(id) {
      const body = document.getElementById(id + '-body');
      if (body) {
        body.style.display = body.style.display === 'none' ? 'block' : 'none';
      }
    }

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
        // Mode 1: Autonomous Agent Mission with Tools & SSE
        try {
          // 1. Dispatch mission via POST
          const initResp = await fetch('/api/v1/agent/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ goal: text, max_iterations: 15 })
          });
          const initData = await initResp.json();
          const missionId = initData.mission_id || Date.now();

          // 2. Open EventSource SSE
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
                  <div class="tool-step-title">⚙️ Tool Executing: ${eventData.tool}</div>
                  <div class="tool-step-obs">Args: ${JSON.stringify(eventData.arguments)}</div>
                `;
                slots.bubbleEl.appendChild(card);
              } else if (type === 'tool_observation') {
                const obsDiv = document.createElement('div');
                obsDiv.className = 'tool-step-card';
                obsDiv.innerHTML = `
                  <div class="tool-step-title">✅ Observation: ${eventData.tool}</div>
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
                slots.bubbleEl.innerHTML += `<div style="color:#EF4444; font-size:12px; margin-top:8px;">⚠️ ${eventData.content}</div>`;
              }

              // Update Telemetry
              updateLiveTelemetry(t0, tokenCount);
              scrollChatToBottom();
            } catch (err) {
              console.warn('SSE Parse err', err);
            }
          };

          activeEventSource.onerror = (err) => {
            console.warn('SSE stream closed', err);
            activeEventSource.close();
            setStreamingState(false);
          };

        } catch (err) {
          slots.bubbleEl.innerHTML = `<span style="color:#EF4444">Error dispatching mission: ${err.message}</span>`;
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
            const lines = buffer.split('\\n');
            buffer = lines.pop(); // keep remainder

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
                    slots.bubbleEl.innerHTML += `<div style="color:#EF4444; font-size:12px; margin-top:8px;">⚠️ ${chunk.content}</div>`;
                  }
                  updateLiveTelemetry(t0, tokenCount);
                  scrollChatToBottom();
                } catch (e) {
                  // Json parse error on chunk
                }
              }
            }
          }

          conversationHistory.push({ role: 'assistant', content: responseAccumulator });
        } catch (err) {
          if (err.name !== 'AbortError') {
            slots.bubbleEl.innerHTML = `<span style="color:#EF4444">Chat Error: ${err.message}</span>`;
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
      // Amortized GCP Spot price (~$0.000003 per token)
      sessionCost += 0.000003;

      statTokens.textContent = sessionTokens.toLocaleString();
      statSpeed.textContent = `${tps} t/s`;
      statCost.textContent = `$${sessionCost.toFixed(6)}`;
    }

    function scrollChatToBottom() {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function escapeHtml(str) {
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    // Markdown Parser (fenced code, bold, lists, headers)
    function formatMarkdown(text) {
      if (!text) return "";
      let html = text;

      // Code blocks with syntax badge & copy button
      html = html.replace(/```([a-zA-Z0-9_+-]*)\\n([\\s\\S]*?)```/g, (match, lang, code) => {
        const langLabel = lang ? lang.toUpperCase() : "CODE";
        return `<pre><div style="display:flex; justify-content:space-between; color:var(--text-muted); font-size:11px; margin-bottom:6px;"><span>${langLabel}</span></div><code>${escapeHtml(code)}</code></pre>`;
      });

      // Inline code
      html = html.replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.08); padding:2px 5px; border-radius:4px;">$1</code>');

      // Headings
      html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
      html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
      html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

      // Bold & Italic
      html = html.replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
      html = html.replace(/\\*(.*?)\\*/g, '<em>$1</em>');

      // Bullet lists
      html = html.replace(/^\\s*-\\s+(.*$)/gim, '<li>$1</li>');
      html = html.replace(/(<li>.*<\\/li>)/s, '<ul>$1</ul>');

      // Line breaks
      html = html.replace(/\\n/g, '<br>');

      return html;
    }

    // Cost Ledger Drawer Modal Events
    btnOpenLedger.addEventListener('click', async () => {
      ledgerModal.style.display = 'flex';
      try {
        const [sumResp, ledgerResp] = await Promise.all([
          fetch('/api/v1/agent/cost/summary'),
          fetch('/api/v1/agent/cost/ledger?limit=10')
        ]);

        if (sumResp.ok) {
          const sum = await sumResp.json();
          ledgerSummaryBox.innerHTML = `
            <div><strong>Total Missions:</strong> ${sum.total_missions}</div>
            <div><strong>Total Tokens Processed:</strong> ${sum.total_tokens.toLocaleString()} (Prompt: ${sum.total_prompt_tokens.toLocaleString()}, Output: ${sum.total_completion_tokens.toLocaleString()})</div>
            <div><strong>Thinking Tokens:</strong> ${sum.total_thinking_tokens.toLocaleString()}</div>
            <div style="color:#10B981; margin-top:4px;"><strong>Cumulative Cost:</strong> $${sum.total_cost_usd.toFixed(6)} USD</div>
          `;
        }

        if (ledgerResp.ok) {
          const records = await ledgerResp.json();
          if (records.length === 0) {
            ledgerTableBody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">No recorded missions yet.</td></tr>';
          } else {
            ledgerTableBody.innerHTML = records.map(r => `
              <tr>
                <td title="${r.mission_id}">${r.mission_id.substring(0, 8)}...</td>
                <td>${r.tokens_used.toLocaleString()}</td>
                <td style="color:#10B981;">$${r.cost_usd.toFixed(6)}</td>
                <td>${r.duration_seconds.toFixed(1)}s</td>
              </tr>
            `).join('');
          }
        }
      } catch (err) {
        ledgerSummaryBox.innerHTML = `<span style="color:#EF4444">Failed to fetch ledger: ${err.message}</span>`;
      }
    });

    btnCloseLedger.addEventListener('click', () => {
      ledgerModal.style.display = 'none';
    });

    window.addEventListener('click', (e) => {
      if (e.target === ledgerModal) {
        ledgerModal.style.display = 'none';
      }
    });
  </script>
</body>
</html>
"""


@router.get("/ui", response_class=HTMLResponse, summary="Interactive Web UI Dashboard")
@router.get("/chat", response_class=HTMLResponse, summary="Interactive Web Chat")
async def serve_ui():
    """Serves the state-of-the-art dark mode interface for Nemotron 3 Ultra."""
    return HTMLResponse(content=HTML_CONTENT)
