grammar SMEL;

// ==================== PARSER RULES ====================
migration: header operation* EOF;
header: migrationDecl fromToDecl usingDecl;                         // MIGRATION name:ver FROM type TO type USING schema:ver
migrationDecl: MIGRATION identifier COLON version;                  // MIGRATION payment_migration:1.0
fromToDecl: FROM databaseType TO databaseType;                      // FROM RELATIONAL TO Doucment
usingDecl: USING identifier COLON version;                          // USING iso20022_schema:1.0
databaseType: RELATIONAL | DOCUMENT | GRAPH | COLUMNAR;             // Abstract database model types
version: VERSION_NUMBER | INTEGER_LITERAL;                          // 1 | 1.0 | 1.0.0

// Operations (unified entry points: add, delete, drop, rename)
operation: nest | unnest | flatten | unwind
         | copy | move | merge | split | cast | linking | extract
         | add | delete | drop | rename;

nest: NEST identifier INTO identifier AS identifier nestClause*;    // NEST Child INTO Parent AS alias [clauses]
nestClause: withCardinalityClause | usingKeyClause | whereClause;
unnest: UNNEST identifier FROM identifier unnestClause*;            // UNNEST embedded FROM Parent
unnestClause: AS identifier | usingKeyClause;
flatten: FLATTEN qualifiedName (INTO|AS) identifier flattenClause*; // FLATTEN Parent.child INTO NewEntity
flattenClause: renameClause | addReferenceClause;
unwind: UNWIND qualifiedName AS identifier unwindClause*;           // UNWIND array[] AS NewEntity
unwindClause: generateKeyClause | addReferenceClause | linkingClause;

// Shared clauses
withCardinalityClause: WITH CARDINALITY cardinalityType;            // WITH CARDINALITY ONE_TO_MANY
usingKeyClause: USING KEY identifier;                               // USING KEY foreign_key
whereClause: WHERE condition;                                       // WHERE a.id = b.ref_id
renameClause: RENAME identifier TO qualifiedName (IN identifier)?;  // RENAME old TO new [IN entity]
addReferenceClause: ADD REFERENCE identifier TO identifier;         // ADD REFERENCE ref_id TO Target
generateKeyClause: GENERATE KEY identifier (AS SERIAL | FROM identifier); // GENERATE KEY id AS SERIAL
linkingClause: LINKING qualifiedName TO identifier;                 // LINKING source.field TO target

// Standalone operations
copy: COPY qualifiedName TO qualifiedName;                          // COPY source TO target
move: MOVE qualifiedName TO qualifiedName;                          // MOVE source TO target
merge: MERGE identifier COMMA identifier INTO identifier (AS identifier)?; // MERGE A, B INTO C [AS alias]
split: SPLIT identifier INTO identifier COMMA identifier;           // SPLIT source INTO A, B
cast: CAST qualifiedName TO dataType;                               // CAST Entity.field TO Integer
linking: LINKING qualifiedName TO identifier;                       // LINKING source TO target

// ADD operation - unified entry point with internal branching by type
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

// Add key: ADD PRIMARY KEY id TO Customer
keyAdd: keyType KEY identifier (TO identifier)? keyClause*;

// Add variation: ADD VARIATION v1 TO Customer WITH ATTRIBUTES (a, b)
variationAdd: VARIATION identifier TO identifier variationClause*;

// Add relationship type (Graph): ADD RELTYPE ACTED_IN FROM Actor TO Movie
relTypeAdd: RELTYPE identifier FROM identifier TO identifier relTypeClause*;

// DELETE operation - unified entry point with internal branching by type
delete: DELETE (attributeDelete | referenceDelete | embeddedDelete | entityDelete);

// Delete attribute: DELETE ATTRIBUTE Customer.email
attributeDelete: ATTRIBUTE qualifiedName;

// Delete reference: DELETE REFERENCE Customer.order_id
referenceDelete: REFERENCE qualifiedName;

// Delete embedded: DELETE EMBEDDED Customer.address
embeddedDelete: EMBEDDED qualifiedName;

// Delete entity: DELETE ENTITY Customer
entityDelete: ENTITY identifier;

// DROP operation - unified entry point for structural elements
drop: DROP (keyDrop | variationDrop | relTypeDrop);

// Drop key: DROP PRIMARY KEY id FROM Customer
keyDrop: keyType KEY identifier (FROM identifier)?;

// Drop variation: DROP VARIATION v1 FROM Customer
variationDrop: VARIATION identifier FROM identifier;

// Drop relationship type: DROP RELTYPE ACTED_IN
relTypeDrop: RELTYPE identifier;

// RENAME operation - unified entry point with internal branching
rename: RENAME (featureRename | entityRename | relTypeRename);

// Rename feature: RENAME oldName TO newName IN Entity
featureRename: identifier TO identifier (IN identifier)?;

// Rename entity: RENAME ENTITY OldName TO NewName
entityRename: ENTITY identifier TO identifier;

// Rename relationship type: RENAME RELTYPE oldName TO newName
relTypeRename: RELTYPE identifier TO identifier;

// Key types (matches KeyType in unified_meta_schema.py)
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

// Common types (matches unified_meta_schema.py)
cardinalityType: ONE_TO_ONE | ONE_TO_MANY | ZERO_TO_ONE | ZERO_TO_MANY; // & + ? *
dataType: STRING | TEXT | INT | INTEGER | LONG | DOUBLE | FLOAT | DECIMAL
        | BOOLEAN | DATE | DATETIME | TIMESTAMP | UUID | BINARY | identifier;

// Path and identifiers
qualifiedName: pathSegment (DOT pathSegment)*;                      // Entity.field[].subfield
pathSegment: identifier (LBRACKET RBRACKET)?;                       // field or field[]
identifier: IDENTIFIER;

// Condition (simplified for schema migration: only equality and AND for composite keys)
condition: qualifiedName EQUALS qualifiedName                       // a.id = b.ref_id
         | condition AND condition                                  // composite key: a.id1 = b.ref1 AND a.id2 = b.ref2
         | LPAREN condition RPAREN;                                 // grouping

// Literals (kept for addClause WITH DEFAULT)
literal: STRING_LITERAL | INTEGER_LITERAL | DECIMAL_LITERAL | TRUE | FALSE | NULL;

// ==================== LEXER RULES ====================
// Keywords
MIGRATION: 'MIGRATION'; FROM: 'FROM'; TO: 'TO'; USING: 'USING'; AS: 'AS';
INTO: 'INTO'; WITH: 'WITH'; WHERE: 'WHERE'; IN: 'IN'; KEY: 'KEY'; AND: 'AND';
COUNT: 'COUNT';

// Database model types (abstract)
RELATIONAL: 'RELATIONAL'; DOCUMENT: 'DOCUMENT'; GRAPH: 'GRAPH'; COLUMNAR: 'COLUMNAR';

// Operations
NEST: 'NEST'; UNNEST: 'UNNEST'; FLATTEN: 'FLATTEN'; UNWIND: 'UNWIND';
DELETE: 'DELETE'; ADD: 'ADD'; RENAME: 'RENAME'; COPY: 'COPY'; MOVE: 'MOVE';
MERGE: 'MERGE'; SPLIT: 'SPLIT'; CAST: 'CAST'; GENERATE: 'GENERATE'; LINKING: 'LINKING';
DROP: 'DROP'; EXTRACT: 'EXTRACT';

// RelType (Graph relationship types)
RELTYPE: 'RELTYPE'; PROPERTIES: 'PROPERTIES'; STRUCTURE: 'STRUCTURE';

// Feature types
REFERENCE: 'REFERENCE'; ATTRIBUTE: 'ATTRIBUTE'; EMBEDDED: 'EMBEDDED';
ENTITY: 'ENTITY'; VARIATION: 'VARIATION';

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
TYPE: 'TYPE'; DEFAULT: 'DEFAULT'; SERIAL: 'SERIAL';

// Constraints
NOT_NULL: 'NOT NULL';

// Literals
TRUE: 'true' | 'TRUE'; FALSE: 'false' | 'FALSE'; NULL: 'null' | 'NULL';

// Symbols
COLON: ':'; COMMA: ','; DOT: '.'; LPAREN: '('; RPAREN: ')'; LBRACKET: '['; RBRACKET: ']';
EQUALS: '=';

// Patterns
VERSION_NUMBER: [0-9]+ '.' [0-9]+ ('.' [0-9]+)?;
INTEGER_LITERAL: [0-9]+;
DECIMAL_LITERAL: [0-9]+ '.' [0-9]+;
STRING_LITERAL: '\'' (~['\r\n] | '\'\'')* '\'' | '"' (~["\r\n] | '""')* '"';
IDENTIFIER: [a-zA-Z_][a-zA-Z0-9_]*;

// Skip
LINE_COMMENT: '--' ~[\r\n]* -> skip;
BLOCK_COMMENT: '/*' .*? '*/' -> skip;
WS: [ \t\r\n]+ -> skip;