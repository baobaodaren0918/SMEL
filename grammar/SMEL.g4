/*
 * SMEL - Schema Migration & Evolution Language
 * A domain-specific language for database schema migration
 *
 * Supported database models: RELATIONAL, DOCUMENT, GRAPH, COLUMNAR
 * Design: from André Conrad
 *
 * Example SMEL script:
 *   MIGRATION person_migration:1.0
 *   FROM DOCUMENT TO RELATIONAL
 *   USING person_schema:1.0
 *
 *   FLATTEN person.address AS address
 *     GENERATE KEY address_id AS SERIAL
 *     ADD REFERENCE person_id TO person
 *
 *   FLATTEN person.tags[] AS person_tag
 *     GENERATE KEY tag_id AS String PREFIX "t"
 *     ADD REFERENCE person_id TO person
 */
grammar SMEL;

// ============================================================================
// PARSER RULES
// ============================================================================

// Entry point: migration script = header + operations
migration: header operation* EOF;
header: migrationDecl fromToDecl usingDecl;                         // MIGRATION name:ver FROM type TO type USING schema:ver
migrationDecl: MIGRATION identifier COLON version;                  // MIGRATION payment_migration:1.0
fromToDecl: FROM databaseType TO databaseType;                      // FROM RELATIONAL TO Doucment
usingDecl: USING identifier COLON version;                          // USING iso20022_schema:1.0
databaseType: RELATIONAL | DOCUMENT | GRAPH | COLUMNAR;             // Abstract database model types
version: VERSION_NUMBER | INTEGER_LITERAL;                          // 1 | 1.0 | 1.0.0

// ============================================================================
// OPERATIONS
// ============================================================================
// Structure:  NEST, UNNEST, FLATTEN
// Movement:   COPY, MOVE, MERGE, SPLIT, EXTRACT
// Type:       CAST, LINKING
// CRUD:       ADD, DELETE, DROP, RENAME

operation: nest | unnest | flatten
         | copy | move | merge | split | cast | linking | extract
         | add | delete | drop | rename;

// ----------------------------------------------------------------------------
// NEST - Merge separate table into embedded document (PostgreSQL -> MongoDB)
// ----------------------------------------------------------------------------
// Example: NEST address INTO person AS address WITH CARDINALITY ONE_TO_ONE
//   Before: person(id, name), address(id, street, person_id)
//   After:  person(id, name, address: {street: ...})
//
nest: NEST identifier INTO identifier AS identifier nestClause*;    // NEST Child INTO Parent AS alias [clauses]
nestClause: withCardinalityClause | usingKeyClause | whereClause;

// ----------------------------------------------------------------------------
// UNNEST - Extract embedded document to separate table (MongoDB -> PostgreSQL)
// ----------------------------------------------------------------------------
// Example: UNNEST address FROM person
//   Before: person(id, name, address: {street: ...})
//   After:  person(id, name), address(id, street, person_id)
//
unnest: UNNEST identifier FROM identifier unnestClause*;            // UNNEST embedded FROM Parent
unnestClause: AS identifier | usingKeyClause;

// ----------------------------------------------------------------------------
// FLATTEN - Unified extraction operation (MongoDB -> PostgreSQL)
// ----------------------------------------------------------------------------
// FLATTEN handles three scenarios based on source type and clauses:
//
// 1. Embedded Object (e.g., person.address)
//    FLATTEN person.address AS address
//        GENERATE KEY id AS String PREFIX "addr"
//        ADD REFERENCE person_id TO person
//    Result: address(id, street, city, person_id) - copies all attributes
//
// 2. Primitive Array (e.g., person.tags[])
//    FLATTEN person.tags[] AS person_tag
//        GENERATE KEY id AS String PREFIX "t"
//        ADD REFERENCE person_id TO person
//    Result: person_tag(id, value, person_id) - adds 'value' column
//
// 3. Reference Array / M:N (e.g., person.knows[])
//    FLATTEN person.knows[] AS person_knows
//        ADD REFERENCE person_id TO person
//        ADD REFERENCE knows_person_id TO person
//    Result: person_knows(person_id, knows_person_id) - composite PK from FKs
//
// Auto-detection logic:
//   - Has []? -> Array type
//   - Has GENERATE KEY? -> Single PK, otherwise Composite PK (all FKs)
//   - Source is ListDataType? -> Add 'value' column
//   - Source is EntityType? -> Copy all attributes
//
// Supports deep nested paths (from André Conrad):
//   FLATTEN person.address.location AS location
//
flatten: FLATTEN qualifiedName AS identifier flattenClause*;
flattenClause: generateKeyClause | addReferenceClause | columnRenameClause;

// Column rename within FLATTEN (no IN entity - applies to new table only)
// Used to rename default 'value' column in primitive arrays
// Example: RENAME value TO tag_value
columnRenameClause: RENAME identifier TO identifier;

// ----------------------------------------------------------------------------
// SHARED CLAUSES - Reusable clause definitions
// ----------------------------------------------------------------------------
//
// Cardinality (relationship multiplicity):
//   ONE_TO_ONE   (&)  - Required, exactly one      (1..1)
//   ONE_TO_MANY  (+)  - Required, at least one     (1..n)
//   ZERO_TO_ONE  (?)  - Optional, at most one      (0..1)
//   ZERO_TO_MANY (*)  - Optional, unlimited        (0..n)
//
withCardinalityClause: WITH CARDINALITY cardinalityType;            // WITH CARDINALITY ONE_TO_MANY
usingKeyClause: USING KEY identifier;                               // USING KEY foreign_key
whereClause: WHERE condition;                                       // WHERE a.id = b.ref_id
renameClause: RENAME identifier TO qualifiedName (IN identifier)?;  // RENAME old TO new [IN entity]
addReferenceClause: ADD REFERENCE identifier TO identifier;         // ADD REFERENCE ref_id TO Target

// GENERATE KEY - Primary key generation strategies:
//   AS SERIAL              -> Auto-increment integer (PostgreSQL SERIAL)
//   AS STRING PREFIX "x"   -> UUID-like string with prefix (e.g., "pty_abc123")
//   FROM field             -> Copy value from existing field
//
// Example: GENERATE KEY party_id AS String PREFIX "pty"
//   -> Creates VARCHAR(255) column with values like "pty_abc123"
//
generateKeyClause: GENERATE KEY identifier (AS SERIAL | AS STRING PREFIX STRING_LITERAL | FROM identifier);
linkingClause: LINKING qualifiedName TO identifier;                 // LINKING source.field TO target

// ----------------------------------------------------------------------------
// STANDALONE OPERATIONS - Simple single-purpose operations
// ----------------------------------------------------------------------------
//
// COPY:    Duplicate an attribute to another location (keeps original)
// MOVE:    Relocate an attribute to another location (removes original)
// MERGE:   Combine two entities into one new entity
// SPLIT:   Divide one entity into two separate entities
// CAST:    Change the data type of an attribute
// LINKING: Create a relationship link between entities
//
copy: COPY qualifiedName TO qualifiedName;                          // COPY source TO target
move: MOVE qualifiedName TO qualifiedName;                          // MOVE source TO target
merge: MERGE identifier COMMA identifier INTO identifier (AS identifier)?; // MERGE A, B INTO C [AS alias]
split: SPLIT identifier INTO identifier COMMA identifier;           // SPLIT source INTO A, B
cast: CAST qualifiedName TO dataType;                               // CAST Entity.field TO Integer
linking: LINKING qualifiedName TO identifier;                       // LINKING source TO target

// ============================================================================
// ADD OPERATION - Unified entry point for adding new elements
// ============================================================================
// Supports adding:
//   - ATTRIBUTE:  Add new attribute to entity
//   - REFERENCE:  Add foreign key relationship
//   - EMBEDDED:   Add embedded object relationship (MongoDB style)
//   - ENTITY:     Add new entity/table
//   - KEY:        Add primary/unique/foreign key constraint
//   - VARIATION:  Add structural variation (U-Schema support)
//   - RELTYPE:    Add relationship type (Graph database support)
//
add: ADD (attributeAdd | referenceAdd | embeddedAdd | entityAdd
        | keyAdd | variationAdd | relTypeAdd);

// Add attribute: ADD ATTRIBUTE email TO Customer WITH TYPE String NOT NULL
attributeAdd: ATTRIBUTE identifier (TO identifier)? attributeClause*;
attributeClause: withTypeClause | withDefaultClause | notNullClause;
withTypeClause: WITH TYPE dataType;                                 // WITH TYPE String
withDefaultClause: WITH DEFAULT literal;                            // WITH DEFAULT 'value'
notNullClause: NOT_NULL;                                            // NOT NULL (is_optional = false)

// Add reference: ADD REFERENCE customer_id TO Order WITH CARDINALITY ONE_TO_MANY
referenceAdd: REFERENCE qualifiedName TO identifier referenceClause*;
referenceClause: withCardinalityClause | usingKeyClause | whereClause;

// Add embedded: ADD EMBEDDED address TO Customer WITH CARDINALITY ONE_TO_ONE
embeddedAdd: EMBEDDED identifier TO identifier embeddedClause*;
embeddedClause: withCardinalityClause | withStructureClause;
withStructureClause: WITH STRUCTURE LPAREN identifierList RPAREN;   // WITH STRUCTURE (field1, field2)

// Add entity: ADD ENTITY Product WITH ATTRIBUTES (id, name)
entityAdd: ENTITY identifier entityClause*;
entityClause: withAttributesClause | withKeyClause;
withKeyClause: WITH KEY identifier;                                 // WITH KEY id

// Add key: ADD PRIMARY KEY id TO Customer OR ADD PRIMARY KEY (id1, id2) TO Customer
keyAdd: keyType KEY keyColumns (TO identifier)? keyClause*;

// Key columns - single identifier or parenthesized list for composite keys
keyColumns: identifier | LPAREN identifierList RPAREN;

// Add variation: ADD VARIATION v1 TO Customer WITH ATTRIBUTES (a, b)
variationAdd: VARIATION identifier TO identifier variationClause*;

// Add relationship type (Graph): ADD RELTYPE ACTED_IN FROM Actor TO Movie
relTypeAdd: RELTYPE identifier FROM identifier TO identifier relTypeClause*;

// ============================================================================
// DELETE OPERATION - Remove elements from schema
// ============================================================================
// Supports deleting:
//   - ATTRIBUTE: Remove attribute from entity
//   - REFERENCE: Remove foreign key relationship
//   - EMBEDDED:  Remove embedded object relationship
//   - ENTITY:    Remove entire entity/table
//
delete: DELETE (attributeDelete | referenceDelete | embeddedDelete | entityDelete);

// Delete attribute: DELETE ATTRIBUTE Customer.email
attributeDelete: ATTRIBUTE qualifiedName;

// Delete reference: DELETE REFERENCE Customer.order_id
referenceDelete: REFERENCE qualifiedName;

// Delete embedded: DELETE EMBEDDED Customer.address
embeddedDelete: EMBEDDED qualifiedName;

// Delete entity: DELETE ENTITY Customer
entityDelete: ENTITY identifier;

// ============================================================================
// DROP OPERATION - Drop structural/constraint elements
// ============================================================================
// Supports dropping:
//   - KEY:       Drop primary/unique/foreign key constraint
//   - VARIATION: Drop structural variation (U-Schema)
//   - RELTYPE:   Drop relationship type (Graph database)
//
drop: DROP (keyDrop | variationDrop | relTypeDrop);

// Drop key: DROP PRIMARY KEY id FROM Customer OR DROP PRIMARY KEY (id1, id2) FROM Customer
keyDrop: keyType KEY keyColumns (FROM identifier)?;

// Drop variation: DROP VARIATION v1 FROM Customer
variationDrop: VARIATION identifier FROM identifier;

// Drop relationship type: DROP RELTYPE ACTED_IN
relTypeDrop: RELTYPE identifier;

// ============================================================================
// RENAME OPERATION - Rename schema elements
// ============================================================================
// Supports renaming:
//   - Feature (attribute/relationship): RENAME oldName TO newName IN Entity
//   - Entity:  RENAME ENTITY OldName TO NewName
//   - RelType: RENAME RELTYPE oldName TO newName (Graph database)
//
rename: RENAME (featureRename | entityRename | relTypeRename);

// Rename feature: RENAME oldName TO newName IN Entity
featureRename: identifier TO identifier (IN identifier)?;

// Rename entity: RENAME ENTITY OldName TO NewName
entityRename: ENTITY identifier TO identifier;

// Rename relationship type: RENAME RELTYPE oldName TO newName
relTypeRename: RELTYPE identifier TO identifier;

// ----------------------------------------------------------------------------
// KEY TYPES - Constraint types for different database models
// ----------------------------------------------------------------------------
// Matches PKTypeEnum in unified_meta_schema.py (from André Conrad)
//
//   PRIMARY:    Standard primary key (all databases)
//   UNIQUE:     Unique constraint (all databases)
//   FOREIGN:    Foreign key reference (relational)
//   PARTITION:  Partition key (Cassandra - columnar)
//   CLUSTERING: Clustering key (Cassandra - columnar)
//
keyType: PRIMARY | UNIQUE | FOREIGN | PARTITION | CLUSTERING;
keyClause: referencesClause | withColumnsClause;
referencesClause: REFERENCES identifier LPAREN identifierList RPAREN; // REFERENCES Target(id)
withColumnsClause: WITH COLUMNS LPAREN identifierList RPAREN;       // WITH COLUMNS (col1, col2)
identifierList: identifier (COMMA identifier)*;                      // id1, id2, id3

// Variation clauses (U-Schema StructuralVariation support)
variationClause: withAttributesClause | withRelationshipsClause | withCountClause;
withAttributesClause: WITH ATTRIBUTES LPAREN identifierList RPAREN; // WITH ATTRIBUTES (a, b, c)
withRelationshipsClause: WITH RELATIONSHIPS LPAREN identifierList RPAREN; // WITH RELATIONSHIPS (r1, r2)
withCountClause: WITH COUNT INTEGER_LITERAL;                        // WITH COUNT 100

// RelType clauses (Graph relationship type support)
relTypeClause: withPropertiesClause | withCardinalityClause;
withPropertiesClause: WITH PROPERTIES LPAREN identifierList RPAREN; // WITH PROPERTIES (role, year)

// Extract operation - extract attributes from entity to create new entity
extract: EXTRACT LPAREN identifierList RPAREN FROM identifier INTO identifier extractClause*;
extractClause: generateKeyClause | addReferenceClause;              // EXTRACT (a,b,c) FROM E INTO NewE

// ----------------------------------------------------------------------------
// COMMON TYPES - Shared type definitions
// ----------------------------------------------------------------------------
// Matches PrimitiveType and Cardinality in unified_meta_schema.py
//

// Cardinality notation:
//   ONE_TO_ONE   (&) = (1,1) - Required, exactly one
//   ONE_TO_MANY  (+) = (1,n) - Required, at least one
//   ZERO_TO_ONE  (?) = (0,1) - Optional, at most one
//   ZERO_TO_MANY (*) = (0,n) - Optional, unlimited
cardinalityType: ONE_TO_ONE | ONE_TO_MANY | ZERO_TO_ONE | ZERO_TO_MANY;

// Data types (matches PrimitiveType enum):
//   String types:  STRING, TEXT
//   Numeric types: INT, INTEGER, LONG, DOUBLE, FLOAT, DECIMAL
//   Other types:   BOOLEAN, DATE, DATETIME, TIMESTAMP, UUID, BINARY
//   Custom types:  identifier (for database-specific types)
dataType: STRING | TEXT | INT | INTEGER | LONG | DOUBLE | FLOAT | DECIMAL
        | BOOLEAN | DATE | DATETIME | TIMESTAMP | UUID | BINARY | identifier;

// ----------------------------------------------------------------------------
// PATH AND IDENTIFIERS - Dot-separated paths for nested access
// ----------------------------------------------------------------------------
// Supports André Conrad's nested path notation:
//   - Simple:     person
//   - Nested:     person.address
//   - Deep:       person.address.location
//   - With array: person.tags[]
//
// Examples:
//   FLATTEN person.address.location AS location
//   FLATTEN person.tags[] AS person_tag
//
qualifiedName: pathSegment (DOT pathSegment)*;                      // Entity.field[].subfield
pathSegment: identifier (LBRACKET RBRACKET)?;                       // field or field[]
identifier: IDENTIFIER;

// Condition (simplified for schema migration: only equality and AND for composite keys)
condition: qualifiedName EQUALS qualifiedName                       // a.id = b.ref_id
         | condition AND condition                                  // composite key: a.id1 = b.ref1 AND a.id2 = b.ref2
         | LPAREN condition RPAREN;                                 // grouping

// Literals (kept for addClause WITH DEFAULT)
literal: STRING_LITERAL | INTEGER_LITERAL | DECIMAL_LITERAL | TRUE | FALSE | NULL;

// ============================================================================
// LEXER RULES
// ============================================================================
// Token definitions for the SMEL language.
// ANTLR4 lexer rules must start with uppercase letters.
//

// ----------------------------------------------------------------------------
// KEYWORDS - Reserved words in SMEL
// ----------------------------------------------------------------------------
MIGRATION: 'MIGRATION'; FROM: 'FROM'; TO: 'TO'; USING: 'USING'; AS: 'AS';
INTO: 'INTO'; WITH: 'WITH'; WHERE: 'WHERE'; IN: 'IN'; KEY: 'KEY'; AND: 'AND';
COUNT: 'COUNT';

// Database model types (abstract - not product-specific)
// Matches DatabaseType enum in unified_meta_schema.py
RELATIONAL: 'RELATIONAL'; DOCUMENT: 'DOCUMENT'; GRAPH: 'GRAPH'; COLUMNAR: 'COLUMNAR';

// Operations
NEST: 'NEST'; UNNEST: 'UNNEST'; FLATTEN: 'FLATTEN';
DELETE: 'DELETE'; ADD: 'ADD'; RENAME: 'RENAME'; COPY: 'COPY'; MOVE: 'MOVE';
MERGE: 'MERGE'; SPLIT: 'SPLIT'; CAST: 'CAST'; GENERATE: 'GENERATE'; LINKING: 'LINKING';
DROP: 'DROP'; EXTRACT: 'EXTRACT';

// RelType (Graph relationship types)
RELTYPE: 'RELTYPE'; PROPERTIES: 'PROPERTIES'; STRUCTURE: 'STRUCTURE';

// Feature types
REFERENCE: 'REFERENCE'; ATTRIBUTE: 'ATTRIBUTE'; EMBEDDED: 'EMBEDDED';
ENTITY: 'ENTITY'; VARIATION: 'VARIATION'; VALUE: 'VALUE';

// Key types (matches KeyType in unified_meta_schema.py)
PRIMARY: 'PRIMARY'; UNIQUE: 'UNIQUE'; FOREIGN: 'FOREIGN';
PARTITION: 'PARTITION'; CLUSTERING: 'CLUSTERING';
REFERENCES: 'REFERENCES'; COLUMNS: 'COLUMNS';

// Variation clauses
ATTRIBUTES: 'ATTRIBUTES'; RELATIONSHIPS: 'RELATIONSHIPS';

// Cardinality
CARDINALITY: 'CARDINALITY';
ONE_TO_ONE: 'ONE_TO_ONE'; ONE_TO_MANY: 'ONE_TO_MANY';               // & = (1,1)  + = (1,n)
ZERO_TO_ONE: 'ZERO_TO_ONE'; ZERO_TO_MANY: 'ZERO_TO_MANY';           // ? = (0,1)  * = (0,n)

// Data types (keywords)
STRING: 'String'; TEXT: 'Text'; INT: 'Int'; INTEGER: 'Integer'; LONG: 'Long';
DOUBLE: 'Double'; FLOAT: 'Float'; DECIMAL: 'Decimal'; BOOLEAN: 'Boolean';
DATE: 'Date'; DATETIME: 'DateTime'; TIMESTAMP: 'Timestamp'; UUID: 'UUID'; BINARY: 'Binary';
TYPE: 'TYPE'; DEFAULT: 'DEFAULT'; SERIAL: 'SERIAL'; PREFIX: 'PREFIX';

// Constraints
NOT_NULL: 'NOT NULL';

// Literals
TRUE: 'true' | 'TRUE'; FALSE: 'false' | 'FALSE'; NULL: 'null' | 'NULL';

// Symbols
COLON: ':'; COMMA: ','; DOT: '.'; LPAREN: '('; RPAREN: ')'; LBRACKET: '['; RBRACKET: ']';
EQUALS: '=';

// ----------------------------------------------------------------------------
// PATTERNS - Regular expression patterns for literals and identifiers
// ----------------------------------------------------------------------------
//
// VERSION_NUMBER:  1.0 | 1.0.0 | 2.1.3
// INTEGER_LITERAL: 0 | 1 | 42 | 1000
// DECIMAL_LITERAL: 1.5 | 3.14 | 0.001
// STRING_LITERAL:  'hello' | "world" | 'it''s ok' (escaped quotes)
// IDENTIFIER:      person | _id | customer_name | MyEntity
//
VERSION_NUMBER: [0-9]+ '.' [0-9]+ ('.' [0-9]+)?;
INTEGER_LITERAL: [0-9]+;
DECIMAL_LITERAL: [0-9]+ '.' [0-9]+;
STRING_LITERAL: '\'' (~['\r\n] | '\'\'')* '\'' | '"' (~["\r\n] | '""')* '"';
IDENTIFIER: [a-zA-Z_][a-zA-Z0-9_]*;

// ----------------------------------------------------------------------------
// SKIP - Whitespace and comments (ignored by parser)
// ----------------------------------------------------------------------------
// Supports:
//   - Line comments:  -- this is a comment
//   - Block comments: /* this is a
//                        multi-line comment */
//   - Whitespace:     spaces, tabs, newlines
//
LINE_COMMENT: '--' ~[\r\n]* -> skip;
BLOCK_COMMENT: '/*' .*? '*/' -> skip;
WS: [ \t\r\n]+ -> skip;