-- ============================================================================
-- FAIRwDDI DDI Model Database Schema (PostgreSQL >= 17)
-- Aligned with DDI 4.0 / DDI-CDI / DDI-Lifecycle 3.3
-- Canonical URN Primary Keys & Foreign Key Relationships
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Organizational Hierarchy
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS request_ddi_distributor (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_ddi_collection (
    urn VARCHAR(512) PRIMARY KEY,
    distributor_id BIGINT NOT NULL REFERENCES request_ddi_distributor(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description JSONB NOT NULL DEFAULT '[]'::jsonb,
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_coll_content_hash_idx ON request_ddi_collection (content_hash);

CREATE TABLE IF NOT EXISTS request_ddi_subcollection (
    urn VARCHAR(512) PRIMARY KEY,
    collection_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_collection(urn) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_subcoll_content_hash_idx ON request_ddi_subcollection (content_hash);

-- ----------------------------------------------------------------------------
-- 2. Concept Layer (Controlled Vocabularies & Thesauri)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS request_ddi_concept (
    id BIGSERIAL PRIMARY KEY,
    uri VARCHAR(512) UNIQUE,
    vocabulary VARCHAR(128) NOT NULL DEFAULT '',
    notation VARCHAR(128),
    label JSONB NOT NULL DEFAULT '[]'::jsonb,
    description JSONB NOT NULL DEFAULT '[]'::jsonb,
    definition JSONB NOT NULL DEFAULT '[]'::jsonb,
    parent_id BIGINT REFERENCES request_ddi_concept(id) ON DELETE SET NULL,
    concept_type VARCHAR(64) NOT NULL DEFAULT 'concept',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_concept_uri_idx ON request_ddi_concept (uri);
CREATE INDEX IF NOT EXISTS req_ddi_concept_vocab_idx ON request_ddi_concept (vocabulary);
CREATE INDEX IF NOT EXISTS req_ddi_concept_notation_idx ON request_ddi_concept (notation);

CREATE TABLE IF NOT EXISTS request_ddi_conceptualvariable (
    urn VARCHAR(512) PRIMARY KEY,
    concept_id BIGINT REFERENCES request_ddi_concept(id) ON DELETE SET NULL,
    label JSONB NOT NULL DEFAULT '[]'::jsonb,
    description JSONB NOT NULL DEFAULT '[]'::jsonb,
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_cv_content_hash_idx ON request_ddi_conceptualvariable (content_hash);

-- ----------------------------------------------------------------------------
-- 3. Representation Layer
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS request_ddi_questionitem (
    urn VARCHAR(512) PRIMARY KEY,
    question_text JSONB NOT NULL DEFAULT '[]'::jsonb,
    pre_question_text JSONB NOT NULL DEFAULT '[]'::jsonb,
    post_question_text JSONB NOT NULL DEFAULT '[]'::jsonb,
    interviewer_instructions JSONB NOT NULL DEFAULT '[]'::jsonb,
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_qi_content_hash_idx ON request_ddi_questionitem (content_hash);

CREATE TABLE IF NOT EXISTS request_ddi_questiongroup (
    urn VARCHAR(512) PRIMARY KEY,
    label JSONB NOT NULL DEFAULT '[]'::jsonb,
    description JSONB NOT NULL DEFAULT '[]'::jsonb,
    parent_group_urn VARCHAR(512) REFERENCES request_ddi_questiongroup(urn) ON DELETE SET NULL,
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_qg_content_hash_idx ON request_ddi_questiongroup (content_hash);

CREATE TABLE IF NOT EXISTS request_ddi_questiongroupitem (
    id BIGSERIAL PRIMARY KEY,
    question_group_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_questiongroup(urn) ON DELETE CASCADE,
    question_item_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_questionitem(urn) ON DELETE CASCADE,
    "order" INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT req_ddi_qg_item_unique UNIQUE (question_group_urn, question_item_urn)
);

CREATE TABLE IF NOT EXISTS request_ddi_category (
    urn VARCHAR(512) PRIMARY KEY,
    label JSONB NOT NULL DEFAULT '[]'::jsonb,
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_cat_content_hash_idx ON request_ddi_category (content_hash);

CREATE TABLE IF NOT EXISTS request_ddi_categoryscheme (
    urn VARCHAR(512) PRIMARY KEY,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    description JSONB NOT NULL DEFAULT '[]'::jsonb,
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_cs_content_hash_idx ON request_ddi_categoryscheme (content_hash);

CREATE TABLE IF NOT EXISTS request_ddi_categoryschemeitem (
    id BIGSERIAL PRIMARY KEY,
    category_scheme_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_categoryscheme(urn) ON DELETE CASCADE,
    category_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_category(urn) ON DELETE CASCADE,
    "order" INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT req_ddi_cs_item_unique UNIQUE (category_scheme_urn, category_urn)
);

CREATE TABLE IF NOT EXISTS request_ddi_codelist (
    urn VARCHAR(512) PRIMARY KEY,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    description JSONB NOT NULL DEFAULT '[]'::jsonb,
    category_scheme_urn VARCHAR(512) REFERENCES request_ddi_categoryscheme(urn) ON DELETE SET NULL,
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_cl_content_hash_idx ON request_ddi_codelist (content_hash);

CREATE TABLE IF NOT EXISTS request_ddi_code (
    id BIGSERIAL PRIMARY KEY,
    code_list_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_codelist(urn) ON DELETE CASCADE,
    category_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_category(urn) ON DELETE CASCADE,
    code_value VARCHAR(64) NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT req_ddi_code_unique UNIQUE (code_list_urn, code_value)
);

CREATE TABLE IF NOT EXISTS request_ddi_representedvariable (
    urn VARCHAR(512) PRIMARY KEY,
    conceptual_variable_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_conceptualvariable(urn) ON DELETE CASCADE,
    question_item_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_questionitem(urn) ON DELETE CASCADE,
    code_list_urn VARCHAR(512) REFERENCES request_ddi_codelist(urn) ON DELETE SET NULL,
    label JSONB NOT NULL DEFAULT '[]'::jsonb,
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_rv_content_hash_idx ON request_ddi_representedvariable (content_hash);

-- ----------------------------------------------------------------------------
-- 4. Dataset Layer
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS request_ddi_studyunit (
    urn VARCHAR(512) PRIMARY KEY,
    subcollection_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_subcollection(urn) ON DELETE CASCADE,
    title JSONB NOT NULL DEFAULT '[]'::jsonb,
    external_ref VARCHAR(512) UNIQUE,
    year INTEGER,
    description JSONB NOT NULL DEFAULT '[]'::jsonb,
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_su_content_hash_idx ON request_ddi_studyunit (content_hash);

CREATE TABLE IF NOT EXISTS request_ddi_instancevariable (
    urn VARCHAR(512) PRIMARY KEY,
    study_unit_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_studyunit(urn) ON DELETE CASCADE,
    represented_variable_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_representedvariable(urn) ON DELETE CASCADE,
    variable_name VARCHAR(255) NOT NULL,
    universe JSONB NOT NULL DEFAULT '[]'::jsonb,
    notes JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_indexed BOOLEAN NOT NULL DEFAULT FALSE,
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT req_ddi_iv_study_var_unique UNIQUE (study_unit_urn, variable_name)
);

CREATE INDEX IF NOT EXISTS req_ddi_iv_is_indexed_idx ON request_ddi_instancevariable (is_indexed);
CREATE INDEX IF NOT EXISTS req_ddi_iv_content_hash_idx ON request_ddi_instancevariable (content_hash);

CREATE TABLE IF NOT EXISTS request_ddi_studyunitvariable (
    id BIGSERIAL PRIMARY KEY,
    study_unit_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_studyunit(urn) ON DELETE CASCADE,
    instance_variable_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_instancevariable(urn) ON DELETE CASCADE,
    "order" INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT req_ddi_suv_unique UNIQUE (study_unit_urn, instance_variable_urn)
);

-- ----------------------------------------------------------------------------
-- 5. Infrastructure, Provenance, Quarantine, and Staging Layer
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS request_ddi_urnalias (
    id BIGSERIAL PRIMARY KEY,
    alias_urn VARCHAR(512) NOT NULL UNIQUE,
    canonical_urn VARCHAR(512) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    hash_strategy VARCHAR(64) NOT NULL DEFAULT 'v1_strict_sha256',
    source_file VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_urn_alias_canon_idx ON request_ddi_urnalias (canonical_urn);

CREATE TABLE IF NOT EXISTS request_ddi_metadataquarantine (
    id BIGSERIAL PRIMARY KEY,
    incoming_urn VARCHAR(512) NOT NULL,
    existing_urn VARCHAR(512),
    entity_type VARCHAR(64) NOT NULL,
    incoming_content JSONB NOT NULL,
    existing_content_hash VARCHAR(64),
    incoming_content_hash VARCHAR(64) NOT NULL,
    conflict_type VARCHAR(32) NOT NULL,
    resolution VARCHAR(32),
    resolved_by VARCHAR(255),
    resolved_at TIMESTAMPTZ,
    source_file VARCHAR(512),
    import_task_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_mq_resolution_idx ON request_ddi_metadataquarantine (resolution);

CREATE TABLE IF NOT EXISTS request_ddi_stagedimport (
    id BIGSERIAL PRIMARY KEY,
    source_format VARCHAR(64) NOT NULL,
    file_name VARCHAR(512) NOT NULL,
    file_path VARCHAR(512),
    import_options JSONB NOT NULL DEFAULT '{}'::jsonb,
    total_resources INT NOT NULL DEFAULT 0,
    processed_resources INT NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'staged',
    import_task_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS request_ddi_stagedresourcenode (
    id BIGSERIAL PRIMARY KEY,
    staged_import_id BIGINT NOT NULL REFERENCES request_ddi_stagedimport(id) ON DELETE CASCADE,
    resource_type VARCHAR(64) NOT NULL,
    raw_urn VARCHAR(512) NOT NULL,
    raw_value JSONB NOT NULL,
    canonical_urn VARCHAR(512),
    status VARCHAR(32) NOT NULL DEFAULT 'staged',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_srn_res_type_idx ON request_ddi_stagedresourcenode (resource_type);
CREATE INDEX IF NOT EXISTS req_ddi_srn_raw_urn_idx ON request_ddi_stagedresourcenode (raw_urn);
CREATE INDEX IF NOT EXISTS req_ddi_srn_canon_urn_idx ON request_ddi_stagedresourcenode (canonical_urn);

COMMIT;
