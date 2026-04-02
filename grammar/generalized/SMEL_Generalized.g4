/*
 * SMEL_Generalized - Schema Migration & Evolution Language (Generalized Operations Version)
 * A domain-specific language for database schema migration
 *
 * This version uses generalized, parameterized operations.
 * Operations use a base keyword with parameters (e.g., ADD PROPERTY, ADD CONSTRAINT)
 *
 * Comparison: This is the "Generalized" version. See SMEL_Specific.g4
 * for the "Specific" version that uses independent keywords for each operation.
 *
 * Supported database models: RELATIONAL, DOCUMENT, GRAPH, COLUMNAR
 * Design: from André Conrad
 *
 * Example SMEL script:
 *   MIGRATION person_migration:1.0
 *   FROM DOCUMENT TO RELATIONAL
 *   USING person_schema:1.0
 *
 *   -- Extract nested object to table
 *   FLATTEN person.address AS address
 *   ADD PRIMARY KEY address_id TO address
 *   ADD FOREIGN KEY person_id TO address REFERENCES person(id)
 *
 *   -- Expand array to table
 *   UNWIND person.tags[] INTO person_tag
 *   ADD PRIMARY KEY id TO person_tag
 *   ADD FOREIGN KEY person_id TO person_tag REFERENCES person(id)
 */
grammar SMEL_Generalized;

// ============================================================================
// PARSER RULES
// ============================================================================

// Entry point: migration script = header + operations
migration: header operation* EOF;
header: migrationDecl fromToDecl usingDecl;                         // MIGRATION name:ver FROM type TO type USING schema:ver
migrationDecl: MIGRATION identifier COLON version;                  // MIGRATION payment_migration:1.0
fromToDecl: FROM databaseType TO databaseType;                      // FROM RELATIONAL TO Document
usingDecl: USING identifier COLON version;                          // USING iso20022_schema:1.0
databaseType: RELATIONAL | DOCUMENT | GRAPH | COLUMNAR;             // Abstract database model types
version: VERSION_NUMBER | INTEGER_LITERAL;                          // 1 | 1.0 | 1.0.0

// ============================================================================
// OPERATIONS - Generalized operations with parameters
// ============================================================================
// Structure:  NEST, UNNEST, FLATTEN, UNWIND, EXTRACT
// Movement:   COPY, MOVE, MERGE, SPLIT
// Type:       CAST
// CRUD:       ADD, DELETE, RENAME

operation: nest_gen | unnest_gen | flatten_gen | unflatten_gen | unwind_gen | wind_gen
         | copy_gen | move_gen | merge_gen | split_gen | cast_gen | recard_gen
         | transform_gen
         | add_gen | delete_gen | rename_gen;

// ============================================================================
// ADD - Generalized ADD operation with type parameter
// ============================================================================
// Supports adding:
//   - PROPERTY:    Add new property to entity
//   - CONSTRAINT:  Add foreign key constraint
//   - EMBEDDED:    Add embedded object relationship (MongoDB style)
//   - ENTITY:      Add new entity/table
//   - KEY:         Add primary/unique/foreign key constraint
//
// Example: ADD PROPERTY email TO Customer WITH TYPE String NOT NULL
// Example: ADD PRIMARY KEY id TO Customer
// Example: ADD ENTITY CONTAINS FROM orders TO products WITH PROPERTIES (unitPrice Decimal)

add_gen: ADD (propertyAdd | constraintAdd | embeddedAdd | entityAdd
        | keyAdd | labelAdd);

// Add property: ADD PROPERTY email TO Customer WITH TYPE String NOT NULL
propertyAdd: PROPERTY identifier (TO identifier)? propertyClause*;
propertyClause: withTypeClause | withDefaultClause | notNullClause;
withTypeClause: WITH TYPE dataType;
withDefaultClause: WITH DEFAULT literal;
notNullClause: NOT_NULL;

// Add constraint: ADD CONSTRAINT entity.field REFERENCES target_table(target_column)
// SQL-style foreign key constraint syntax with explicit entity.field
// Example: ADD CONSTRAINT address.person_id REFERENCES person(person_id)
// Example: ADD CONSTRAINT order.customer_id REFERENCES customer(id) WITH CARDINALITY ONE_TO_MANY
constraintAdd: CONSTRAINT qualifiedName REFERENCES identifier LPAREN identifier RPAREN constraintClause*;
constraintClause: withCardinalityClause | usingKeyClause | whereClause;

// Add embedded: ADD EMBEDDED address TO Customer WITH CARDINALITY ONE_TO_ONE
embeddedAdd: EMBEDDED identifier TO identifier embeddedClause*;
embeddedClause: withCardinalityClause | withStructureClause;
withStructureClause: WITH STRUCTURE LPAREN identifierList RPAREN;

// Add entity: ADD ENTITY Product WITH PROPERTIES (id String, name String)
// Add edge:   ADD ENTITY CONTAINS FROM orders TO products WITH PROPERTIES (unitPrice Decimal)
// Add edge:   ADD ENTITY REPORTS_TO FROM employees TO employees WITH CARDINALITY ONE_TO_MANY
entityAdd: ENTITY identifier (FROM identifier TO identifier)? (WITH CARDINALITY cardinalityType)? entityClause*;
entityClause: withPropertiesClause | withKeyClause;
withKeyClause: WITH KEY identifier;

// Add key: ADD KEY entity.field AS String (explicit entity.field syntax)
// Or full form: ADD PRIMARY KEY id TO Customer WITH TYPE UUID (legacy TO syntax)
// Example: ADD KEY address.address_id AS String  (new explicit syntax)
// Example: ADD PRIMARY KEY (id1, id2) TO Customer (composite key)
keyAdd: keyType? KEY keyColumns (AS dataType)? (TO identifier)? keyClause*;
// Note: keyType is optional, defaults to PRIMARY KEY when omitted
// Note: AS dataType is a simplified alternative to WITH TYPE dataType
// Note: keyColumns now supports qualifiedName (entity.field) for explicit entity specification

// Key columns - qualifiedName (entity.field) or parenthesized list for composite keys
keyColumns: qualifiedName | LPAREN identifierList RPAREN;

// Add label (Graph): ADD LABEL Employee TO Person
labelAdd: LABEL identifier TO identifier;

// ============================================================================
// DELETE - Generalized DELETE operation with type parameter
// ============================================================================
// Supports deleting:
//   - PROPERTY:    Remove property from entity
//   - CONSTRAINT:  Remove foreign key constraint
//   - EMBEDDED:    Remove embedded object relationship
//   - ENTITY:      Remove entire entity/table
//   - KEY:         Remove key constraints (PRIMARY, FOREIGN, UNIQUE, PARTITION, CLUSTERING)
//   - LABEL:       Remove label
//
// Example: DELETE PROPERTY Customer.email
// Example: DELETE PRIMARY KEY id FROM Customer

delete_gen: DELETE (propertyDelete | constraintDelete | embeddedDelete | entityDelete
          | keyDelete | labelDelete);

// Delete property: DELETE PROPERTY Customer.email
propertyDelete: PROPERTY qualifiedName;

// Delete constraint: DELETE CONSTRAINT Customer.order_id
constraintDelete: CONSTRAINT qualifiedName;

// Delete embedded: DELETE EMBEDDED Customer.address
embeddedDelete: EMBEDDED qualifiedName;

// Delete entity: DELETE ENTITY Customer
entityDelete: ENTITY identifier;

// Delete key: DELETE PRIMARY KEY id FROM Customer
keyDelete: keyType KEY keyColumns (FROM identifier)?;

// Delete label: DELETE LABEL Employee FROM Person
labelDelete: LABEL identifier FROM identifier;

// ============================================================================
// RENAME - Generalized RENAME operation with type parameter
// ============================================================================
// Supports renaming:
//   - Property: RENAME PROPERTY oldName TO newName IN Entity
//   - Entity:   RENAME ENTITY OldName TO NewName
//
// Example: RENAME PROPERTY email TO contact_email IN Customer

rename_gen: RENAME (propertyRename | entityRename);

// Rename property: RENAME PROPERTY oldName TO newName IN Entity
propertyRename: PROPERTY identifier TO identifier (IN identifier)?;

// Rename entity: RENAME ENTITY OldName TO NewName
entityRename: ENTITY identifier TO identifier;

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
keyClause: referencesClause | withColumnsClause | withTypeClause;
referencesClause: REFERENCES identifier LPAREN identifierList RPAREN;
withColumnsClause: WITH COLUMNS LPAREN identifierList RPAREN;
identifierList: identifier (COMMA identifier)*;

// ============================================================================
// STRUCTURE OPERATIONS
// ============================================================================

// FLATTEN - Flatten nested object fields into parent table (reduce depth by 1)
// Reference: André Conrad - "Die Operation FLATTEN erstellt aus dem Objekt in der Spalte
//            jeweils eine Spalte für jedes Attribut dieses Objekts"
// Example: FLATTEN person.name
//   Before: person { name: { vorname, nachname }, age }
//   After:  person { name_vorname, name_nachname, age }
flatten_gen: FLATTEN qualifiedName;

// UNFLATTEN - Combine flat fields into nested object (reverse of FLATTEN)
// Example: UNFLATTEN person:vorname, nachname AS name
//   Before: person { vorname, nachname, age }
//   After:  person { name: { vorname, nachname }, age }
unflatten_gen: UNFLATTEN identifier COLON identifierList AS identifier;

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
// Note: Use separate ADD KEY, ADD CONSTRAINT for constraints
unnest_gen: UNNEST qualifiedName COLON unnestFieldList AS identifier (WITH unnestCarryList)?;

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
// Note: Use separate ADD KEY, ADD CONSTRAINT, RENAME PROPERTY for constraints
unwind_gen: UNWIND qualifiedName (INTO identifier)?;

// WIND - Convert scalar property back to array (reverse of UNWIND)
// Syntax: WIND person_tag.tags
// Cross-entity movement is handled by MERGE, not WIND.
wind_gen: WIND qualifiedName;

// NEST - Merge separate table into embedded document (PostgreSQL -> MongoDB)
// Example: NEST address:street,city IN person.address WHERE address.person_id = person.person_id
// Example with deletion: NEST address:street,city IN person.address WHERE address.person_id = person.person_id WITH DELETION
//   - 'address' is source entity
//   - ':street,city' are properties to embed
//   - 'IN person.address' specifies target (person entity, address field)
//   - WHERE clause specifies join condition
//   - WITH DELETION optionally removes source entity after embedding
nest_gen: NEST identifier COLON unnestFieldList IN qualifiedName WHERE condition (WITH DELETION)?;

// ============================================================================
// SIMPLE OPERATIONS
// ============================================================================

// COPY: Duplicate a property or entity
// Example: COPY PROPERTY email FROM person TO employee
// Example: COPY ENTITY person AS employee
// Example: COPY ENTITY works_at AS employed_at FROM person TO company  (copy EDGE with explicit endpoints)
copy_gen: COPY (entityCopy | propertyCopy);
propertyCopy: PROPERTY identifier FROM identifier TO identifier;
entityCopy: ENTITY identifier AS identifier (FROM identifier TO identifier)?;

// MOVE: Relocate a property to another entity (removes original)
// Example: MOVE PROPERTY email FROM person TO employee
move_gen: MOVE PROPERTY identifier FROM identifier TO identifier;

// MERGE: Combine two entities into one new entity
// Example: MERGE A, B INTO C AS alias
merge_gen: MERGE identifier COMMA identifier INTO identifier (AS identifier)?;

// SPLIT: Divide one entity into multiple separate entities (vertical partitioning)
// Reference: André Conrad - "SPLIT Person into Person:id, firstname, lastname AND knows:id, knows"
// Example: SPLIT person INTO person:person_id, vorname, nachname, age; person_tag:person_id, tags
//   Before: person { person_id, vorname, nachname, age, tags[] }
//   After:  person { person_id, vorname, nachname, age }
//          person_tag { person_id, tags[] }
// Note: Fields can be duplicated across parts (e.g., person_id in both parts)
split_gen: SPLIT identifier INTO splitPartGen (SEMICOLON splitPartGen)+;
splitPartGen: identifier COLON identifierList;

// CAST: Change the data type of a property, the type of a constraint, or the kind of an entity
// Example: CAST PROPERTY Entity.field TO Integer
// Example: CAST CONSTRAINT Entity.field TO UNIQUE KEY
// Example: CAST ENTITY orders TO DOCUMENT
cast_gen: CAST (constraintCast | entityCast | propertyCast);
propertyCast: PROPERTY qualifiedName TO dataType;
constraintCast: CONSTRAINT qualifiedName TO constraintKeyType;
entityCast: ENTITY identifier TO databaseType;

// RECARD: Change the multiplicity/cardinality of a reference
// Example: RECARD person.address_id TO ONE_TO_MANY
recard_gen: RECARD qualifiedName TO cardinalityType;

// TRANSFORM: Transform entity between node and relationship (Graph database)
// Reference: Hausler et al. - "transform a node with its features into a relationship" / vice versa
// Example: TRANSFORM works_at INTO RELATIONSHIP FROM person TO company
// Example: TRANSFORM works_at INTO RELATIONSHIP FROM person TO company WITH CARDINALITY ZERO_TO_MANY
// Example: TRANSFORM works_at INTO ENTITY
transform_gen: TRANSFORM identifier INTO transformTarget;
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

// Entity clauses (for ADD ENTITY)
// WITH PROPERTIES (name String, age Integer) - each property has name and type
withPropertiesClause: WITH PROPERTIES LPAREN propertyDefList RPAREN;
propertyDefList: propertyDef (COMMA propertyDef)*;
propertyDef: identifier dataType;

// ============================================================================
// COMMON TYPES - Shared type definitions
// ============================================================================

// Cardinality notation
cardinalityType: ONE_TO_ONE | ONE_TO_MANY | ZERO_TO_ONE | ZERO_TO_MANY;

// Constraint key type (for CAST CONSTRAINT)
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
// KEYWORDS - Reserved words in SMEL_Generalized
// ----------------------------------------------------------------------------
MIGRATION: 'MIGRATION'; FROM: 'FROM'; TO: 'TO'; USING: 'USING'; AS: 'AS';
INTO: 'INTO'; WITH: 'WITH'; WHERE: 'WHERE'; IN: 'IN'; KEY: 'KEY'; AND: 'AND'; DELETION: 'DELETION';
ON: 'ON';

// Database model types
RELATIONAL: 'RELATIONAL'; DOCUMENT: 'DOCUMENT'; GRAPH: 'GRAPH'; COLUMNAR: 'COLUMNAR';

// Generalized operations (no suffix)
NEST: 'NEST'; UNNEST: 'UNNEST'; FLATTEN: 'FLATTEN'; UNFLATTEN: 'UNFLATTEN';
UNWIND: 'UNWIND'; WIND: 'WIND';
ADD: 'ADD'; DELETE: 'DELETE'; RENAME: 'RENAME';
COPY: 'COPY'; MOVE: 'MOVE'; MERGE: 'MERGE'; SPLIT: 'SPLIT';
CAST: 'CAST'; RECARD: 'RECARD'; TRANSFORM: 'TRANSFORM';
RELATIONSHIP: 'RELATIONSHIP'; BETWEEN: 'BETWEEN';

// Type parameters for generalized operations
PROPERTY: 'PROPERTY'; CONSTRAINT: 'CONSTRAINT'; EMBEDDED: 'EMBEDDED'; ENTITY: 'ENTITY';
LABEL: 'LABEL';

// Entity/Variation clauses
PROPERTIES: 'PROPERTIES';

// Key types
PRIMARY: 'PRIMARY'; UNIQUE: 'UNIQUE'; FOREIGN: 'FOREIGN';
PARTITION: 'PARTITION'; CLUSTERING: 'CLUSTERING';
NODE: 'NODE'; DOCUMENT_ID: 'DOCUMENT_ID';
REFERENCE: 'REFERENCE'; REFERENCES: 'REFERENCES'; COLUMNS: 'COLUMNS';

// Structural keywords
STRUCTURE: 'STRUCTURE';

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
