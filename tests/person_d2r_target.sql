CREATE TABLE person (
    person_id VARCHAR(255) PRIMARY KEY,
    age INTEGER,
    vorname VARCHAR(255),
    nachname VARCHAR(255)
);

CREATE TABLE address (
    person_id VARCHAR(255) NOT NULL REFERENCES person(person_id),
    street VARCHAR(255),
    city VARCHAR(255),
    address_id VARCHAR(255) PRIMARY KEY
);

CREATE TABLE employment (
    person_id VARCHAR(255) NOT NULL REFERENCES person(person_id),
    position VARCHAR(255),
    employment_id VARCHAR(255) PRIMARY KEY
);

CREATE TABLE company (
    employment_id VARCHAR(255) NOT NULL REFERENCES employment(employment_id),
    name VARCHAR(255),
    company_id VARCHAR(255) PRIMARY KEY
);

CREATE TABLE company_address (
    company_id VARCHAR(255) NOT NULL REFERENCES company(company_id),
    street VARCHAR(255),
    city VARCHAR(255),
    company_address_id VARCHAR(255) PRIMARY KEY
);

CREATE TABLE person_tag (
    person_id VARCHAR(255) NOT NULL REFERENCES person(person_id),
    tag_value VARCHAR(255),
    person_tag_id VARCHAR(255) PRIMARY KEY
);

CREATE TABLE person_knows (
    person_id VARCHAR(255) NOT NULL REFERENCES person(person_id),
    knows_person_id VARCHAR(255) NOT NULL REFERENCES person(person_id),
    PRIMARY KEY (person_id, knows_person_id)
);
