-- Self-contained relational source for the install-base materialization example.
-- Contains both schema and rows so it works as a drop-in source file: the
-- materializer loads every mappings/sql/*.sql file into an in-memory SQLite
-- database (schema files first), then runs each mapping's rr:sqlQuery against it.
CREATE TABLE install_base (
  item_id TEXT PRIMARY KEY,
  item_name TEXT NOT NULL,
  product TEXT NOT NULL,
  location TEXT NOT NULL,
  status TEXT NOT NULL
);
INSERT INTO install_base VALUES ('IB-001', 'Edge Gateway 1', 'Gateway X100', 'Site A', 'active');
INSERT INTO install_base VALUES ('IB-002', 'Edge Gateway 2', 'Gateway X100', 'Site B', 'active');
INSERT INTO install_base VALUES ('IB-003', 'Sensor Hub 7', 'Hub H7', 'Site A', 'maintenance');
