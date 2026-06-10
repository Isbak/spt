CREATE TABLE source_system (
  source_system_id TEXT PRIMARY KEY,
  source_system_name TEXT NOT NULL,
  system_type TEXT NOT NULL,
  owner TEXT NOT NULL,
  steward TEXT NOT NULL
);
CREATE TABLE organization (
  organization_id TEXT PRIMARY KEY,
  organization_name TEXT NOT NULL,
  status_code TEXT NOT NULL,
  source_system_id TEXT NOT NULL REFERENCES source_system(source_system_id)
);
CREATE TABLE person (
  person_id TEXT PRIMARY KEY,
  given_name TEXT NOT NULL,
  family_name TEXT NOT NULL,
  email TEXT NOT NULL,
  organization_id TEXT REFERENCES organization(organization_id),
  source_system_id TEXT NOT NULL REFERENCES source_system(source_system_id)
);
CREATE TABLE dataset (
  dataset_id TEXT PRIMARY KEY,
  dataset_name TEXT NOT NULL,
  version TEXT NOT NULL,
  status_code TEXT NOT NULL,
  source_system_id TEXT NOT NULL REFERENCES source_system(source_system_id)
);
