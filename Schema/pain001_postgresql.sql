-- PostgreSQL Schema for ISO 20022 pain.001.001.03
-- CustomerCreditTransferInitiationV03 (Customer-to-Bank Payment Initiation)
-- Source: Nordea Message Implementation Guidelines v2.2 (2025-09-18, Open/Public)

-- Level 0: PARTY - Base Table
-- ISO 20022 Component: PartyIdentification32 (9.1.x)
-- Used for: InitiatingParty, Debtor, Creditor
CREATE TABLE party (
    party_id    SERIAL PRIMARY KEY,
    name        VARCHAR(140) NOT NULL,  -- 9.1.0  Party name (person or organization)
    street_name VARCHAR(70),            -- 9.1.5  Street name incl. building number
    post_code   VARCHAR(16),            -- 9.1.7  Postal code
    town_name   VARCHAR(35),            -- 9.1.8  Town/City name
    country     VARCHAR(2)              -- 9.1.10 Country code (ISO 3166 alpha-2)
);
-- Level 1: ACCOUNT - Bank Account Information
-- ISO 20022 Component: CashAccount16 (1.1.x)
-- Each account belongs to exactly one party (1:N relationship)
CREATE TABLE account (
    acct_id   SERIAL PRIMARY KEY,
    party_id  INTEGER NOT NULL          -- Account owner reference
              REFERENCES party(party_id),
    iban      VARCHAR(34) NOT NULL,     -- 1.1.1  IBAN
    currency  VARCHAR(3),               -- 1.1.11 Account currency (ISO 4217)
    agent_bic VARCHAR(11)               -- 6.1.1  Bank BIC (SWIFT code)
);
-- Level 2: PAYMENT_MESSAGE - Group Header
-- ISO 20022 Component: GroupHeader32 (1.0)
-- Contains characteristics shared by all transactions in the message
-- 3NF: nb_of_txs and ctrl_sum removed (derived data - can be calculated from payment_info/credit_transfer_tx)

CREATE TABLE payment_message (
    msg_id            VARCHAR(35) PRIMARY KEY,  -- 1.1  Message ID (unique 90 days)
    creation_datetime TIMESTAMP NOT NULL,       -- 1.2  Creation date and time
    initg_pty_id      INTEGER NOT NULL          -- 1.8  Initiating party reference
                      REFERENCES party(party_id)
);

-- Level 3: PAYMENT_INFO - Payment Information
-- ISO 20022 Component: PaymentInstructionInformation3 (2.0)
-- Groups transactions with same debtor, execution date, payment method
-- 3NF: nb_of_txs, ctrl_sum removed (derived data)
-- 3NF: dbtr_id removed (redundant - derivable via dbtr_acct_id -> account.party_id)

CREATE TABLE payment_info (
    pmt_inf_id    VARCHAR(35) PRIMARY KEY,  -- 2.1   Payment info ID (unique 90 days)
    msg_id        VARCHAR(35) NOT NULL      -- FK    Reference to parent message
                  REFERENCES payment_message(msg_id),
    pmt_mtd       VARCHAR(3) NOT NULL,      -- 2.2   Payment method (TRF/CHK)
    reqd_exctn_dt DATE NOT NULL,            -- 2.17  Requested execution date
    dbtr_acct_id  INTEGER NOT NULL          -- 2.20  Debtor account reference
                  REFERENCES account(acct_id)
);


-- Level 4: CREDIT_TRANSFER_TX - Credit Transfer Transaction Information
-- ISO 20022 Component: CreditTransferTransactionInformation10 (2.27)
-- Individual payment transaction within a payment information block
-- 3NF: cdtr_id removed (redundant - derivable via cdtr_acct_id -> account.party_id)

CREATE TABLE credit_transfer_tx (
    tx_id         SERIAL PRIMARY KEY,
    pmt_inf_id    VARCHAR(35) NOT NULL      -- FK    Reference to parent payment info
                  REFERENCES payment_info(pmt_inf_id),
    end_to_end_id VARCHAR(35) NOT NULL,     -- 2.30  End-to-end ID (unique 90 days)
    instd_amt     DECIMAL(13,2) NOT NULL,   -- 2.43  Instructed amount
    instd_amt_ccy VARCHAR(3) NOT NULL,      -- 2.43  Instructed amount currency
    cdtr_acct_id  INTEGER NOT NULL          -- 2.80  Creditor account reference
                  REFERENCES account(acct_id)
);

-- Level 5: REMITTANCE_INFO - Remittance Information
-- ISO 20022 Component: RemittanceInformation7 (2.98)
-- Payment reference information for creditor reconciliation

CREATE TABLE remittance_info (
    rmt_id       SERIAL PRIMARY KEY,
    tx_id        INTEGER NOT NULL           -- FK    Reference to parent transaction
                 REFERENCES credit_transfer_tx(tx_id),
    ustrd        TEXT,                      -- 2.99  Unstructured remittance info
    strd_ref     VARCHAR(35),               -- 2.126 Structured reference (creditor ref)
    rfrd_doc_nb  VARCHAR(35),               -- 2.107 Document number (invoice)
    rfrd_doc_amt DECIMAL(13,2)              -- 2.119 Remitted amount
);
