"""Interactive Visual Explorer HTML/JS application for FAIRwDDI Question Bank."""

EXPLORER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>FAIRwDDI Question Bank & Harmonization Explorer</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-base: #0b0f19;
      --bg-surface: #111827;
      --bg-elevated: #1e293b;
      --bg-card: #162032;
      --border: #334155;
      --border-focus: #3b82f6;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      
      --c-question: #10b981;
      --c-repvar: #8b5cf6;
      --c-instvar: #f59e0b;
      --c-alias: #06b6d4;
      --c-study: #3b82f6;
      --c-concept: #ec4899;
      --c-codelist: #6366f1;

      --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
      --font-mono: 'Fira Code', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: var(--font-sans);
      background-color: var(--bg-base);
      color: var(--text);
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }

    header {
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border);
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-shrink: 0;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-logo {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      background: linear-gradient(135deg, #3b82f6, #10b981);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 14px;
      color: white;
    }
    .brand-title {
      font-size: 16px;
      font-weight: 700;
      letter-spacing: -0.3px;
    }
    .brand-subtitle {
      font-size: 12px;
      color: var(--text-muted);
    }

    .nav-tabs {
      display: flex;
      gap: 6px;
      background: var(--bg-base);
      padding: 4px;
      border-radius: 8px;
      border: 1px solid var(--border);
    }
    .nav-tab {
      padding: 6px 14px;
      font-size: 13px;
      font-weight: 500;
      border-radius: 6px;
      cursor: pointer;
      color: var(--text-muted);
      border: none;
      background: transparent;
      transition: all 0.15s;
    }
    .nav-tab:hover { color: var(--text); background: var(--bg-elevated); }
    .nav-tab.active {
      color: white;
      background: #2563eb;
      font-weight: 600;
    }

    .header-links a {
      color: var(--text-muted);
      text-decoration: none;
      font-size: 13px;
      margin-left: 16px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .header-links a:hover { color: #60a5fa; }

    /* KPI Top Bar */
    .kpi-bar {
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border);
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1px;
      background-color: var(--border);
      flex-shrink: 0;
    }
    .kpi-card {
      background: var(--bg-surface);
      padding: 10px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .kpi-label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-val { font-size: 20px; font-weight: 700; font-family: var(--font-mono); }
    .kpi-badge {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 12px;
      font-weight: 600;
      background: rgba(16, 185, 129, 0.15);
      color: #10b981;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }

    /* Main Container */
    .tab-content {
      flex: 1;
      display: none;
      height: 100%;
      overflow: hidden;
    }
    .tab-content.active { display: flex; }

    /* Explorer Layout */
    .explorer-layout {
      width: 100%;
      height: 100%;
      display: flex;
    }

    /* Left Sidebar: Question List */
    .sidebar {
      width: 380px;
      border-right: 1px solid var(--border);
      background: var(--bg-surface);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }
    .search-box {
      padding: 12px;
      border-bottom: 1px solid var(--border);
    }
    .search-input {
      width: 100%;
      background: var(--bg-base);
      border: 1px solid var(--border);
      padding: 8px 12px;
      border-radius: 6px;
      color: var(--text);
      font-size: 13px;
      outline: none;
    }
    .search-input:focus { border-color: var(--border-focus); }
    .filter-row {
      margin-top: 8px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 12px;
      color: var(--text-muted);
    }
    .filter-row label {
      display: flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
    }

    .question-list {
      flex: 1;
      overflow-y: auto;
      padding: 8px;
    }
    .q-item {
      padding: 10px 12px;
      border-radius: 6px;
      margin-bottom: 6px;
      background: var(--bg-card);
      border: 1px solid transparent;
      cursor: pointer;
      transition: all 0.15s;
    }
    .q-item:hover {
      border-color: var(--border);
      background: var(--bg-elevated);
    }
    .q-item.selected {
      border-color: #3b82f6;
      background: rgba(59, 130, 246, 0.12);
    }
    .q-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 4px;
    }
    .q-name {
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--text-muted);
    }
    .q-badge {
      font-size: 10px;
      font-weight: 600;
      padding: 2px 6px;
      border-radius: 10px;
      background: rgba(16, 185, 129, 0.2);
      color: #34d399;
    }
    .q-text {
      font-size: 13px;
      line-height: 1.4;
      color: var(--text);
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .q-meta {
      margin-top: 6px;
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
    .tag {
      font-size: 10px;
      padding: 1px 6px;
      border-radius: 4px;
      background: var(--bg-base);
      color: var(--text-muted);
      border: 1px solid var(--border);
    }

    /* Main Area: Cascade Visualizer */
    .graph-area {
      flex: 1;
      display: flex;
      flex-direction: column;
      position: relative;
      background: radial-gradient(#1e293b 1px, transparent 1px) 0 0/24px 24px, #0b0f19;
      overflow: hidden;
    }
    .graph-header {
      padding: 12px 20px;
      background: rgba(17, 24, 39, 0.85);
      backdrop-filter: blur(8px);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      z-index: 5;
    }
    .graph-title { font-size: 14px; font-weight: 600; }
    .legend {
      display: flex;
      gap: 12px;
      font-size: 11px;
    }
    .legend-item { display: flex; align-items: center; gap: 4px; }
    .dot { width: 8px; height: 8px; border-radius: 50%; }

    #cascade-canvas {
      flex: 1;
      width: 100%;
      height: 100%;
      cursor: grab;
      user-select: none;
    }
    #cascade-canvas:active { cursor: grabbing; }

    /* Zoom / Viewport controls */
    .zoom-toolbar {
      position: absolute;
      bottom: 20px;
      right: 380px;
      display: flex;
      gap: 6px;
      background: rgba(17, 24, 39, 0.9);
      padding: 6px;
      border-radius: 8px;
      border: 1px solid var(--border);
      backdrop-filter: blur(8px);
      z-index: 10;
    }
    .zoom-btn {
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text);
      width: 32px;
      height: 32px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 14px;
      font-weight: 600;
      transition: all 0.15s;
    }
    .zoom-btn:hover { background: var(--bg-elevated); border-color: var(--border-focus); }

    /* Inspector Drawer */
    .inspector {
      width: 360px;
      background: var(--bg-surface);
      border-left: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      z-index: 5;
    }
    .inspector-header {
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      font-size: 13px;
      font-weight: 600;
    }
    .inspector-body {
      flex: 1;
      overflow-y: auto;
      overflow-x: hidden;
      padding: 16px;
      font-size: 12px;
      box-sizing: border-box;
    }
    .prop-group { margin-bottom: 14px; }
    .prop-label { font-size: 10px; text-transform: uppercase; color: var(--text-dim); margin-bottom: 4px; font-weight: 600; }
    .prop-value { font-size: 12px; color: var(--text); word-break: break-all; overflow-wrap: anywhere; box-sizing: border-box; }
    .prop-mono {
      font-family: var(--font-mono);
      font-size: 11px;
      line-height: 1.45;
      background: var(--bg-base);
      padding: 8px 10px;
      border-radius: 6px;
      border: 1px solid var(--border);
      word-break: break-all;
      overflow-wrap: anywhere;
      white-space: pre-wrap;
      box-sizing: border-box;
      max-width: 100%;
      display: block;
    }

    /* Detail & Pane Views */
    .two-pane-layout {
      display: flex;
      height: 100%;
      width: 100%;
      overflow: hidden;
    }
    .detail-area {
      flex: 1;
      padding: 24px 32px;
      overflow-y: auto;
      background: var(--bg-surface);
    }
    .detail-card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 20px;
    }
    .detail-title {
      font-size: 18px;
      font-weight: 700;
      color: #f8fafc;
      margin-bottom: 6px;
    }
    .detail-subtitle {
      font-size: 13px;
      color: var(--text-muted);
      margin-bottom: 14px;
    }
    .detail-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      margin-top: 10px;
    }
    .detail-table th, .detail-table td {
      padding: 8px 12px;
      border: 1px solid var(--border);
      text-align: left;
    }
    .detail-table th {
      background: var(--bg-elevated);
      color: var(--text-dim);
      font-weight: 600;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .detail-table tr:hover {
      background: rgba(255, 255, 255, 0.02);
    }
    .action-btn {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 10px;
      font-size: 11px;
      font-weight: 600;
      color: #60a5fa;
      background: rgba(59, 130, 246, 0.1);
      border: 1px solid rgba(59, 130, 246, 0.3);
      border-radius: 4px;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.15s;
    }
    .action-btn:hover {
      background: rgba(59, 130, 246, 0.2);
      border-color: #60a5fa;
    }
    .action-btn:disabled {
      opacity: 0.35;
      cursor: not-allowed;
      border-color: var(--border-subtle);
      color: var(--text-dim);
      pointer-events: none;
    }

    /* History Navigation Toolbar */
    .nav-history {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      margin-right: 12px;
      padding-right: 12px;
      border-right: 1px solid var(--border);
    }
    .history-btn {
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 5px 11px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: all 0.15s;
    }
    .history-btn:hover:not(:disabled) {
      background: var(--bg-elevated);
      border-color: #60a5fa;
      color: #60a5fa;
    }
    .history-btn:disabled {
      opacity: 0.3;
      cursor: not-allowed;
      border-color: var(--border);
      color: var(--text-dim);
    }

    /* Loading Spinner */
    .spinner {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: var(--text-muted);
      font-size: 13px;
    }

    /* Node Card Hover and Active */
    .node-card {
      transition: filter 0.15s ease;
    }
    .node-card:hover {
      filter: drop-shadow(0 0 8px rgba(59, 130, 246, 0.5));
    }
    .node-card.selected rect.card-bg {
      stroke: #60a5fa !important;
      stroke-width: 2.5px !important;
    }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="brand-logo">DDI</div>
      <div>
        <div class="brand-title">FAIRwDDI Question Bank & Harmonization Explorer</div>
        <div class="brand-subtitle">CDSP Sciences Po / CNRS — Multi-Wave Longitudinal Question Bank</div>
      </div>
    </div>

    <div class="nav-tabs">
      <button class="nav-tab active" onclick="switchTab('explorer')">Question & Variable Cascade</button>
      <button class="nav-tab" onclick="switchTab('codelists')">Code List Explorer</button>
      <button class="nav-tab" onclick="switchTab('categories')">Category Explorer</button>
    </div>

    <div class="header-links">
      <div class="nav-history">
        <button class="history-btn" id="btn-hist-back" onclick="navHistoryBack()" title="Back (Alt+Left)" disabled>
          ‹ Back
        </button>
        <button class="history-btn" id="btn-hist-forward" onclick="navHistoryForward()" title="Forward (Alt+Right)" disabled>
          Forward ›
        </button>
      </div>
      <a href="/api/docs" target="_blank">📖 Swagger API Docs</a>
    </div>
  </header>

  <div class="kpi-bar">
    <div class="kpi-card">
      <div>
        <div class="kpi-label">Ingested Surveys</div>
        <div class="kpi-val" id="kpi-surveys">-</div>
      </div>
    </div>
    <div class="kpi-card">
      <div>
        <div class="kpi-label">Canonical Questions</div>
        <div class="kpi-val" id="kpi-questions">-</div>
      </div>
    </div>
    <div class="kpi-card">
      <div>
        <div class="kpi-label">Reusable Code Lists</div>
        <div class="kpi-val" id="kpi-codelists" style="color: #818cf8;">-</div>
      </div>
      <div class="kpi-badge">Response Scales</div>
    </div>
    <div class="kpi-card">
      <div>
        <div class="kpi-label">Standardized Categories</div>
        <div class="kpi-val" id="kpi-categories" style="color: #38bdf8;">-</div>
      </div>
      <div class="kpi-badge">Harmonized</div>
    </div>
  </div>

  <!-- TAB 1: Explorer -->
  <div id="tab-explorer" class="tab-content active">
    <div class="explorer-layout">
      <!-- Sidebar -->
      <div class="sidebar">
        <div class="search-box">
          <input type="text" id="q-search" class="search-input" placeholder="Search questions or variables..." oninput="filterQuestions()" />
          <div class="filter-row">
            <label>
              <input type="checkbox" id="q-reused-only" checked onchange="loadQuestions(0)" />
              Reused across surveys only
            </label>
            <span id="q-count-label">0 items</span>
          </div>
          <div class="filter-row" style="margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--border-subtle);">
            <button class="action-btn" id="q-prev-btn" onclick="prevQuestionsPage()" style="padding: 2px 8px; font-size: 11px;">‹ Prev</button>
            <span id="q-page-label" style="font-family: var(--font-mono); font-size: 11px; color: var(--text-dim);">0–0</span>
            <button class="action-btn" id="q-next-btn" onclick="nextQuestionsPage()" style="padding: 2px 8px; font-size: 11px;">Next ›</button>
          </div>
        </div>
        <div id="question-list" class="question-list">
          <div class="spinner">Loading questions...</div>
        </div>
      </div>

      <!-- Graph Area -->
      <div class="graph-area">
        <div class="graph-header">
          <div class="graph-title" id="graph-title">Select a question to inspect variable cascade</div>
          <div class="legend">
            <div class="legend-item"><span class="dot" style="background: var(--c-alias);"></span> URNAlias</div>
            <div class="legend-item"><span class="dot" style="background: var(--c-question);"></span> QuestionItem</div>
            <div class="legend-item"><span class="dot" style="background: var(--c-repvar);"></span> RepresentedVariable</div>
            <div class="legend-item"><span class="dot" style="background: var(--c-instvar);"></span> InstanceVariable</div>
            <div class="legend-item"><span class="dot" style="background: var(--c-codelist);"></span> CodeList</div>
          </div>
        </div>
        <svg id="cascade-canvas">
          <g id="viewport"></g>
        </svg>

        <div class="zoom-toolbar">
          <button class="zoom-btn" onclick="zoomIn()" title="Zoom In">+</button>
          <button class="zoom-btn" onclick="zoomOut()" title="Zoom Out">−</button>
          <button class="zoom-btn" onclick="fitView()" title="Fit View" style="font-size: 11px; width: 44px;">Fit</button>
        </div>
      </div>

      <!-- Inspector -->
      <div class="inspector">
        <div class="inspector-header">Entity Inspector</div>
        <div id="inspector-body" class="inspector-body">
          <div style="color: var(--text-dim); text-align: center; margin-top: 40px;">
            Click on any node in the cascade graph to view full URN attributes and hashes.
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- TAB 2: Code List Explorer -->
  <div id="tab-codelists" class="tab-content">
    <div class="two-pane-layout">
      <!-- Sidebar -->
      <div class="sidebar">
        <div class="search-box">
          <input type="text" id="cl-search" class="search-input" placeholder="Search code lists or labels..." oninput="filterCodeLists()" />
          <div class="filter-row">
            <label>
              <input type="checkbox" id="cl-reused-only" onchange="loadCodeLists(0)" />
              Reused in >1 variable only
            </label>
            <span id="cl-count-label">0 items</span>
          </div>
          <div class="filter-row" style="margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--border-subtle);">
            <button class="action-btn" id="cl-prev-btn" onclick="prevCodeListsPage()" style="padding: 2px 8px; font-size: 11px;">‹ Prev</button>
            <span id="cl-page-label" style="font-family: var(--font-mono); font-size: 11px; color: var(--text-dim);">0–0</span>
            <button class="action-btn" id="cl-next-btn" onclick="nextCodeListsPage()" style="padding: 2px 8px; font-size: 11px;">Next ›</button>
          </div>
        </div>
        <div id="codelist-list" class="question-list">
          <div class="spinner">Loading code lists...</div>
        </div>
      </div>

      <!-- Main Detail Area -->
      <div class="detail-area" id="codelist-detail">
        <div style="color: var(--text-dim); text-align: center; margin-top: 60px;">
          Select a Code List from the sidebar to inspect its response categories and variable reuse.
        </div>
      </div>
    </div>
  </div>

  <!-- TAB 3: Category Explorer -->
  <div id="tab-categories" class="tab-content">
    <div class="two-pane-layout">
      <!-- Sidebar -->
      <div class="sidebar">
        <div class="search-box">
          <input type="text" id="cat-search" class="search-input" placeholder="Search categories in French/English..." oninput="filterCategories()" />
          <div class="filter-row">
            <label>
              <input type="checkbox" id="cat-reused-only" onchange="loadCategories(0)" />
              Reused in >1 code list only
            </label>
            <span id="cat-count-label">0 items</span>
          </div>
          <div class="filter-row" style="margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--border-subtle);">
            <button class="action-btn" id="cat-prev-btn" onclick="prevCategoriesPage()" style="padding: 2px 8px; font-size: 11px;">‹ Prev</button>
            <span id="cat-page-label" style="font-family: var(--font-mono); font-size: 11px; color: var(--text-dim);">0–0</span>
            <button class="action-btn" id="cat-next-btn" onclick="nextCategoriesPage()" style="padding: 2px 8px; font-size: 11px;">Next ›</button>
          </div>
        </div>
        <div id="category-list" class="question-list">
          <div class="spinner">Loading categories...</div>
        </div>
      </div>

      <!-- Main Detail Area -->
      <div class="detail-area" id="category-detail">
        <div style="color: var(--text-dim); text-align: center; margin-top: 60px;">
          Select a Category from the sidebar to inspect its response domain standardization and longitudinal survey footprint.
        </div>
      </div>
    </div>
  </div>

  <script>
    let currentQuestions = [];
    let selectedQuestionUrn = null;
    let selectedNodeId = null;
    let currentGraphPositions = {};

    let currentCodeLists = [];
    let selectedCodeListUrn = null;

    let currentCategories = [];
    let selectedCategoryUrn = null;

    // Navigation History Stack
    let navHistory = [];
    let navHistoryIndex = -1;
    let isNavigatingHistory = false;

    // Card dimensions
    const CARD_W = 220;
    const CARD_H = 54;

    // Viewport transform (pan / zoom)
    let transform = { x: 40, y: 40, scale: 1 };
    let isPanning = false;
    let startPoint = { x: 0, y: 0 };

    async function init() {
      setupPanZoom();
      setupHistoryListeners();
      await loadOverview();
      await loadQuestions();
      loadCodeLists();
      loadCategories();

      // Check URL hash for deep link
      if (window.location.hash && window.location.hash.length > 2) {
        const raw = window.location.hash.slice(1);
        const slashIdx = raw.indexOf('/');
        if (slashIdx !== -1) {
          const tab = raw.slice(0, slashIdx);
          const urn = decodeURIComponent(raw.slice(slashIdx + 1));
          if (['explorer', 'codelists', 'categories'].includes(tab)) {
            navigateTo(tab, urn);
            return;
          }
        }
      }

      if (currentQuestions.length > 0) {
        recordHistory('explorer', currentQuestions[0].urn);
      }
    }

    function setupHistoryListeners() {
      window.addEventListener('popstate', (e) => {
        if (e.state && e.state.tab) {
          const idx = navHistory.findIndex(h => h.tab === e.state.tab && h.urn === e.state.urn);
          if (idx !== -1) {
            navHistoryIndex = idx;
          }
          applyNavState(e.state);
        }
      });

      window.addEventListener('keydown', (e) => {
        if (e.altKey && e.key === 'ArrowLeft') {
          e.preventDefault();
          navHistoryBack();
        } else if (e.altKey && e.key === 'ArrowRight') {
          e.preventDefault();
          navHistoryForward();
        }
      });
    }

    function recordHistory(tab, urn) {
      if (isNavigatingHistory) return;
      if (navHistoryIndex >= 0 && navHistoryIndex < navHistory.length) {
        const cur = navHistory[navHistoryIndex];
        if (cur.tab === tab && cur.urn === urn) return;
      }
      if (navHistoryIndex < navHistory.length - 1) {
        navHistory = navHistory.slice(0, navHistoryIndex + 1);
      }
      navHistory.push({ tab, urn });
      navHistoryIndex = navHistory.length - 1;

      const hash = `#${tab}/${encodeURIComponent(urn || '')}`;
      if (window.location.hash !== hash) {
        history.pushState({ tab, urn }, '', hash);
      }
      updateHistoryButtons();
    }

    function updateHistoryButtons() {
      const backBtn = document.getElementById('btn-hist-back');
      const fwdBtn = document.getElementById('btn-hist-forward');
      if (backBtn) backBtn.disabled = navHistoryIndex <= 0;
      if (fwdBtn) fwdBtn.disabled = navHistoryIndex >= navHistory.length - 1;
    }

    function navHistoryBack() {
      if (navHistoryIndex > 0) {
        navHistoryIndex--;
        applyNavState(navHistory[navHistoryIndex]);
      }
    }

    function navHistoryForward() {
      if (navHistoryIndex < navHistory.length - 1) {
        navHistoryIndex++;
        applyNavState(navHistory[navHistoryIndex]);
      }
    }

    async function applyNavState(state) {
      if (!state) return;
      isNavigatingHistory = true;
      switchTab(state.tab, false);
      if (state.tab === 'explorer' && state.urn) {
        if (currentQuestions.length === 0) await loadQuestions();
        await selectQuestion(state.urn, false);
      } else if (state.tab === 'codelists' && state.urn) {
        if (currentCodeLists.length === 0) await loadCodeLists();
        await selectCodeList(state.urn, false);
      } else if (state.tab === 'categories' && state.urn) {
        if (currentCategories.length === 0) await loadCategories();
        await selectCategory(state.urn, false);
      }
      const hash = `#${state.tab}/${encodeURIComponent(state.urn || '')}`;
      if (window.location.hash !== hash) {
        history.replaceState({ tab: state.tab, urn: state.urn }, '', hash);
      }
      isNavigatingHistory = false;
      updateHistoryButtons();
    }

    async function navigateTo(tab, urn) {
      switchTab(tab, false);
      if (tab === 'explorer') {
        if (currentQuestions.length === 0) await loadQuestions();
        await selectQuestion(urn, false);
      } else if (tab === 'codelists') {
        if (currentCodeLists.length === 0) await loadCodeLists();
        await selectCodeList(urn, false);
      } else if (tab === 'categories') {
        if (currentCategories.length === 0) await loadCategories();
        await selectCategory(urn, false);
      }
      recordHistory(tab, urn);
    }

    function setupPanZoom() {
      const svg = document.getElementById('cascade-canvas');

      svg.addEventListener('mousedown', (e) => {
        if (e.target.closest('.node-card')) return;
        isPanning = true;
        startPoint = { x: e.clientX - transform.x, y: e.clientY - transform.y };
      });

      window.addEventListener('mousemove', (e) => {
        if (!isPanning) return;
        transform.x = e.clientX - startPoint.x;
        transform.y = e.clientY - startPoint.y;
        applyTransform();
      });

      window.addEventListener('mouseup', () => { isPanning = false; });

      svg.addEventListener('wheel', (e) => {
        e.preventDefault();
        const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
        const rect = svg.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const newScale = Math.min(2.5, Math.max(0.3, transform.scale * zoomFactor));
        transform.x = mouseX - (mouseX - transform.x) * (newScale / transform.scale);
        transform.y = mouseY - (mouseY - transform.y) * (newScale / transform.scale);
        transform.scale = newScale;
        applyTransform();
      }, { passive: false });
    }

    function applyTransform() {
      const vp = document.getElementById('viewport');
      if (vp) {
        vp.setAttribute('transform', `translate(${transform.x}, ${transform.y}) scale(${transform.scale})`);
      }
    }

    function zoomIn() {
      transform.scale = Math.min(2.5, transform.scale * 1.25);
      applyTransform();
    }

    function zoomOut() {
      transform.scale = Math.max(0.3, transform.scale / 1.25);
      applyTransform();
    }

    function fitView() {
      const svg = document.getElementById('cascade-canvas');
      const w = svg.clientWidth || 800;
      const h = svg.clientHeight || 500;

      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      Object.values(currentGraphPositions).forEach(p => {
        minX = Math.min(minX, p.x);
        minY = Math.min(minY, p.y);
        maxX = Math.max(maxX, p.x + CARD_W);
        maxY = Math.max(maxY, p.y + CARD_H);
      });

      if (minX === Infinity) return;

      const padding = 60;
      const graphW = (maxX - minX) + padding * 2;
      const graphH = (maxY - minY) + padding * 2;

      const scale = Math.min(1.15, Math.min(w / graphW, h / graphH));
      transform.scale = Math.max(0.4, scale);
      transform.x = (w - (maxX - minX) * transform.scale) / 2 - minX * transform.scale;
      transform.y = (h - (maxY - minY) * transform.scale) / 2 - minY * transform.scale;
      applyTransform();
    }

    async function loadOverview() {
      try {
        const res = await fetch('/api/overview');
        const data = await res.json();
        document.getElementById('kpi-surveys').textContent = data.survey_count;
        document.getElementById('kpi-questions').textContent = data.question_count;
        document.getElementById('kpi-codelists').textContent = data.codelist_count;
        document.getElementById('kpi-categories').textContent = data.category_count;
      } catch (err) {
        console.error('Failed to load overview:', err);
      }
    }

    const PAGE_SIZE = 100;

    let questionsOffset = 0;
    let questionsHasMore = false;
    let qSearchTimer = null;

    async function loadQuestions(offset = 0) {
      questionsOffset = offset;
      const reusedEl = document.getElementById('q-reused-only');
      const reusedOnly = reusedEl ? reusedEl.checked : true;
      const searchEl = document.getElementById('q-search');
      const q = searchEl ? searchEl.value.trim() : '';

      const listEl = document.getElementById('question-list');
      if (!listEl) return;
      listEl.innerHTML = '<div class="spinner">Loading questions...</div>';

      try {
        const res = await fetch(`/api/questions?limit=${PAGE_SIZE}&offset=${offset}&q=${encodeURIComponent(q)}&reused_only=${reusedOnly}`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        const data = await res.json();
        currentQuestions = Array.isArray(data) ? data : [];
        questionsHasMore = currentQuestions.length === PAGE_SIZE;
        updateQuestionPagination();
        renderQuestionList(currentQuestions);

        if (currentQuestions.length > 0 && !selectedQuestionUrn) {
          await selectQuestion(currentQuestions[0].urn, false);
        }
      } catch (err) {
        listEl.innerHTML = `<div style="color: #f87171; padding: 12px;">Failed to load questions: ${err}</div>`;
      }
    }

    function updateQuestionPagination() {
      const prevBtn = document.getElementById('q-prev-btn');
      const nextBtn = document.getElementById('q-next-btn');
      const pageLabel = document.getElementById('q-page-label');
      if (prevBtn) prevBtn.disabled = questionsOffset === 0;
      if (nextBtn) nextBtn.disabled = !questionsHasMore;
      const start = currentQuestions.length > 0 ? questionsOffset + 1 : 0;
      const end = questionsOffset + currentQuestions.length;
      if (pageLabel) pageLabel.textContent = `${start}–${end}`;
    }

    function prevQuestionsPage() {
      if (questionsOffset > 0) {
        loadQuestions(Math.max(0, questionsOffset - PAGE_SIZE));
      }
    }

    function nextQuestionsPage() {
      if (questionsHasMore) {
        loadQuestions(questionsOffset + PAGE_SIZE);
      }
    }

    function renderQuestionList(items) {
      const listEl = document.getElementById('question-list');
      if (!listEl) return;
      document.getElementById('q-count-label').textContent = `${items.length} items`;

      if (items.length === 0) {
        listEl.innerHTML = '<div style="color: var(--text-dim); text-align: center; margin-top: 20px;">No questions found.</div>';
        return;
      }

      listEl.innerHTML = items.map(q => `
        <div class="q-item ${q.urn === selectedQuestionUrn ? 'selected' : ''}" onclick="selectQuestion('${q.urn}')">
          <div class="q-header">
            <span class="q-name">${escapeHtml(q.name)}</span>
            ${q.is_reused ? '<span class="q-badge">Reused</span>' : ''}
          </div>
          <div class="q-text">${escapeHtml(q.text_display)}</div>
          <div class="q-meta">
            ${q.surveys.map(s => `<span class="tag">${escapeHtml(s.replace('fr.cdsp.ddi.', '').replace('fr.cdsp.', ''))}</span>`).join('')}
            ${q.variable_names.map(v => `<span class="tag" style="color: #f59e0b;">${escapeHtml(v)}</span>`).slice(0, 3).join('')}
          </div>
        </div>
      `).join('');
    }

    function filterQuestions() {
      clearTimeout(qSearchTimer);
      qSearchTimer = setTimeout(() => {
        loadQuestions(0);
      }, 250);
    }

    async function selectQuestion(urn, pushHistory = true) {
      selectedQuestionUrn = urn;
      selectedNodeId = urn;
      renderQuestionList(currentQuestions);

      if (pushHistory) {
        recordHistory('explorer', urn);
      }

      const qObj = currentQuestions.find(x => x.urn === urn);
      if (qObj) {
        document.getElementById('graph-title').textContent = qObj.text_display;
      }

      try {
        const res = await fetch(`/api/questions/${encodeURIComponent(urn)}/cascade`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const graph = await res.json();
        renderCascadeGraph(graph);
        const qNode = graph.nodes.find(n => n.id === urn);
        if (qNode) {
          document.getElementById('graph-title').textContent = qNode.sublabel || qNode.label;
          inspectNode(qNode);
        }
      } catch (err) {
        console.error('Failed to load cascade:', err);
      }
    }

    function renderCascadeGraph(graph) {
      const svg = document.getElementById('cascade-canvas');
      const width = svg.clientWidth || 800;
      const height = svg.clientHeight || 500;
      svg.innerHTML = '';

      // Defs for arrow markers
      const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
      defs.innerHTML = `
        <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M 1 2 L 7 5 L 1 8 Z" fill="#64748b" />
        </marker>
        <marker id="arrow-alias" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M 1 2 L 7 5 L 1 8 Z" fill="#06b6d4" />
        </marker>
        <marker id="arrow-down" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M 1 2 L 7 5 L 1 8 Z" fill="#818cf8" />
        </marker>
      `;
      svg.appendChild(defs);

      const viewport = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      viewport.setAttribute('id', 'viewport');
      svg.appendChild(viewport);

      // Hierarchical Flow:
      // Col 0: URNAlias (x = 40)
      // Col 1: QuestionItem / ConceptualVariable (x = 330)
      // Col 2: RepresentedVariable (x = 690) with CodeList placed directly BELOW it
      // Col 3: InstanceVariable (x = 1050) (Dataset realizations in waves)

      const col0_X = 40;
      const col1_X = 330;
      const col2_X = 690;
      const col3_X = 1050;
      const CL_H = 46;
      const CL_GAP = 20;

      const repVars = graph.nodes.filter(n => n.type === 'RepresentedVariable');
      const aliases = graph.nodes.filter(n => n.type === 'URNAlias');
      const questions = graph.nodes.filter(n => n.type === 'QuestionItem' || n.type === 'ConceptualVariable');

      // Map RV -> CodeList (membership) and RV -> InstanceVariables (realization)
      const rvToCl = {};
      const rvToIvs = {};
      graph.links.forEach(l => {
        if (l.type === 'membership') rvToCl[l.source] = l.target;
        if (l.type === 'realization') {
          rvToIvs[l.source] = rvToIvs[l.source] || [];
          rvToIvs[l.source].push(l.target);
        }
      });

      const positions = {};
      const waveClusterH = CARD_H + CL_GAP + CL_H + 26; // RV (54) + gap (20) + CL (46) + inter-wave gap (26) = 146px
      const waveCount = Math.max(repVars.length, 1);
      const totalWaveH = waveCount * waveClusterH;
      const startY = Math.max(40, (height - totalWaveH) / 2);

      // 1. Position Waves: RepresentedVariables, CodeLists (BELOW RV), and InstanceVariables
      repVars.forEach((rv, idx) => {
        const clusterY = startY + idx * waveClusterH;
        positions[rv.id] = { x: col2_X, y: clusterY, type: 'RepresentedVariable' };

        // CodeList sits directly BELOW its RepresentedVariable
        const clId = rvToCl[rv.id];
        if (clId) {
          positions[clId] = { x: col2_X, y: clusterY + CARD_H + CL_GAP, type: 'CodeList' };
        }

        // InstanceVariables sit in Column 3 aligned horizontally with the RV
        const ivIds = rvToIvs[rv.id] || [];
        ivIds.forEach((ivId, ivIdx) => {
          positions[ivId] = { x: col3_X, y: clusterY + ivIdx * 64, type: 'InstanceVariable' };
        });
      });

      // Handle any orphan CodeLists or InstanceVariables not caught in mapping
      graph.nodes.forEach(n => {
        if (!positions[n.id]) {
          if (n.type === 'CodeList') {
            positions[n.id] = { x: col2_X, y: startY + CARD_H + CL_GAP, type: 'CodeList' };
          } else if (n.type === 'InstanceVariable') {
            positions[n.id] = { x: col3_X, y: startY, type: 'InstanceVariable' };
          }
        }
      });

      // 2. Position QuestionItem & ConceptualVariable (Col 1, vertically centered)
      const qiY = startY + Math.max(0, (waveCount - 1) * waveClusterH) / 2;
      questions.forEach((q, idx) => {
        positions[q.id] = { x: col1_X, y: qiY + (idx - (questions.length - 1) / 2) * 70, type: q.type };
      });

      // 3. Position URNAliases (Col 0, vertically distributed)
      const aliasCount = aliases.length;
      aliases.forEach((a, idx) => {
        const aSpacing = 68;
        const aStartY = qiY - ((aliasCount - 1) * aSpacing) / 2;
        positions[a.id] = { x: col0_X, y: aStartY + idx * aSpacing, type: 'URNAlias' };
      });

      currentGraphPositions = positions;

      // 4. Render Links
      graph.links.forEach(l => {
        const s = positions[l.source];
        const t = positions[l.target];
        if (!s || !t) return;

        // Special case: CodeList directly below RepresentedVariable
        if (l.type === 'membership') {
          const x = s.x + CARD_W / 2;
          const y1 = s.y + CARD_H;
          const y2 = t.y;

          const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
          path.setAttribute('d', `M ${x} ${y1} L ${x} ${y2}`);
          path.setAttribute('stroke', '#818cf8');
          path.setAttribute('stroke-width', '2');
          path.setAttribute('marker-end', 'url(#arrow-down)');
          viewport.appendChild(path);
          return;
        }

        // Standard Horizontal Left-to-Right Links
        const sH = s.type === 'CodeList' ? CL_H : CARD_H;
        const tH = t.type === 'CodeList' ? CL_H : CARD_H;
        const x1 = s.x + CARD_W;
        const y1 = s.y + sH / 2;
        const x2 = t.x;
        const y2 = t.y + tH / 2;

        const isAlias = l.type === 'alias';
        const dx = Math.abs(x2 - x1);
        const cpOffset = Math.max(45, dx * 0.45);

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        const d = `M ${x1} ${y1} C ${x1 + cpOffset} ${y1}, ${x2 - cpOffset} ${y2}, ${x2} ${y2}`;
        path.setAttribute('d', d);
        path.setAttribute('stroke', isAlias ? '#06b6d4' : '#64748b');
        path.setAttribute('stroke-width', '2');
        path.setAttribute('fill', 'none');
        if (isAlias) path.setAttribute('stroke-dasharray', '4,4');
        path.setAttribute('marker-end', isAlias ? 'url(#arrow-alias)' : 'url(#arrow)');
        viewport.appendChild(path);
      });

      // 5. Render Node Cards
      graph.nodes.forEach(n => {
        const pos = positions[n.id];
        if (!pos) return;

        const color = getNodeColor(n.type);
        const isSelected = n.id === selectedNodeId;
        const isCodeList = n.type === 'CodeList';
        const cardH = isCodeList ? CL_H : CARD_H;

        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('class', `node-card ${isSelected ? 'selected' : ''}`);
        g.setAttribute('transform', `translate(${pos.x}, ${pos.y})`);
        g.style.cursor = 'pointer';
        g.onclick = (e) => {
          e.stopPropagation();
          selectedNodeId = n.id;
          document.querySelectorAll('.node-card').forEach(el => el.classList.remove('selected'));
          g.classList.add('selected');
          inspectNode(n);
        };

        // Card Background Box
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('class', 'card-bg');
        rect.setAttribute('width', CARD_W);
        rect.setAttribute('height', cardH);
        rect.setAttribute('rx', '8');
        rect.setAttribute('fill', isCodeList ? '#0f172a' : '#162032');
        rect.setAttribute('stroke', isSelected ? '#60a5fa' : color);
        rect.setAttribute('stroke-width', isSelected ? '2.5' : '1.5');
        g.appendChild(rect);

        // Left Colored Accent Bar
        const bar = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        bar.setAttribute('width', '5');
        bar.setAttribute('height', cardH);
        bar.setAttribute('rx', '4');
        bar.setAttribute('fill', color);
        g.appendChild(bar);

        // Entity Type Badge
        const typeText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        typeText.setAttribute('x', '14');
        typeText.setAttribute('y', '15');
        typeText.setAttribute('fill', color);
        typeText.setAttribute('font-size', '9');
        typeText.setAttribute('font-weight', '700');
        typeText.setAttribute('letter-spacing', '0.5');
        typeText.textContent = isCodeList ? 'CODE LIST' : n.type.toUpperCase();
        g.appendChild(typeText);

        // Main Title Label
        const titleText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        titleText.setAttribute('x', '14');
        titleText.setAttribute('y', '30');
        titleText.setAttribute('fill', '#f8fafc');
        titleText.setAttribute('font-size', '12');
        titleText.setAttribute('font-weight', '600');
        titleText.textContent = truncate(n.label, 24);
        g.appendChild(titleText);

        // Subtitle / Scope Label
        if (n.sublabel && !isCodeList) {
          const subText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
          subText.setAttribute('x', '14');
          subText.setAttribute('y', '44');
          subText.setAttribute('fill', '#94a3b8');
          subText.setAttribute('font-size', '10');
          subText.textContent = truncate(n.sublabel, 30);
          g.appendChild(subText);
        }

        viewport.appendChild(g);
      });

      // Auto-fit graph cleanly into canvas on initial load
      setTimeout(() => fitView(), 10);
    }

    function truncate(str, maxLen) {
      if (!str) return '';
      str = String(str);
      return str.length > maxLen ? str.slice(0, maxLen - 1) + '…' : str;
    }

    function getNodeColor(type) {
      switch(type) {
        case 'QuestionItem': return '#10b981';
        case 'RepresentedVariable': return '#8b5cf6';
        case 'InstanceVariable': return '#f59e0b';
        case 'URNAlias': return '#06b6d4';
        case 'ConceptualVariable': return '#ec4899';
        case 'CodeList': return '#6366f1';
        default: return '#3b82f6';
      }
    }

    function inspectNode(node) {
      if (!node) return;
      const body = document.getElementById('inspector-body');
      body.innerHTML = `
        <div class="prop-group">
          <div class="prop-label">Entity Type</div>
          <div class="prop-value"><span class="tag" style="background: ${getNodeColor(node.type)}; color: white; font-weight: 600;">${node.type}</span></div>
        </div>
        <div class="prop-group">
          <div class="prop-label">Label / Name</div>
          <div class="prop-value" style="font-weight: 600; font-size: 13px;">${escapeHtml(node.label)}</div>
        </div>
        <div class="prop-group">
          <div class="prop-label">URN Identifier</div>
          <div class="prop-mono">${escapeHtml(node.id)}</div>
        </div>
        ${node.type === 'CodeList' && node.data && node.data.codes && node.data.codes.length > 0 ? `
          <div class="prop-group">
            <div class="prop-label">Codes & Response Categories (${node.data.codes.length})</div>
            <div style="max-height: 280px; overflow-y: auto; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-base);">
              <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
                <thead>
                  <tr style="background: var(--bg-elevated); color: var(--text-dim); text-align: left; position: sticky; top: 0; z-index: 1;">
                    <th style="padding: 6px 8px; width: 44px; border-bottom: 1px solid var(--border);">Code</th>
                    <th style="padding: 6px 8px; border-bottom: 1px solid var(--border);">Category Label</th>
                  </tr>
                </thead>
                <tbody>
                  ${node.data.codes.map(c => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.04); ${c.is_missing ? 'color: var(--text-dim); font-style: italic;' : ''}">
                      <td style="padding: 5px 8px; font-family: var(--font-mono); font-weight: 600; color: #818cf8; vertical-align: top;">
                        ${escapeHtml(c.value)}
                        ${c.is_missing ? '<span style="font-size: 9px; display: block; color: #f87171;">missing</span>' : ''}
                      </td>
                      <td style="padding: 5px 8px; vertical-align: top; line-height: 1.4;">
                        ${escapeHtml(c.label || '(no label)')}
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
            <button class="action-btn" onclick="navigateTo('codelists', '${escapeHtml(node.id)}')" style="width: 100%; justify-content: center; padding: 6px 12px; margin-top: 8px;">
              Open in Code List Explorer ↗
            </button>
          </div>
        ` : ''}
        ${node.data && node.data.question_text ? `
          <div class="prop-group">
            <div class="prop-label">Question Text (Multilingual)</div>
            <div class="prop-mono">${escapeHtml(JSON.stringify(node.data.question_text, null, 2))}</div>
          </div>
        ` : ''}
        ${node.data && node.data.study_unit ? `
          <div class="prop-group">
            <div class="prop-label">Study Dataset</div>
            <div class="prop-value" style="font-weight: 500; color: #60a5fa;">${escapeHtml(node.data.study_unit)}</div>
          </div>
        ` : ''}
        ${node.data && node.data.strategy ? `
          <div class="prop-group">
            <div class="prop-label">Provenance Hash Strategy</div>
            <div class="prop-value">${escapeHtml(node.data.strategy)}</div>
          </div>
        ` : ''}
      `;
    }

    /* CODE LIST EXPLORER FUNCTIONS */
    let codeListsOffset = 0;
    let codeListsHasMore = false;
    let clSearchTimer = null;

    async function loadCodeLists(offset = 0) {
      codeListsOffset = offset;
      const reusedEl = document.getElementById('cl-reused-only');
      const reusedOnly = reusedEl ? reusedEl.checked : false;
      const searchEl = document.getElementById('cl-search');
      const q = searchEl ? searchEl.value.trim() : '';

      const listEl = document.getElementById('codelist-list');
      if (!listEl) return;
      listEl.innerHTML = '<div class="spinner">Loading code lists...</div>';

      try {
        const res = await fetch(`/api/codelists?limit=${PAGE_SIZE}&offset=${offset}&q=${encodeURIComponent(q)}&reused_only=${reusedOnly}`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        const data = await res.json();
        currentCodeLists = Array.isArray(data) ? data : [];
        codeListsHasMore = currentCodeLists.length === PAGE_SIZE;
        updateCodeListPagination();
        renderCodeListItems(currentCodeLists);

        if (currentCodeLists.length > 0 && !selectedCodeListUrn) {
          await selectCodeList(currentCodeLists[0].urn, false);
        }
      } catch (err) {
        listEl.innerHTML = `<div style="color: #f87171; padding: 12px;">Failed to load code lists: ${err}</div>`;
      }
    }

    function updateCodeListPagination() {
      const prevBtn = document.getElementById('cl-prev-btn');
      const nextBtn = document.getElementById('cl-next-btn');
      const pageLabel = document.getElementById('cl-page-label');
      if (prevBtn) prevBtn.disabled = codeListsOffset === 0;
      if (nextBtn) nextBtn.disabled = !codeListsHasMore;
      const start = currentCodeLists.length > 0 ? codeListsOffset + 1 : 0;
      const end = codeListsOffset + currentCodeLists.length;
      if (pageLabel) pageLabel.textContent = `${start}–${end}`;
    }

    function prevCodeListsPage() {
      if (codeListsOffset > 0) {
        loadCodeLists(Math.max(0, codeListsOffset - PAGE_SIZE));
      }
    }

    function nextCodeListsPage() {
      if (codeListsHasMore) {
        loadCodeLists(codeListsOffset + PAGE_SIZE);
      }
    }

    function renderCodeListItems(items) {
      const listEl = document.getElementById('codelist-list');
      if (!listEl) return;
      const countEl = document.getElementById('cl-count-label');
      if (countEl) countEl.textContent = `${items.length} items`;

      if (items.length === 0) {
        listEl.innerHTML = '<div style="color: var(--text-dim); text-align: center; margin-top: 20px;">No code lists found.</div>';
        return;
      }

      listEl.innerHTML = items.map(cl => `
        <div class="q-item ${cl.urn === selectedCodeListUrn ? 'selected' : ''}" onclick="selectCodeList('${cl.urn}')">
          <div class="q-header">
            <span class="q-name" style="color: #818cf8;">${escapeHtml(cl.name)}</span>
            ${cl.is_reused ? '<span class="q-badge">Harmonized</span>' : ''}
          </div>
          <div class="q-text" style="color: var(--text-muted); font-size: 11px;">
            ${escapeHtml(cl.codes.slice(0, 4).map(c => c.category_label || c.code_value).join(' • '))}${cl.codes.length > 4 ? '…' : ''}
          </div>
          <div class="q-meta" style="margin-top: 6px;">
            <span class="tag" style="background: rgba(99, 102, 241, 0.15); color: #818cf8; font-weight: 600;">${cl.code_count} codes</span>
            <span class="tag" style="color: #f59e0b; font-weight: 600;">${cl.variable_count} variables</span>
            ${cl.surveys.map(s => `<span class="tag">${escapeHtml(s.replace('fr.cdsp.ddi.', '').replace('fr.cdsp.', ''))}</span>`).join('')}
          </div>
        </div>
      `).join('');
    }

    function filterCodeLists() {
      clearTimeout(clSearchTimer);
      clSearchTimer = setTimeout(() => {
        loadCodeLists(0);
      }, 250);
    }

    async function selectCodeList(urn, pushHistory = true) {
      selectedCodeListUrn = urn;
      if (pushHistory) {
        recordHistory('codelists', urn);
      }
      let cl = currentCodeLists.find(x => x.urn === urn);
      if (!cl) {
        try {
          const res = await fetch(`/api/codelists/${encodeURIComponent(urn)}`);
          if (res.ok) {
            cl = await res.json();
            currentCodeLists.unshift(cl);
          }
        } catch (e) {
          console.error("Failed to fetch codelist detail", e);
        }
      }
      renderCodeListItems(currentCodeLists);
      if (cl) {
        renderCodeListDetail(cl);
        const sel = document.querySelector('#codelist-list .q-item.selected');
        if (sel) sel.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    }

    function renderCodeListDetail(cl) {
      const container = document.getElementById('codelist-detail');
      if (!container) return;
      container.innerHTML = `
        <div class="detail-card">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <div>
              <div class="detail-title" style="color: #818cf8;">${escapeHtml(cl.name)}</div>
              ${cl.description ? `<div class="detail-subtitle">${escapeHtml(cl.description)}</div>` : '<div class="detail-subtitle">Reusable DDI CodeList Specification</div>'}
            </div>
            <div>
              <span class="tag" style="background: rgba(99, 102, 241, 0.2); color: #818cf8; font-weight: 600; padding: 4px 8px;">
                ${cl.code_count} Response Codes
              </span>
              ${cl.is_reused ? '<span class="q-badge" style="padding: 4px 8px;">Reused Across Variables</span>' : ''}
            </div>
          </div>
          <div class="prop-group" style="margin-bottom: 0;">
            <div class="prop-label">URN Identifier</div>
            <div class="prop-mono">${escapeHtml(cl.urn)}</div>
          </div>
        </div>

        <div class="detail-card">
          <div class="detail-title" style="font-size: 15px; margin-bottom: 4px;">Response Domain Specification (Codes & Categories)</div>
          <div class="detail-subtitle">Allowable numerical values and standardized category response labels.</div>
          <table class="detail-table">
            <thead>
              <tr>
                <th style="width: 70px;">Code</th>
                <th>Category Response Label</th>
                <th style="width: 90px;">Status</th>
                <th>Category Reference</th>
              </tr>
            </thead>
            <tbody>
              ${cl.codes.map(c => `
                <tr style="${c.is_missing ? 'color: var(--text-dim); font-style: italic;' : ''}">
                  <td style="font-family: var(--font-mono); font-weight: 700; color: #818cf8; font-size: 12px;">${escapeHtml(c.code_value)}</td>
                  <td style="font-weight: 500;">
                    ${escapeHtml(c.category_label || '(no label)')}
                    ${c.category_urn ? `
                      <a href="javascript:void(0)" onclick="navigateTo('categories', '${c.category_urn}');" class="action-btn" style="margin-left: 8px; font-size: 10px; padding: 2px 6px;">
                        Inspect Category ↗
                      </a>
                    ` : ''}
                  </td>
                  <td>
                    ${c.is_missing ? '<span style="color: #f87171; font-weight: 600;">Missing</span>' : '<span style="color: #34d399;">Valid</span>'}
                  </td>
                  <td class="prop-mono" style="font-size: 10px; padding: 3px 6px;">${escapeHtml(c.category_urn)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>

        <div class="detail-card">
          <div class="detail-title" style="font-size: 15px; margin-bottom: 4px;">Associated Variables & Questions (${cl.variable_count})</div>
          <div class="detail-subtitle">Variables and survey datasets sharing this standardized response domain.</div>
          ${cl.questions && cl.questions.length > 0 ? `
            <table class="detail-table">
              <thead>
                <tr>
                  <th style="width: 140px;">Question Item</th>
                  <th>Question Wording</th>
                  <th style="width: 130px;">Action</th>
                </tr>
              </thead>
              <tbody>
                ${cl.questions.map(q => `
                  <tr>
                    <td style="font-family: var(--font-mono); font-weight: 600; color: #10b981;">${escapeHtml(q.name)}</td>
                    <td>${escapeHtml(q.text)}</td>
                    <td>
                      <button class="action-btn" onclick="navigateTo('explorer', '${q.urn}');">
                        View Cascade ↗
                      </button>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          ` : `
            <div style="color: var(--text-dim); font-size: 12px; margin-top: 8px;">
              Used by variables: ${cl.variable_names.join(', ')}
            </div>
          `}
        </div>
      `;
    }

    /* CATEGORY EXPLORER FUNCTIONS */
    let categoriesOffset = 0;
    let categoriesHasMore = false;
    let catSearchTimer = null;

    async function loadCategories(offset = 0) {
      categoriesOffset = offset;
      const reusedEl = document.getElementById('cat-reused-only');
      const reusedOnly = reusedEl ? reusedEl.checked : false;
      const searchEl = document.getElementById('cat-search');
      const q = searchEl ? searchEl.value.trim() : '';

      const listEl = document.getElementById('category-list');
      if (!listEl) return;
      listEl.innerHTML = '<div class="spinner">Loading categories...</div>';

      try {
        const res = await fetch(`/api/categories?limit=${PAGE_SIZE}&offset=${offset}&q=${encodeURIComponent(q)}&reused_only=${reusedOnly}`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        const data = await res.json();
        currentCategories = Array.isArray(data) ? data : [];
        categoriesHasMore = currentCategories.length === PAGE_SIZE;
        updateCategoryPagination();
        renderCategoryItems(currentCategories);

        if (currentCategories.length > 0 && !selectedCategoryUrn) {
          await selectCategory(currentCategories[0].urn, false);
        }
      } catch (err) {
        listEl.innerHTML = `<div style="color: #f87171; padding: 12px;">Failed to load categories: ${err}</div>`;
      }
    }

    function updateCategoryPagination() {
      const prevBtn = document.getElementById('cat-prev-btn');
      const nextBtn = document.getElementById('cat-next-btn');
      const pageLabel = document.getElementById('cat-page-label');
      if (prevBtn) prevBtn.disabled = categoriesOffset === 0;
      if (nextBtn) nextBtn.disabled = !categoriesHasMore;
      const start = currentCategories.length > 0 ? categoriesOffset + 1 : 0;
      const end = categoriesOffset + currentCategories.length;
      if (pageLabel) pageLabel.textContent = `${start}–${end}`;
    }

    function prevCategoriesPage() {
      if (categoriesOffset > 0) {
        loadCategories(Math.max(0, categoriesOffset - PAGE_SIZE));
      }
    }

    function nextCategoriesPage() {
      if (categoriesHasMore) {
        loadCategories(categoriesOffset + PAGE_SIZE);
      }
    }

    function renderCategoryItems(items) {
      const listEl = document.getElementById('category-list');
      if (!listEl) return;
      const countEl = document.getElementById('cat-count-label');
      if (countEl) countEl.textContent = `${items.length} items`;

      if (items.length === 0) {
        listEl.innerHTML = '<div style="color: var(--text-dim); text-align: center; margin-top: 20px;">No categories found.</div>';
        return;
      }

      listEl.innerHTML = items.map(cat => `
        <div class="q-item ${cat.urn === selectedCategoryUrn ? 'selected' : ''}" onclick="selectCategory('${cat.urn}')">
          <div class="q-header">
            <span class="q-name" style="color: #38bdf8;">${escapeHtml(cat.label_display)}</span>
            ${cat.is_reused ? '<span class="q-badge" style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; border-color: rgba(56, 189, 248, 0.4);">Harmonized</span>' : ''}
          </div>
          <div class="q-text" style="color: var(--text-dim); font-family: var(--font-mono); font-size: 10px;">
            ${escapeHtml(cat.name)}
          </div>
          <div class="q-meta" style="margin-top: 6px;">
            <span class="tag" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; font-weight: 600;">Used in ${cat.codelist_count} Code Lists</span>
            ${cat.surveys.map(s => `<span class="tag">${escapeHtml(s.replace('fr.cdsp.ddi.', '').replace('fr.cdsp.', ''))}</span>`).join('')}
          </div>
        </div>
      `).join('');
    }

    function filterCategories() {
      clearTimeout(catSearchTimer);
      catSearchTimer = setTimeout(() => {
        loadCategories(0);
      }, 250);
    }

    async function selectCategory(urn, pushHistory = true) {
      selectedCategoryUrn = urn;
      if (pushHistory) {
        recordHistory('categories', urn);
      }
      let cat = currentCategories.find(x => x.urn === urn);
      if (!cat) {
        try {
          const res = await fetch(`/api/categories/${encodeURIComponent(urn)}`);
          if (res.ok) {
            cat = await res.json();
            currentCategories.unshift(cat);
          }
        } catch (e) {
          console.error("Failed to fetch category detail", e);
        }
      }
      renderCategoryItems(currentCategories);
      if (cat) {
        renderCategoryDetail(cat);
        const sel = document.querySelector('#category-list .q-item.selected');
        if (sel) sel.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    }

    function renderCategoryDetail(cat) {
      const container = document.getElementById('category-detail');
      if (!container) return;
      container.innerHTML = `
        <div class="detail-card">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <div>
              <div class="detail-title" style="color: #38bdf8;">${escapeHtml(cat.label_display)}</div>
              <div class="detail-subtitle">Standardized DDI Category Entity</div>
            </div>
            <div>
              <span class="tag" style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; font-weight: 600; padding: 4px 8px;">
                Referenced in ${cat.codelist_count} Code Lists
              </span>
              ${cat.is_missing ? '<span style="color: #f87171; font-weight: 600; margin-left: 6px;">Missing Code</span>' : ''}
            </div>
          </div>
          <div class="prop-group">
            <div class="prop-label">URN Identifier</div>
            <div class="prop-mono">${escapeHtml(cat.urn)}</div>
          </div>
          ${cat.label && typeof cat.label === 'object' ? `
            <div class="prop-group" style="margin-bottom: 0;">
              <div class="prop-label">Multilingual Labels</div>
              <div class="prop-mono">${escapeHtml(JSON.stringify(cat.label, null, 2))}</div>
            </div>
          ` : ''}
        </div>

        <div class="detail-card">
          <div class="detail-title" style="font-size: 15px; margin-bottom: 4px;">Code Lists Referencing this Category (${cat.codelist_count})</div>
          <div class="detail-subtitle">Standard response domains reusing this identical category with their assigned numerical codes, survey waves, and URN identifiers.</div>
          <table class="detail-table">
            <thead>
              <tr>
                <th style="width: 170px;">Code List Name</th>
                <th style="width: 140px;">Survey Wave</th>
                <th>Code List URN</th>
                <th style="width: 70px; text-align: center;">Code</th>
                <th style="width: 70px;">Status</th>
                <th style="width: 130px;">Action</th>
              </tr>
            </thead>
            <tbody>
              ${cat.codelists.map(cr => `
                <tr style="${cr.is_missing ? 'color: var(--text-dim); font-style: italic;' : ''}">
                  <td style="font-weight: 600; color: #818cf8; vertical-align: middle;">${escapeHtml(cr.code_list_name)}</td>
                  <td style="vertical-align: middle;">
                    ${(cr.surveys || []).map(s => `
                      <span class="tag" style="background: rgba(99, 102, 241, 0.15); color: #818cf8; font-weight: 600; font-size: 11px; padding: 2px 6px;">
                        ${escapeHtml(s.replace('fr.cdsp.ddi.', '').replace('fr.cdsp.', '').replace('.ea-study', ''))}
                      </span>
                    `).join('')}
                  </td>
                  <td class="prop-mono" style="font-size: 10px; padding: 4px 6px; vertical-align: middle;">${escapeHtml(cr.code_list_urn)}</td>
                  <td style="font-family: var(--font-mono); font-weight: 700; color: #818cf8; text-align: center; vertical-align: middle;">${escapeHtml(cr.code_value)}</td>
                  <td style="vertical-align: middle;">${cr.is_missing ? '<span style="color: #f87171; font-weight: 600;">Missing</span>' : '<span style="color: #34d399; font-weight: 600;">Valid</span>'}</td>
                  <td style="vertical-align: middle;">
                    <button class="action-btn" onclick="navigateTo('codelists', '${cr.code_list_urn}');">
                      View Code List ↗
                    </button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>

        <div class="detail-card">
          <div class="detail-title" style="font-size: 15px; margin-bottom: 4px;">Longitudinal Survey Footprint (${cat.surveys.length})</div>
          <div class="detail-subtitle">Survey study units where this category is realized across data collection waves.</div>
          <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px;">
            ${cat.surveys.map(s => `
              <span class="tag" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; font-weight: 600; padding: 6px 12px; font-size: 12px;">
                📊 ${escapeHtml(s)}
              </span>
            `).join('')}
          </div>
        </div>
      `;
    }

    function switchTab(tabId, pushHistory = true) {
      document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      let urn = null;
      if (tabId === 'explorer') {
        document.querySelectorAll('.nav-tab')[0].classList.add('active');
        document.getElementById('tab-explorer').classList.add('active');
        urn = selectedQuestionUrn;
      } else if (tabId === 'codelists') {
        document.querySelectorAll('.nav-tab')[1].classList.add('active');
        document.getElementById('tab-codelists').classList.add('active');
        if (currentCodeLists.length === 0) loadCodeLists();
        urn = selectedCodeListUrn;
      } else if (tabId === 'categories') {
        document.querySelectorAll('.nav-tab')[2].classList.add('active');
        document.getElementById('tab-categories').classList.add('active');
        if (currentCategories.length === 0) loadCategories();
        urn = selectedCategoryUrn;
      }

      if (pushHistory && urn) {
        recordHistory(tabId, urn);
      }
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    window.onload = init;
  </script>
</body>
</html>
"""
