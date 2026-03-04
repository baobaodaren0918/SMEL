/*
 * SMEL_Pauschalisiert - Schema Migration & Evolution Language (Generalized Operations Version)
 * A domain-specific language for database schema migration
 *
 * This version uses generalized, parameterized operations.
 * Operations use a base keyword with parameters (e.g., ADD_PS ATTRIBUTE, ADD_PS CONSTRAINT)
 *
 * Comparison: This is the "Pauschalisiert" (Generalized) version. See SMEL_Specific.g4
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
 *   FLATTEN_PS person.address AS address
 *   ADD_PS PRIMARY KEY address_id TO address
 *   ADD_PS FOREIGN KEY person_id TO address REFERENCES person(id)
 *
 *   -- Expand array to table
 *   UNWIND_PS person.tags[] INTO person_tag
 *   ADD_PS PRIMARY KEY id TO person_tag
 *   ADD_PS FOREIGN KEY person_id TO person_tag REFERENCES person(id)
 */
grammar SMEL_Pauschalisiert;

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
// Structure:  NEST_PS, UNNEST_PS, FLATTEN_PS, UNWIND_PS, EXTRACT_PS
// Movement:   COPY_PS, MOVE_PS, MERGE_PS, SPLIT_PS
// Type:       CAST_PS
// CRUD:       ADD_PS, DELETE_PS, REMOVE_PS, RENAME_PS

operation: nest_ps | unnest_ps | flatten_ps | unflatten_ps | unwind_ps | wind_ps
         | copy_ps | move_ps | merge_ps | split_ps | cast_ps | recard_ps
         | transform_ps
         | add_ps | delete_ps | remove_ps | rename_ps;

// ============================================================================
// ADD_PS - Generalized ADD operation with type parameter
// ============================================================================
// Supports adding:
//   - ATTRIBUTE:   Add new attribute to entity
//   - CONSTRAINT:  Add foreign key constraint
//   - EMBEDDED:    Add embedded object relationship (MongoDB style)
//   - ENTITY:      Add new entity/table
//   - KEY:         Add primary/unique/foreign key constraint
//   - RELTYPE:     Add relationship type (Graph database support)
//
// Example: ADD_PS ATTRIBUTE email TO Customer WITH TYPE String NOT NULL
// Example: ADD_PS PRIMARY KEY id TO Customer

add_ps: ADD_PS (attributeAdd | constraintAdd | embeddedAdd | entityAdd
        | keyAdd | labelAdd | reltypeAdd);

// Add attribute: ADD_PS ATTRIBUTE email TO Customer WITH TYPE String NOT NULL
attributeAdd: ATTRIBUTE identifier (TO identifier)? attributeClause*;
attributeClause: withTypeClause | withDefaultClause | notNullClause;
withTypeClause: WITH TYPE dataType;
withDefaultClause: WITH DEFAULT literal;
notNullClause: NOT_NULL;

// Add constraint: ADD_PS CONSTRAINT entity.field REFERENCES target_table(target_column)
// SQL-style foreign key constraint syntax with explicit entity.field
// Example: ADD_PS CONSTRAINT address.person_id REFERENCES person(person_id)
// Example: ADD_PS CONSTRAINT order.customer_id REFERENCES customer(id) WITH CARDINALITY ONE_TO_MANY
constraintAdd: CONSTRAINT qualifiedName REFERENCES identifier LPAREN identifier RPAREN constraintClause*;
constraintClause: withCardinalityClause | usingKeyClause | whereClause;

// Add embedded: ADD_PS EMBEDDED address TO Customer WITH CARDINALITY ONE_TO_ONE
embeddedAdd: EMBEDDED identifier TO identifier embeddedClause*;
embeddedClause: withCardinalityClause | withStructureClause;
withStructureClause: WITH STRUCTURE LPAREN identifierList RPAREN;

// Add entity: ADD_PS ENTITY Product WITH ATTRIBUTES (id, name)
entityAdd: ENTITY identifier entityClause*;
entityClause: withAttributesClause | withKeyClause;
withKeyClause: WITH KEY identifier;

// Add key: ADD_PS KEY entity.field AS String (explicit entity.field syntax)
// Or full form: ADD_PS PRIMARY KEY id TO Customer WITH TYPE UUID (legacy TO syntax)
// Example: ADD_PS KEY address.address_id AS String  (new explicit syntax)
// Example: ADD_PS PRIMARY KEY (id1, id2) TO Customer (composite key)
keyAdd: keyType? KEY keyColumns (AS dataType)? (TO identifier)? keyClause*;
// Note: keyType is optional, defaults to PRIMARY KEY when omitted
// Note: AS dataType is a simplified alternative to WITH TYPE dataType
// Note: keyColumns now supports qualifiedName (entity.field) for explicit entity specification

// Key columns - qualifiedName (entity.field) or parenthesized list for composite keys
keyColumns: qualifiedName | LPAREN identifierList RPAREN;

// Add label (Graph): ADD_PS LABEL Employee TO Person
labelAdd: LABEL identifier TO identifier;

// Add relationship type (Graph): ADD_PS RELTYPE works_at BETWEEN person AND company
reltypeAdd: RELTYPE identifier BETWEEN identifier AND identifier;

// ============================================================================
// DELETE_PS - Generalized DELETE operation with type parameter
// ============================================================================
// Supports deleting:
//   - ATTRIBUTE:   Remove attribute from entity
//   - CONSTRAINT:  Remove foreign key constraint
//   - EMBEDDED:    Remove embedded object relationship
//   - ENTITY:      Remove entire entity/table
//   - KEY:         Remove key constraints (PRIMARY, FOREIGN, UNIQUE, PARTITION, CLUSTERING)
//   - LABEL:       Remove label
//
// Example: DELETE_PS ATTRIBUTE Customer.email
// Example: DELETE_PS PRIMARY KEY id FROM Customer

delete_ps: DELETE_PS (attributeDelete | constraintDelete | embeddedDelete | entityDelete
          | keyDelete | labelDelete | reltypeDelete);

// Delete attribute: DELETE_PS ATTRIBUTE Customer.email
attributeDelete: ATTRIBUTE qualifiedName;

// Delete constraint: DELETE_PS CONSTRAINT Customer.order_id
constraintDelete: CONSTRAINT qualifiedName;

// Delete embedded: DELETE_PS EMBEDDED Customer.address
embeddedDelete: EMBEDDED qualifiedName;

// Delete entity: DELETE_PS ENTITY Customer
entityDelete: ENTITY identifier;

// Delete key: DELETE_PS PRIMARY KEY id FROM Customer
keyDelete: keyType KEY keyColumns (FROM identifier)?;

// Delete label: DELETE_PS LABEL Employee FROM Person
labelDelete: LABEL identifier FROM identifier;

// Delete relationship type (Graph): DELETE_PS RELTYPE works_at
reltypeDelete: RELTYPE identifier;

// ============================================================================
// REMOVE_PS - Generalized REMOVE operation with type parameter
// ============================================================================
// Non-destructive constraint removal (preserves structure, removes metadata)
// Supports removing:
//   - UNIQUE KEY: Remove unique constraint (constraint relaxation)
//   - FOREIGN KEY: Remove foreign key constraint (temporarily disable FK)
//   - LABEL:      Remove label (graph reclassification)
//
// Example: REMOVE_PS UNIQUE KEY email FROM Customer

remove_ps: REMOVE_PS (uniqueKeyRemove | foreignKeyRemove | labelRemove);

// Remove unique key: REMOVE_PS UNIQUE KEY email FROM Customer
uniqueKeyRemove: UNIQUE KEY keyColumns FROM identifier;

// Remove foreign key: REMOVE_PS FOREIGN KEY customer_id FROM Order
foreignKeyRemove: FOREIGN KEY keyColumns FROM identifier;

// Remove label: REMOVE_PS LABEL Manager FROM Person
labelRemove: LABEL identifier FROM identifier;

// ============================================================================
// RENAME_PS - Generalized RENAME operation with type parameter
// ============================================================================
// Supports renaming:
//   - Attribute: RENAME_PS ATTRIBUTE oldName TO newName IN Entity
//   - Entity:  RENAME_PS ENTITY OldName TO NewName
//
// Example: RENAME_PS ATTRIBUTE email TO contact_email IN Customer

rename_ps: RENAME_PS (attributeRename | entityRename | reltypeRename);

// Rename attribute: RENAME_PS ATTRIBUTE oldName TO newName IN Entity
attributeRename: ATTRIBUTE identifier TO identifier (IN identifier)?;

// Rename entity: RENAME_PS ENTITY OldName TO NewName
entityRename: ENTITY identifier TO identifier;

// Rename relationship type (Graph): RENAME_PS RELTYPE works_at TO employed_at
reltypeRename: RELTYPE identifier TO identifier;

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

// FLATTEN_PS - Flatten nested object fields into parent table (reduce depth by 1)
// Reference: André Conrad - "Die Operation FLATTEN erstellt aus dem Objekt in der Spalte
//            jeweils eine Spalte für jedes Attribut dieses Objekts"
// Example: FLATTEN_PS person.name
//   Before: person { name: { vorname, nachname }, age }
//   After:  person { name_vorname, name_nachname, age }
flatten_ps: FLATTEN_PS qualifiedName;

// UNFLATTEN_PS - Combine flat fields into nested object (reverse of FLATTEN)
// Example: UNFLATTEN_PS person:vorname, nachname AS name
//   Before: person { vorname, nachname, age }
//   After:  person { name: { vorname, nachname }, age }
unflatten_ps: UNFLATTEN_PS identifier COLON identifierList AS identifier;

// UNNEST_PS - Extract nested object to separate table (normalization)
// Example: UNNEST_PS person.address:street,city AS address WITH person.person_id TO address.person_id
// Example with multiple carry fields:
//   UNNEST_PS person.employment:position AS employment
//       WITH person.person_id TO employment.person_id, person.dept_id TO employment.dept_id
//   - 'street,city' are attributes to extract
//   - WITH clause: copy fields from source to new table (can carry multiple fields)
//   - WITH is optional, for cases where no parent fields need to be copied
//   Before: person { person_id, address: { street, city } }
//   After:  person { person_id }
//           address { person_id, street, city }
// Note: Use separate ADD_PS KEY, ADD_PS CONSTRAINT for constraints
unnest_ps: UNNEST_PS qualifiedName COLON unnestFieldList AS identifier (WITH unnestCarryList)?;

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

// UNWIND_PS - Expand array field into multiple rows
// Reference: André Conrad - array expansion operation
// Supports two modes:
//   1. Expand in place: UNWIND_PS person_tag.tags (expands array within existing table)
//   2. Create new table: UNWIND_PS person.tags[] INTO person_tag (legacy, creates new table)
// Note: Use separate ADD_PS KEY, ADD_PS CONSTRAINT, RENAME_PS ATTRIBUTE for constraints
unwind_ps: UNWIND_PS qualifiedName (INTO identifier)?;

// WIND_PS - Convert scalar attribute back to array (reverse of UNWIND_PS)
// Syntax: WIND_PS person_tag.tags
// Cross-entity movement is handled by MERGE_PS, not WIND_PS.
wind_ps: WIND_PS qualifiedName;

// NEST_PS - Merge separate table into embedded document (PostgreSQL -> MongoDB)
// Example: NEST_PS address:street,city IN person.address WHERE address.person_id = person.person_id
// Example with deletion: NEST_PS address:street,city IN person.address WHERE address.person_id = person.person_id WITH DELETION
//   - 'address' is source entity
//   - ':street,city' are attributes to embed
//   - 'IN person.address' specifies target (person entity, address field)
//   - WHERE clause specifies join condition
//   - WITH DELETION optionally removes source entity after embedding
nest_ps: NEST_PS identifier COLON unnestFieldList IN qualifiedName WHERE condition (WITH DELETION)?;

// ============================================================================
// SIMPLE OPERATIONS - All with _PS suffix
// ============================================================================

// COPY_PS: Duplicate an attribute or entity
// Example: COPY_PS ATTRIBUTE person.name TO person.first_name
// Example: COPY_PS ENTITY person AS employee
copy_ps: COPY_PS (entityCopy | attributeCopy);
attributeCopy: ATTRIBUTE qualifiedName TO qualifiedName;
entityCopy: ENTITY identifier AS identifier;

// MOVE_PS: Relocate an attribute to another location (removes original)
// Example: MOVE_PS ATTRIBUTE person.name TO other.name
move_ps: MOVE_PS ATTRIBUTE qualifiedName TO qualifiedName;

// MERGE_PS: Combine two entities into one new entity
// Example: MERGE_PS A, B INTO C AS alias
merge_ps: MERGE_PS identifier COMMA identifier INTO identifier (AS identifier)?;

// SPLIT_PS: Divide one entity into multiple separate entities (vertical partitioning)
// Reference: André Conrad - "SPLIT Person into Person:id, firstname, lastname AND knows:id, knows"
// Example: SPLIT_PS person INTO person:person_id, vorname, nachname, age; person_tag:person_id, tags
//   Before: person { person_id, vorname, nachname, age, tags[] }
//   After:  person { person_id, vorname, nachname, age }
//          person_tag { person_id, tags[] }
// Note: Fields can be duplicated across parts (e.g., person_id in both parts)
split_ps: SPLIT_PS identifier INTO splitPartPs (SEMICOLON splitPartPs)+;
splitPartPs: identifier COLON identifierList;

// CAST_PS: Change the data type of an attribute or the type of a constraint
// Example: CAST_PS ATTRIBUTE Entity.field TO Integer
// Example: CAST_PS CONSTRAINT Entity.field TO UNIQUE KEY
cast_ps: CAST_PS (constraintCast | attributeCast);
attributeCast: ATTRIBUTE qualifiedName TO dataType;
constraintCast: CONSTRAINT qualifiedName TO constraintKeyType;

// RECARD_PS: Change the multiplicity/cardinality of a reference
// Example: RECARD_PS person.address_id TO ONE_TO_MANY
recard_ps: RECARD_PS qualifiedName TO cardinalityType;

// TRANSFORM_PS: Transform entity between node and relationship (Graph database)
// Reference: Hausler et al. - "transform a node with its features into a relationship" / vice versa
// Example: TRANSFORM_PS works_at TO RELATIONSHIP BETWEEN person AND company
// Example: TRANSFORM_PS works_at TO ENTITY
transform_ps: TRANSFORM_PS identifier TO transformTarget;
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

// Entity clauses (for ADD_PS ENTITY)
withAttributesClause: WITH ATTRIBUTES LPAREN identifierList RPAREN;

// ============================================================================
// COMMON TYPES - Shared type definitions
// ============================================================================

// Cardinality notation
cardinalityType: ONE_TO_ONE | ONE_TO_MANY | ZERO_TO_ONE | ZERO_TO_MANY;

// Constraint key type (for CAST_PS CONSTRAINT)
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
// KEYWORDS - Reserved words in SMEL_Pauschalisiert
// ----------------------------------------------------------------------------
MIGRATION: 'MIGRATION'; FROM: 'FROM'; TO: 'TO'; USING: 'USING'; AS: 'AS';
INTO: 'INTO'; WITH: 'WITH'; WHERE: 'WHERE'; IN: 'IN'; KEY: 'KEY'; AND: 'AND'; DELETION: 'DELETION';
ON: 'ON';

// Database model types
RELATIONAL: 'RELATIONAL'; DOCUMENT: 'DOCUMENT'; GRAPH: 'GRAPH'; COLUMNAR: 'COLUMNAR';

// Generalized operations with _PS suffix
NEST_PS: 'NEST_PS'; UNNEST_PS: 'UNNEST_PS'; FLATTEN_PS: 'FLATTEN_PS'; UNFLATTEN_PS: 'UNFLATTEN_PS';
UNWIND_PS: 'UNWIND_PS'; WIND_PS: 'WIND_PS';
ADD_PS: 'ADD_PS'; DELETE_PS: 'DELETE_PS'; REMOVE_PS: 'REMOVE_PS'; RENAME_PS: 'RENAME_PS';
COPY_PS: 'COPY_PS'; MOVE_PS: 'MOVE_PS'; MERGE_PS: 'MERGE_PS'; SPLIT_PS: 'SPLIT_PS';
CAST_PS: 'CAST_PS'; RECARD_PS: 'RECARD_PS'; TRANSFORM_PS: 'TRANSFORM_PS';
RELATIONSHIP: 'RELATIONSHIP'; BETWEEN: 'BETWEEN';

// Shared keywords
RENAME: 'RENAME';

// Type parameters for generalized operations
ATTRIBUTE: 'ATTRIBUTE'; CONSTRAINT: 'CONSTRAINT'; EMBEDDED: 'EMBEDDED'; ENTITY: 'ENTITY';
LABEL: 'LABEL'; RELTYPE: 'RELTYPE';

// Entity/Variation clauses
ATTRIBUTES: 'ATTRIBUTES';

// Key types
PRIMARY: 'PRIMARY'; UNIQUE: 'UNIQUE'; FOREIGN: 'FOREIGN';
PARTITION: 'PARTITION'; CLUSTERING: 'CLUSTERING';
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
