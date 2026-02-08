/*
 * SMEL_Specific - Schema Migration & Evolution Language (Specific Operations Version)
 * A domain-specific language for database schema migration
 *
 * This version uses specific, independent keywords for each operation.
 * Each operation has its own dedicated keyword (e.g., ADD_ATTRIBUTE, ADD_REFERENCE)
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
// Movement:   COPY, COPY_KEY, MOVE, MERGE, SPLIT
// Type:       CAST, LINKING
// CRUD:       ADD_*, DELETE_*, REMOVE_*, RENAME_*

operation: add_attribute | add_reference | add_embedded | add_entity
         | add_primary_key | add_foreign_key | add_unique_key
         | add_partition_key | add_clustering_key
         | add_variation | add_reltype | add_index | add_label
         | delete_attribute | delete_reference | delete_embedded | delete_entity
         | delete_primary_key | delete_foreign_key | delete_unique_key
         | delete_partition_key | delete_clustering_key
         | delete_variation | delete_reltype | delete_index | delete_label
         | remove_index | remove_unique_key | remove_foreign_key
         | remove_label | remove_variation
         | rename_feature | rename_entity | rename_reltype
         | flatten | unwind | nest | unnest | extract
         | copy | copy_key | move | merge | split | cast | linking
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

// ADD_REFERENCE: Add foreign key relationship (SQL-style) with explicit entity.field
// Example: ADD_REFERENCE address.person_id REFERENCES person(person_id)
// Example: ADD_REFERENCE order.customer_id REFERENCES customer(id) WITH CARDINALITY ONE_TO_MANY
add_reference: ADD_REFERENCE qualifiedName REFERENCES identifier LPAREN identifier RPAREN referenceClause*;
referenceClause: withCardinalityClause | usingKeyClause | whereClause;

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

// ADD_VARIATION: Add structural variation (U-Schema support)
// Example: ADD_VARIATION v1 TO Customer WITH ATTRIBUTES (a, b)
add_variation: ADD_VARIATION identifier TO identifier variationClause*;

// ADD_RELTYPE: Add relationship type (Graph database support)
// Example: ADD_RELTYPE ACTED_IN FROM Actor TO Movie
add_reltype: ADD_RELTYPE identifier FROM identifier TO identifier relTypeClause*;

// ADD_INDEX: Add index to table (relational/document)
// Example: ADD_INDEX idx_name ON Customer (email, name)
add_index: ADD_INDEX identifier ON identifier LPAREN identifierList RPAREN;

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

// DELETE_REFERENCE: Remove foreign key relationship
// Example: DELETE_REFERENCE Customer.order_id
delete_reference: DELETE_REFERENCE qualifiedName;

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

// DELETE_VARIATION: Delete structural variation
// Example: DELETE_VARIATION v1 FROM Customer
delete_variation: DELETE_VARIATION identifier FROM identifier;

// DELETE_RELTYPE: Delete relationship type
// Example: DELETE_RELTYPE ACTED_IN
delete_reltype: DELETE_RELTYPE identifier;

// DELETE_INDEX: Delete index
// Example: DELETE_INDEX idx_name FROM Customer
delete_index: DELETE_INDEX identifier FROM identifier;

// DELETE_LABEL: Delete label from node
// Example: DELETE_LABEL Employee FROM Person
delete_label: DELETE_LABEL identifier FROM identifier;

// ============================================================================
// REMOVE OPERATIONS - Non-destructive constraint removal
// ============================================================================
// These operations remove constraints/metadata while preserving structure
// Useful for schema evolution: index optimization, constraint relaxation, etc.

// REMOVE_INDEX: Remove index (for optimization)
// Example: REMOVE_INDEX idx_name FROM Customer
remove_index: REMOVE_INDEX identifier FROM identifier;

// REMOVE_UNIQUE_KEY: Remove unique constraint (constraint relaxation)
// Example: REMOVE_UNIQUE_KEY email FROM Customer
remove_unique_key: REMOVE_UNIQUE_KEY keyColumns FROM identifier;

// REMOVE_FOREIGN_KEY: Remove foreign key constraint (temporarily disable FK)
// Example: REMOVE_FOREIGN_KEY customer_id FROM Order
remove_foreign_key: REMOVE_FOREIGN_KEY keyColumns FROM identifier;

// REMOVE_LABEL: Remove label from node (graph reclassification)
// Example: REMOVE_LABEL Manager FROM Person
remove_label: REMOVE_LABEL identifier FROM identifier;

// REMOVE_VARIATION: Remove structural variation (simplify schema)
// Example: REMOVE_VARIATION v1 FROM Customer
remove_variation: REMOVE_VARIATION identifier FROM identifier;

// ============================================================================
// RENAME OPERATIONS - Specific keywords for each type
// ============================================================================

// RENAME_FEATURE: Rename attribute or relationship
// Example: RENAME_FEATURE email TO contact_email IN Customer
rename_feature: RENAME_FEATURE identifier TO identifier (IN identifier)?;

// RENAME_ENTITY: Rename entity/table
// Example: RENAME_ENTITY Customer TO Client
rename_entity: RENAME_ENTITY identifier TO identifier;

// RENAME_RELTYPE: Rename relationship type (Graph database)
// Example: RENAME_RELTYPE ACTED_IN TO PERFORMED_IN
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

// UNNEST - Extract nested object to separate table (normalization)
// Reference: Bianca Meier - reverse of NEST operation
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
// Note: Use separate ADD_PRIMARY_KEY, ADD_REFERENCE for constraints
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
// Note: Use separate ADD_PRIMARY_KEY, ADD_FOREIGN_KEY, RENAME_FEATURE for constraints
unwind: UNWIND qualifiedName (INTO identifier)?;

// NEST - Merge separate table into embedded document (PostgreSQL -> MongoDB)
// Reference: Bianca Meier - NEST vendor:id,name,country IN product.vendor WHERE vendor.id = product.vendorid [with Deletion]
// Example: NEST address:street,city IN person.address WHERE address.person_id = person.person_id
// Example with deletion: NEST address:street,city IN person.address WHERE address.person_id = person.person_id WITH DELETION
//   - 'address' is source entity
//   - ':street,city' are attributes to embed
//   - 'IN person.address' specifies target (person entity, address field)
//   - WHERE clause specifies join condition
//   - WITH DELETION optionally removes source entity after embedding
nest: NEST identifier COLON unnestFieldList IN qualifiedName WHERE qualifiedName EQUALS qualifiedName (WITH DELETION)?;

// EXTRACT - Extract attributes from entity to create new entity
// Example: EXTRACT (a, b, c) FROM Entity INTO NewEntity
// Note: Use separate ADD_PRIMARY_KEY, ADD_FOREIGN_KEY operations for constraints
extract: EXTRACT LPAREN identifierList RPAREN FROM identifier INTO identifier;

// ============================================================================
// SIMPLE OPERATIONS
// ============================================================================

// COPY: Duplicate an attribute to another location (keeps original)
// Example: COPY source TO target
copy: COPY qualifiedName TO qualifiedName;

// COPY_KEY: Copy primary key value to another table (optionally as foreign key)
// Example: COPY_KEY person.id TO person_tag.person_id
// Example: COPY_KEY person.id TO person_tag.person_id AS FOREIGN KEY
copy_key: COPY_KEY qualifiedName TO qualifiedName copyKeyClause?;
copyKeyClause: AS FOREIGN KEY;

// MOVE: Relocate an attribute to another location (removes original)
// Example: MOVE source TO target
move: MOVE qualifiedName TO qualifiedName;

// MERGE: Combine two entities into one new entity
// Example: MERGE A, B INTO C AS alias
merge: MERGE identifier COMMA identifier INTO identifier (AS identifier)?;

// SPLIT: Divide one entity into multiple separate entities (vertical partitioning)
// Reference: André Conrad - "SPLIT Person into Person:id, firstname, lastname AND knows:id, knows"
// Example: SPLIT person INTO person(person_id, vorname, nachname, age), person_tag(person_id, tags)
//   Before: person { person_id, vorname, nachname, age, tags[] }
//   After:  person { person_id, vorname, nachname, age }
//          person_tag { person_id, tags[] }
// Note: Fields can be duplicated across parts (e.g., person_id in both parts)
split: SPLIT identifier INTO splitPart (COMMA splitPart)+;
splitPart: identifier LPAREN identifierList RPAREN;

// CAST: Change the data type of an attribute
// Example: CAST Entity.field TO Integer
cast: CAST qualifiedName TO dataType;

// LINKING: Create a relationship link between entities
// Example: LINKING source.field TO target
linking: LINKING qualifiedName TO identifier;

// ============================================================================
// SHARED CLAUSES - Reusable clause definitions
// ============================================================================

// Cardinality (relationship multiplicity)
withCardinalityClause: WITH CARDINALITY cardinalityType;
usingKeyClause: USING KEY identifier;
whereClause: WHERE condition;

// Variation clauses (U-Schema StructuralVariation support)
variationClause: withAttributesClause | withRelationshipsClause | withCountClause;
withAttributesClause: WITH ATTRIBUTES LPAREN identifierList RPAREN;
withRelationshipsClause: WITH RELATIONSHIPS LPAREN identifierList RPAREN;
withCountClause: WITH COUNT INTEGER_LITERAL;

// RelType clauses (Graph relationship type support)
relTypeClause: withPropertiesClause | withCardinalityClause;
withPropertiesClause: WITH PROPERTIES LPAREN identifierList RPAREN;

// Identifier list
identifierList: identifier (COMMA identifier)*;

// ============================================================================
// COMMON TYPES - Shared type definitions
// ============================================================================

// Cardinality notation
cardinalityType: ONE_TO_ONE | ONE_TO_MANY | ZERO_TO_ONE | ZERO_TO_MANY;

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
COUNT: 'COUNT'; ON: 'ON';

// Database model types
RELATIONAL: 'RELATIONAL'; DOCUMENT: 'DOCUMENT'; GRAPH: 'GRAPH'; COLUMNAR: 'COLUMNAR';

// Structure operations
NEST: 'NEST'; UNNEST: 'UNNEST'; FLATTEN: 'FLATTEN'; EXTRACT: 'EXTRACT'; UNWIND: 'UNWIND';

// Simple operations
COPY: 'COPY'; COPY_KEY: 'COPY_KEY'; MOVE: 'MOVE'; MERGE: 'MERGE'; SPLIT: 'SPLIT'; CAST: 'CAST'; LINKING: 'LINKING';

// ADD operations - specific keywords
ADD_ATTRIBUTE: 'ADD_ATTRIBUTE';
ADD_REFERENCE: 'ADD_REFERENCE';
ADD_EMBEDDED: 'ADD_EMBEDDED';
ADD_ENTITY: 'ADD_ENTITY';
ADD_PRIMARY_KEY: 'ADD_PRIMARY_KEY';
ADD_FOREIGN_KEY: 'ADD_FOREIGN_KEY';
ADD_UNIQUE_KEY: 'ADD_UNIQUE_KEY';
ADD_PARTITION_KEY: 'ADD_PARTITION_KEY';
ADD_CLUSTERING_KEY: 'ADD_CLUSTERING_KEY';
ADD_VARIATION: 'ADD_VARIATION';
ADD_RELTYPE: 'ADD_RELTYPE';
ADD_INDEX: 'ADD_INDEX';
ADD_LABEL: 'ADD_LABEL';

// DELETE operations - specific keywords
DELETE_ATTRIBUTE: 'DELETE_ATTRIBUTE';
DELETE_REFERENCE: 'DELETE_REFERENCE';
DELETE_EMBEDDED: 'DELETE_EMBEDDED';
DELETE_ENTITY: 'DELETE_ENTITY';
DELETE_PRIMARY_KEY: 'DELETE_PRIMARY_KEY';
DELETE_FOREIGN_KEY: 'DELETE_FOREIGN_KEY';
DELETE_UNIQUE_KEY: 'DELETE_UNIQUE_KEY';
DELETE_PARTITION_KEY: 'DELETE_PARTITION_KEY';
DELETE_CLUSTERING_KEY: 'DELETE_CLUSTERING_KEY';
DELETE_VARIATION: 'DELETE_VARIATION';
DELETE_RELTYPE: 'DELETE_RELTYPE';
DELETE_INDEX: 'DELETE_INDEX';
DELETE_LABEL: 'DELETE_LABEL';

// REMOVE operations - specific keywords (non-destructive constraint removal)
REMOVE_INDEX: 'REMOVE_INDEX';
REMOVE_UNIQUE_KEY: 'REMOVE_UNIQUE_KEY';
REMOVE_FOREIGN_KEY: 'REMOVE_FOREIGN_KEY';
REMOVE_LABEL: 'REMOVE_LABEL';
REMOVE_VARIATION: 'REMOVE_VARIATION';

// RENAME operations - specific keywords
RENAME_FEATURE: 'RENAME_FEATURE';
RENAME_ENTITY: 'RENAME_ENTITY';
RENAME_RELTYPE: 'RENAME_RELTYPE';

// Shared keywords
RENAME: 'RENAME';

// RelType (Graph relationship types)
RELTYPE: 'RELTYPE'; PROPERTIES: 'PROPERTIES'; STRUCTURE: 'STRUCTURE';

// Feature types
ATTRIBUTE: 'ATTRIBUTE'; EMBEDDED: 'EMBEDDED';
ENTITY: 'ENTITY'; VARIATION: 'VARIATION'; VALUE: 'VALUE';
INDEX: 'INDEX'; LABEL: 'LABEL';

// Key types
PRIMARY: 'PRIMARY'; UNIQUE: 'UNIQUE'; FOREIGN: 'FOREIGN';
PARTITION: 'PARTITION'; CLUSTERING: 'CLUSTERING';
REFERENCE: 'REFERENCE'; REFERENCES: 'REFERENCES'; COLUMNS: 'COLUMNS';

// Variation clauses
ATTRIBUTES: 'ATTRIBUTES'; RELATIONSHIPS: 'RELATIONSHIPS';

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
COLON: ':'; COMMA: ','; DOT: '.'; LPAREN: '('; RPAREN: ')'; LBRACKET: '['; RBRACKET: ']';
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
