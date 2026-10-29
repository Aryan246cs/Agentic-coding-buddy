-- Apply before deploying the custom React website builder to PostgreSQL.
-- Fresh local SQLite databases are created from SQLAlchemy metadata; older
-- local databases add the two nullable project columns on API startup.
ALTER TABLE projects ADD COLUMN draft_files JSON;
ALTER TABLE projects ADD COLUMN published_files JSON;

CREATE TABLE site_revisions (
    id VARCHAR(32) PRIMARY KEY,
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    label VARCHAR(120) NOT NULL,
    prompt TEXT,
    spec JSON NOT NULL,
    files JSON NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uq_site_revision_version UNIQUE (project_id, version)
);
CREATE INDEX ix_site_revisions_project ON site_revisions (project_id, version);
