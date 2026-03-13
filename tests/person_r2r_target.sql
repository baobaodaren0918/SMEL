CREATE TABLE person (
    person_id VARCHAR(255) PRIMARY KEY,
    first_name VARCHAR(255),
    last_name VARCHAR(255)
);

CREATE TABLE address (
    address_id VARCHAR(255) PRIMARY KEY,
    person_id VARCHAR(255) NOT NULL REFERENCES person(person_id),
    street VARCHAR(255),
    city VARCHAR(255)
);

CREATE TABLE employment (
    employment_id VARCHAR(255) PRIMARY KEY,
    person_id VARCHAR(255) NOT NULL REFERENCES person(person_id),
    role VARCHAR(255),
    start_date VARCHAR(255)
);

CREATE TABLE company (
    company_id VARCHAR(255) PRIMARY KEY,
    employment_id VARCHAR(255) NOT NULL REFERENCES employment(employment_id),
    company_name VARCHAR(255),
    street VARCHAR(255),
    city VARCHAR(255)
);

CREATE TABLE person_knows (
    person_id VARCHAR(255) NOT NULL REFERENCES person(person_id),
    knows_person_id VARCHAR(255) NOT NULL REFERENCES person(person_id),
    PRIMARY KEY (person_id, knows_person_id)
);

CREATE TABLE person_detail (
    person_id VARCHAR(255) NOT NULL REFERENCES person(person_id),
    age VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(255),
    detail_id VARCHAR(255) PRIMARY KEY
);

CREATE TABLE tag (
    tag_id VARCHAR(255) PRIMARY KEY,
    person_id VARCHAR(255) NOT NULL REFERENCES person(person_id),
    label VARCHAR(255)
);
