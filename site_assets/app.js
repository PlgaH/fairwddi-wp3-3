/**
 * FAIRwDDI Lifecycle — Static Portal & Documentation Engine
 * Sciences Po / CNRS — Centre des Données Socio-Politiques (CDSP)
 */

(function () {
  'use strict';

  // Global State
  const state = {
    currentRoute: 'home',
    theme: localStorage.getItem('fairwddi_theme') || (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'),
    searchOpen: false,
    selectedSearchResult: 0,
    currentDiagramId: 'cascade_diagram',
    diagramZoom: 1,
    mobileSidebarOpen: false,
    sidebarCollapsed: false
  };

  // DOM Elements cache
  let el = {};

  // Icons Helper (SVG strings)
  const icons = {
    'file-text': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>`,
    'compass': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>`,
    'database': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>`,
    'git-merge': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M6 21V9a9 9 0 0 0 9 9"/></svg>`,
    'sliders': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="20" y1="21" x2="20" y2="16"/></svg>`,
    'shield': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
    'code': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>`,
    'layers': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>`,
    'help-circle': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    'terminal': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>`,
    'book-open': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>`,
    'info': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
    'trending-up': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>`,
    'briefcase': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>`,
    'calendar': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`,
    'presentation': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h20"/><path d="M21 3v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3"/><path d="m7 21 5-5 5 5"/></svg>`,
    'github': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/></svg>`,
    'cpu': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>`,
    'tool': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>`,
    'image': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>`,
    'copy': `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`,
    'check': `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
    'search': `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
    'moon': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`,
    'sun': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`,
    'menu': `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`,
    'external': `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>`,
    'arrow-right': `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`,
    'arrow-left': `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>`,
    'sidebar': `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg>`
  };

  /**
   * Initialize Application
   */
  async function initApp() {
    el = {
      appContainer: document.querySelector('.app-container'),
      themeToggle: document.getElementById('theme-toggle-btn'),
      mobileMenuBtn: document.getElementById('mobile-menu-btn'),
      sidebar: document.getElementById('site-sidebar'),
      siteMain: document.querySelector('.site-main'),
      contentWrapper: document.querySelector('.content-wrapper'),
      mainContent: document.getElementById('main-content-target'),
      tocContainer: document.getElementById('site-toc-target'),
      progressBar: document.getElementById('reading-progress-bar'),
      searchTrigger: document.getElementById('search-trigger-btn'),
      searchModal: document.getElementById('search-modal'),
      searchInput: document.getElementById('search-modal-input'),
      searchResults: document.getElementById('search-modal-results'),
      sidebarSearchInput: document.getElementById('sidebar-search-input'),
      navLinks: document.querySelectorAll('.header-nav .nav-link')
    };

    applyTheme(state.theme);
    setupEventListeners();
    handleRoute();
  }

  function setupEventListeners() {
    window.addEventListener('hashchange', handleRoute);
    window.addEventListener('scroll', handleScroll, { passive: true });

    if (el.themeToggle) {
      el.themeToggle.addEventListener('click', toggleTheme);
    }

    if (el.mobileMenuBtn) {
      el.mobileMenuBtn.addEventListener('click', () => {
        state.mobileSidebarOpen = !state.mobileSidebarOpen;
        el.sidebar.classList.toggle('open', state.mobileSidebarOpen);
      });
    }

    document.addEventListener('click', (e) => {
      if (state.mobileSidebarOpen && !el.sidebar.contains(e.target) && !el.mobileMenuBtn.contains(e.target)) {
        state.mobileSidebarOpen = false;
        el.sidebar.classList.remove('open');
      }
      const dd = document.getElementById('diagram-custom-dropdown');
      if (dd && !dd.contains(e.target)) {
        dd.classList.remove('is-open');
        const trigger = document.getElementById('diagram-dropdown-trigger');
        if (trigger) trigger.setAttribute('aria-expanded', 'false');
      }
    });

    if (el.searchTrigger) {
      el.searchTrigger.addEventListener('click', openSearchModal);
    }

    window.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        openSearchModal();
      } else if (e.key === 'Escape') {
        if (state.searchOpen) {
          closeSearchModal();
        }
        const dd = document.getElementById('diagram-custom-dropdown');
        if (dd && dd.classList.contains('is-open')) {
          dd.classList.remove('is-open');
          const trigger = document.getElementById('diagram-dropdown-trigger');
          if (trigger) {
            trigger.setAttribute('aria-expanded', 'false');
            trigger.focus();
          }
        }
      }
    });

    if (el.searchModal) {
      el.searchModal.addEventListener('click', (e) => {
        if (e.target === el.searchModal) closeSearchModal();
      });
    }

    if (el.searchInput) {
      el.searchInput.addEventListener('input', handleSearchInput);
      el.searchInput.addEventListener('keydown', handleSearchKeydown);
    }

    if (el.sidebarSearchInput) {
      el.sidebarSearchInput.addEventListener('input', (e) => {
        filterSidebarLinks(e.target.value.toLowerCase().trim());
      });
    }
  }

  function applyTheme(theme) {
    state.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('fairwddi_theme', theme);
    if (el.themeToggle) {
      el.themeToggle.innerHTML = theme === 'dark' ? icons['sun'] : icons['moon'];
      el.themeToggle.setAttribute('title', `Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`);
    }
  }

  function toggleTheme() {
    applyTheme(state.theme === 'dark' ? 'light' : 'dark');
    if (window.mermaid) {
      try {
        window.mermaid.initialize({
          theme: state.theme === 'dark' ? 'dark' : 'default',
          startOnLoad: false
        });
      } catch (e) {
        // ignore
      }
    }
  }

  function handleRoute() {
    const rawHash = window.location.hash.slice(1).replace(/^\//, '');
    const route = rawHash.split('#')[0] || 'home';
    state.currentRoute = route;

    if (state.mobileSidebarOpen) {
      state.mobileSidebarOpen = false;
      if (el.sidebar) el.sidebar.classList.remove('open');
    }

    updateHeaderNav(route);
    updateSidebarNav(route);

    if (route === 'home' || route === '') {
      resetLayoutWidth();
      renderHomeView();
    } else if (route === 'explorer') {
      renderExplorerView();
    } else if (route.startsWith('diagrams')) {
      const parts = route.split('/');
      const diagramId = parts[1] || 'cascade_diagram';
      renderDiagramsView(diagramId);
    } else if (route === 'tools') {
      resetLayoutWidth();
      renderToolsView();
    } else if (route === 'slides') {
      resetLayoutWidth();
      renderSlidesView();
    } else {
      resetLayoutWidth();
      renderDocumentView(route);
    }

    if (rawHash.includes('#')) {
      const anchorId = rawHash.split('#')[1];
      const anchorEl = document.getElementById(anchorId);
      if (anchorEl) {
        setTimeout(() => anchorEl.scrollIntoView({ behavior: 'smooth' }), 100);
      }
    } else {
      window.scrollTo({ top: 0, behavior: 'instant' });
    }
  }

  function resetLayoutWidth() {
    if (el.contentWrapper) el.contentWrapper.classList.remove('full-width');
    if (el.siteMain) el.siteMain.classList.remove('full-width');
    if (el.appContainer) el.appContainer.classList.remove('full-width');
  }

  function updateHeaderNav(route) {
    if (!el.navLinks) return;
    el.navLinks.forEach((link) => {
      const href = link.getAttribute('href').replace(/^#\/?/, '');
      if (href === 'home' && (route === 'home' || route === '')) {
        link.classList.add('active');
      } else if (href && route.startsWith(href)) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });
  }

  function updateSidebarNav(route) {
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    sidebarLinks.forEach((link) => {
      const href = link.getAttribute('href').replace(/^#\/?/, '');
      if (href === route || (href === 'home' && (route === 'home' || route === ''))) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });
  }

  function filterSidebarLinks(query) {
    const groups = document.querySelectorAll('.nav-group');
    groups.forEach((group) => {
      let visibleCount = 0;
      const links = group.querySelectorAll('.sidebar-link');
      links.forEach((link) => {
        const text = link.textContent.toLowerCase();
        if (!query || text.includes(query)) {
          link.style.display = 'flex';
          visibleCount++;
        } else {
          link.style.display = 'none';
        }
      });
      group.style.display = visibleCount > 0 ? 'flex' : 'none';
    });
  }

  function renderHomeView() {
    const data = window.FAIRWDDI_DATA || { metadata: {}, documents: [] };
    const meta = data.metadata || {};
    const stats = meta.stats || { modelsCount: 28, deliverablesCount: 10, diagramsCount: 8 };

    if (el.tocContainer) el.tocContainer.style.display = 'none';

    el.mainContent.innerHTML = `
      <div class="hero-section">
        <div class="hero-badge-row">
          <span class="badge-tag cdsp">Sciences Po • CDSP / CNRS</span>
          <span class="badge-tag primary">${meta.workPackage || 'FAIRwDDI WP3 ST3'}</span>
          <span class="badge-tag emerald">Phase I Validated • v1.0.0-RC1</span>
        </div>
        <h1 class="hero-title">
          FAIR DDI-Lifecycle <span class="accent">Architecture Portal</span>
        </h1>
        <p class="hero-subtitle">
          Standard-agnostic DDI architecture aligned with <strong>DDI 4.0 (COGS)</strong>, <strong>DDI-CDI</strong>, and <strong>DDI-Lifecycle 3.3</strong> for the Sciences Po CDSP <strong>ReQuest</strong> question bank.
        </p>

        <div class="hero-stats-grid">
          <div class="stat-card">
            <span class="stat-value">${stats.modelsCount || 28}</span>
            <span class="stat-label">Core Database Models</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">100%</span>
            <span class="stat-label">Deterministic URNs</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">JSONB</span>
            <span class="stat-label">Faceted Multilingual (ISO 639-1)</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">3-Tier</span>
            <span class="stat-label">Variable Cascade (GSIM/CDI/DDI)</span>
          </div>
        </div>

        <div class="hero-actions">
          <a href="#explorer" class="btn-primary">
            ${icons['cpu']} Launch Database Explorer
          </a>
          <a href="#deliverables/phase1_report" class="btn-secondary">
            ${icons['file-text']} Read Phase I Report
          </a>
          <a href="#diagrams" class="btn-secondary">
            ${icons['image']} Architecture Diagrams (${stats.diagramsCount || 8})
          </a>
          <a href="#tools" class="btn-secondary">
            ${icons['tool']} Interactive Tools
          </a>
        </div>
      </div>

      <div class="section-heading-wrap">
        <div>
          <h2 class="section-title">Core Deliverables & Specifications</h2>
          <p class="section-sub">Technical audit reports, formal PostgreSQL schemas, and normalization engines.</p>
        </div>
      </div>

      <div class="card-grid-3">
        <a href="#deliverables/phase1_report" class="feature-card">
          <div class="card-top">
            <div class="card-icon-wrap">${icons['file-text']}</div>
            <span class="card-badge">Deliverable</span>
          </div>
          <h3 class="card-title">Phase I Audit & Specification Report</h3>
          <p class="card-desc">Formal Phase I deliverable with legacy database audit, requirements analysis, and validated standard-agnostic DDI-L schema.</p>
          <div class="card-footer-action">Read Deliverable ${icons['arrow-right']}</div>
        </a>

        <a href="#research/database" class="feature-card">
          <div class="card-top">
            <div class="card-icon-wrap">${icons['database']}</div>
            <span class="card-badge">28 Models</span>
          </div>
          <h3 class="card-title">Target Database Model Specification</h3>
          <p class="card-desc">Complete 28-model PostgreSQL 17 schema, ER diagrams, DDIIdentifiable mixin, staging nodes, and zero-data-loss migration path.</p>
          <div class="card-footer-action">Explore Schema ${icons['arrow-right']}</div>
        </a>

        <a href="#research/summary" class="feature-card">
          <div class="card-top">
            <div class="card-icon-wrap">${icons['compass']}</div>
            <span class="card-badge">Overview</span>
          </div>
          <h3 class="card-title">Master Architectural Executive Summary</h3>
          <p class="card-desc">Comprehensive executive summary capturing all architectural decisions, design patterns, database schemas, and ingestion workflows.</p>
          <div class="card-footer-action">View Summary ${icons['arrow-right']}</div>
        </a>

        <a href="#research/normalization" class="feature-card">
          <div class="card-top">
            <div class="card-icon-wrap">${icons['sliders']}</div>
            <span class="card-badge">Pipeline</span>
          </div>
          <h3 class="card-title">Normalization & Ingestion Pipeline</h3>
          <p class="card-desc">4-phase cascade, standard-agnostic core, 2-stage ingestion pipeline, format adapters, and multilingual dictionary merging.</p>
          <div class="card-footer-action">View Ingestion Specs ${icons['arrow-right']}</div>
        </a>

        <a href="#research/hashing_algorithms" class="feature-card">
          <div class="card-top">
            <div class="card-icon-wrap">${icons['shield']}</div>
            <span class="card-badge">SHA-256 / BLAKE3</span>
          </div>
          <h3 class="card-title">Content Fingerprinting & Hashing</h3>
          <p class="card-desc">Simple vs Compound hashing, deterministic 16-char URN hashes, set-theoretic matching, and BLAKE3 benchmarks.</p>
          <div class="card-footer-action">View Hashing Algorithms ${icons['arrow-right']}</div>
        </a>

        <a href="#research/cli_user_guide" class="feature-card">
          <div class="card-top">
            <div class="card-icon-wrap">${icons['terminal']}</div>
            <span class="card-badge">CLI Manual</span>
          </div>
          <h3 class="card-title">fairwddi CLI User Guide</h3>
          <p class="card-desc">Command-line tools reference, database setup, vocabulary seeding, staging inspection, and programmatic Python APIs.</p>
          <div class="card-footer-action">Open CLI Guide ${icons['arrow-right']}</div>
        </a>
      </div>

      <div class="hero-section" style="padding: 2rem; margin-bottom: 3rem;">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1.5rem;">
          <div style="max-width: 600px;">
            <span class="badge-tag primary" style="margin-bottom: 0.5rem;">Interactive Tool</span>
            <h3 style="font-family: var(--font-heading); font-size: 1.6rem; color: var(--text-bright); margin-bottom: 0.5rem;">
              Interactive Database Model Explorer
            </h3>
            <p style="color: var(--text-muted); font-size: 0.95rem;">
              Search across all 28 PostgreSQL tables, filter by layer (Concept, Representation, Dataset, Organization, Infrastructure, Staging), view fields, generate SQL DDL, and inspect the interactive Variable Cascade spotlight.
            </p>
          </div>
          <div>
            <a href="#explorer" class="btn-primary" style="padding: 0.8rem 1.6rem;">
              ${icons['cpu']} Open Database Explorer
            </a>
          </div>
        </div>
      </div>
    `;
  }

  function renderExplorerView() {
    if (el.tocContainer) el.tocContainer.style.display = 'none';
    if (el.contentWrapper) el.contentWrapper.classList.add('full-width');
    if (el.siteMain) el.siteMain.classList.add('full-width');
    if (el.appContainer) el.appContainer.classList.add('full-width');

    el.mainContent.innerHTML = `
      <div class="article-header" style="margin-bottom: 0.85rem; padding-bottom: 0.75rem;">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
          <div>
            <div class="breadcrumbs" style="margin-bottom: 0.35rem;">
              <a href="#home">Home</a> <span>/</span> <span>Interactive Database Explorer</span>
            </div>
            <h1 class="article-title" style="font-size: 1.75rem; margin-bottom: 0.2rem;">FAIRwDDI Database Model Explorer</h1>
            <div style="font-size: 0.85rem; color: var(--text-muted);">
              28 Core Models • Standard-Agnostic PostgreSQL 17 / SQLite • DDI 4.0 / CDI / DDI-L 3.3
            </div>
          </div>

          <div class="explorer-actions">
            <button class="btn-secondary" onclick="toggleSidebarCollapse()" title="Toggle Sidebar Width">
              ${icons['sidebar']} Toggle Sidebar
            </button>
            <a href="./deliverables/research/database_explorer.html" target="_blank" rel="noopener noreferrer" class="btn-primary" style="background: linear-gradient(135deg, var(--brand-cdsp), var(--brand-primary));">
              ${icons['external']} Open in Standalone Tab ↗
            </a>
          </div>
        </div>
      </div>

      <div class="explorer-hub-container">
        <div class="explorer-toolbar">
          <div class="layer-filter-pills">
            <span style="font-size: 0.78rem; font-weight: 700; color: var(--text-dim); text-transform: uppercase;">Quick Filter Layer:</span>
            <button class="layer-pill" onclick="filterExplorerLayer('all')">All (28)</button>
            <button class="layer-pill" onclick="filterExplorerLayer('concept')">Concept (SKOS)</button>
            <button class="layer-pill" onclick="filterExplorerLayer('representation')">Representation & Questions</button>
            <button class="layer-pill" onclick="filterExplorerLayer('dataset')">Dataset (Waves)</button>
            <button class="layer-pill" onclick="filterExplorerLayer('organization')">Organization</button>
            <button class="layer-pill" onclick="filterExplorerLayer('infrastructure')">Infrastructure (URNs)</button>
            <button class="layer-pill" onclick="filterExplorerLayer('staging')">Staging & Ingestion</button>
          </div>

          <div style="font-size: 0.82rem; color: var(--text-dim);">
            <span>💡 Tip: Click nodes to inspect schema fields or generate SQL DDL</span>
          </div>
        </div>

        <div class="explorer-frame-container" id="explorer-frame-wrap">
          <iframe src="./deliverables/research/database_explorer.html" id="explorer-iframe" title="FAIRwDDI Database Explorer"></iframe>
        </div>
      </div>
    `;

    window.filterExplorerLayer = function (layer) {
      const iframe = document.getElementById('explorer-iframe');
      if (iframe && iframe.contentWindow) {
        try {
          const filterBtn = iframe.contentWindow.document.querySelector(`[data-layer="${layer}"]`);
          if (filterBtn) filterBtn.click();
        } catch (e) {
          console.log('Layer filter dispatched:', layer);
        }
      }
    };

    window.toggleSidebarCollapse = function () {
      state.sidebarCollapsed = !state.sidebarCollapsed;
      if (el.appContainer) {
        el.appContainer.classList.toggle('sidebar-collapsed', state.sidebarCollapsed);
      }
    };
  }

  /**
   * View: Diagrams Gallery (WITH CONVENIENT DROPDOWN SELECTOR & STEP BUTTONS)
   */
  function renderDiagramsView(activeDiagramId) {
    if (el.tocContainer) el.tocContainer.style.display = 'none';
    if (el.contentWrapper) el.contentWrapper.classList.add('full-width');
    if (el.siteMain) el.siteMain.classList.add('full-width');
    if (el.appContainer) el.appContainer.classList.add('full-width');

    const data = window.FAIRWDDI_DATA || {};
    const diagrams = data.diagrams || [];
    const activeDiag = diagrams.find((d) => d.id === activeDiagramId) || diagrams[0] || {};
    state.currentDiagramId = activeDiag.id;
    const currentIndex = diagrams.findIndex((d) => d.id === activeDiag.id);
    const prevDiag = currentIndex > 0 ? diagrams[currentIndex - 1] : diagrams[diagrams.length - 1];
    const nextDiag = currentIndex < diagrams.length - 1 ? diagrams[currentIndex + 1] : diagrams[0];

    // Group diagrams by category for clean optgroups
    const categories = {};
    diagrams.forEach(d => {
      const cat = d.category || 'Architecture';
      if (!categories[cat]) categories[cat] = [];
      categories[cat].push(d);
    });

    el.mainContent.innerHTML = `
      <div class="article-header" style="margin-bottom: 0.85rem; padding-bottom: 0.75rem;">
        <div class="breadcrumbs" style="margin-bottom: 0.35rem;">
          <a href="#home">Home</a> <span>/</span> <a href="#diagrams">Architecture Diagrams</a> <span>/</span> <span>${activeDiag.title || 'Diagrams'}</span>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
          <div>
            <h1 class="article-title" style="font-size: 1.75rem; margin-bottom: 0.2rem;">FAIRwDDI Architecture Diagrams & Visualizations</h1>
            <p style="color: var(--text-muted); font-size: 0.9rem;">
              High-resolution vector architecture diagrams covering data modeling, ingestion pipelines, variable cascades, and hashing workflows.
            </p>
          </div>
          <div>
            <button class="btn-secondary" onclick="toggleSidebarCollapse()" title="Toggle Sidebar Width">
              ${icons['sidebar']} Toggle Sidebar
            </button>
          </div>
        </div>
      </div>

      <div class="diagram-viewer-wrap">
        <!-- Modern Diagram Dropdown Selector Bar -->
        <div class="diagram-selector-bar">
          <div class="diagram-selector-left">
            <label class="diagram-select-label">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
              <span>Diagram:</span>
            </label>
            <div class="diagram-custom-dropdown" id="diagram-custom-dropdown">
              <button type="button" class="diagram-dropdown-trigger" id="diagram-dropdown-trigger" aria-haspopup="listbox" aria-expanded="false" onclick="toggleDiagramDropdown(event)">
                <div class="diagram-trigger-content">
                  <span class="diagram-trigger-badge">${activeDiag.category || 'Architecture'}</span>
                  <span class="diagram-trigger-title">${activeDiag.title}</span>
                </div>
                <div class="diagram-trigger-chevron">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
                </div>
              </button>

              <div class="diagram-dropdown-menu" id="diagram-dropdown-menu" role="listbox">
                ${Object.entries(categories).map(([cat, diags]) => `
                  <div class="diagram-menu-group">
                    <div class="diagram-group-header">
                      <span class="diagram-group-tag">${cat}</span>
                      <span class="diagram-group-line"></span>
                    </div>
                    ${diags.map(d => `
                      <div class="diagram-menu-item ${d.id === activeDiag.id ? 'is-active' : ''}" 
                           role="option" 
                           aria-selected="${d.id === activeDiag.id ? 'true' : 'false'}"
                           tabindex="0"
                           onclick="selectDiagram('${d.id}')"
                           onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();selectDiagram('${d.id}');}">
                        <div class="diagram-item-left">
                          <span class="diagram-item-check">
                            ${d.id === activeDiag.id ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>' : ''}
                          </span>
                          <span class="diagram-item-title">${d.title}</span>
                        </div>
                        <span class="diagram-item-badge">${d.category}</span>
                      </div>
                    `).join('')}
                  </div>
                `).join('')}
              </div>
            </div>
            <span class="diagram-index-badge">${currentIndex + 1} of ${diagrams.length}</span>
          </div>

          <div class="diagram-step-nav">
            <a href="#diagrams/${prevDiag.id}" class="diagram-nav-btn" title="Previous: ${prevDiag.title}">
              ${icons['arrow-left']} Previous
            </a>
            <a href="#diagrams/${nextDiag.id}" class="diagram-nav-btn" title="Next: ${nextDiag.title}">
              Next ${icons['arrow-right']}
            </a>
          </div>
        </div>

        <!-- Diagram Header Info -->
        <div class="diagram-viewer-header">
          <div>
            <span class="badge-tag primary" style="margin-bottom: 0.35rem;">${activeDiag.category || 'Architecture'}</span>
            <h2 style="font-family: var(--font-heading); font-size: 1.35rem; color: var(--text-bright);">${activeDiag.title}</h2>
            <p style="color: var(--text-muted); font-size: 0.88rem; margin-top: 0.25rem;">${activeDiag.description || ''}</p>
          </div>
          <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
            <button class="btn-secondary" style="padding: 0.45rem 0.85rem; font-size: 0.85rem;" onclick="downloadDiagramSVG('${activeDiag.id}')">
              Download SVG
            </button>
            <button class="btn-secondary" style="padding: 0.45rem 0.85rem; font-size: 0.85rem;" onclick="copyDiagramSVG('${activeDiag.id}')">
              ${icons['copy']} Copy XML
            </button>
          </div>
        </div>

        <!-- Diagram Canvas Container -->
        <div class="diagram-canvas-box" id="diagram-canvas-box">
          <div id="diagram-svg-render" style="width: 100%; display: flex; justify-content: center;">
            ${activeDiag.svg || '<p>Diagram SVG loading...</p>'}
          </div>

          <div class="diagram-controls-bar">
            <button class="diagram-ctrl-btn" title="Zoom Out" onclick="zoomDiagram(-0.2)">−</button>
            <button class="diagram-ctrl-btn" title="Reset Zoom" onclick="resetDiagramZoom()">100%</button>
            <button class="diagram-ctrl-btn" title="Zoom In" onclick="zoomDiagram(0.2)">+</button>
            <button class="diagram-ctrl-btn" title="Toggle Light/Dark Canvas" onclick="toggleDiagramCanvas()">🎨</button>
          </div>
        </div>
      </div>
    `;

    window.zoomDiagram = function (delta) {
      state.diagramZoom = Math.max(0.4, Math.min(3.0, state.diagramZoom + delta));
      const svg = document.querySelector('#diagram-svg-render svg');
      if (svg) svg.style.transform = `scale(${state.diagramZoom})`;
    };

    window.resetDiagramZoom = function () {
      state.diagramZoom = 1;
      const svg = document.querySelector('#diagram-svg-render svg');
      if (svg) svg.style.transform = `scale(1)`;
    };

    window.toggleDiagramCanvas = function () {
      const box = document.getElementById('diagram-canvas-box');
      if (box) box.classList.toggle('dark-canvas');
    };

    window.downloadDiagramSVG = function (diagId) {
      const diag = (window.FAIRWDDI_DATA.diagrams || []).find((d) => d.id === diagId);
      if (!diag || !diag.svg) return;
      const blob = new Blob([diag.svg], { type: 'image/svg+xml' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${diagId}.svg`;
      a.click();
      URL.revokeObjectURL(url);
    };

    window.copyDiagramSVG = function (diagId) {
      const diag = (window.FAIRWDDI_DATA.diagrams || []).find((d) => d.id === diagId);
      if (!diag || !diag.svg) return;
      navigator.clipboard.writeText(diag.svg).then(() => {
        alert('SVG XML copied to clipboard!');
      });
    };

    window.toggleSidebarCollapse = function () {
      state.sidebarCollapsed = !state.sidebarCollapsed;
      if (el.appContainer) {
        el.appContainer.classList.toggle('sidebar-collapsed', state.sidebarCollapsed);
      }
    };

    window.toggleDiagramDropdown = function (e) {
      if (e) e.stopPropagation();
      const dd = document.getElementById('diagram-custom-dropdown');
      const trigger = document.getElementById('diagram-dropdown-trigger');
      if (!dd) return;
      const isOpen = dd.classList.toggle('is-open');
      if (trigger) trigger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    };

    window.selectDiagram = function (diagId) {
      const dd = document.getElementById('diagram-custom-dropdown');
      if (dd) dd.classList.remove('is-open');
      const trigger = document.getElementById('diagram-dropdown-trigger');
      if (trigger) trigger.setAttribute('aria-expanded', 'false');
      window.location.hash = '#diagrams/' + diagId;
    };
  }

  function renderToolsView() {
    if (el.tocContainer) el.tocContainer.style.display = 'none';

    el.mainContent.innerHTML = `
      <div class="article-header">
        <div class="breadcrumbs">
          <a href="#home">Home</a> <span>/</span> <span>Interactive Tools</span>
        </div>
        <h1 class="article-title">FAIRwDDI Interactive Playground & Utilities</h1>
        <p style="color: var(--text-muted); font-size: 1.05rem;">
          Live tools to test canonical DDI URN generation, multilingual JSONB structures, and set-theoretic deduplication hashing.
        </p>
      </div>

      <div class="tools-container">
        <div class="tool-card">
          <div class="tool-header">
            <h2 class="tool-title">1. Canonical URN Generator & Validator</h2>
            <p class="tool-subtitle">Generates deterministic URNs adhering to the URL-Shortener / Git 16-character hex standard (<code>urn:ddi:fr.cdsp:EntityType:prefix-hash:1.0.0</code>).</p>
          </div>

          <div class="tool-form-grid">
            <div class="form-group">
              <label class="form-label">Agency Identifier</label>
              <input type="text" id="urn-agency" class="form-input" value="fr.cdsp" />
            </div>

            <div class="form-group">
              <label class="form-label">Entity Resource Type</label>
              <select id="urn-entity-type" class="form-select">
                <option value="ConceptualVariable|cnv">ConceptualVariable (cnv)</option>
                <option value="RepresentedVariable|rep" selected>RepresentedVariable (rep)</option>
                <option value="InstanceVariable|var">InstanceVariable (var)</option>
                <option value="QuestionItem|qst">QuestionItem (qst)</option>
                <option value="Category|cat">Category (cat)</option>
                <option value="CodeList|cl">CodeList (cl)</option>
                <option value="StudyUnit|stu">StudyUnit (stu)</option>
                <option value="Concept|cpt">Concept (cpt)</option>
                <option value="Organization|org">Organization (org)</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">Version</label>
              <input type="text" id="urn-version" class="form-input" value="1.0.0" />
            </div>

            <div class="form-group" style="grid-column: 1 / -1;">
              <label class="form-label">Content String to Hash</label>
              <input type="text" id="urn-content" class="form-input" value="Dans quelle mesure faites-vous confiance à la justice ?" />
            </div>
          </div>

          <div class="tool-output-box">
            <div class="tool-output-label">Generated Canonical URN (Deterministic 16-Char Hex)</div>
            <div class="tool-output-val" id="urn-output">Generating...</div>
            <div style="margin-top: 0.6rem; font-size: 0.8rem; color: var(--text-dim);" id="urn-hash-details"></div>
          </div>
        </div>

        <div class="tool-card">
          <div class="tool-header">
            <h2 class="tool-title">2. Multilingual JSONB Faceted Dictionary Builder</h2>
            <p class="tool-subtitle">Builds sorted-key canonical JSONB dictionaries with ISO 639-1 language tags and generates Django ORM queries.</p>
          </div>

          <div class="tool-form-grid">
            <div class="form-group">
              <label class="form-label">French (fr)</label>
              <input type="text" id="json-fr" class="form-input" value="Niveau d'éducation le plus élevé" />
            </div>
            <div class="form-group">
              <label class="form-label">English (en)</label>
              <input type="text" id="json-en" class="form-input" value="Highest level of education completed" />
            </div>
            <div class="form-group">
              <label class="form-label">German (de)</label>
              <input type="text" id="json-de" class="form-input" value="Höchster erreichter Bildungsabschluss" />
            </div>
          </div>

          <div class="tool-output-box">
            <div class="tool-output-label">Canonical JSONB (Sorted Keys)</div>
            <pre style="margin: 0; color: #38bdf8; font-family: var(--font-mono); font-size: 0.88rem;"><code id="json-output">...</code></pre>
          </div>
        </div>

        <div class="tool-card">
          <div class="tool-header">
            <h2 class="tool-title">3. Set-Theoretic Unordered Hashing Deduplicator</h2>
            <p class="tool-subtitle">Demonstrates how order-independent set hashing eliminates 70% of false duplicate alerts when XML elements appear in different orders.</p>
          </div>

          <div class="tool-form-grid">
            <div class="form-group">
              <label class="form-label">Response Options (Order A)</label>
              <textarea id="set-a" class="form-textarea" rows="4">1: Tout à fait d'accord
2: Plutôt d'accord
3: Plutôt pas d'accord
4: Pas du tout d'accord</textarea>
            </div>
            <div class="form-group">
              <label class="form-label">Response Options (Order B - Scrambled Order)</label>
              <textarea id="set-b" class="form-textarea" rows="4">4: Pas du tout d'accord
2: Plutôt d'accord
1: Tout à fait d'accord
3: Plutôt pas d'accord</textarea>
            </div>
          </div>

          <div class="tool-output-box" id="set-output-box">
            <div class="tool-output-label">Set-Theoretic Unordered CodeList Hash Comparison</div>
            <div id="set-output-result" style="font-family: var(--font-mono); font-size: 0.9rem;">Comparing...</div>
          </div>
        </div>
      </div>
    `;

    setupToolsListeners();
  }

  async function sha256Hex(str) {
    const encoder = new TextEncoder();
    const data = encoder.encode(str);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
  }

  function setupToolsListeners() {
    const updateUrn = async () => {
      const agency = document.getElementById('urn-agency')?.value.trim() || 'fr.cdsp';
      const typeEl = document.getElementById('urn-entity-type');
      if (!typeEl) return;
      const [entity, prefix] = typeEl.value.split('|');
      const version = document.getElementById('urn-version')?.value.trim() || '1.0.0';
      const content = document.getElementById('urn-content')?.value.trim() || '';

      const fullHash = await sha256Hex(content);
      const shortHash = fullHash.substring(0, 16);
      const canonicalUrn = `urn:ddi:${agency}:${entity}:${prefix}-fr-${shortHash}:${version}`;

      const outEl = document.getElementById('urn-output');
      const detEl = document.getElementById('urn-hash-details');
      if (outEl) outEl.textContent = canonicalUrn;
      if (detEl) detEl.textContent = `Full SHA-256 Content Fingerprint: ${fullHash}`;
    };

    ['urn-agency', 'urn-entity-type', 'urn-version', 'urn-content'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('input', updateUrn);
    });
    updateUrn();

    const updateJsonb = () => {
      const fr = document.getElementById('json-fr')?.value.trim() || '';
      const en = document.getElementById('json-en')?.value.trim() || '';
      const de = document.getElementById('json-de')?.value.trim() || '';

      const dict = {};
      if (de) dict.de = de;
      if (en) dict.en = en;
      if (fr) dict.fr = fr;

      const out = document.getElementById('json-output');
      if (out) out.textContent = JSON.stringify(dict, Object.keys(dict).sort(), 2);
    };

    ['json-fr', 'json-en', 'json-de'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('input', updateJsonb);
    });
    updateJsonb();

    const updateSetCompare = async () => {
      const txtA = document.getElementById('set-a')?.value || '';
      const txtB = document.getElementById('set-b')?.value || '';
      const linesA = txtA.split('\n').map((s) => s.trim()).filter(Boolean).sort();
      const linesB = txtB.split('\n').map((s) => s.trim()).filter(Boolean).sort();

      const hashA = (await sha256Hex(linesA.join('|'))).substring(0, 16);
      const hashB = (await sha256Hex(linesB.join('|'))).substring(0, 16);

      const isMatch = hashA === hashB;
      const resEl = document.getElementById('set-output-result');
      if (resEl) {
        resEl.innerHTML = `
          <div>Hash A: <span style="color: #38bdf8;">ucl-fr-${hashA}</span></div>
          <div>Hash B: <span style="color: #38bdf8;">ucl-fr-${hashB}</span></div>
          <div style="margin-top: 0.5rem; font-weight: 700; color: ${isMatch ? '#34d399' : '#f43f5e'};">
            ${isMatch ? '✅ MATCH! Both sets produce identical canonical URNs despite different XML ordering.' : '❌ Mismatch'}
          </div>
        `;
      }
    };

    ['set-a', 'set-b'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('input', updateSetCompare);
    });
    updateSetCompare();
  }

  function renderSlidesView() {
    if (el.tocContainer) el.tocContainer.style.display = 'none';

    el.mainContent.innerHTML = `
      <div class="article-header">
        <div class="breadcrumbs">
          <a href="#home">Home</a> <span>/</span> <span>Kickoff Presentation Slides</span>
        </div>
        <h1 class="article-title">Kickoff & Architecture Presentation (September 9, 2026)</h1>
        <div class="article-meta">
          <span class="meta-item"><span class="badge-tag primary">Interactive Marp Deck</span></span>
          <span class="meta-item"><span class="badge-tag cdsp">Sciences Po CDSP</span></span>
        </div>
      </div>

      <div class="explorer-hub-container">
        <div class="explorer-toolbar">
          <div>
            <span style="font-size: 0.88rem; color: var(--text-muted);">Use keyboard arrow keys or onscreen controls to navigate slides.</span>
          </div>
          <div class="explorer-actions">
            <a href="./docs/20260909_meeting.html" target="_blank" class="btn-secondary" style="padding: 0.45rem 0.85rem; font-size: 0.85rem;">
              ${icons['external']} Open in New Window
            </a>
            <a href="./docs/20260909_meeting.pdf" target="_blank" class="btn-secondary" style="padding: 0.45rem 0.85rem; font-size: 0.85rem;">
              Download PDF
            </a>
          </div>
        </div>

        <div class="explorer-frame-container" style="height: 720px;">
          <iframe src="./docs/20260909_meeting.html" title="Presentation Slides"></iframe>
        </div>
      </div>
    `;
  }

  function renderDocumentView(routeId) {
    const data = window.FAIRWDDI_DATA || { documents: [] };
    const docs = data.documents || [];
    const doc = docs.find((d) => d.id === routeId);

    if (!doc) {
      render404View(routeId);
      return;
    }

    renderTableOfContents(doc.headings || []);

    const renderedHtml = parseMarkdown(doc.content);

    const currentIndex = docs.findIndex((d) => d.id === routeId);
    const prevDoc = currentIndex > 0 ? docs[currentIndex - 1] : null;
    const nextDoc = currentIndex < docs.length - 1 ? docs[currentIndex + 1] : null;

    el.mainContent.innerHTML = `
      <article>
        <div class="article-header">
          <div class="breadcrumbs">
            <a href="#home">Home</a> <span>/</span> <span>${doc.category}</span> <span>/</span> <span>${doc.shortTitle}</span>
          </div>
          <h1 class="article-title">${doc.title}</h1>
          <div class="article-meta">
            <span class="meta-item"><span class="badge-tag primary">${doc.badge || doc.category}</span></span>
            <span class="meta-item">⏱️ ${doc.readTimeMinutes || 5} min read</span>
            <span class="meta-item">📝 ${doc.wordCount?.toLocaleString() || 0} words</span>
            <span class="meta-item">📁 <code>${doc.file}</code></span>
          </div>
        </div>

        <div class="markdown-body" id="markdown-body-content">
          ${renderedHtml}
        </div>

        <div class="article-pagination">
          ${prevDoc ? `
            <a href="#${prevDoc.id}" class="pagination-btn prev">
              <span class="pagination-label">← Previous Document</span>
              <span class="pagination-title">${prevDoc.shortTitle}</span>
            </a>
          ` : '<div></div>'}

          ${nextDoc ? `
            <a href="#${nextDoc.id}" class="pagination-btn next">
              <span class="pagination-label">Next Document →</span>
              <span class="pagination-title">${nextDoc.shortTitle}</span>
            </a>
          ` : '<div></div>'}
        </div>
      </article>
    `;

    postProcessArticle();
  }

  function render404View(routeId) {
    if (el.tocContainer) el.tocContainer.style.display = 'none';
    el.mainContent.innerHTML = `
      <div class="hero-section" style="text-align: center; padding: 4rem 2rem;">
        <span class="badge-tag cdsp" style="margin-bottom: 1rem;">Page Not Found</span>
        <h1 class="hero-title" style="font-size: 2.5rem;">404 — Document Not Found</h1>
        <p class="hero-subtitle" style="margin: 0 auto 2rem;">
          Could not locate document for route <code>#${routeId}</code>.
        </p>
        <div style="display: flex; justify-content: center; gap: 1rem;">
          <a href="#home" class="btn-primary">Return to Portal Home</a>
          <a href="#deliverables/phase1_report" class="btn-secondary">Phase I Report</a>
        </div>
      </div>
    `;
  }

  function renderTableOfContents(headings) {
    if (!el.tocContainer) return;

    if (!headings || headings.length === 0) {
      el.tocContainer.style.display = 'none';
      return;
    }

    el.tocContainer.style.display = 'flex';
    el.tocContainer.innerHTML = `
      <div class="toc-title">${icons['book-open']} On this page</div>
      <ul class="toc-list">
        ${headings.filter((h) => h.level === 2 || h.level === 3).map((h) => `
          <li class="toc-item level-${h.level}">
            <a href="#${state.currentRoute}#${h.slug}" class="toc-link" data-slug="${h.slug}">
              ${h.text}
            </a>
          </li>
        `).join('')}
      </ul>
    `;
  }

  function parseMarkdown(md) {
    if (!md) return '';

    let html = '';
    if (window.marked) {
      try {
        html = window.marked.parse(md);
      } catch (e) {
        html = fallbackMarkdownParser(md);
      }
    } else {
      html = fallbackMarkdownParser(md);
    }

    html = html.replace(/<blockquote>\s*<p>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*?)(<\/p>[\s\S]*?<\/blockquote>)/gi, (match, type, titleLine, rest) => {
      const typeLower = type.toLowerCase();
      return `<div class="callout ${typeLower}">
        <div class="callout-icon">${icons['info']}</div>
        <div class="callout-content">
          <div class="callout-title">${type}</div>
          <p>${titleLine}</p>
          ${rest.replace(/<\/p>[\s\S]*?<\/blockquote>/, '')}
        </div>
      </div>`;
    });

    html = html.replace(/href="file:\/\/\/[^"]*?deliverables\/phase1_report\.md"/g, 'href="#deliverables/phase1_report"');
    html = html.replace(/href="file:\/\/\/[^"]*?deliverables\/research\/([a-z0-9_-]+)\.md"/g, 'href="#research/$1"');
    html = html.replace(/href="file:\/\/\/[^"]*?docs\/([a-z0-9_-]+)\.md"/g, 'href="#docs/$1"');
    html = html.replace(/href="deliverables\/research\/database_explorer\.html"/g, 'href="#explorer"');
    html = html.replace(/href="docs\/assets\/diagrams\/([a-z0-9_-]+)\.svg"/g, 'href="#diagrams/$1"');

    html = html.replace(/<(h[1-4])>(.*?)<\/\1>/gi, (match, tag, content) => {
      const cleanText = content.replace(/<[^>]*>/g, '').trim();
      const slug = cleanText.toLowerCase().replace(/[^\w\- ]/g, '').trim().replace(/\s+/g, '-');
      return `<${tag} id="${slug}">${content}</${tag}>`;
    });

    return html;
  }

  function fallbackMarkdownParser(src) {
    let out = src;
    out = out.replace(/```([a-z0-9_-]*)\n([\s\S]*?)```/g, (m, lang, code) => {
      const escaped = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      return `<div class="code-block-wrapper"><div class="code-block-header"><span>${lang || 'text'}</span><button class="code-copy-btn">${icons['copy']} Copy</button></div><pre><code class="language-${lang}">${escaped}</code></pre></div>`;
    });
    out = out.replace(/`([^`]+)`/g, '<code>$1</code>');
    out = out.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    out = out.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    out = out.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    out = out.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    out = out.replace(/\n\n+/g, '</p><p>');
    return '<p>' + out + '</p>';
  }

  function postProcessArticle() {
    const mermaidBlocks = document.querySelectorAll('.markdown-body pre code.language-mermaid, .markdown-body pre.mermaid');
    if (mermaidBlocks.length > 0 && window.mermaid) {
      try {
        window.mermaid.initialize({
          theme: state.theme === 'dark' ? 'dark' : 'default',
          startOnLoad: false
        });
        mermaidBlocks.forEach((block, idx) => {
          const rawCode = block.textContent;
          const wrap = document.createElement('div');
          wrap.className = 'mermaid-diagram-wrap';
          wrap.id = `mermaid-diag-${idx}`;
          block.closest('.code-block-wrapper, pre').replaceWith(wrap);
          window.mermaid.render(`mermaid-svg-${idx}`, rawCode).then(({ svg }) => {
            wrap.innerHTML = svg;
          });
        });
      } catch (e) {
        console.warn('Mermaid rendering error:', e);
      }
    }

    if (window.Prism) {
      window.Prism.highlightAllUnder(document.getElementById('markdown-body-content'));
    }

    const preBlocks = document.querySelectorAll('.markdown-body pre');
    preBlocks.forEach((pre) => {
      if (pre.closest('.code-block-wrapper')) return;
      const code = pre.querySelector('code');
      const langMatch = code?.className.match(/language-([a-z0-9_-]+)/i);
      const lang = langMatch ? langMatch[1] : 'text';

      const wrap = document.createElement('div');
      wrap.className = 'code-block-wrapper';
      wrap.innerHTML = `
        <div class="code-block-header">
          <span>${lang}</span>
          <button class="code-copy-btn">${icons['copy']} Copy</button>
        </div>
      `;
      pre.parentNode.insertBefore(wrap, pre);
      wrap.appendChild(pre);

      const copyBtn = wrap.querySelector('.code-copy-btn');
      copyBtn.addEventListener('click', () => {
        const textToCopy = code ? code.innerText : pre.innerText;
        navigator.clipboard.writeText(textToCopy).then(() => {
          copyBtn.innerHTML = `${icons['check']} Copied!`;
          setTimeout(() => {
            copyBtn.innerHTML = `${icons['copy']} Copy`;
          }, 2000);
        });
      });
    });
  }

  function handleScroll() {
    const winScroll = document.documentElement.scrollTop || document.body.scrollTop;
    const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    const scrolled = height > 0 ? (winScroll / height) * 100 : 0;
    if (el.progressBar) {
      el.progressBar.style.width = scrolled + '%';
    }

    const headings = document.querySelectorAll('.markdown-body h2, .markdown-body h3');
    let currentActiveSlug = '';
    headings.forEach((heading) => {
      const rect = heading.getBoundingClientRect();
      if (rect.top <= 120) {
        currentActiveSlug = heading.id;
      }
    });

    if (currentActiveSlug) {
      const tocLinks = document.querySelectorAll('.toc-link');
      tocLinks.forEach((link) => {
        if (link.getAttribute('data-slug') === currentActiveSlug) {
          link.classList.add('active');
        } else {
          link.classList.remove('active');
        }
      });
    }
  }

  function openSearchModal() {
    state.searchOpen = true;
    state.selectedSearchResult = 0;
    if (el.searchModal) {
      el.searchModal.classList.add('open');
      if (el.searchInput) {
        el.searchInput.value = '';
        el.searchInput.focus();
      }
      renderSearchResults('');
    }
  }

  function closeSearchModal() {
    state.searchOpen = false;
    if (el.searchModal) el.searchModal.classList.remove('open');
  }

  function handleSearchInput(e) {
    const query = e.target.value.toLowerCase().trim();
    renderSearchResults(query);
  }

  function renderSearchResults(query) {
    const data = window.FAIRWDDI_DATA || { searchIndex: [] };
    const items = data.searchIndex || [];
    let matches = [];

    if (!query) {
      matches = (data.documents || []).slice(0, 6).map((d) => ({
        docId: d.id,
        docTitle: d.title,
        category: d.category,
        sectionTitle: d.shortTitle,
        sectionSlug: '',
        preview: d.description || ''
      }));
    } else {
      const qTokens = query.split(/\s+/);
      matches = items.filter((item) => {
        const full = `${item.docTitle} ${item.sectionTitle} ${item.text}`.toLowerCase();
        return qTokens.every((t) => full.includes(t));
      }).slice(0, 12);
    }

    if (matches.length === 0) {
      el.searchResults.innerHTML = `
        <div style="padding: 2rem; text-align: center; color: var(--text-dim);">
          No results found for "${query}".
        </div>
      `;
      return;
    }

    el.searchResults.innerHTML = matches.map((m, idx) => {
      const route = `#${m.docId}${m.sectionSlug ? '#' + m.sectionSlug : ''}`;
      return `
        <a href="${route}" class="search-result-item ${idx === 0 ? 'selected' : ''}" data-idx="${idx}" onclick="window.closeSearchModalDirect()">
          <div class="result-top-row">
            <span class="result-title">${highlightText(m.sectionTitle || m.docTitle, query)}</span>
            <span class="result-badge">${m.category}</span>
          </div>
          <div class="result-preview">${highlightText(m.preview, query)}</div>
        </a>
      `;
    }).join('');
  }

  function highlightText(text, query) {
    if (!query || !text) return text;
    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return text.replace(regex, '<strong style="color: var(--brand-primary);">$1</strong>');
  }

  function handleSearchKeydown(e) {
    const items = document.querySelectorAll('.search-result-item');
    if (items.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      state.selectedSearchResult = (state.selectedSearchResult + 1) % items.length;
      updateSelectedSearchItem(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      state.selectedSearchResult = (state.selectedSearchResult - 1 + items.length) % items.length;
      updateSelectedSearchItem(items);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const activeItem = items[state.selectedSearchResult];
      if (activeItem) {
        closeSearchModal();
        window.location.hash = activeItem.getAttribute('href');
      }
    }
  }

  function updateSelectedSearchItem(items) {
    items.forEach((it, idx) => {
      it.classList.toggle('selected', idx === state.selectedSearchResult);
      if (idx === state.selectedSearchResult) {
        it.scrollIntoView({ block: 'nearest' });
      }
    });
  }

  window.closeSearchModalDirect = function () {
    closeSearchModal();
  };

  document.addEventListener('DOMContentLoaded', initApp);
})();
