# Statement of Work (SOW): FAIRwDDI WP3 ST3

**Project Title:** Implementation of DDI-Lifecycle for ReQuest  
**Objective:** Transform the CDSP ReQuest database from a pseudo-DDI-L model to a compliant DDI-Lifecycle (DDI-L) architecture to ensure interoperability, support multilingualism, and enable variable cascading.  
**Project Duration:** July 20, 2026 – December 18, 2026  
**Total Effort:** 25 days

---

## Implementation Task List

### Phase I: Audit and Modeling (July 20 – Sept 30, 2026)

_Goal: Analyze existing database, define DDI-L profile, and design target architecture._

- **Lancement et Immersion:** Conduct kickoff meeting, establish development environments, and review existing database schema and sample DDI-L files.
- **Audit of Current Model & DDI-L Profile Definition:** Identify gaps between the current PostgreSQL schema and DDI-L standards; formalize a minimal DDI-L profile for ReQuest.
- **New Schema Design:** Architect a new PostgreSQL schema treating "question" as a reusable object; implement "variable cascade" and multilingual support (JSON/JSONB).
- **Audit Reporting & Validation:** Draft final audit report and recommendations; present to CDSP/partners for validation.

### Phase II: Development of Python Library (Aug 17 – Oct 31, 2026)

_Goal: Create the interface for the new database model and manage DDI-L metadata exchange._

- **Project Initialization:** Configure project infrastructure (GitHub, development agents); define base data structures (Pydantic/Django); integrate DDI-L resources via Data Artifex (DDI-Toolkit).
- **Import/Export Implementation:** Develop mapping functions for metadata; ensure strict adherence to DDI-L schema standards.
- **Advanced Feature Development:** Implement logic for multilingual metadata and "variable cascade" management.
- **Quality Assurance & Documentation:** Execute unit tests (Pytest) and finalize technical documentation (Sphinx/README).

### Phase III: Finalization and Support (Oct 19 – Dec 18, 2026)

_Goal: Integrate the solution into CDSP infrastructure and close the project._

- **Delivery and Coordination:** Deliver and present the DDI-L export script; coordinate migration and integration strategy.
- **Technical Integration Support:** Provide guidance on schema refactoring and tool adaptation; assist with pre-production testing.
- **Project Closure:** Finalize administrative/technical documentation and hold the wrap-up meeting.

---

## Deliverables Summary

| Phase         | Deliverable                 | Description                                                                              |
| :------------ | :-------------------------- | :--------------------------------------------------------------------------------------- |
| **Phase I**   | Rapport d'audit             | Technical audit report, formal DDI-L profile, and validated SQL target schema.           |
| **Phase II**  | Bibliothèque Python reQuest | Source code, unit tests, import/export scripts (DDI-L compliant), and documentation.     |
| **Phase III** | Dossier de clôture          | Activity summary, technical audit, feedback, and strategic roadmap for future evolution. |

---

## Key Risks and Assumptions

| Risk/Assumption                   | Impact                            | Mitigation Strategy                                     |
| :-------------------------------- | :-------------------------------- | :------------------------------------------------------ |
| **No source DDI-L profiles**      | Divergence from CDSP expectations | Early dialogue with partners; use of standard examples. |
| **Internal support availability** | Delays or schema misalignment     | Designate a dedicated technical point of contact.       |
| **Over-engineering**              | Increased structural complexity   | Prioritize a lightweight, rigorous schema initially.    |
| **ReQuest environment**           | Tech/library conflicts            | Early, close collaboration with existing developers.    |

Would you like me to create a draft email to kick off the coordination with the CDSP team based on these phases?
