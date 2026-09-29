#!/usr/bin/env python3
"""
FAIRwDDI Lifecycle — Static Site Bundle Builder
Generates index.html, site_assets/app.css, site_assets/app.js, 404.html, and site_data.js.
"""

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent

INDEX_HTML = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  
  <title>FAIRwDDI Lifecycle — Standard-Agnostic DDI Architecture for ReQuest</title>
  <meta name="description" content="FAIR DDI-Lifecycle 3.3, DDI 4.0, and DDI-CDI standard-agnostic database architecture, deliverable reports, and interactive database explorer for the Sciences Po CDSP ReQuest question bank." />
  <meta name="keywords" content="FAIR, DDI, DDI-Lifecycle, DDI-CDI, DDI 4, ReQuest, Sciences Po, CDSP, CNRS, Question Bank, CESSDA, ELSST, PostgreSQL 17, JSONB" />
  <meta name="author" content="Centre des Données Socio-Politiques (CDSP), Sciences Po / CNRS" />

  <!-- OpenGraph / Social Meta -->
  <meta property="og:type" content="website" />
  <meta property="og:title" content="FAIRwDDI Lifecycle Architecture & Deliverables Portal" />
  <meta property="og:description" content="Comprehensive DDI architecture deliverables, research reports, and interactive 28-model database explorer." />
  <meta property="og:site_name" content="FAIRwDDI Lifecycle" />

  <!-- Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  
  <!-- Prism Syntax Highlighting -->
  <link href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism-tomorrow.min.css" rel="stylesheet" />
  
  <!-- Main Stylesheet -->
  <link rel="stylesheet" href="./site_assets/app.css" />
</head>
<body>

  <!-- Top Reading Progress Bar -->
  <div class="reading-progress-bar" id="reading-progress-bar"></div>

  <!-- Top Sticky Header -->
  <header class="site-header">
    <div class="header-inner">
      <div class="header-left">
        <button class="mobile-menu-btn" id="mobile-menu-btn" aria-label="Toggle navigation menu">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        </button>

        <a href="#home" class="brand-link">
          <div class="brand-logo">F</div>
          <div class="brand-text-wrap">
            <span class="brand-title">FAIRwDDI Lifecycle</span>
            <span class="brand-sub">Sciences Po CDSP • WP3 ST3</span>
          </div>
        </a>
      </div>

      <!-- Navigation Links -->
      <nav class="header-nav">
        <a href="#home" class="nav-link active">Overview</a>
        <a href="#deliverables/phase1_report" class="nav-link">Deliverables</a>
        <a href="#explorer" class="nav-link">
          Database Explorer <span class="nav-pill">28 Models</span>
        </a>
        <a href="#diagrams" class="nav-link">Diagrams</a>
        <a href="#tools" class="nav-link">Tools</a>
        <a href="#slides" class="nav-link">Slides</a>
        <a href="#docs/request_overview" class="nav-link">Docs</a>
      </nav>

      <!-- Right Header Actions -->
      <div class="header-right">
        <button class="search-trigger-btn" id="search-trigger-btn" aria-label="Search documentation">
          <span style="display: flex; align-items: center; gap: 0.5rem;">
            <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            Search portal...
          </span>
          <span class="search-shortcut">⌘K</span>
        </button>

        <button class="theme-toggle-btn" id="theme-toggle-btn" aria-label="Toggle dark/light theme" title="Toggle theme">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
        </button>

        <a href="https://github.com/PlgaH/fairwddi-wp3-3" target="_blank" rel="noopener noreferrer" class="github-link-btn" title="View on GitHub" aria-label="GitHub Repository">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/></svg>
        </a>
      </div>
    </div>
  </header>

  <!-- App Body Layout -->
  <div class="app-container">
    
    <!-- Left Sidebar Navigation -->
    <aside class="site-sidebar" id="site-sidebar">
      <div class="sidebar-search-box">
        <svg class="sidebar-search-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input type="text" class="sidebar-search-input" id="sidebar-search-input" placeholder="Filter articles..." aria-label="Filter sidebar articles" />
      </div>

      <!-- Section: Core Deliverables -->
      <div class="nav-group">
        <div class="nav-group-header">Core Deliverables</div>
        <a href="#deliverables/phase1_report" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/></svg>
            Phase I Audit Report
          </span>
          <span class="sidebar-badge">v1.0.0</span>
        </a>
        <a href="#research/summary" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>
            Executive Summary
          </span>
          <span class="sidebar-badge">Summary</span>
        </a>
        <a href="#research/database" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
            Database Specification
          </span>
          <span class="sidebar-badge">28 Models</span>
        </a>
      </div>

      <!-- Section: Research & Technical Specs -->
      <div class="nav-group">
        <div class="nav-group-header">Research & Technical Specs</div>
        <a href="#research/normalization" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="21" x2="4" y2="14"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="20" y1="21" x2="20" y2="16"/></svg>
            Normalization Pipeline
          </span>
          <span class="sidebar-badge">Cascade</span>
        </a>
        <a href="#research/hashing_algorithms" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            Content Fingerprinting
          </span>
          <span class="sidebar-badge">SHA/BLAKE3</span>
        </a>
        <a href="#research/postgres_django_json" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
            PostgreSQL JSONB Architecture
          </span>
          <span class="sidebar-badge">JSONB</span>
        </a>
        <a href="#research/variable_cascade" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
            Variable Cascade Comparison
          </span>
          <span class="sidebar-badge">Standards</span>
        </a>
        <a href="#research/variable_question_relationships" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/></svg>
            Variable & Question Relations
          </span>
          <span class="sidebar-badge">6 Paths</span>
        </a>
        <a href="#research/cli_user_guide" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
            fairwddi CLI Manual
          </span>
          <span class="sidebar-badge">CLI</span>
        </a>
        <a href="#research/glossary" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
            Canonical DDI Glossary
          </span>
          <span class="sidebar-badge">Glossary</span>
        </a>
        <a href="#research/database_diagram" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/></svg>
            Database ER Diagram & Mermaid
          </span>
          <span class="sidebar-badge">ERD</span>
        </a>
      </div>

      <!-- Section: Interactive Visualizations -->
      <div class="nav-group">
        <div class="nav-group-header">Interactive Explorers</div>
        <a href="#explorer" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>
            Interactive Database Explorer
          </span>
          <span class="sidebar-badge" style="background: rgba(59, 130, 246, 0.2); color: var(--brand-primary);">App</span>
        </a>
        <a href="#diagrams" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/></svg>
            Architecture SVG Gallery
          </span>
          <span class="sidebar-badge">8 SVGs</span>
        </a>
        <a href="#tools" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6"/></svg>
            Interactive Playground Tools
          </span>
          <span class="sidebar-badge">Tools</span>
        </a>
        <a href="#slides" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h20"/><path d="M21 3v11a2 2 0 0 1-2 2H5"/></svg>
            Kickoff Presentation Slides
          </span>
          <span class="sidebar-badge">Slides</span>
        </a>
      </div>

      <!-- Section: Project Documentation -->
      <div class="nav-group">
        <div class="nav-group-header">Documentation & Background</div>
        <a href="#docs/request_overview" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/></svg>
            ReQuest Platform Overview
          </span>
        </a>
        <a href="#docs/request_upgrade" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/></svg>
            ReQuest Upgrade Roadmap
          </span>
        </a>
        <a href="#docs/sow" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/></svg>
            Statement of Work (SOW)
          </span>
        </a>
        <a href="#docs/activities" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/></svg>
            Activity Tracking Log
          </span>
        </a>
        <a href="#docs/meeting_notes" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h20"/></svg>
            Kickoff Presentation Notes
          </span>
        </a>
        <a href="#docs/readme" class="sidebar-link">
          <span class="sidebar-link-content">
            <svg class="sidebar-link-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 19c-5 1.5-5-2.5-7-3"/></svg>
            Repository README
          </span>
        </a>
      </div>
    </aside>

    <!-- Main Content Reader Container -->
    <main class="site-main">
      <div class="content-wrapper" id="main-content-target">
        <!-- Rendered dynamically by app.js -->
      </div>
    </main>

    <!-- Right Sticky Table of Contents (On this page) -->
    <aside class="site-toc" id="site-toc-target">
      <!-- Populated dynamically by app.js -->
    </aside>

  </div>

  <!-- Global Search Modal (Cmd + K) -->
  <div class="search-modal-backdrop" id="search-modal">
    <div class="search-modal-card">
      <div class="search-input-header">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input type="text" class="search-modal-input" id="search-modal-input" placeholder="Search reports, schemas, glossaries..." autocomplete="off" />
      </div>
      <div class="search-modal-results" id="search-modal-results">
        <!-- Results rendered dynamically -->
      </div>
      <div class="search-modal-footer">
        <div class="search-key-hints">
          <span><span class="key-badge">↑</span> <span class="key-badge">↓</span> Navigate</span>
          <span><span class="key-badge">↵</span> Select</span>
          <span><span class="key-badge">ESC</span> Close</span>
        </div>
        <span>FAIRwDDI Live Search Index</span>
      </div>
    </div>
  </div>

  <!-- Site Footer -->
  <footer class="site-footer">
    <div class="footer-inner">
      <div class="footer-top-grid">
        <div class="footer-brand-col">
          <div style="display: flex; align-items: center; gap: 0.6rem;">
            <div class="brand-logo" style="width: 28px; height: 28px; font-size: 0.9rem;">F</div>
            <span style="font-family: var(--font-heading); font-weight: 700; font-size: 1.1rem; color: var(--text-bright);">FAIRwDDI Lifecycle</span>
          </div>
          <p class="footer-text">
            Standard-agnostic DDI architecture, multi-standard ingestion, and question-bank harmonization for the Sciences Po Centre des Données Socio-Politiques (CDSP / CNRS).
          </p>
        </div>

        <div>
          <div class="footer-col-title">Core Deliverables</div>
          <ul class="footer-links-list">
            <li><a href="#deliverables/phase1_report" class="footer-link">Phase I Audit Report</a></li>
            <li><a href="#research/database" class="footer-link">Target Database Model</a></li>
            <li><a href="#research/summary" class="footer-link">Executive Summary</a></li>
            <li><a href="#research/normalization" class="footer-link">Normalization Pipeline</a></li>
          </ul>
        </div>

        <div>
          <div class="footer-col-title">Interactive Apps</div>
          <ul class="footer-links-list">
            <li><a href="#explorer" class="footer-link">Database Explorer</a></li>
            <li><a href="#diagrams" class="footer-link">Architecture Diagrams</a></li>
            <li><a href="#tools" class="footer-link">Interactive Tools</a></li>
            <li><a href="#slides" class="footer-link">Kickoff Presentation</a></li>
          </ul>
        </div>

        <div>
          <div class="footer-col-title">Standards Alignment</div>
          <ul class="footer-links-list">
            <li><span class="footer-text" style="color: var(--text-dim);">DDI-Lifecycle 3.3</span></li>
            <li><span class="footer-text" style="color: var(--text-dim);">DDI 4.0 (COGS Model)</span></li>
            <li><span class="footer-text" style="color: var(--text-dim);">DDI-CDI Cross-Domain</span></li>
            <li><span class="footer-text" style="color: var(--text-dim);">CESSDA ELSST SKOS</span></li>
          </ul>
        </div>
      </div>

      <div class="footer-bottom-row">
        <div>© 2026 Centre des Données Socio-Politiques (CDSP), Sciences Po / CNRS. FAIRwDDI WP3 ST3.</div>
        <div>Validated DDI Architecture • PostgreSQL 17 JSONB • ICU Multilingual</div>
      </div>
    </div>
  </footer>

  <!-- External Libraries: Marked (Markdown parser), Prism (Syntax highlighter), Mermaid (Diagrams) -->
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/prism.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-python.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-sql.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-json.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-yaml.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-bash.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>

  <!-- Site Data Manifest & Core Application Engine -->
  <script src="./site_assets/site_data.js"></script>
  <script src="./site_assets/app.js"></script>
</body>
</html>
"""

FOUR_OH_FOUR_HTML = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Redirecting — FAIRwDDI Lifecycle</title>
  <script>
    (function () {
      var fullPath = window.location.pathname;
      var pathSegments = fullPath.split('/').filter(Boolean);
      // Remove repository base segment if on GitHub Pages
      if (pathSegments.length > 0 && pathSegments[0] === 'fairwddi-wp3-3') {
        pathSegments.shift();
      }
      var route = pathSegments.join('/').replace(/\\.html$/, '');
      var base = window.location.pathname.startsWith('/fairwddi-wp3-3') ? '/fairwddi-wp3-3/' : './';
      if (route) {
        window.location.replace(base + '#' + route);
      } else {
        window.location.replace(base + '#home');
      }
    })();
  </script>
</head>
<body style="background: #0a0e17; color: #94a3b8; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0;">
  <div style="text-align: center;">
    <h2 style="color: #f8fafc; margin-bottom: 0.5rem;">Redirecting to FAIRwDDI Portal...</h2>
    <p>If you are not redirected automatically, <a href="./#home" style="color: #3b82f6;">click here</a>.</p>
  </div>
</body>
</html>
"""

def generate_bundle():
    print("Generating complete site files...")
    
    # Write index.html
    (WORKSPACE / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    print(f"✅ Wrote index.html ({(WORKSPACE / 'index.html').stat().st_size:,} bytes)")

    # Write 404.html
    (WORKSPACE / "404.html").write_text(FOUR_OH_FOUR_HTML, encoding="utf-8")
    print(f"✅ Wrote 404.html ({(WORKSPACE / '404.html').stat().st_size:,} bytes)")

    # Ensure .nojekyll
    (WORKSPACE / ".nojekyll").write_text("# Disable Jekyll\n", encoding="utf-8")
    print("✅ Wrote .nojekyll")

if __name__ == "__main__":
    generate_bundle()
