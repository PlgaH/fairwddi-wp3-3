-- ============================================================================
-- FAIRwDDI DDI Model Database Schema (PostgreSQL >= 17)
-- Aligned with DDI 4.0 / DDI-CDI / DDI-Lifecycle
-- Standalone DDL Initialization Script
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
    id BIGSERIAL PRIMARY KEY,
    distributor_id BIGINT NOT NULL REFERENCES request_ddi_distributor(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description JSONB NOT NULL DEFAULT '[]'::jsonb,
    urn VARCHAR(512) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_ddi_subcollection (
    id BIGSERIAL PRIMARY KEY,
    collection_id BIGINT NOT NULL REFERENCES request_ddi_collection(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    urn VARCHAR(512) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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
    id BIGSERIAL PRIMARY KEY,
    urn VARCHAR(512) UNIQUE,
    agency VARCHAR(255) NOT NULL DEFAULT 'fr.cdsp',
    ddi_identifier VARCHAR(255),
    version VARCHAR(64) NOT NULL DEFAULT '1.0.0',
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    concept_id BIGINT REFERENCES request_ddi_concept(id) ON DELETE SET NULL,
    label JSONB NOT NULL DEFAULT '[]'::jsonb,
    description JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_cv_ddi_id_idx ON request_ddi_conceptualvariable (ddi_identifier);
CREATE INDEX IF NOT EXISTS req_ddi_cv_content_hash_idx ON request_ddi_conceptualvariable (content_hash);

-- ----------------------------------------------------------------------------
-- 3. Representation Layer
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS request_ddi_questionitem (
    id BIGSERIAL PRIMARY KEY,
    urn VARCHAR(512) UNIQUE,
    agency VARCHAR(255) NOT NULL DEFAULT 'fr.cdsp',
    ddi_identifier VARCHAR(255),
    version VARCHAR(64) NOT NULL DEFAULT '1.0.0',
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    question_text JSONB NOT NULL DEFAULT '[]'::jsonb,
    pre_question_text JSONB NOT NULL DEFAULT '[]'::jsonb,
    post_question_text JSONB NOT NULL DEFAULT '[]'::jsonb,
    interviewer_instructions JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_qi_ddi_id_idx ON request_ddi_questionitem (ddi_identifier);
CREATE INDEX IF NOT EXISTS req_ddi_qi_content_hash_idx ON request_ddi_questionitem (content_hash);

CREATE TABLE IF NOT EXISTS request_ddi_category (
    id BIGSERIAL PRIMARY KEY,
    urn VARCHAR(512) UNIQUE,
    agency VARCHAR(255) NOT NULL DEFAULT 'fr.cdsp',
    ddi_identifier VARCHAR(255),
    version VARCHAR(64) NOT NULL DEFAULT '1.0.0',
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    label JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_cat_ddi_id_idx ON request_ddi_category (ddi_identifier);
CREATE INDEX IF NOT EXISTS req_ddi_cat_content_hash_idx ON request_ddi_category (content_hash);

CREATE TABLE IF NOT EXISTS request_ddi_categoryset (
    id BIGSERIAL PRIMARY KEY,
    urn VARCHAR(512) UNIQUE,
    agency VARCHAR(255) NOT NULL DEFAULT 'fr.cdsp',
    ddi_identifier VARCHAR(255),
    version VARCHAR(64) NOT NULL DEFAULT '1.0.0',
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    description JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_ddi_categorysetitem (
    id BIGSERIAL PRIMARY KEY,
    category_set_id BIGINT NOT NULL REFERENCES request_ddi_categoryset(id) ON DELETE CASCADE,
    category_id BIGINT NOT NULL REFERENCES request_ddi_category(id) ON DELETE CASCADE,
    "order" INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT req_ddi_cs_item_unique UNIQUE (category_set_id, category_id)
);

CREATE TABLE IF NOT EXISTS request_ddi_codelist (
    id BIGSERIAL PRIMARY KEY,
    urn VARCHAR(512) UNIQUE,
    agency VARCHAR(255) NOT NULL DEFAULT 'fr.cdsp',
    ddi_identifier VARCHAR(255),
    version VARCHAR(64) NOT NULL DEFAULT '1.0.0',
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    description JSONB NOT NULL DEFAULT '[]'::jsonb,
    category_set_id BIGINT REFERENCES request_ddi_categoryset(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_cl_ddi_id_idx ON request_ddi_codelist (ddi_identifier);
CREATE INDEX IF NOT EXISTS req_ddi_cl_content_hash_idx ON request_ddi_codelist (content_hash);

CREATE TABLE IF NOT EXISTS request_ddi_codeitem (
    id BIGSERIAL PRIMARY KEY,
    code_list_id BIGINT NOT NULL REFERENCES request_ddi_codelist(id) ON DELETE CASCADE,
    category_id BIGINT NOT NULL REFERENCES request_ddi_category(id) ON DELETE CASCADE,
    code_value VARCHAR(64) NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT req_ddi_code_item_unique UNIQUE (code_list_id, code_value)
);

CREATE TABLE IF NOT EXISTS request_ddi_representedvariable (
    id BIGSERIAL PRIMARY KEY,
    urn VARCHAR(512) UNIQUE,
    agency VARCHAR(255) NOT NULL DEFAULT 'fr.cdsp',
    ddi_identifier VARCHAR(255),
    version VARCHAR(64) NOT NULL DEFAULT '1.0.0',
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    conceptual_variable_id BIGINT NOT NULL REFERENCES request_ddi_conceptualvariable(id) ON DELETE CASCADE,
    question_item_id BIGINT NOT NULL REFERENCES request_ddi_questionitem(id) ON DELETE CASCADE,
    code_list_id BIGINT REFERENCES request_ddi_codelist(id) ON DELETE SET NULL,
    label JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_rv_ddi_id_idx ON request_ddi_representedvariable (ddi_identifier);
CREATE INDEX IF NOT EXISTS req_ddi_rv_content_hash_idx ON request_ddi_representedvariable (content_hash);

-- ----------------------------------------------------------------------------
-- 4. Dataset Layer
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS request_ddi_studyunit (
    id BIGSERIAL PRIMARY KEY,
    urn VARCHAR(512) UNIQUE,
    agency VARCHAR(255) NOT NULL DEFAULT 'fr.cdsp',
    ddi_identifier VARCHAR(255),
    version VARCHAR(64) NOT NULL DEFAULT '1.0.0',
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    subcollection_id BIGINT NOT NULL REFERENCES request_ddi_subcollection(id) ON DELETE CASCADE,
    title JSONB NOT NULL DEFAULT '[]'::jsonb,
    external_ref VARCHAR(512) UNIQUE,
    year INTEGER,
    description JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_su_ddi_id_idx ON request_ddi_studyunit (ddi_identifier);

CREATE TABLE IF NOT EXISTS request_ddi_instancevariable (
    id BIGSERIAL PRIMARY KEY,
    urn VARCHAR(512) UNIQUE,
    agency VARCHAR(255) NOT NULL DEFAULT 'fr.cdsp',
    ddi_identifier VARCHAR(255),
    version VARCHAR(64) NOT NULL DEFAULT '1.0.0',
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    study_unit_id BIGINT NOT NULL REFERENCES request_ddi_studyunit(id) ON DELETE CASCADE,
    represented_variable_id BIGINT NOT NULL REFERENCES request_ddi_representedvariable(id) ON DELETE CASCADE,
    variable_name VARCHAR(255) NOT NULL,
    universe JSONB NOT NULL DEFAULT '[]'::jsonb,
    notes JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_indexed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT req_ddi_iv_study_var_unique UNIQUE (study_unit_id, variable_name)
);

CREATE INDEX IF NOT EXISTS req_ddi_iv_is_indexed_idx ON request_ddi_instancevariable (is_indexed);

-- ----------------------------------------------------------------------------
-- 5. Grouping / Organization Layer
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS request_ddi_variablegroup (
    id BIGSERIAL PRIMARY KEY,
    urn VARCHAR(512) UNIQUE,
    agency VARCHAR(255) NOT NULL DEFAULT 'fr.cdsp',
    ddi_identifier VARCHAR(255),
    version VARCHAR(64) NOT NULL DEFAULT '1.0.0',
    content_hash VARCHAR(64) NOT NULL DEFAULT '',
    content_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    study_unit_id BIGINT REFERENCES request_ddi_studyunit(id) ON DELETE CASCADE,
    collection_id BIGINT REFERENCES request_ddi_collection(id) ON DELETE CASCADE,
    parent_group_id BIGINT REFERENCES request_ddi_variablegroup(id) ON DELETE SET NULL,
    label JSONB NOT NULL DEFAULT '[]'::jsonb,
    description JSONB NOT NULL DEFAULT '[]'::jsonb,
    type_of_group VARCHAR(64) NOT NULL DEFAULT 'Thematic',
    concept_id BIGINT REFERENCES request_ddi_concept(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_ddi_variablegroupmembership (
    id BIGSERIAL PRIMARY KEY,
    variable_group_id BIGINT NOT NULL REFERENCES request_ddi_variablegroup(id) ON DELETE CASCADE,
    instance_variable_id BIGINT NOT NULL REFERENCES request_ddi_instancevariable(id) ON DELETE CASCADE,
    "order" INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT req_ddi_vgm_unique UNIQUE (variable_group_id, instance_variable_id)
);

-- ----------------------------------------------------------------------------
-- 6. Infrastructure, Provenance, Quarantine, and Staging Layer
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
