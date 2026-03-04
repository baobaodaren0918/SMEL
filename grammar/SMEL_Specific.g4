/*
 * SMEL_Specific - Schema Migration & Evolution Language (Specific Operations Version)
 * A domain-specific language for database schema migration
 *
 * This version uses specific, independent keywords for each operation.
 * Each operation has its own dedicated keyword (e.g., ADD_ATTRIBUTE, ADD_CONSTRAINT)
 *
 * Comparison: This is the "Specific" version. See SMEL_Pauschalisiert.g4 for the
 * "Generalized" version that uses parameterized operations (e.g., ADD_PS ATTRIBUTE).
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
 *   ADD_PRIMARY_KEY address_id TO address
 *   ADD_FOREIGN_KEY person_id TO address REFERENCES person(id)
 *
 *   -- Expand array to table
 *   UNWIND person.tags[] INTO person_tag
 *   ADD_PRIMARY_KEY id TO person_tag
 *   ADD_FOREIGN_KEY person_id TO person_tag REFERENCES person(id)
 */
grammar SMEL_Specific;

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
// OPERATIONS - Each operation is a separate, specific keyword
// ============================================================================
// Structure:  NEST, UNNEST, FLATTEN, UNWIND, EXTRACT
// Movement:   COPY, MOVE, MERGE, SPLIT
// Type:       CAST
// CRUD:       ADD_*, DELETE_*, REMOVE_*, RENAME_*

operation: add_attribute | add_constraint | add_embedded | add_entity
         | add_primary_key | add_foreign_key | add_unique_key
         | add_partition_key | add_clustering_key
         | add_label
         | delete_attribute | delete_constraint | delete_embedded | delete_entity
         | delete_primary_key | delete_foreign_key | delete_unique_key
         | delete_partition_key | delete_clustering_key
         | delete_label
         | remove_unique_key | remove_foreign_key
         | remove_label
         | rename_attribute | rename_entity
         | flatten | unflatten | unwind | wind | nest | unnest
         | copy_attribute | copy_entity | move_attribute | merge | split | cast_attribute | cast_constraint | recard
         | transform
         | add_reltype | delete_reltype | rename_reltype
;

// ============================================================================
// ADD OPERATIONS - Specific keywords for each type
// ============================================================================

// ADD_ATTRIBUTE: Add new attribute to entity
// Example: ADD_ATTRIBUTE email TO Customer WITH TYPE String NOT NULL
add_attribute: ADD_ATTRIBUTE identifier (TO identifier)? attributeClause*;
attributeClause: withTypeClause | withDefaultClause | notNullClause;
withTypeClause: WITH TYPE dataType;
withDefaultClause: WITH DEFAULT literal;
notNullClause: NOT_NULL;

// ADD_CONSTRAINT: Add foreign key constraint (SQL-style) with explicit entity.field
// Example: ADD_CONSTRAINT address.person_id REFERENCES person(person_id)
// Example: ADD_CONSTRAINT order.customer_id REFERENCES customer(id) WITH CARDINALITY ONE_TO_MANY
add_constraint: ADD_CONSTRAINT qualifiedName REFERENCES identifier LPAREN identifier RPAREN constraintClause*;
constraintClause: withCardinalityClause | usingKeyClause | whereClause;

// ADD_EMBEDDED: Add embedded object relationship (MongoDB style)
// Example: ADD_EMBEDDED address TO Customer WITH CARDINALITY ONE_TO_ONE
add_embedded: ADD_EMBEDDED identifier TO identifier embeddedClause*;
embeddedClause: withCardinalityClause | withStructureClause;
withStructureClause: WITH STRUCTURE LPAREN identifierList RPAREN;

// ADD_ENTITY: Add new entity/table
// Example: ADD_ENTITY Product WITH ATTRIBUTES (id, name)
add_entity: ADD_ENTITY identifier entityClause*;
entityClause: withAttributesClause | withKeyClause;
withKeyClause: WITH KEY identifier;

// ADD_PRIMARY_KEY: Add primary key constraint
// Example: ADD_PRIMARY_KEY address.address_id AS String  (new explicit entity.field syntax)
// Example: ADD_PRIMARY_KEY (id1, id2) TO Customer  (composite key)
// Example: ADD_PRIMARY_KEY id TO Customer WITH TYPE UUID (legacy TO syntax)
// Note: AS dataType is a simplified alternative to WITH TYPE dataType
// Note: keyColumns now supports qualifiedName (entity.field) for explicit entity specification
add_primary_key: ADD_PRIMARY_KEY keyColumns (AS dataType)? (TO identifier)? keyClause*;

// ADD_FOREIGN_KEY: Add foreign key constraint
// Example: ADD_FOREIGN_KEY customer_id TO Order REFERENCES Customer(id)
add_foreign_key: ADD_FOREIGN_KEY keyColumns (TO identifier)? keyClause*;

// ADD_UNIQUE_KEY: Add unique constraint
// Example: ADD_UNIQUE_KEY email TO Customer
add_unique_key: ADD_UNIQUE_KEY keyColumns (TO identifier)? keyClause*;

// ADD_PARTITION_KEY: Add partition key (Cassandra - columnar)
// Example: ADD_PARTITION_KEY user_id TO UserActivity
add_partition_key: ADD_PARTITION_KEY keyColumns (TO identifier)? keyClause*;

// ADD_CLUSTERING_KEY: Add clustering key (Cassandra - columnar)
// Example: ADD_CLUSTERING_KEY timestamp TO UserActivity
add_clustering_key: ADD_CLUSTERING_KEY keyColumns (TO identifier)? keyClause*;

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

// DELETE_ATTRIBUTE: Remove attribute from entity
// Example: DELETE_ATTRIBUTE Customer.email
delete_attribute: DELETE_ATTRIBUTE qualifiedName;

// DELETE_CONSTRAINT: Remove foreign key constraint
// Example: DELETE_CONSTRAINT Customer.order_id
delete_constraint: DELETE_CONSTRAINT qualifiedName;

// DELETE_EMBEDDED: Remove embedded object relationship
// Example: DELETE_EMBEDDED Customer.address
delete_embedded: DELETE_EMBEDDED qualifiedName;

// DELETE_ENTITY: Remove entire entity/table
// Example: DELETE_ENTITY Customer
delete_entity: DELETE_ENTITY identifier;

// DELETE_PRIMARY_KEY: Delete primary key constraint
// Example: DELETE_PRIMARY_KEY id FROM Customer
delete_primary_key: DELETE_PRIMARY_KEY keyColumns (FROM identifier)?;

// DELETE_FOREIGN_KEY: Delete foreign key constraint
// Example: DELETE_FOREIGN_KEY customer_id FROM Order
delete_foreign_key: DELETE_FOREIGN_KEY keyColumns (FROM identifier)?;

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
// REMOVE OPERATIONS - Non-destructive constraint removal
// ============================================================================
// These operations remove constraints/metadata while preserving structure
// Useful for schema evolution: constraint relaxation, etc.

// REMOVE_UNIQUE_KEY: Remove unique constraint (constraint relaxation)
// Example: REMOVE_UNIQUE_KEY email FROM Customer
remove_unique_key: REMOVE_UNIQUE_KEY keyColumns FROM identifier;

// REMOVE_FOREIGN_KEY: Remove foreign key constraint (temporarily disable FK)
// Example: REMOVE_FOREIGN_KEY customer_id FROM Order
remove_foreign_key: REMOVE_FOREIGN_KEY keyColumns FROM identifier;

// REMOVE_LABEL: Remove label from node (graph reclassification)
// Example: REMOVE_LABEL Manager FROM Person
remove_label: REMOVE_LABEL identifier FROM identifier;

// ============================================================================
// RENAME OPERATIONS - Specific keywords for each type
// ============================================================================

// RENAME_ATTRIBUTE: Rename attribute within an entity
// Example: RENAME_ATTRIBUTE email TO contact_email IN Customer
rename_attribute: RENAME_ATTRIBUTE identifier TO identifier (IN identifier)?;

// RENAME_ENTITY: Rename entity/table
// Example: RENAME_ENTITY Customer TO Client
rename_entity: RENAME_ENTITY identifier TO identifier;

// ============================================================================
// RELTYPE OPERATIONS - Relationship type management (Graph database)
// ============================================================================

// ADD_RELTYPE: Add new relationship type
// Example: ADD_RELTYPE works_at BETWEEN person AND company
add_reltype: ADD_RELTYPE identifier BETWEEN identifier AND identifier;

// DELETE_RELTYPE: Remove relationship type
// Example: DELETE_RELTYPE works_at
delete_reltype: DELETE_RELTYPE identifier;

// RENAME_RELTYPE: Rename relationship type
// Example: RENAME_RELTYPE works_at TO employed_at
rename_reltype: RENAME_RELTYPE identifier TO identifier;

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
//   - 'street,city' are attributes to extract
//   - WITH clause: copy fields from source to new table (can carry multiple fields)
//   - WITH is optional, for cases where no parent fields need to be copied
//   Before: person { person_id, address: { street, city } }
//   After:  person { person_id }
//           address { person_id, street, city }
// Note: Use separate ADD_PRIMARY_KEY, ADD_CONSTRAINT for constraints
unnest: UNNEST qualifiedName COLON unnestFieldList AS identifier (WITH unnestCarryList)?;

// Carry list for UNNEST: fields to copy from source to new table
unnestCarryList: unnestCarryField (COMMA unnestCarryField)*;
unnestCarryField: qualifiedName TO qualifiedName;

// Field list for UNNEST: supports both attributes and nested objects (recursive)
// - identifier: regular attribute (e.g., position, name, street, city)
// - identifier{...}: nested object with its contents (e.g., company{name, address{street, city}})
unnestFieldList: unnestField (COMMA unnestField)*;
unnestField: identifier                                    # AttributeField
           | identifier LBRACE unnestFieldList RBRACE      # NestedField
           ;

// UNWIND - Expand array field into multiple rows
// Reference: André Conrad - array expansion operation
// Supports two modes:
//   1. Expand in place: UNWIND person_tag.tags (expands array within existing table)
//   2. Create new table: UNWIND person.tags[] INTO person_tag (legacy, creates new table)
// Note: Use separate ADD_PRIMARY_KEY, ADD_FOREIGN_KEY, RENAME_ATTRIBUTE for constraints
unwind: UNWIND qualifiedName (INTO identifier)?;

// WIND - Convert scalar attribute back to array (reverse of UNWIND)
// Syntax: WIND person_tag.tags
// Cross-entity movement is handled by MERGE, not WIND.
wind: WIND qualifiedName;

// NEST - Merge separate table into embedded document (PostgreSQL -> MongoDB)
// Example: NEST address:street,city IN person.address WHERE address.person_id = person.person_id
// Example with deletion: NEST address:street,city IN person.address WHERE address.person_id = person.person_id WITH DELETION
//   - 'address' is source entity
//   - ':street,city' are attributes to embed
//   - 'IN person.address' specifies target (person entity, address field)
//   - WHERE clause specifies join condition
//   - WITH DELETION optionally removes source entity after embedding
nest: NEST identifier COLON unnestFieldList IN qualifiedName WHERE condition (WITH DELETION)?;

// ============================================================================
// SIMPLE OPERATIONS
// ============================================================================

// COPY_ATTRIBUTE: Duplicate an attribute to another location (keeps original)
// Example: COPY_ATTRIBUTE person.name TO person.first_name
copy_attribute: COPY_ATTRIBUTE qualifiedName TO qualifiedName;

// COPY_ENTITY: Duplicate an entire entity with all its structure (attributes, keys, constraints)
// Reference: PRISM "COPY TABLE R INTO S", CoDEL "Addtable(S, R)"
// Example: COPY_ENTITY person AS employee
copy_entity: COPY_ENTITY identifier AS identifier;

// MOVE_ATTRIBUTE: Relocate an attribute to another location (removes original)
// Example: MOVE_ATTRIBUTE person.name TO other.name
move_attribute: MOVE_ATTRIBUTE qualifiedName TO qualifiedName;

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

// CAST_ATTRIBUTE: Change the data type of an attribute
// Example: CAST_ATTRIBUTE Entity.field TO Integer
cast_attribute: CAST_ATTRIBUTE qualifiedName TO dataType;

// CAST_CONSTRAINT: Change the type of a constraint
// Reference: Orion "Cast Reference" - change the type of a constraint
// Example: CAST_CONSTRAINT person.email TO UNIQUE KEY
// Example: CAST_CONSTRAINT person.city TO PARTITION KEY
cast_constraint: CAST_CONSTRAINT qualifiedName TO constraintKeyType;

// RECARD: Change the multiplicity/cardinality of a reference
// Reference: Orion "Mult Reference" - change the multiplicity of a reference
// Example: RECARD person.address_id TO ONE_TO_MANY
recard: RECARD qualifiedName TO cardinalityType;

// TRANSFORM: Transform entity between node and relationship (Graph database)
// Reference: Hausler et al. - "transform a node with its features into a relationship" / vice versa
// Example: TRANSFORM works_at TO RELATIONSHIP BETWEEN person AND company
// Example: TRANSFORM works_at TO ENTITY
transform: TRANSFORM identifier TO transformTarget;
transformTarget: RELATIONSHIP BETWEEN identifier AND identifier    # TransformToRelationship
              | ENTITY                                             # TransformToEntity
              ;

// ============================================================================
// SHARED CLAUSES - Reusable clause definitions
// ============================================================================

// Cardinality (relationship multiplicity)
withCardinalityClause: WITH CARDINALITY cardinalityType;
usingKeyClause: USING KEY identifier;
whereClause: WHERE condition;

// Entity clauses (for ADD_ENTITY)
withAttributesClause: WITH ATTRIBUTES LPAREN identifierList RPAREN;

// Identifier list
identifierList: identifier (COMMA identifier)*;

// ============================================================================
// COMMON TYPES - Shared type definitions
// ============================================================================

// Cardinality notation
cardinalityType: ONE_TO_ONE | ONE_TO_MANY | ZERO_TO_ONE | ZERO_TO_MANY;

// Constraint key type (for CAST_CONSTRAINT)
constraintKeyType: PRIMARY KEY | UNIQUE KEY | PARTITION KEY | CLUSTERING KEY;

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
// KEYWORDS - Reserved words in SMEL_Specific
// ----------------------------------------------------------------------------
MIGRATION: 'MIGRATION'; FROM: 'FROM'; TO: 'TO'; USING: 'USING'; AS: 'AS';
INTO: 'INTO'; WITH: 'WITH'; WHERE: 'WHERE'; IN: 'IN'; KEY: 'KEY'; AND: 'AND'; DELETION: 'DELETION';
ON: 'ON';

// Database model types
RELATIONAL: 'RELATIONAL'; DOCUMENT: 'DOCUMENT'; GRAPH: 'GRAPH'; COLUMNAR: 'COLUMNAR';

// Structure operations
NEST: 'NEST'; UNNEST: 'UNNEST'; FLATTEN: 'FLATTEN'; UNFLATTEN: 'UNFLATTEN';
UNWIND: 'UNWIND'; WIND: 'WIND';

// Simple operations
COPY_ATTRIBUTE: 'COPY_ATTRIBUTE'; COPY_ENTITY: 'COPY_ENTITY'; MOVE_ATTRIBUTE: 'MOVE_ATTRIBUTE'; MERGE: 'MERGE'; SPLIT: 'SPLIT';
CAST_ATTRIBUTE: 'CAST_ATTRIBUTE'; CAST_CONSTRAINT: 'CAST_CONSTRAINT'; RECARD: 'RECARD';
TRANSFORM: 'TRANSFORM'; RELATIONSHIP: 'RELATIONSHIP'; BETWEEN: 'BETWEEN';

// ADD operations - specific keywords
ADD_ATTRIBUTE: 'ADD_ATTRIBUTE';
ADD_CONSTRAINT: 'ADD_CONSTRAINT';
ADD_EMBEDDED: 'ADD_EMBEDDED';
ADD_ENTITY: 'ADD_ENTITY';
ADD_PRIMARY_KEY: 'ADD_PRIMARY_KEY';
ADD_FOREIGN_KEY: 'ADD_FOREIGN_KEY';
ADD_UNIQUE_KEY: 'ADD_UNIQUE_KEY';
ADD_PARTITION_KEY: 'ADD_PARTITION_KEY';
ADD_CLUSTERING_KEY: 'ADD_CLUSTERING_KEY';
ADD_LABEL: 'ADD_LABEL';

// DELETE operations - specific keywords
DELETE_ATTRIBUTE: 'DELETE_ATTRIBUTE';
DELETE_CONSTRAINT: 'DELETE_CONSTRAINT';
DELETE_EMBEDDED: 'DELETE_EMBEDDED';
DELETE_ENTITY: 'DELETE_ENTITY';
DELETE_PRIMARY_KEY: 'DELETE_PRIMARY_KEY';
DELETE_FOREIGN_KEY: 'DELETE_FOREIGN_KEY';
DELETE_UNIQUE_KEY: 'DELETE_UNIQUE_KEY';
DELETE_PARTITION_KEY: 'DELETE_PARTITION_KEY';
DELETE_CLUSTERING_KEY: 'DELETE_CLUSTERING_KEY';
DELETE_LABEL: 'DELETE_LABEL';

// REMOVE operations - specific keywords (non-destructive constraint removal)
REMOVE_UNIQUE_KEY: 'REMOVE_UNIQUE_KEY';
REMOVE_FOREIGN_KEY: 'REMOVE_FOREIGN_KEY';
REMOVE_LABEL: 'REMOVE_LABEL';

// RENAME operations - specific keywords
RENAME_ATTRIBUTE: 'RENAME_ATTRIBUTE';
RENAME_ENTITY: 'RENAME_ENTITY';

// RELTYPE operations - specific keywords (Graph database)
ADD_RELTYPE: 'ADD_RELTYPE';
DELETE_RELTYPE: 'DELETE_RELTYPE';
RENAME_RELTYPE: 'RENAME_RELTYPE';

// Shared keywords
RENAME: 'RENAME';

// Structural keywords
STRUCTURE: 'STRUCTURE';

// Feature types
ATTRIBUTE: 'ATTRIBUTE'; EMBEDDED: 'EMBEDDED';
ENTITY: 'ENTITY'; VALUE: 'VALUE';
LABEL: 'LABEL';

// Entity/Variation clauses
ATTRIBUTES: 'ATTRIBUTES';

// Key types
PRIMARY: 'PRIMARY'; UNIQUE: 'UNIQUE'; FOREIGN: 'FOREIGN';
PARTITION: 'PARTITION'; CLUSTERING: 'CLUSTERING';
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
