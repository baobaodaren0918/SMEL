/*
 * SMILE_Specific - Schema Migration & Evolution Language (Specific Operations Version)
 * A domain-specific language for database schema migration
 *
 * This version uses specific, independent keywords for each operation.
 * Each operation has its own dedicated keyword (e.g., ADD_PROPERTY, ADD_FOREIGN_KEY)
 *
 * Comparison: This is the "Specific" version. See SMILE_Generalized.g4 for the
 * "Generalized" version that uses parameterized operations (e.g., ADD PROPERTY).
 *
 * Supported database models: RELATIONAL, DOCUMENT, GRAPH, COLUMNAR
 * Design: from André Conrad
 *
 * Example SMILE migration script:
 *   MIGRATION person_migration:1.0
 *   FROM DOCUMENT TO RELATIONAL
 *   USING person_schema VERSION 1.0
 *
 * Example SMILE evolution script:
 *   EVOLUTION person_evolution:1.0
 *   FROM DOCUMENT TO DOCUMENT
 *   USING person_schema VERSION 1.0 TO 2.0
 *
 *   -- Extract nested object to table
 *   FLATTEN person.address AS address
 *   ADD_PRIMARY_KEY address_id TO address
 *   ADD_FOREIGN_KEY person_id TO address REFERENCES person(id)
 *
 *   -- Expand array to table
 *   UNWIND person.tags[] INTO person_tag
 *   ADD_PRIMARY_KEY id TO person_tag
 *   ADD_FOREIGN_KEY person_id TO person_tag REFERENCES person(id)
 */
grammar SMILE_Specific;

// ============================================================================
// PARSER RULES
// ============================================================================

// Entry point: migration script = header + operations
migration: header operation* EOF;
header: (migrationDecl | evolutionDecl) fromToDecl usingDecl;        // MIGRATION|EVOLUTION name:ver FROM type TO type USING schema VERSION ver
migrationDecl: MIGRATION identifier COLON version;                  // MIGRATION payment_migration:1.0
evolutionDecl: EVOLUTION identifier COLON version;                  // EVOLUTION payment_evolution:1.0
fromToDecl: FROM databaseType TO databaseType;                      // FROM RELATIONAL TO Document
usingDecl: USING identifier VERSION_KW version (TO version)?;       // USING iso20022_schema VERSION 1.0 [TO 2.0]
databaseType: RELATIONAL | DOCUMENT | GRAPH | COLUMNAR;             // Abstract database model types
version: VERSION_NUMBER | INTEGER_LITERAL;                          // 1 | 1.0 | 1.0.0

// ============================================================================
// OPERATIONS - Each operation is a separate, specific keyword
// ============================================================================
// Structure:  NEST, UNNEST, FLATTEN, UNFLATTEN, WIND, UNWIND
// Movement:   COPY, MOVE, MERGE, SPLIT
// Type:       CAST
// CRUD:       ADD_*, DELETE_*, RENAME_*

operation: add_property | add_foreign_key | add_embedded | add_entity
         | add_primary_key | add_unique_key
         | add_partition_key | add_clustering_key
         | add_label
         | delete_property | delete_foreign_key | delete_embedded | delete_entity
         | delete_primary_key | delete_unique_key
         | delete_partition_key | delete_clustering_key
         | delete_label
         | rename_property | rename_entity
         | flatten | unflatten | unwind | wind | nest | unnest
         | copy_property | copy_entity | move_property | merge | split | cast_property | cast_constraint | cast_entity | recard
         | transform
;

// ============================================================================
// ADD OPERATIONS - Specific keywords for each type
// ============================================================================

// ADD_PROPERTY: Add new property to entity
// Example: ADD_PROPERTY email TO Customer WITH TYPE String NOT NULL
add_property: ADD_PROPERTY identifier (TO identifier)? propertyClause*;
propertyClause: withTypeClause | withDefaultClause | notNullClause;
withTypeClause: WITH TYPE dataType;
withDefaultClause: WITH DEFAULT literal;
notNullClause: NOT_NULL;

// ADD_FOREIGN_KEY: Add foreign key constraint (SQL-style) with explicit entity.field
// Example: ADD_FOREIGN_KEY address.person_id REFERENCES person(person_id)
// Example: ADD_FOREIGN_KEY order.customer_id REFERENCES customer(id) WITH CARDINALITY ONE_TO_MANY
add_foreign_key: ADD_FOREIGN_KEY qualifiedName REFERENCES identifier LPAREN identifier RPAREN constraintClause*;
constraintClause: withCardinalityClause | usingKeyClause | whereClause;

// ADD_EMBEDDED: Add embedded object relationship (MongoDB style)
// Example: ADD_EMBEDDED address TO Customer WITH CARDINALITY ONE_TO_ONE
add_embedded: ADD_EMBEDDED identifier TO identifier embeddedClause*;
embeddedClause: withCardinalityClause | withStructureClause;
withStructureClause: WITH STRUCTURE LPAREN identifierList RPAREN;

// ADD_ENTITY: Add new entity/table or edge (relationship type)
// Example: ADD_ENTITY Product WITH PROPERTIES (id String, name String)
// Example: ADD_ENTITY CONTAINS FROM orders TO products WITH PROPERTIES (unitPrice Decimal, quantity Integer)
// Example: ADD_ENTITY REPORTS_TO FROM employees TO employees WITH CARDINALITY ONE_TO_MANY
add_entity: ADD_ENTITY identifier (FROM identifier TO identifier)? (WITH CARDINALITY cardinalityType)? entityClause*;
entityClause: withPropertiesClause | withKeyClause;
withKeyClause: WITH KEY identifier;

// ADD_PRIMARY_KEY: Add primary key constraint
// Example: ADD_PRIMARY_KEY address.address_id AS String  (new explicit entity.field syntax)
// Example: ADD_PRIMARY_KEY (id1, id2) TO Customer  (composite key)
// Example: ADD_PRIMARY_KEY id TO Customer WITH TYPE UUID (legacy TO syntax)
// Note: AS dataType is a simplified alternative to WITH TYPE dataType
// Note: keyColumns now supports qualifiedName (entity.field) for explicit entity specification
add_primary_key: ADD_PRIMARY_KEY keyColumns (AS dataType)? (TO identifier)? keyClause*;

// ADD_UNIQUE_KEY: Add unique constraint
// Example: ADD_UNIQUE_KEY email TO Customer
add_unique_key: ADD_UNIQUE_KEY keyColumns (AS dataType)? (TO identifier)? keyClause*;

// ADD_PARTITION_KEY: Add partition key (Cassandra - columnar)
// Example: ADD_PARTITION_KEY user_id TO UserActivity
add_partition_key: ADD_PARTITION_KEY keyColumns (AS dataType)? (TO identifier)? keyClause*;

// ADD_CLUSTERING_KEY: Add clustering key (Cassandra - columnar)
// Example: ADD_CLUSTERING_KEY timestamp TO UserActivity
add_clustering_key: ADD_CLUSTERING_KEY keyColumns (AS dataType)? (TO identifier)? keyClause*;

// ADD_LABEL: Add label to node (graph database)
// Example: ADD_LABEL Employee TO Person
add_label: ADD_LABEL identifier TO identifier;

// Key columns - qualifiedName (entity.field) or parenthesized list for composite keys
keyColumns: qualifiedName | LPAREN identifierList RPAREN;

// Key constraint clauses
keyClause: referencesClause | withColumnsClause | withTypeClause;
referencesClause: REFERENCES identifier LPAREN identifierList RPAREN;
withColumnsClause: WITH COLUMNS LPAREN identifierList RPAREN;

// ============================================================================
// DELETE OPERATIONS - Specific keywords for each type
// ============================================================================

// DELETE_PROPERTY: Remove property from entity
// Example: DELETE_PROPERTY Customer.email
delete_property: DELETE_PROPERTY qualifiedName;

// DELETE_FOREIGN_KEY: Remove foreign key constraint
// Example: DELETE_FOREIGN_KEY Customer.order_id
delete_foreign_key: DELETE_FOREIGN_KEY qualifiedName;

// DELETE_EMBEDDED: Remove embedded object relationship
// Example: DELETE_EMBEDDED Customer.address
delete_embedded: DELETE_EMBEDDED qualifiedName;

// DELETE_ENTITY: Remove entire entity/table
// Example: DELETE_ENTITY Customer
delete_entity: DELETE_ENTITY identifier;

// DELETE_PRIMARY_KEY: Delete primary key constraint
// Example: DELETE_PRIMARY_KEY id FROM Customer
delete_primary_key: DELETE_PRIMARY_KEY keyColumns (FROM identifier)?;

// DELETE_UNIQUE_KEY: Delete unique constraint
// Example: DELETE_UNIQUE_KEY email FROM Customer
delete_unique_key: DELETE_UNIQUE_KEY keyColumns (FROM identifier)?;

// DELETE_PARTITION_KEY: Delete partition key
// Example: DELETE_PARTITION_KEY user_id FROM UserActivity
delete_partition_key: DELETE_PARTITION_KEY keyColumns (FROM identifier)?;

// DELETE_CLUSTERING_KEY: Delete clustering key
// Example: DELETE_CLUSTERING_KEY timestamp FROM UserActivity
delete_clustering_key: DELETE_CLUSTERING_KEY keyColumns (FROM identifier)?;

// DELETE_LABEL: Delete label from node
// Example: DELETE_LABEL Employee FROM Person
delete_label: DELETE_LABEL identifier FROM identifier;

// ============================================================================
// RENAME OPERATIONS - Specific keywords for each type
// ============================================================================

// RENAME_PROPERTY: Rename property within an entity
// Example: RENAME_PROPERTY email TO contact_email IN Customer
rename_property: RENAME_PROPERTY identifier TO identifier (IN identifier)?;

// RENAME_ENTITY: Rename entity/table
// Example: RENAME_ENTITY Customer TO Client
rename_entity: RENAME_ENTITY identifier TO identifier;

// ============================================================================
// STRUCTURE OPERATIONS
// ============================================================================

// FLATTEN - Flatten nested object fields into parent table (reduce depth by 1)
// Reference: André Conrad - "Die Operation FLATTEN erstellt aus dem Objekt in der Spalte
//            jeweils eine Spalte für jedes Attribut dieses Objekts"
// Example: FLATTEN person.name
//   Before: person { name: { vorname, nachname }, age }
//   After:  person { name_vorname, name_nachname, age }
flatten: FLATTEN qualifiedName;

// UNFLATTEN - Combine flat fields into nested object (reverse of FLATTEN)
// Example: UNFLATTEN person:vorname, nachname AS name
//   Before: person { vorname, nachname, age }
//   After:  person { name: { vorname, nachname }, age }
unflatten: UNFLATTEN identifier COLON identifierList AS identifier;

// UNNEST - Extract nested object to separate table (normalization)
// Example: UNNEST person.address:street,city AS address WITH person.person_id TO address.person_id
// Example with multiple carry fields:
//   UNNEST person.employment:position AS employment
//       WITH person.person_id TO employment.person_id, person.dept_id TO employment.dept_id
//   - 'street,city' are properties to extract
//   - WITH clause: copy fields from source to new table (can carry multiple fields)
//   - WITH is optional, for cases where no parent fields need to be copied
//   Before: person { person_id, address: { street, city } }
//   After:  person { person_id }
//           address { person_id, street, city }
// Note: Use separate ADD_PRIMARY_KEY, ADD_FOREIGN_KEY for constraints
unnest: UNNEST qualifiedName COLON unnestFieldList AS identifier (WITH unnestCarryList)?;

// Carry list for UNNEST: fields to copy from source to new table
unnestCarryList: unnestCarryField (COMMA unnestCarryField)*;
unnestCarryField: qualifiedName TO qualifiedName;

// Field list for UNNEST: supports both properties and nested objects (recursive)
// - identifier: regular property (e.g., position, name, street, city)
// - identifier{...}: nested object with its contents (e.g., company{name, address{street, city}})
unnestFieldList: unnestField (COMMA unnestField)*;
unnestField: identifier                                    # SimpleField
           | identifier LBRACE unnestFieldList RBRACE      # NestedField
           ;

// UNWIND - Expand array field into multiple rows
// Reference: André Conrad - array expansion operation
// Supports two modes:
//   1. Expand in place: UNWIND person_tag.tags (expands array within existing table)
//   2. Create new table: UNWIND person.tags[] INTO person_tag (legacy, creates new table)
// Note: Use separate ADD_PRIMARY_KEY, ADD_FOREIGN_KEY, RENAME_PROPERTY for constraints
unwind: UNWIND qualifiedName (INTO identifier)?;

// WIND - Convert scalar property back to array (reverse of UNWIND)
// Syntax: WIND person_tag.tags
// Cross-entity movement is handled by MERGE, not WIND.
wind: WIND qualifiedName;

// NEST - Merge separate table into embedded document (PostgreSQL -> MongoDB)
// Example: NEST address:street,city IN person.address WHERE address.person_id = person.person_id
//   - 'address' is source entity
//   - ':street,city' are properties to embed
//   - 'IN person.address' specifies target (person entity, address field)
//   - WHERE clause specifies join condition
// Note: source entity is not removed automatically; use DELETE_ENTITY explicitly when desired.
nest: NEST identifier COLON unnestFieldList IN qualifiedName WHERE condition;

// ============================================================================
// SIMPLE OPERATIONS
// ============================================================================

// COPY_PROPERTY: Duplicate a property to another entity (keeps original)
// Example: COPY_PROPERTY name FROM person TO other
copy_property: COPY_PROPERTY identifier FROM identifier TO identifier;

// COPY_ENTITY: Duplicate an entire entity with all its structure (properties, keys, constraints)
// Reference: PRISM "COPY TABLE R INTO S", CoDEL "Addtable(S, R)"
// Example: COPY_ENTITY person AS employee
// Example: COPY_ENTITY works_at AS employed_at FROM person TO company  (copy EDGE with explicit endpoints)
copy_entity: COPY_ENTITY identifier AS identifier (FROM identifier TO identifier)?;

// MOVE_PROPERTY: Relocate a property to another entity (removes original)
// Example: MOVE_PROPERTY name FROM person TO other
move_property: MOVE_PROPERTY identifier FROM identifier TO identifier;

// MERGE: Combine two entities into one new entity
// Example: MERGE A, B INTO C AS alias
merge: MERGE identifier COMMA identifier INTO identifier (AS identifier)?;

// SPLIT: Divide one entity into multiple separate entities (vertical partitioning)
// Reference: André Conrad - "SPLIT Person into Person:id, firstname, lastname AND knows:id, knows"
// Example: SPLIT person INTO person:person_id, vorname, nachname, age; person_tag:person_id, tags
//   Before: person { person_id, vorname, nachname, age, tags[] }
//   After:  person { person_id, vorname, nachname, age }
//          person_tag { person_id, tags[] }
// Note: Fields can be duplicated across parts (e.g., person_id in both parts)
split: SPLIT identifier INTO splitPart (SEMICOLON splitPart)+;
splitPart: identifier COLON identifierList;

// CAST_PROPERTY: Change the data type of a property
// Example: CAST_PROPERTY Entity.field TO Integer
cast_property: CAST_PROPERTY qualifiedName TO dataType;

// CAST_CONSTRAINT: Change the type of a constraint
// Reference: Orion "Cast Reference" - change the type of a constraint
// Example: CAST_CONSTRAINT person.email TO UNIQUE KEY
// Example: CAST_CONSTRAINT person.city TO PARTITION KEY
cast_constraint: CAST_CONSTRAINT qualifiedName TO constraintKeyType;

// CAST_ENTITY: Change the entity_kind of an entity type (cross-paradigm type conversion)
// Example: CAST_ENTITY orders TO DOCUMENT
// Example: CAST_ENTITY person TO GRAPH
// Note: Overrides automatic entity_kind normalization for this entity
// Note: For VERTEX<->EDGE conversion, use TRANSFORM instead
cast_entity: CAST_ENTITY identifier TO databaseType;

// RECARD: Change the multiplicity/cardinality of a reference
// Reference: Orion "Mult Reference" - change the multiplicity of a reference
// Example: RECARD person.address_id TO ONE_TO_MANY
recard: RECARD qualifiedName TO cardinalityType;

// TRANSFORM: Transform entity between node and relationship (Graph database)
// Reference: Hausler et al. - "transform a node with its features into a relationship" / vice versa
// Example: TRANSFORM works_at INTO RELATIONSHIP FROM person TO company
// Example: TRANSFORM works_at INTO RELATIONSHIP FROM person TO company WITH CARDINALITY ZERO_TO_MANY
// Example: TRANSFORM works_at INTO ENTITY
transform: TRANSFORM identifier INTO transformTarget;
transformTarget: RELATIONSHIP FROM identifier TO identifier (WITH CARDINALITY cardinalityType)?   # TransformToRelationship
              | ENTITY                                                                            # TransformToEntity
              ;

// ============================================================================
// SHARED CLAUSES - Reusable clause definitions
// ============================================================================

// Cardinality (relationship multiplicity)
withCardinalityClause: WITH CARDINALITY cardinalityType;
usingKeyClause: USING KEY identifier;
whereClause: WHERE condition;

// Entity clauses (for ADD_ENTITY)
// WITH PROPERTIES (name String, age Integer) - each property has name and type
withPropertiesClause: WITH PROPERTIES LPAREN propertyDefList RPAREN;
propertyDefList: propertyDef (COMMA propertyDef)*;
propertyDef: identifier dataType;

// Identifier list
identifierList: identifier (COMMA identifier)*;

// ============================================================================
// COMMON TYPES - Shared type definitions
// ============================================================================

// Cardinality notation
cardinalityType: ONE_TO_ONE | ONE_TO_MANY | ZERO_TO_ONE | ZERO_TO_MANY;

// Constraint key type (for CAST_CONSTRAINT)
constraintKeyType: PRIMARY KEY | UNIQUE KEY | PARTITION KEY | CLUSTERING KEY | NODE KEY | DOCUMENT_ID;

// Data types
dataType: STRING | TEXT | INT | INTEGER | LONG | DOUBLE | FLOAT | DECIMAL
        | BOOLEAN | DATE | DATETIME | TIMESTAMP | UUID | BINARY | identifier;

// Path and identifiers
qualifiedName: pathSegment (DOT pathSegment)*;
pathSegment: identifier (LBRACKET RBRACKET)?;
identifier: IDENTIFIER;

// Condition (simplified for schema migration)
condition: qualifiedName EQUALS qualifiedName
         | condition AND condition
         | LPAREN condition RPAREN;

// Literals
literal: STRING_LITERAL | INTEGER_LITERAL | DECIMAL_LITERAL | TRUE | FALSE | NULL;

// ============================================================================
// LEXER RULES
// ============================================================================

// ----------------------------------------------------------------------------
// KEYWORDS - Reserved words in SMILE_Specific
// ----------------------------------------------------------------------------
MIGRATION: 'MIGRATION'; EVOLUTION: 'EVOLUTION'; VERSION_KW: 'VERSION';
FROM: 'FROM'; TO: 'TO'; USING: 'USING'; AS: 'AS';
INTO: 'INTO'; WITH: 'WITH'; WHERE: 'WHERE'; IN: 'IN'; KEY: 'KEY'; AND: 'AND';
ON: 'ON';

// Database model types
RELATIONAL: 'RELATIONAL'; DOCUMENT: 'DOCUMENT'; GRAPH: 'GRAPH'; COLUMNAR: 'COLUMNAR';

// Structure operations
NEST: 'NEST'; UNNEST: 'UNNEST'; FLATTEN: 'FLATTEN'; UNFLATTEN: 'UNFLATTEN';
UNWIND: 'UNWIND'; WIND: 'WIND';

// Simple operations
COPY_PROPERTY: 'COPY_PROPERTY'; COPY_ENTITY: 'COPY_ENTITY'; MOVE_PROPERTY: 'MOVE_PROPERTY'; MERGE: 'MERGE'; SPLIT: 'SPLIT';
CAST_PROPERTY: 'CAST_PROPERTY'; CAST_CONSTRAINT: 'CAST_CONSTRAINT'; CAST_ENTITY: 'CAST_ENTITY'; RECARD: 'RECARD';
TRANSFORM: 'TRANSFORM'; RELATIONSHIP: 'RELATIONSHIP'; BETWEEN: 'BETWEEN';

// ADD operations - specific keywords
ADD_PROPERTY: 'ADD_PROPERTY';
ADD_EMBEDDED: 'ADD_EMBEDDED';
ADD_ENTITY: 'ADD_ENTITY';
ADD_PRIMARY_KEY: 'ADD_PRIMARY_KEY';
ADD_FOREIGN_KEY: 'ADD_FOREIGN_KEY';
ADD_UNIQUE_KEY: 'ADD_UNIQUE_KEY';
ADD_PARTITION_KEY: 'ADD_PARTITION_KEY';
ADD_CLUSTERING_KEY: 'ADD_CLUSTERING_KEY';
ADD_LABEL: 'ADD_LABEL';

// DELETE operations - specific keywords
DELETE_PROPERTY: 'DELETE_PROPERTY';
DELETE_EMBEDDED: 'DELETE_EMBEDDED';
DELETE_ENTITY: 'DELETE_ENTITY';
DELETE_PRIMARY_KEY: 'DELETE_PRIMARY_KEY';
DELETE_FOREIGN_KEY: 'DELETE_FOREIGN_KEY';
DELETE_UNIQUE_KEY: 'DELETE_UNIQUE_KEY';
DELETE_PARTITION_KEY: 'DELETE_PARTITION_KEY';
DELETE_CLUSTERING_KEY: 'DELETE_CLUSTERING_KEY';
DELETE_LABEL: 'DELETE_LABEL';

// RENAME operations - specific keywords
RENAME_PROPERTY: 'RENAME_PROPERTY';
RENAME_ENTITY: 'RENAME_ENTITY';


// Shared keywords
RENAME: 'RENAME';

// Structural keywords
STRUCTURE: 'STRUCTURE';

// Feature types
PROPERTY_TOKEN: 'PROPERTY'; EMBEDDED: 'EMBEDDED';
ENTITY: 'ENTITY'; VALUE: 'VALUE';
LABEL: 'LABEL';

// Entity/Variation clauses
PROPERTIES: 'PROPERTIES';

// Key types
PRIMARY: 'PRIMARY'; UNIQUE: 'UNIQUE'; FOREIGN: 'FOREIGN';
PARTITION: 'PARTITION'; CLUSTERING: 'CLUSTERING';
NODE: 'NODE'; DOCUMENT_ID: 'DOCUMENT_ID';
REFERENCE: 'REFERENCE'; REFERENCES: 'REFERENCES'; COLUMNS: 'COLUMNS';

// Cardinality
CARDINALITY: 'CARDINALITY';
ONE_TO_ONE: 'ONE_TO_ONE'; ONE_TO_MANY: 'ONE_TO_MANY';
ZERO_TO_ONE: 'ZERO_TO_ONE'; ZERO_TO_MANY: 'ZERO_TO_MANY';

// Data types
STRING: 'String'; TEXT: 'Text'; INT: 'Int'; INTEGER: 'Integer'; LONG: 'Long';
DOUBLE: 'Double'; FLOAT: 'Float'; DECIMAL: 'Decimal'; BOOLEAN: 'Boolean';
DATE: 'Date'; DATETIME: 'DateTime'; TIMESTAMP: 'Timestamp'; UUID: 'UUID'; BINARY: 'Binary';
TYPE: 'TYPE'; DEFAULT: 'DEFAULT'; SERIAL: 'SERIAL'; PREFIX: 'PREFIX';

// Constraints
NOT_NULL: 'NOT NULL';

// Literals
TRUE: 'true' | 'TRUE'; FALSE: 'false' | 'FALSE'; NULL: 'null' | 'NULL';

// Symbols
COLON: ':'; SEMICOLON: ';'; COMMA: ','; DOT: '.'; LPAREN: '('; RPAREN: ')'; LBRACKET: '['; RBRACKET: ']';
LBRACE: '{'; RBRACE: '}';
EQUALS: '=';

// ----------------------------------------------------------------------------
// PATTERNS
// ----------------------------------------------------------------------------
VERSION_NUMBER: [0-9]+ '.' [0-9]+ ('.' [0-9]+)?;
INTEGER_LITERAL: [0-9]+;
DECIMAL_LITERAL: [0-9]+ '.' [0-9]+;
STRING_LITERAL: '\'' (~['\r\n] | '\'\'')* '\'' | '"' (~["\r\n] | '""')* '"';
IDENTIFIER: [a-zA-Z_][a-zA-Z0-9_]*;

// ----------------------------------------------------------------------------
// SKIP - Whitespace and comments
// ----------------------------------------------------------------------------
LINE_COMMENT: '--' ~[\r\n]* -> skip;
BLOCK_COMMENT: '/*' .*? '*/' -> skip;
WS: [ \t\r\n]+ -> skip;
