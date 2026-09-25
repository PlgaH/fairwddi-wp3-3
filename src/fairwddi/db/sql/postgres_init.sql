-- ============================================================================
-- FAIRwDDI DDI Model Database Schema (PostgreSQL >= 17)
-- Aligned with DDI 4.0 / DDI-CDI / DDI-Lifecycle 3.3
-- Canonical URN Primary Keys & Foreign Key Relationships
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Organizational Hierarchy
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS request_ddi_organization (
    urn VARCHAR(512) PRIMARY KEY,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    organization_type VARCHAR(64),
    hashes JSONB DEFAULT '{}'::jsonb,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_org_type_idx ON request_ddi_organization (organization_type);

CREATE TABLE IF NOT EXISTS request_ddi_group (
    urn VARCHAR(512) PRIMARY KEY,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    description JSONB DEFAULT '[]'::jsonb,
    group_type VARCHAR(64),
    "references" JSONB DEFAULT '[]'::jsonb,
    hashes JSONB DEFAULT '{}'::jsonb,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_group_group_type ON request_ddi_group (group_type);

-- ----------------------------------------------------------------------------
-- 2. Concept Layer (Controlled Vocabularies & Thesauri)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS request_ddi_conceptscheme (
    urn VARCHAR(512) PRIMARY KEY,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    description JSONB DEFAULT '[]'::jsonb,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_ddi_concept (
    urn VARCHAR(512) PRIMARY KEY,
    scheme_urn VARCHAR(512) REFERENCES request_ddi_conceptscheme(urn) ON DELETE CASCADE,
    uri VARCHAR(512) UNIQUE,
    vocabulary VARCHAR(128),
    notation VARCHAR(128),
    label JSONB DEFAULT '[]'::jsonb,
    description JSONB DEFAULT '[]'::jsonb,
    definition JSONB DEFAULT '[]'::jsonb,
    parent_urn VARCHAR(512) REFERENCES request_ddi_concept(urn) ON DELETE SET NULL,
    concept_type VARCHAR(64),
    hashes JSONB DEFAULT '{}'::jsonb,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_concept_scheme_idx ON request_ddi_concept (scheme_urn);
CREATE INDEX IF NOT EXISTS req_ddi_concept_uri_idx ON request_ddi_concept (uri);
CREATE INDEX IF NOT EXISTS req_ddi_concept_vocab_idx ON request_ddi_concept (vocabulary);
CREATE INDEX IF NOT EXISTS req_ddi_concept_notation_idx ON request_ddi_concept (notation);

CREATE TABLE IF NOT EXISTS request_ddi_conceptualvariablescheme (
    urn VARCHAR(512) PRIMARY KEY,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    description JSONB DEFAULT '[]'::jsonb,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_ddi_conceptualvariable (
    urn VARCHAR(512) PRIMARY KEY,
    scheme_urn VARCHAR(512) REFERENCES request_ddi_conceptualvariablescheme(urn) ON DELETE CASCADE,
    concept_urn VARCHAR(512) REFERENCES request_ddi_concept(urn) ON DELETE SET NULL,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    label JSONB DEFAULT '[]'::jsonb,
    description JSONB DEFAULT '[]'::jsonb,
    hashes JSONB DEFAULT '{}'::jsonb,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_ddi_semanticrelationship (
    id BIGSERIAL PRIMARY KEY,
    subject_type VARCHAR(128) NOT NULL,
    subject_urn VARCHAR(512) NOT NULL,
    predicate VARCHAR(256) NOT NULL,
    object_type VARCHAR(128) NOT NULL,
    object_urn VARCHAR(512) NOT NULL,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_semrel_triple UNIQUE (subject_urn, predicate, object_urn)
);

CREATE INDEX IF NOT EXISTS idx_semrel_sub_pred ON request_ddi_semanticrelationship (subject_urn, predicate);
CREATE INDEX IF NOT EXISTS idx_semrel_obj_pred ON request_ddi_semanticrelationship (object_urn, predicate);
CREATE INDEX IF NOT EXISTS idx_semrel_predicate ON request_ddi_semanticrelationship (predicate);
CREATE INDEX IF NOT EXISTS idx_semrel_sub_type ON request_ddi_semanticrelationship (subject_type);
CREATE INDEX IF NOT EXISTS idx_semrel_obj_type ON request_ddi_semanticrelationship (object_type);


-- ----------------------------------------------------------------------------
-- 3. Representation Layer & Instruments
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS request_ddi_questionscheme (
    urn VARCHAR(512) PRIMARY KEY,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    description JSONB DEFAULT '[]'::jsonb,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_ddi_questionitem (
    urn VARCHAR(512) PRIMARY KEY,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    question_text JSONB DEFAULT '[]'::jsonb,
    scheme_urn VARCHAR(512) REFERENCES request_ddi_questionscheme(urn) ON DELETE CASCADE,
    hashes JSONB DEFAULT '{}'::jsonb,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_ddi_categoryscheme (
    urn VARCHAR(512) PRIMARY KEY,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    description JSONB DEFAULT '[]'::jsonb,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_ddi_category (
    urn VARCHAR(512) PRIMARY KEY,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    scheme_urn VARCHAR(512) REFERENCES request_ddi_categoryscheme(urn) ON DELETE CASCADE,
    concept_urn VARCHAR(512) REFERENCES request_ddi_concept(urn) ON DELETE SET NULL,
    label JSONB DEFAULT '[]'::jsonb,
    parent_urn VARCHAR(512) REFERENCES request_ddi_category(urn) ON DELETE SET NULL,
    "order" INTEGER DEFAULT 0,
    is_missing BOOLEAN DEFAULT FALSE,
    hashes JSONB DEFAULT '{}'::jsonb,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_ddi_codelist (
    urn VARCHAR(512) PRIMARY KEY,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    description JSONB DEFAULT '[]'::jsonb,
    scheme_urn VARCHAR(512) REFERENCES request_ddi_categoryscheme(urn) ON DELETE SET NULL,
    hashes JSONB DEFAULT '{}'::jsonb,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_ddi_code (
    urn VARCHAR(512) PRIMARY KEY,
    code_list_urn VARCHAR(512) REFERENCES request_ddi_codelist(urn) ON DELETE CASCADE,
    category_urn VARCHAR(512) REFERENCES request_ddi_category(urn) ON DELETE CASCADE,
    code_value VARCHAR(64),
    parent_urn VARCHAR(512) REFERENCES request_ddi_code(urn) ON DELETE SET NULL,
    "order" INTEGER DEFAULT 0,
    is_missing BOOLEAN DEFAULT FALSE,
    hashes JSONB DEFAULT '{}'::jsonb,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT req_ddi_code_unique UNIQUE (code_list_urn, code_value)
);

CREATE TABLE IF NOT EXISTS request_ddi_representedvariablescheme (
    urn VARCHAR(512) PRIMARY KEY,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    description JSONB DEFAULT '[]'::jsonb,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_ddi_representedvariable (
    urn VARCHAR(512) PRIMARY KEY,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    label JSONB DEFAULT '[]'::jsonb,
    description JSONB DEFAULT '[]'::jsonb,
    value_representation JSONB DEFAULT '{}'::jsonb,
    scheme_urn VARCHAR(512) REFERENCES request_ddi_representedvariablescheme(urn) ON DELETE CASCADE,
    conceptual_variable_urn VARCHAR(512) REFERENCES request_ddi_conceptualvariable(urn) ON DELETE CASCADE,
    code_list_urn VARCHAR(512) REFERENCES request_ddi_codelist(urn) ON DELETE SET NULL,
    hashes JSONB DEFAULT '{}'::jsonb,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_ddi_questionvariable (
    id BIGSERIAL PRIMARY KEY,
    question_item_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_questionitem(urn) ON DELETE CASCADE,
    represented_variable_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_representedvariable(urn) ON DELETE CASCADE,
    path VARCHAR(512) NOT NULL DEFAULT '',
    "order" INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT req_ddi_qv_unique UNIQUE (question_item_urn, represented_variable_urn)
);

CREATE TABLE IF NOT EXISTS request_ddi_instrument (
    urn VARCHAR(512) PRIMARY KEY,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    label JSONB DEFAULT '[]'::jsonb,
    description JSONB DEFAULT '[]'::jsonb,
    hashes JSONB DEFAULT '{}'::jsonb,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_ddi_instrumentquestion (
    id BIGSERIAL PRIMARY KEY,
    instrument_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_instrument(urn) ON DELETE CASCADE,
    question_item_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_questionitem(urn) ON DELETE CASCADE,
    path VARCHAR(512) NOT NULL DEFAULT '',
    "order" INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT req_ddi_iq_unique UNIQUE (instrument_urn, question_item_urn, path)
);

-- ----------------------------------------------------------------------------
-- 4. Dataset Layer
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS request_ddi_studyunit (
    urn VARCHAR(512) PRIMARY KEY,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    title JSONB DEFAULT '[]'::jsonb,
    external_ref VARCHAR(512) UNIQUE,
    year INTEGER,
    description JSONB DEFAULT '[]'::jsonb,
    hashes JSONB DEFAULT '{}'::jsonb,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_ddi_instancevariablescheme (
    urn VARCHAR(512) PRIMARY KEY,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    description JSONB DEFAULT '[]'::jsonb,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_ddi_instancevariable (
    urn VARCHAR(512) PRIMARY KEY,
    name JSONB NOT NULL DEFAULT '[]'::jsonb,
    label JSONB DEFAULT '[]'::jsonb,
    description JSONB DEFAULT '[]'::jsonb,
    scheme_urn VARCHAR(512) REFERENCES request_ddi_instancevariablescheme(urn) ON DELETE CASCADE,
    represented_variable_urn VARCHAR(512) REFERENCES request_ddi_representedvariable(urn) ON DELETE CASCADE,
    hashes JSONB DEFAULT '{}'::jsonb,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_ddi_studyunitvariable (
    id BIGSERIAL PRIMARY KEY,
    study_unit_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_studyunit(urn) ON DELETE CASCADE,
    instance_variable_urn VARCHAR(512) NOT NULL REFERENCES request_ddi_instancevariable(urn) ON DELETE CASCADE,
    path VARCHAR(512) NOT NULL DEFAULT '',
    "order" INTEGER DEFAULT 0,
    CONSTRAINT req_ddi_suv_unique UNIQUE (study_unit_urn, instance_variable_urn)
);

-- ----------------------------------------------------------------------------
-- 5. Event Logging & Resource Lifecycle Audit Trail
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS request_ddi_eventlog (
    id BIGSERIAL PRIMARY KEY,
    urn VARCHAR(512) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(128) NOT NULL,
    event_data JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS req_ddi_event_urn_ts_idx ON request_ddi_eventlog (urn, timestamp);
CREATE INDEX IF NOT EXISTS req_ddi_event_type_idx ON request_ddi_eventlog (event_type);

-- ----------------------------------------------------------------------------
-- 6. Infrastructure, Provenance, Quarantine, and Staging Layer
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS request_ddi_urnregistry (
    urn VARCHAR(512) PRIMARY KEY,
    resource_type VARCHAR(64) NOT NULL,
    extended_attributes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS req_ddi_urn_reg_type_idx ON request_ddi_urnregistry (resource_type);

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
