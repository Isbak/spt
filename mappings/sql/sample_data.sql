INSERT INTO source_system VALUES ('SRC-SQL-001', 'Generic Operational SQL', 'relational', 'Platform data owner', 'Platform data steward');
INSERT INTO organization VALUES ('ORG-001', 'Example Operations', 'active', 'SRC-SQL-001');
INSERT INTO organization VALUES ('ORG-002', 'Example Analytics', 'active', 'SRC-SQL-001');
INSERT INTO person VALUES ('PER-001', 'Alex', 'Morgan', 'alex.morgan@example.org', 'ORG-001', 'SRC-SQL-001');
INSERT INTO person VALUES ('PER-002', 'Jordan', 'Lee', 'jordan.lee@example.org', 'ORG-002', 'SRC-SQL-001');
INSERT INTO dataset VALUES ('DS-001', 'People master extract', '2026.06', 'active', 'SRC-SQL-001');
INSERT INTO dataset VALUES ('DS-002', 'Organization reference extract', '2026.06', 'active', 'SRC-SQL-001');
