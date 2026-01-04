-- PostgreSQL Schema for ISO 20022 pain.001.001.03 (Version 2.0)
-- Evolved schema with structural changes:
-- 1. party renamed to participant
-- 2. party address fields extracted to new address entity
-- 3. instd_amt and instd_amt_ccy merged into amount entity
-- 4. New audit fields added
-- 5. remittance_info split into structured and unstructured parts

-- Level 0: ADDRESS - Extracted from party
CREATE TABLE address (
    address_id  SERIAL PRIMARY KEY,
    street_name VARCHAR(70),
    post_code   VARCHAR(16),
    town_name   VARCHAR(35),
    country     VARCHAR(2)
);

-- Level 0: PARTICIPANT - Renamed from party, address extracted
CREATE TABLE participant (
    participant_id SERIAL PRIMARY KEY,
    name           VARCHAR(140) NOT NULL,
    address_id     INTEGER REFERENCES address(address_id),
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Level 1: ACCOUNT - Bank Account Information
CREATE TABLE account (
    acct_id        SERIAL PRIMARY KEY,
    participant_id INTEGER NOT NULL REFERENCES participant(participant_id),
    iban           VARCHAR(34) NOT NULL,
    currency       VARCHAR(3),
    agent_bic      VARCHAR(11),
    is_active      BOOLEAN DEFAULT TRUE
);

-- Level 2: PAYMENT_MESSAGE - Group Header
CREATE TABLE payment_message (
    msg_id            VARCHAR(35) PRIMARY KEY,
    creation_datetime TIMESTAMP NOT NULL,
    initg_pty_id      INTEGER NOT NULL REFERENCES participant(participant_id),
    status            VARCHAR(20) DEFAULT 'PENDING'
);

-- Level 3: PAYMENT_INFO - Payment Information
CREATE TABLE payment_info (
    pmt_inf_id    VARCHAR(35) PRIMARY KEY,
    msg_id        VARCHAR(35) NOT NULL REFERENCES payment_message(msg_id),
    pmt_mtd       VARCHAR(3) NOT NULL,
    reqd_exctn_dt DATE NOT NULL,
    dbtr_acct_id  INTEGER NOT NULL REFERENCES account(acct_id),
    priority      INTEGER DEFAULT 0
);

-- Level 4: AMOUNT - Extracted from credit_transfer_tx
CREATE TABLE amount (
    amount_id SERIAL PRIMARY KEY,
    value     DECIMAL(13,2) NOT NULL,
    currency  VARCHAR(3) NOT NULL
);

-- Level 4: CREDIT_TRANSFER_TX - Credit Transfer Transaction
CREATE TABLE credit_transfer_tx (
    tx_id         SERIAL PRIMARY KEY,
    pmt_inf_id    VARCHAR(35) NOT NULL REFERENCES payment_info(pmt_inf_id),
    end_to_end_id VARCHAR(35) NOT NULL,
    amount_id     INTEGER NOT NULL REFERENCES amount(amount_id),
    cdtr_acct_id  INTEGER NOT NULL REFERENCES account(acct_id),
    tx_status     VARCHAR(20) DEFAULT 'INITIATED'
);

-- Level 5: REMITTANCE_STRUCTURED - Split from remittance_info
CREATE TABLE remittance_structured (
    rmt_strd_id  SERIAL PRIMARY KEY,
    tx_id        INTEGER NOT NULL REFERENCES credit_transfer_tx(tx_id),
    strd_ref     VARCHAR(35),
    rfrd_doc_nb  VARCHAR(35),
    rfrd_doc_amt DECIMAL(13,2)
);

-- Level 5: REMITTANCE_UNSTRUCTURED - Split from remittance_info
CREATE TABLE remittance_unstructured (
    rmt_ustrd_id SERIAL PRIMARY KEY,
    tx_id        INTEGER NOT NULL REFERENCES credit_transfer_tx(tx_id),
    ustrd        TEXT
);
