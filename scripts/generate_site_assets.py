#!/usr/bin/env python3
"""
Writes site_assets/app.css and site_assets/app.js directly from script.
"""

from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
ASSETS = WORKSPACE / "site_assets"
ASSETS.mkdir(parents=True, exist_ok=True)

APP_CSS = """/* ==========================================================================
   FAIRwDDI Lifecycle — GitHub Pages Static Documentation & Portal Stylesheet
   Sciences Po / CNRS — Centre des Données Socio-Politiques (CDSP)
   ========================================================================== */

:root {
  /* Color Palette — Dark Mode (Default) */
  --bg-app: #0a0e17;
  --bg-surface: #111827;
  --bg-card: #162032;
  --bg-elevated: #1e293b;
  --bg-hover: #26354a;
  --bg-active: #2e415e;
  --bg-input: #0f172a;
  --bg-code: #0b1120;
  --bg-modal-backdrop: rgba(5, 8, 15, 0.85);

  --border-color: #273549;
  --border-subtle: #1e293b;
  --border-focus: #3b82f6;

  --text-main: #f8fafc;
  --text-muted: #94a3b8;
  --text-dim: #64748b;
  --text-bright: #ffffff;

  /* Accent Colors */
  --brand-primary: #3b82f6;
  --brand-primary-rgb: 59, 130, 246;
  --brand-primary-hover: #2563eb;
  --brand-cdsp: #e11d48;
  --brand-cdsp-dark: #9f1239;
  
  --accent-cyan: #06b6d4;
  --accent-purple: #8b5cf6;
  --accent-emerald: #10b981;
  --accent-amber: #f59e0b;
  --accent-rose: #f43f5e;
  --accent-indigo: #6366f1;

  /* Layer Specific Colors */
  --layer-concept: #8b5cf6;
  --layer-rep: #10b981;
  --layer-dataset: #f59e0b;
  --layer-org: #3b82f6;
  --layer-infra: #06b6d4;
  --layer-staging: #ec4899;

  /* Shadows & Glows */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -2px rgba(0, 0, 0, 0.3);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -4px rgba(0, 0, 0, 0.4);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
  --glow-brand: 0 0 25px rgba(59, 130, 246, 0.15);
  --glow-cdsp: 0 0 25px rgba(225, 29, 72, 0.15);

  /* Typography */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-heading: 'Outfit', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'Fira Code', 'JetBrains Mono', Consolas, Monaco, monospace;

  /* Layout Measurements */
  --header-height: 64px;
  --sidebar-width: 290px;
  --toc-width: 240px;
  --content-max-width: 1000px;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-full: 9999px;
  --transition-fast: 0.15s ease;
  --transition-normal: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

[data-theme="light"] {
  --bg-app: #f8fafc;
  --bg-surface: #ffffff;
  --bg-card: #ffffff;
  --bg-elevated: #f1f5f9;
  --bg-hover: #e2e8f0;
  --bg-active: #cbd5e1;
  --bg-input: #f8fafc;
  --bg-code: #f1f5f9;
  --bg-modal-backdrop: rgba(15, 23, 42, 0.6);

  --border-color: #cbd5e1;
  --border-subtle: #f1f5f9;
  --border-focus: #2563eb;

  --text-main: #0f172a;
  --text-muted: #475569;
  --text-dim: #94a3b8;
  --text-bright: #020617;

  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  --glow-brand: 0 0 25px rgba(59, 130, 246, 0.08);
  --glow-cdsp: 0 0 25px rgba(225, 29, 72, 0.08);
}

/* Base Styles & Reset */
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  font-family: var(--font-sans);
  font-size: 15px;
  line-height: 1.6;
  color: var(--text-main);
  background-color: var(--bg-app);
  scroll-behavior: smooth;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  background-color: var(--bg-app);
}

a {
  color: var(--brand-primary);
  text-decoration: none;
  transition: color var(--transition-fast);
}

a:hover {
  color: var(--brand-primary-hover);
}

button {
  font-family: inherit;
  cursor: pointer;
  border: none;
  background: transparent;
}

input, select, textarea {
  font-family: inherit;
  font-size: inherit;
  color: inherit;
}

/* Scrollbar Styling */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--bg-app);
}

::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: var(--radius-full);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--text-dim);
}

/* Header & Navigation */
.site-header {
  position: sticky;
  top: 0;
  z-index: 100;
  height: var(--header-height);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  transition: background-color var(--transition-normal), border-color var(--transition-normal);
}

.header-inner {
  max-width: 1720px;
  height: 100%;
  margin: 0 auto;
  padding: 0 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.25rem;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.mobile-menu-btn {
  display: none;
  width: 38px;
  height: 38px;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
  background: var(--bg-card);
}

.brand-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  text-decoration: none;
  color: var(--text-bright);
}

.brand-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--brand-cdsp), var(--brand-primary));
  color: #ffffff;
  font-weight: 800;
  font-size: 1.1rem;
  box-shadow: var(--shadow-sm);
}

.brand-text-wrap {
  display: flex;
  flex-direction: column;
}

.brand-title {
  font-family: var(--font-heading);
  font-size: 1.15rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #ffffff 30%, #93c5fd 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

[data-theme="light"] .brand-title {
  background: linear-gradient(135deg, #0f172a 30%, #2563eb 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.brand-sub {
  font-size: 0.72rem;
  font-weight: 500;
  color: var(--text-muted);
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.nav-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.45rem 0.85rem;
  border-radius: var(--radius-md);
  font-weight: 500;
  font-size: 0.9rem;
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.nav-link:hover {
  color: var(--text-bright);
  background: var(--bg-hover);
}

.nav-link.active {
  color: #ffffff;
  background: var(--brand-primary);
}

.nav-pill {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.1rem 0.4rem;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.15);
  text-transform: uppercase;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.search-trigger-btn {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.45rem 0.9rem;
  border-radius: var(--radius-md);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  font-size: 0.85rem;
  transition: all var(--transition-fast);
  min-width: 210px;
  justify-content: space-between;
}

.search-trigger-btn:hover {
  border-color: var(--brand-primary);
  color: var(--text-bright);
  background: var(--bg-elevated);
}

.search-shortcut {
  font-size: 0.7rem;
  font-family: var(--font-mono);
  background: var(--bg-app);
  border: 1px solid var(--border-color);
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  color: var(--text-dim);
}

.theme-toggle-btn, .github-link-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.theme-toggle-btn:hover, .github-link-btn:hover {
  color: var(--text-bright);
  border-color: var(--text-dim);
  background: var(--bg-elevated);
}

/* App Layout */
.app-container {
  display: flex;
  flex: 1;
  max-width: 1720px;
  width: 100%;
  margin: 0 auto;
}

.site-sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  background: var(--bg-surface);
  border-right: 1px solid var(--border-color);
  height: calc(100vh - var(--header-height));
  position: sticky;
  top: var(--header-height);
  overflow-y: auto;
  padding: 1.25rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.sidebar-search-box {
  position: relative;
}

.sidebar-search-input {
  width: 100%;
  padding: 0.5rem 0.75rem 0.5rem 2.2rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--bg-input);
  font-size: 0.85rem;
  color: var(--text-main);
  outline: none;
  transition: border-color var(--transition-fast);
}

.sidebar-search-input:focus {
  border-color: var(--brand-primary);
}

.sidebar-search-icon {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-dim);
  pointer-events: none;
}

.nav-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.nav-group-header {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-dim);
  padding: 0.35rem 0.75rem;
  margin-bottom: 0.15rem;
}

.sidebar-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.45rem 0.75rem;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 0.88rem;
  font-weight: 500;
  transition: all var(--transition-fast);
  line-height: 1.35;
}

.sidebar-link-content {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-link-icon {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  opacity: 0.7;
}

.sidebar-link:hover {
  color: var(--text-bright);
  background: var(--bg-hover);
}

.sidebar-link.active {
  color: var(--brand-primary);
  background: rgba(59, 130, 246, 0.12);
  font-weight: 600;
}

.sidebar-badge {
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-dim);
  flex-shrink: 0;
}

.sidebar-link.active .sidebar-badge {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.3);
  color: var(--brand-primary);
}

.site-main {
  flex: 1;
  min-width: 0;
  display: flex;
  justify-content: center;
  padding: 2rem 2.5rem 4rem;
  background-color: var(--bg-app);
}

.content-wrapper {
  width: 100%;
  max-width: var(--content-max-width);
}

.site-toc {
  width: var(--toc-width);
  flex-shrink: 0;
  height: calc(100vh - var(--header-height));
  position: sticky;
  top: var(--header-height);
  overflow-y: auto;
  padding: 2rem 1rem 2rem 1.5rem;
  border-left: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.toc-title {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-dim);
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.toc-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.toc-item {
  font-size: 0.82rem;
  line-height: 1.35;
}

.toc-link {
  color: var(--text-muted);
  display: block;
  padding: 0.2rem 0;
  transition: color var(--transition-fast);
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
}

.toc-item.level-3 .toc-link {
  padding-left: 0.85rem;
  font-size: 0.78rem;
  color: var(--text-dim);
}

.toc-link:hover {
  color: var(--text-bright);
}

.toc-link.active {
  color: var(--brand-primary);
  font-weight: 600;
}

.reading-progress-bar {
  position: fixed;
  top: var(--header-height);
  left: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--brand-cdsp), var(--brand-primary), var(--accent-cyan));
  width: 0%;
  z-index: 101;
  transition: width 0.1s ease;
}

/* Hero Section */
.hero-section {
  position: relative;
  padding: 3rem 2rem;
  border-radius: var(--radius-lg);
  background: radial-gradient(circle at top right, rgba(59, 130, 246, 0.12), transparent 50%),
              radial-gradient(circle at bottom left, rgba(225, 29, 72, 0.08), transparent 50%),
              var(--bg-card);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-lg), var(--glow-brand);
  margin-bottom: 2.5rem;
  overflow: hidden;
}

.hero-badge-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1.25rem;
}

.badge-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.65rem;
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.badge-tag.cdsp {
  background: rgba(225, 29, 72, 0.15);
  color: #f43f5e;
  border: 1px solid rgba(225, 29, 72, 0.3);
}

.badge-tag.primary {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.badge-tag.emerald {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.hero-title {
  font-family: var(--font-heading);
  font-size: 2.6rem;
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: -0.025em;
  color: var(--text-bright);
  margin-bottom: 0.85rem;
}

.hero-title span.accent {
  background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-subtitle {
  font-size: 1.15rem;
  color: var(--text-muted);
  max-width: 820px;
  line-height: 1.6;
  margin-bottom: 2rem;
}

.hero-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  transition: transform var(--transition-fast), border-color var(--transition-fast);
}

.stat-card:hover {
  transform: translateY(-2px);
  border-color: var(--brand-primary);
}

.stat-value {
  font-family: var(--font-heading);
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--text-bright);
}

.stat-label {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-muted);
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.7rem 1.4rem;
  border-radius: var(--radius-md);
  background: var(--brand-primary);
  color: #ffffff;
  font-weight: 600;
  font-size: 0.95rem;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
  transition: all var(--transition-fast);
}

.btn-primary:hover {
  background: var(--brand-primary-hover);
  color: #ffffff;
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.7rem 1.4rem;
  border-radius: var(--radius-md);
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  color: var(--text-bright);
  font-weight: 600;
  font-size: 0.95rem;
  transition: all var(--transition-fast);
}

.btn-secondary:hover {
  background: var(--bg-hover);
  border-color: var(--text-dim);
  color: var(--text-bright);
}

.section-heading-wrap {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.section-title {
  font-family: var(--font-heading);
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text-bright);
}

.section-sub {
  font-size: 0.9rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
}

.card-grid-3 {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.25rem;
  margin-bottom: 3rem;
}

.feature-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: all var(--transition-normal);
  text-decoration: none;
  color: inherit;
  position: relative;
  overflow: hidden;
}

.feature-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: transparent;
  transition: background var(--transition-fast);
}

.feature-card:hover {
  border-color: var(--brand-primary);
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
}

.feature-card:hover::before {
  background: linear-gradient(90deg, var(--brand-cdsp), var(--brand-primary));
}

.card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.card-icon-wrap {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--brand-primary);
}

.card-badge {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: var(--radius-full);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-dim);
}

.card-title {
  font-family: var(--font-heading);
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--text-bright);
  margin-bottom: 0.5rem;
}

.card-desc {
  font-size: 0.88rem;
  color: var(--text-muted);
  line-height: 1.5;
  margin-bottom: 1.25rem;
}

.card-footer-action {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--brand-primary);
  margin-top: auto;
}

/* Article Styles */
.article-header {
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--border-color);
}

.breadcrumbs {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--text-dim);
  margin-bottom: 0.85rem;
}

.breadcrumbs a {
  color: var(--text-muted);
}

.breadcrumbs a:hover {
  color: var(--brand-primary);
}

.article-title {
  font-family: var(--font-heading);
  font-size: 2.25rem;
  font-weight: 800;
  color: var(--text-bright);
  line-height: 1.2;
  margin-bottom: 0.85rem;
}

.article-meta {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  flex-wrap: wrap;
  font-size: 0.82rem;
  color: var(--text-muted);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.markdown-body {
  font-size: 1rem;
  line-height: 1.75;
  color: var(--text-main);
}

.markdown-body h1,
.markdown-body h2,
.markdown-body h3,
.markdown-body h4,
.markdown-body h5,
.markdown-body h6 {
  font-family: var(--font-heading);
  color: var(--text-bright);
  font-weight: 700;
  line-height: 1.3;
  margin-top: 2.2rem;
  margin-bottom: 0.85rem;
  scroll-margin-top: calc(var(--header-height) + 1.5rem);
}

.markdown-body h1 { font-size: 1.85rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; }
.markdown-body h2 { font-size: 1.5rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.4rem; }
.markdown-body h3 { font-size: 1.25rem; }
.markdown-body h4 { font-size: 1.05rem; }

.markdown-body p { margin-bottom: 1.25rem; }
.markdown-body ul, .markdown-body ol { margin-bottom: 1.25rem; padding-left: 1.75rem; }
.markdown-body li { margin-bottom: 0.4rem; }
.markdown-body li > p { margin-bottom: 0.4rem; }
.markdown-body hr { border: 0; height: 1px; background: var(--border-color); margin: 2.5rem 0; }

.markdown-body blockquote {
  border-left: 4px solid var(--brand-primary);
  padding: 0.75rem 1.25rem;
  margin: 1.5rem 0;
  background: var(--bg-surface);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  color: var(--text-muted);
  font-style: italic;
}

.markdown-body table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 1.5rem 0;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  overflow: hidden;
  font-size: 0.9rem;
}

.markdown-body th {
  background: var(--bg-elevated);
  font-weight: 700;
  text-align: left;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-bright);
}

.markdown-body td {
  padding: 0.65rem 1rem;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-surface);
}

.markdown-body tr:last-child td { border-bottom: none; }
.markdown-body tr:hover td { background: var(--bg-hover); }

.markdown-body code {
  font-family: var(--font-mono);
  font-size: 0.88em;
  padding: 0.15em 0.4em;
  border-radius: 4px;
  background: var(--bg-code);
  border: 1px solid var(--border-color);
  color: #38bdf8;
}

[data-theme="light"] .markdown-body code { color: #0369a1; }

.code-block-wrapper {
  position: relative;
  margin: 1.5rem 0;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--bg-code);
  overflow: hidden;
}

.code-block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.4rem 1rem;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
  font-size: 0.78rem;
  color: var(--text-dim);
  font-family: var(--font-mono);
}

.code-copy-btn {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.2rem 0.55rem;
  border-radius: 4px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  font-size: 0.75rem;
  transition: all var(--transition-fast);
}

.code-copy-btn:hover {
  color: var(--text-bright);
  border-color: var(--text-dim);
}

.code-block-wrapper pre {
  margin: 0;
  padding: 1.25rem;
  overflow-x: auto;
  font-family: var(--font-mono);
  font-size: 0.88rem;
  line-height: 1.55;
}

.code-block-wrapper pre code {
  background: transparent;
  border: none;
  padding: 0;
  color: var(--text-main);
}

/* Callouts */
.callout {
  display: flex;
  gap: 1rem;
  padding: 1rem 1.25rem;
  margin: 1.5rem 0;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--bg-surface);
}

.callout-icon { flex-shrink: 0; width: 20px; height: 20px; margin-top: 0.2rem; }
.callout-content { flex: 1; font-size: 0.92rem; line-height: 1.6; }
.callout-title { font-weight: 700; margin-bottom: 0.25rem; font-size: 0.95rem; }

.callout.note { border-left: 4px solid var(--brand-primary); background: rgba(59, 130, 246, 0.06); }
.callout.note .callout-icon, .callout.note .callout-title { color: var(--brand-primary); }

.callout.tip { border-left: 4px solid var(--accent-emerald); background: rgba(16, 185, 129, 0.06); }
.callout.tip .callout-icon, .callout.tip .callout-title { color: var(--accent-emerald); }

.callout.important { border-left: 4px solid var(--accent-purple); background: rgba(139, 92, 246, 0.06); }
.callout.important .callout-icon, .callout.important .callout-title { color: var(--accent-purple); }

.callout.warning { border-left: 4px solid var(--accent-amber); background: rgba(245, 158, 11, 0.06); }
.callout.warning .callout-icon, .callout.warning .callout-title { color: var(--accent-amber); }

.callout.caution { border-left: 4px solid var(--accent-rose); background: rgba(244, 63, 94, 0.06); }
.callout.caution .callout-icon, .callout.caution .callout-title { color: var(--accent-rose); }

.mermaid-diagram-wrap {
  margin: 2rem 0;
  padding: 1.5rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow-x: auto;
  display: flex;
  justify-content: center;
  box-shadow: var(--shadow-sm);
}

.article-pagination {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
  margin-top: 3.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--border-color);
}

.pagination-btn {
  display: flex;
  flex-direction: column;
  padding: 1rem 1.25rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--bg-surface);
  text-decoration: none;
  transition: all var(--transition-fast);
}

.pagination-btn:hover {
  border-color: var(--brand-primary);
  background: var(--bg-hover);
  transform: translateY(-2px);
}

.pagination-btn.next { text-align: right; align-items: flex-end; }
.pagination-label { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: var(--text-dim); margin-bottom: 0.25rem; }
.pagination-title { font-weight: 600; font-size: 0.95rem; color: var(--brand-primary); }

/* Explorer Hub */
.explorer-hub-container { display: flex; flex-direction: column; gap: 1.25rem; width: 100%; }

.explorer-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1.25rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  flex-wrap: wrap;
  gap: 1rem;
}

.layer-filter-pills { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }

.layer-pill {
  padding: 0.35rem 0.75rem;
  border-radius: var(--radius-full);
  font-size: 0.78rem;
  font-weight: 600;
  border: 1px solid var(--border-color);
  background: var(--bg-elevated);
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.layer-pill:hover, .layer-pill.active { background: var(--brand-primary); color: #ffffff; border-color: var(--brand-primary); }

.explorer-actions { display: flex; align-items: center; gap: 0.6rem; }

.explorer-frame-container {
  width: 100%;
  height: 820px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--bg-surface);
  box-shadow: var(--shadow-lg);
}

.explorer-frame-container iframe { width: 100%; height: 100%; border: none; }
.explorer-frame-container.fullscreen { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 9999; border-radius: 0; }

/* Diagrams */
.diagram-viewer-wrap { display: flex; flex-direction: column; gap: 1.5rem; }

.diagram-viewer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 1rem 1.5rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.diagram-tabs-row { display: flex; align-items: center; gap: 0.5rem; overflow-x: auto; padding-bottom: 0.5rem; }

.diagram-tab-btn {
  padding: 0.45rem 0.9rem;
  border-radius: var(--radius-md);
  font-size: 0.82rem;
  font-weight: 600;
  border: 1px solid var(--border-color);
  background: var(--bg-surface);
  color: var(--text-muted);
  white-space: nowrap;
  transition: all var(--transition-fast);
}

.diagram-tab-btn:hover { color: var(--text-bright); background: var(--bg-hover); }
.diagram-tab-btn.active { background: var(--brand-primary); color: #ffffff; border-color: var(--brand-primary); }

.diagram-canvas-box {
  background: #ffffff;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 2rem;
  min-height: 520px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
  box-shadow: var(--shadow-md);
  position: relative;
}

.diagram-canvas-box.dark-canvas { background: #0b1120; }
.diagram-canvas-box svg { max-width: 100%; height: auto; transition: transform 0.2s ease; }

.diagram-controls-bar {
  position: absolute;
  bottom: 1rem;
  right: 1rem;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(8px);
  padding: 0.35rem 0.6rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  color: #ffffff;
}

.diagram-ctrl-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  color: #ffffff;
  font-size: 0.9rem;
  transition: background var(--transition-fast);
}

.diagram-ctrl-btn:hover { background: rgba(255, 255, 255, 0.2); }

/* Tools */
.tools-container { display: flex; flex-direction: column; gap: 2rem; }
.tool-card { background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 1.75rem; box-shadow: var(--shadow-md); }
.tool-header { margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border-color); }
.tool-title { font-family: var(--font-heading); font-size: 1.4rem; font-weight: 700; color: var(--text-bright); }
.tool-subtitle { font-size: 0.88rem; color: var(--text-muted); margin-top: 0.2rem; }
.tool-form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.25rem; margin-bottom: 1.5rem; }
.form-group { display: flex; flex-direction: column; gap: 0.4rem; }
.form-label { font-size: 0.8rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; }
.form-input, .form-select, .form-textarea { padding: 0.6rem 0.85rem; border-radius: var(--radius-md); border: 1px solid var(--border-color); background: var(--bg-input); color: var(--text-main); font-size: 0.9rem; outline: none; transition: border-color var(--transition-fast); }
.form-input:focus, .form-select:focus, .form-textarea:focus { border-color: var(--brand-primary); }
.tool-output-box { background: var(--bg-code); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 1.25rem; position: relative; }
.tool-output-label { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-dim); margin-bottom: 0.5rem; }
.tool-output-val { font-family: var(--font-mono); font-size: 0.95rem; color: #38bdf8; word-break: break-all; }

/* Search Modal */
.search-modal-backdrop {
  position: fixed;
  inset: 0;
  background: var(--bg-modal-backdrop);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  z-index: 1000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 10vh;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s ease;
}

.search-modal-backdrop.open { opacity: 1; pointer-events: auto; }

.search-modal-card {
  width: 90%;
  max-width: 680px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  max-height: 75vh;
  transform: translateY(-20px);
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.search-modal-backdrop.open .search-modal-card { transform: translateY(0); }

.search-input-header {
  display: flex;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-color);
  gap: 0.75rem;
}

.search-modal-input { flex: 1; border: none; background: transparent; font-size: 1.1rem; color: var(--text-bright); outline: none; }

.search-modal-results {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.search-result-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  color: inherit;
  text-decoration: none;
  border: 1px solid transparent;
  transition: all var(--transition-fast);
  cursor: pointer;
}

.search-result-item:hover, .search-result-item.selected { background: var(--bg-hover); border-color: var(--brand-primary); }
.result-top-row { display: flex; align-items: center; justify-content: space-between; }
.result-title { font-weight: 700; font-size: 0.95rem; color: var(--text-bright); }
.result-badge { font-size: 0.68rem; font-weight: 700; padding: 0.1rem 0.4rem; border-radius: 4px; background: var(--bg-card); color: var(--text-dim); }
.result-preview { font-size: 0.82rem; color: var(--text-muted); line-height: 1.4; }

.search-modal-footer {
  padding: 0.6rem 1.25rem;
  background: var(--bg-card);
  border-top: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--text-dim);
}

.search-key-hints { display: flex; align-items: center; gap: 0.75rem; }
.key-badge { font-family: var(--font-mono); padding: 0.1rem 0.35rem; border-radius: 4px; background: var(--bg-surface); border: 1px solid var(--border-color); }

/* Footer */
.site-footer { background: var(--bg-surface); border-top: 1px solid var(--border-color); padding: 3rem 1.5rem 2rem; margin-top: auto; }
.footer-inner { max-width: 1720px; margin: 0 auto; display: flex; flex-direction: column; gap: 2rem; }
.footer-top-grid { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 2rem; }
.footer-brand-col { display: flex; flex-direction: column; gap: 0.85rem; max-width: 380px; }
.footer-text { font-size: 0.85rem; color: var(--text-muted); line-height: 1.5; }
.footer-col-title { font-size: 0.78rem; font-weight: 700; text-transform: uppercase; color: var(--text-dim); margin-bottom: 0.75rem; }
.footer-links-list { list-style: none; display: flex; flex-direction: column; gap: 0.5rem; }
.footer-link { font-size: 0.85rem; color: var(--text-muted); }
.footer-link:hover { color: var(--brand-primary); }
.footer-bottom-row { display: flex; align-items: center; justify-content: space-between; padding-top: 1.5rem; border-top: 1px solid var(--border-subtle); font-size: 0.8rem; color: var(--text-dim); }

/* Responsive */
@media (max-width: 1200px) { .site-toc { display: none; } }
@media (max-width: 900px) {
  .site-sidebar { position: fixed; left: -100%; top: var(--header-height); z-index: 90; transition: left var(--transition-normal); box-shadow: var(--shadow-xl); }
  .site-sidebar.open { left: 0; }
  .mobile-menu-btn { display: flex; }
  .header-nav { display: none; }
  .search-trigger-btn { min-width: auto; }
  .search-shortcut { display: none; }
  .site-main { padding: 1.5rem 1rem 3rem; }
  .hero-title { font-size: 2rem; }
  .footer-top-grid { grid-template-columns: 1fr; }
}
"""

APP_JS = """/**
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
    mobileSidebarOpen: false
  };

  // DOM Elements cache
  let el = {};

  // Icons Helper (SVG strings)
  const icons = {
    'file-text': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>`,
    'compass': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>`,
    'database': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>`,
    'git-merge': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M6 21V9a9 9 0 0 0 9 9"/></svg>`,
    'sliders': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>`,
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
    'arrow-left': `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>`
  };

  /**
   * Initialize Application
   */
  async function initApp() {
    // Cache DOM
    el = {
      app: document.getElementById('app'),
      themeToggle: document.getElementById('theme-toggle-btn'),
      mobileMenuBtn: document.getElementById('mobile-menu-btn'),
      sidebar: document.getElementById('site-sidebar'),
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

    // Apply theme
    applyTheme(state.theme);

    // Setup Event Listeners
    setupEventListeners();

    // Initial Route Handling
    handleRoute();
  }

  /**
   * Setup Event Listeners
   */
  function setupEventListeners() {
    window.addEventListener('hashchange', handleRoute);
    window.addEventListener('scroll', handleScroll, { passive: true });

    // Theme Toggle
    if (el.themeToggle) {
      el.themeToggle.addEventListener('click', toggleTheme);
    }

    // Mobile Sidebar
    if (el.mobileMenuBtn) {
      el.mobileMenuBtn.addEventListener('click', () => {
        state.mobileSidebarOpen = !state.mobileSidebarOpen;
        el.sidebar.classList.toggle('open', state.mobileSidebarOpen);
      });
    }

    // Close mobile sidebar on click outside
    document.addEventListener('click', (e) => {
      if (state.mobileSidebarOpen && !el.sidebar.contains(e.target) && !el.mobileMenuBtn.contains(e.target)) {
        state.mobileSidebarOpen = false;
        el.sidebar.classList.remove('open');
      }
    });

    // Search Modal Triggers & Hotkey (Cmd/Ctrl + K)
    if (el.searchTrigger) {
      el.searchTrigger.addEventListener('click', openSearchModal);
    }

    window.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        openSearchModal();
      } else if (e.key === 'Escape' && state.searchOpen) {
        closeSearchModal();
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

    // Sidebar search filter
    if (el.sidebarSearchInput) {
      el.sidebarSearchInput.addEventListener('input', (e) => {
        filterSidebarLinks(e.target.value.toLowerCase().trim());
      });
    }
  }

  /**
   * Theme Management
   */
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

  /**
   * Route Handler & Dispatcher
   */
  function handleRoute() {
    const rawHash = window.location.hash.slice(1).replace(/^\\//, '');
    const route = rawHash.split('#')[0] || 'home';
    state.currentRoute = route;

    // Close mobile menu on navigate
    if (state.mobileSidebarOpen) {
      state.mobileSidebarOpen = false;
      if (el.sidebar) el.sidebar.classList.remove('open');
    }

    // Update Header Active Link
    updateHeaderNav(route);

    // Update Sidebar Active Link
    updateSidebarNav(route);

    // Render View
    if (route === 'home' || route === '') {
      renderHomeView();
    } else if (route === 'explorer') {
      renderExplorerView();
    } else if (route.startsWith('diagrams')) {
      const parts = route.split('/');
      const diagramId = parts[1] || 'cascade_diagram';
      renderDiagramsView(diagramId);
    } else if (route === 'tools') {
      renderToolsView();
    } else if (route === 'slides') {
      renderSlidesView();
    } else {
      // Document View
      renderDocumentView(route);
    }

    // Scroll to top or specific heading anchor
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

  function updateHeaderNav(route) {
    if (!el.navLinks) return;
    el.navLinks.forEach((link) => {
      const href = link.getAttribute('href').replace(/^#\\/?/, '');
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
      const href = link.getAttribute('href').replace(/^#\\/?/, '');
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

  /**
   * View: Home / Dashboard
   */
  function renderHomeView() {
    const data = window.FAIRWDDI_DATA || { metadata: {}, documents: [] };
    const meta = data.metadata || {};
    const stats = meta.stats || { modelsCount: 28, deliverablesCount: 10, diagramsCount: 8 };

    // Hide TOC for Home
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

      <!-- Feature Spotlight Grid -->
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

      <!-- Interactive Explorer Banner -->
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

  /**
   * View: Embedded Database Explorer
   */
  function renderExplorerView() {
    if (el.tocContainer) el.tocContainer.style.display = 'none';

    el.mainContent.innerHTML = `
      <div class="article-header">
        <div class="breadcrumbs">
          <a href="#home">Home</a> <span>/</span> <span>Interactive Explorer</span>
        </div>
        <h1 class="article-title">FAIRwDDI Interactive Database Model Explorer</h1>
        <div class="article-meta">
          <span class="meta-item"><span class="badge-tag primary">28 Tables</span></span>
          <span class="meta-item"><span class="badge-tag emerald">PostgreSQL 17 / SQLite</span></span>
          <span class="meta-item"><span class="badge-tag cdsp">DDI 4 / CDI / DDI-L 3.3</span></span>
        </div>
      </div>

      <div class="explorer-hub-container">
        <div class="explorer-toolbar">
          <div class="layer-filter-pills">
            <span style="font-size: 0.78rem; font-weight: 700; color: var(--text-dim); text-transform: uppercase;">Quick Filter:</span>
            <button class="layer-pill" onclick="filterExplorerLayer('all')">All Layers</button>
            <button class="layer-pill" onclick="filterExplorerLayer('concept')">Concept</button>
            <button class="layer-pill" onclick="filterExplorerLayer('representation')">Representation</button>
            <button class="layer-pill" onclick="filterExplorerLayer('dataset')">Dataset</button>
            <button class="layer-pill" onclick="filterExplorerLayer('organization')">Organization</button>
            <button class="layer-pill" onclick="filterExplorerLayer('infrastructure')">Infrastructure</button>
            <button class="layer-pill" onclick="filterExplorerLayer('staging')">Staging</button>
          </div>

          <div class="explorer-actions">
            <button class="btn-secondary" style="padding: 0.45rem 0.85rem; font-size: 0.85rem;" onclick="toggleExplorerFullscreen()">
              ${icons['external']} Fullscreen
            </button>
            <a href="./deliverables/research/database_explorer.html" target="_blank" class="btn-secondary" style="padding: 0.45rem 0.85rem; font-size: 0.85rem;">
              ${icons['external']} Open Standalone
            </a>
          </div>
        </div>

        <div class="explorer-frame-container" id="explorer-frame-wrap">
          <iframe src="./deliverables/research/database_explorer.html" id="explorer-iframe" title="Database Explorer"></iframe>
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
          console.log('Layer filter dispatched');
        }
      }
    };

    window.toggleExplorerFullscreen = function () {
      const wrap = document.getElementById('explorer-frame-wrap');
      if (wrap) {
        wrap.classList.toggle('fullscreen');
      }
    };
  }

  /**
   * View: Diagrams Gallery
   */
  function renderDiagramsView(activeDiagramId) {
    if (el.tocContainer) el.tocContainer.style.display = 'none';
    const data = window.FAIRWDDI_DATA || {};
    const diagrams = data.diagrams || [];
    const activeDiag = diagrams.find((d) => d.id === activeDiagramId) || diagrams[0] || {};
    state.currentDiagramId = activeDiag.id;

    el.mainContent.innerHTML = `
      <div class="article-header">
        <div class="breadcrumbs">
          <a href="#home">Home</a> <span>/</span> <a href="#diagrams">Architecture Diagrams</a> <span>/</span> <span>${activeDiag.title || 'Diagrams'}</span>
        </div>
        <h1 class="article-title">FAIRwDDI Architecture Diagrams & Visualizations</h1>
        <p style="color: var(--text-muted); font-size: 1.05rem;">
          High-resolution vector architecture diagrams covering data modeling, ingestion pipelines, variable cascades, and hashing workflows.
        </p>
      </div>

      <div class="diagram-viewer-wrap">
        <!-- Diagram Selector Tabs -->
        <div class="diagram-tabs-row">
          ${diagrams.map((d) => `
            <a href="#diagrams/${d.id}" class="diagram-tab-btn ${d.id === activeDiag.id ? 'active' : ''}">
              ${d.title}
            </a>
          `).join('')}
        </div>

        <!-- Diagram Header Info -->
        <div class="diagram-viewer-header">
          <div>
            <span class="badge-tag primary" style="margin-bottom: 0.35rem;">${activeDiag.category || 'Architecture'}</span>
            <h2 style="font-family: var(--font-heading); font-size: 1.4rem; color: var(--text-bright);">${activeDiag.title}</h2>
            <p style="color: var(--text-muted); font-size: 0.88rem; margin-top: 0.25rem;">${activeDiag.description || ''}</p>
          </div>
          <div style="display: flex; gap: 0.5rem; align-items: center;">
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
  }

  /**
   * View: Interactive Tools
   */
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
        <!-- Tool 1: URN Generator & Validator -->
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

        <!-- Tool 2: Multilingual JSONB Builder -->
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

        <!-- Tool 3: Set-Theoretic Deduplication Simulator -->
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
      const linesA = txtA.split('\\n').map((s) => s.trim()).filter(Boolean).sort();
      const linesB = txtB.split('\\n').map((s) => s.trim()).filter(Boolean).sort();

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

  /**
   * View: Slides Presentation
   */
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

  /**
   * View: Markdown Document
   */
  function renderDocumentView(routeId) {
    const data = window.FAIRWDDI_DATA || { documents: [] };
    const docs = data.documents || [];
    const doc = docs.find((d) => d.id === routeId);

    if (!doc) {
      render404View(routeId);
      return;
    }

    // Render TOC on Right Sidebar
    renderTableOfContents(doc.headings || []);

    // Transform and Render Markdown
    const renderedHtml = parseMarkdown(doc.content);

    // Find Previous and Next Articles for pagination
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

    // Callout box transformer
    html = html.replace(/<blockquote>\\s*<p>\\s*\\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\\]\\s*(.*?)(<\\/p>[\\s\\S]*?<\\/blockquote>)/gi, (match, type, titleLine, rest) => {
      const typeLower = type.toLowerCase();
      return `<div class="callout ${typeLower}">
        <div class="callout-icon">${icons['info']}</div>
        <div class="callout-content">
          <div class="callout-title">${type}</div>
          <p>${titleLine}</p>
          ${rest.replace(/<\\/p>[\\s\\S]*?<\\/blockquote>/, '')}
        </div>
      </div>`;
    });

    // Intercept internal file links
    html = html.replace(/href="file:\\/\\/\\/[^"]*?deliverables\\/phase1_report\\.md"/g, 'href="#deliverables/phase1_report"');
    html = html.replace(/href="file:\\/\\/\\/[^"]*?deliverables\\/research\\/([a-z0-9_-]+)\\.md"/g, 'href="#research/$1"');
    html = html.replace(/href="file:\\/\\/\\/[^"]*?docs\\/([a-z0-9_-]+)\\.md"/g, 'href="#docs/$1"');
    html = html.replace(/href="deliverables\\/research\\/database_explorer\\.html"/g, 'href="#explorer"');
    html = html.replace(/href="docs\\/assets\\/diagrams\\/([a-z0-9_-]+)\\.svg"/g, 'href="#diagrams/$1"');

    // Add slug IDs to headings if missing
    html = html.replace(/<(h[1-4])>(.*?)<\\/\\1>/gi, (match, tag, content) => {
      const cleanText = content.replace(/<[^>]*>/g, '').trim();
      const slug = cleanText.toLowerCase().replace(/[^\\w\\- ]/g, '').trim().replace(/\\s+/g, '-');
      return `<${tag} id="${slug}">${content}</${tag}>`;
    });

    return html;
  }

  function fallbackMarkdownParser(src) {
    let out = src;
    out = out.replace(/```([a-z0-9_-]*)\\n([\\s\\S]*?)```/g, (m, lang, code) => {
      const escaped = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      return `<div class="code-block-wrapper"><div class="code-block-header"><span>${lang || 'text'}</span><button class="code-copy-btn">${icons['copy']} Copy</button></div><pre><code class="language-${lang}">${escaped}</code></pre></div>`;
    });
    out = out.replace(/`([^`]+)`/g, '<code>$1</code>');
    out = out.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    out = out.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    out = out.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    out = out.replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');
    out = out.replace(/\\*([^*]+)\\*/g, '<em>$1</em>');
    out = out.replace(/\\n\\n+/g, '</p><p>');
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
      const qTokens = query.split(/\\s+/);
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
    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&')})`, 'gi');
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

  // Start app on DOMContentLoaded
  document.addEventListener('DOMContentLoaded', initApp);
})();
"""

def generate_assets():
    (ASSETS / "app.css").write_text(APP_CSS, encoding="utf-8")
    print(f"✅ Wrote site_assets/app.css ({(ASSETS / 'app.css').stat().st_size:,} bytes)")

    (ASSETS / "app.js").write_text(APP_JS, encoding="utf-8")
    print(f"✅ Wrote site_assets/app.js ({(ASSETS / 'app.js').stat().st_size:,} bytes)")

if __name__ == "__main__":
    generate_assets()
