-- PostgreSQL Schema: Person (Target for MongoDB -> PostgreSQL migration)
-- 3NF Normalized from MongoDB nested document
-- All tables use VARCHAR primary keys (string IDs with prefixes)

-- Table 1: person (main entity)
-- ID from MongoDB _id (e.g., "p001")
CREATE TABLE person (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

-- Table 2: address (extracted from embedded object)
-- ID with "addr" prefix (e.g., "addr001", "addr002")
CREATE TABLE address (
    id VARCHAR(255) PRIMARY KEY,
    street VARCHAR(255),
    city VARCHAR(255),
    person_id VARCHAR(255) NOT NULL REFERENCES person(id)
);

-- Table 3: person_tag (flattened from value array)
-- ID with "t" prefix (e.g., "t001", "t002")
-- 'value' column renamed to 'tag_value' via RENAME clause (soft configuration)
CREATE TABLE person_tag (
    id VARCHAR(255) PRIMARY KEY,
    tag_value VARCHAR(255) NOT NULL,
    person_id VARCHAR(255) NOT NULL REFERENCES person(id)
);

-- Table 4: person_knows (M:N self-reference join table)
-- Composite primary key (person_id, knows_person_id)
CREATE TABLE person_knows (
    person_id VARCHAR(255) NOT NULL REFERENCES person(id),
    knows_person_id VARCHAR(255) NOT NULL REFERENCES person(id),
    PRIMARY KEY (person_id, knows_person_id)
);
