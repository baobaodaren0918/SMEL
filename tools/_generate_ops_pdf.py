# -*- coding: utf-8 -*-
"""Generate PDF: SMEL 6 Core Structural Operations Reference (EN + ZH)"""
from fpdf import FPDF

# ═══════════════════════════════════════════════════
# Shared code blocks (language-independent)
# ═══════════════════════════════════════════════════

FLATTEN_CODE = [
    'FLATTEN_PS person.name',
    '',
    'Before:                          After:',
    '  person {                         person {',
    '    age,                             age,',
    '    name: {          <-- object      name_vorname,    <-- prefix + field',
    '      vorname,                       name_nachname',
    '      nachname                     }',
    '    }',
    '  }',
]

UNFLATTEN_CODE = [
    'UNFLATTEN_PS suppliers:street, city, region, postal_code, country AS address',
    '',
    'Before:                          After:',
    '  suppliers {                      suppliers {',
    '    supplier_id,                     supplier_id,',
    '    company_name,                    company_name,',
    '    street,       <-- flat          address: {       <-- new object',
    '    city,             fields          street,',
    '    region,                            city,',
    '    postal_code,                       region,',
    '    country                            postal_code,',
    '  }                                    country',
    '                                     }',
    '                                   }',
]

NEST_OBJ_CODE = [
    'NEST_PS customers:company_name, phone IN orders.customer',
    '  WHERE orders.customer_id = customers.customer_id WITH DELETION',
    '',
    'Before:                              After:',
    '  orders {                             orders {',
    '    order_id,                            order_id,',
    '    customer_id FK --> customers         customer: {      <-- OBJECT',
    '  }                                       company_name,',
    '  customers {             deleted ->       phone',
    '    customer_id PK,                      }',
    '    company_name,                       }',
    '    phone',
    '  }',
]

NEST_ARR_CODE = [
    'NEST_PS order_details:unit_price, quantity IN orders.details',
    '  WHERE order_details.order_id = orders.order_id WITH DELETION',
    '',
    'Before:                              After:',
    '  orders {                             orders {',
    '    order_id PK                         order_id,',
    '  }                                     details: [       <-- ARRAY',
    '  order_details {     deleted ->           { unit_price,',
    '    order_id FK --> orders                   quantity }',
    '    unit_price,                           ]',
    '    quantity                             }',
    '  }',
]

UNNEST_CODE = [
    'UNNEST_PS orders.customer:company_name, phone, address{street, city}',
    '  AS customers WITH orders.order_id TO customers.order_id',
    '',
    'Before:                              After:',
    '  orders {                             orders { order_id }',
    '    order_id,                          customers {',
    '    customer: {      <-- embedded       order_id,    <-- carry field (FK)',
    '      company_name,                     company_name,',
    '      phone,                            phone,',
    '      address: {                        address: {   <-- nested transferred',
    '        street, city                      street, city',
    '      }                                 }',
    '    }                                  }',
    '  }',
]

WIND_CODE = [
    'WIND_PS person_tag.tag',
    '',
    'Before (multi-row):                After (single-row, array):',
    '  person_tag {                      person_tag {',
    '    person_id,                        person_id,',
    '    tag        <-- scalar string      tag[]      <-- array of string',
    '  }                                 }',
    '  Row 1: (P1, "python")             Row 1: (P1, ["python","java","sql"])',
    '  Row 2: (P1, "java")',
    '  Row 3: (P1, "sql")',
]

UNWIND_M1_CODE = [
    'UNWIND_PS person.tags[] INTO person_tag',
    '',
    'Before:                            After:',
    '  person {                           person { person_id }',
    '    person_id,                       person_tag {',
    '    tags[]     <-- array               value    <-- element type',
    '  }                                  }',
]

UNWIND_M2_CODE = [
    'UNWIND_PS person_tag.tags',
    '',
    'Before:                            After:',
    '  person_tag {                       person_tag {',
    '    person_id,                         person_id,',
    '    tags[]     <-- ListDataType         tags      <-- scalar (PrimitiveType)',
    '  }                                  }',
]

NEST_FK_CODE = [
    'Case 1: TARGET holds FK to SOURCE  (orders.customer_id -> customers)',
    '  => Each order has ONE customer => embed as OBJECT',
    '  => orders { customer: { company_name, phone } }',
    '',
    'Case 2: SOURCE holds FK to TARGET  (order_details.order_id -> orders)',
    '  => Each order has MANY details => embed as ARRAY',
    '  => orders { details: [ { product_id, quantity } ] }',
]


# ═══════════════════════════════════════════════════
# PDF generator class
# ═══════════════════════════════════════════════════

class OpsPDF(FPDF):
    def __init__(self, lang='en'):
        super().__init__()
        self.lang = lang
        self._use_cjk = (lang == 'zh')
        if self._use_cjk:
            self.add_font('CJK', '', 'C:/Windows/Fonts/msyh.ttc')
            self.add_font('CJK', 'B', 'C:/Windows/Fonts/msyhbd.ttc')

    def _font(self, style='', size=9):
        if self._use_cjk:
            self.set_font('CJK', 'B' if 'B' in style else '', size)
        else:
            self.set_font('Helvetica', style, size)

    def section_title(self, num, title, color):
        self.set_fill_color(*color)
        self.set_text_color(255, 255, 255)
        self._font('B', 13)
        self.cell(0, 9, f'  {num}. {title}', new_x="LMARGIN", new_y="NEXT", fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def label_value(self, label, value):
        self._font('B', 9)
        lw = 32 if self.lang == 'en' else 28
        self.cell(lw, 5, label + ':', new_x="RIGHT")
        self._font('', 9)
        self.multi_cell(0, 5, value, new_x="LMARGIN", new_y="NEXT")

    def code_block(self, lines):
        self.set_font('Courier', '', 8.5)
        self.set_fill_color(245, 245, 247)
        for line in lines:
            self.cell(0, 4.5, '  ' + line, new_x="LMARGIN", new_y="NEXT", fill=True)
        self._font('', 9)
        self.ln(2)

    def body_text(self, text):
        self._font('', 9)
        self.multi_cell(0, 5, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def table_header(self, cols):
        """cols = [(text, width), ...]  last one uses width=0 for remaining"""
        self._font('B', 9)
        self.set_fill_color(58, 58, 60)
        self.set_text_color(255, 255, 255)
        for i, (text, w) in enumerate(cols):
            is_last = (i == len(cols) - 1)
            self.cell(w, 6, ' ' + text, fill=True,
                      new_x="LMARGIN" if is_last else "RIGHT",
                      new_y="NEXT" if is_last else "LAST")
        self.set_text_color(0, 0, 0)

    def table_row(self, cells, idx):
        """cells = [(text, width, font_style), ...]"""
        bg = (245, 245, 247) if idx % 2 == 0 else (255, 255, 255)
        self.set_fill_color(*bg)
        for i, (text, w, fs) in enumerate(cells):
            is_last = (i == len(cells) - 1)
            if fs == 'code':
                self.set_font('Courier', 'B' if self._use_cjk else '', 8)
            elif fs == 'code_sm':
                self.set_font('Courier', '', 7.5)
            elif fs == 'bold':
                self._font('B', 9)
            elif fs == 'sm':
                self._font('', 8)
            else:
                self._font('', 9)
            self.cell(w, 6, ' ' + text, fill=True,
                      new_x="LMARGIN" if is_last else "RIGHT",
                      new_y="NEXT" if is_last else "LAST")


def generate_en(path):
    pdf = OpsPDF('en')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font('Helvetica', 'B', 20)
    pdf.cell(0, 12, 'SMEL - 6 Core Structural Operations', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, 'Schema Migration & Evolution Language', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    # ── Overview ──
    pdf._font('B', 11)
    pdf.cell(0, 8, 'Overview: Three Orthogonal Dimensions', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.table_header([('Dimension', 40), ('Operations', 50), ('Operates On', 35), ('Description', 0)])
    rows = [
        [('Structural Depth', 40, ''), ('FLATTEN / UNFLATTEN', 50, 'code'), ('Object', 35, 'bold'), ('Nested object <-> flat fields (within same entity)', 0, '')],
        [('Entity Boundary', 40, ''), ('NEST / UNNEST', 50, 'code'), ('Entity', 35, 'bold'), ('Independent entity <-> embedded object/array (cross-entity)', 0, '')],
        [('Type Dimension', 40, ''), ('WIND / UNWIND', 50, 'code'), ('Array', 35, 'bold'), ('Scalar property <-> array property (type change)', 0, '')],
    ]
    for i, r in enumerate(rows):
        pdf.table_row(r, i)
    pdf.ln(4)

    # ── Object vs Entity vs Array ──
    pdf._font('B', 11)
    pdf.cell(0, 8, 'Object vs Entity vs Array: Which Operation for What?', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.body_text(
        'The 6 operations handle three different structural concepts:\n'
        '  - Object (nested/embedded): A sub-structure within an entity (e.g., address inside person)\n'
        '  - Entity (independent table): A standalone entity with its own identity (e.g., customers table)\n'
        '  - Array (list/collection): A multi-valued property (e.g., tags[], details[])')
    pdf.ln(1)
    pdf.table_header([('Operation', 28), ('Input', 22), ('Output', 22), ('What It Does', 0)])
    detail = [
        [('FLATTEN', 28, 'code'), ('Object', 22, ''), ('Fields', 22, ''), ('Dissolves nested object into flat fields with prefix', 0, '')],
        [('UNFLATTEN', 28, 'code'), ('Fields', 22, ''), ('Object', 22, ''), ('Groups flat fields into a new nested object', 0, '')],
        [('NEST', 28, 'code'), ('Entity', 22, ''), ('Obj/Array', 22, ''), ('Absorbs independent entity as embedded object or array', 0, '')],
        [('UNNEST', 28, 'code'), ('Obj/Array', 22, ''), ('Entity', 22, ''), ('Extracts embedded object/array into independent entity', 0, '')],
        [('WIND', 28, 'code'), ('Scalar', 22, ''), ('Array', 22, ''), ('Wraps scalar property into array type (ListDataType)', 0, '')],
        [('UNWIND', 28, 'code'), ('Array', 22, ''), ('Scalar', 22, ''), ('Unwraps array into scalar, or extracts into new entity', 0, '')],
    ]
    for i, r in enumerate(detail):
        pdf.table_row(r, i)
    pdf.ln(4)

    # ── NEST: object vs array ──
    pdf._font('B', 11)
    pdf.cell(0, 8, 'NEST: When Object, When Array?', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.body_text('NEST automatically determines whether to embed as object (1:1) or array (1:N) based on FK direction:')
    pdf.code_block(NEST_FK_CODE)
    pdf.ln(2)

    # ── 6 Operations Detail ──
    pdf.section_title(1, 'FLATTEN  --  Nested Object -> Flat Fields', (0, 122, 255))
    pdf.label_value('Operates On', 'Nested Object (Embedded)')
    pdf.label_value('Direction', 'Document style -> Relational style (reduce nesting depth by 1)')
    pdf.label_value('Syntax', 'FLATTEN_PS entity.nested_name')
    pdf.label_value('Reverse', 'UNFLATTEN')
    pdf.ln(1)
    pdf._font('B', 9); pdf.cell(0, 5, 'Example:', new_x="LMARGIN", new_y="NEXT")
    pdf.code_block(FLATTEN_CODE)

    pdf.section_title(2, 'UNFLATTEN  --  Flat Fields -> Nested Object', (0, 122, 255))
    pdf.label_value('Operates On', 'Flat Fields (creates Object)')
    pdf.label_value('Direction', 'Relational style -> Document style (increase nesting depth by 1)')
    pdf.label_value('Syntax', 'UNFLATTEN_PS entity:field1, field2, ... AS nested_name')
    pdf.label_value('Reverse', 'FLATTEN')
    pdf.ln(1)
    pdf._font('B', 9); pdf.cell(0, 5, 'Example:', new_x="LMARGIN", new_y="NEXT")
    pdf.code_block(UNFLATTEN_CODE)

    pdf.section_title(3, 'NEST  --  Independent Entity -> Embedded Object/Array', (255, 59, 48))
    pdf.label_value('Operates On', 'Independent Entity (merges into parent)')
    pdf.label_value('Output', 'Object (1:1 FK) or Array (1:N FK) -- auto-determined')
    pdf.label_value('Direction', 'Normalized (multi-table) -> Denormalized (single document)')
    pdf.label_value('Syntax', 'NEST_PS source:fields IN target.alias WHERE condition [WITH DELETION]')
    pdf.label_value('Reverse', 'UNNEST')
    pdf.ln(1)
    pdf._font('B', 9); pdf.cell(0, 5, 'Example A: Embed as Object (target holds FK)', new_x="LMARGIN", new_y="NEXT")
    pdf.code_block(NEST_OBJ_CODE)
    pdf._font('B', 9); pdf.cell(0, 5, 'Example B: Embed as Array (source holds FK)', new_x="LMARGIN", new_y="NEXT")
    pdf.code_block(NEST_ARR_CODE)

    pdf.section_title(4, 'UNNEST  --  Embedded Object/Array -> Independent Entity', (255, 59, 48))
    pdf.label_value('Operates On', 'Embedded Object or Array')
    pdf.label_value('Output', 'New independent Entity (with FK via WITH clause)')
    pdf.label_value('Direction', 'Denormalized (single document) -> Normalized (multi-table)')
    pdf.label_value('Syntax', 'UNNEST_PS parent.nested:fields AS new_entity WITH parent.pk TO new_entity.fk')
    pdf.label_value('Reverse', 'NEST')
    pdf.ln(1)
    pdf._font('B', 9); pdf.cell(0, 5, 'Example:', new_x="LMARGIN", new_y="NEXT")
    pdf.code_block(UNNEST_CODE)

    pdf.section_title(5, 'WIND  --  Scalar -> Array', (52, 199, 89))
    pdf.label_value('Operates On', 'Scalar Property (converts to Array type)')
    pdf.label_value('Direction', 'Relational (multi-row) -> Document/Columnar (single-row array)')
    pdf.label_value('Syntax', 'WIND_PS entity.property')
    pdf.label_value('Reverse', 'UNWIND')
    pdf.ln(1)
    pdf._font('B', 9); pdf.cell(0, 5, 'Example:', new_x="LMARGIN", new_y="NEXT")
    pdf.code_block(WIND_CODE)

    pdf.section_title(6, 'UNWIND  --  Array -> Scalar / New Entity', (52, 199, 89))
    pdf.label_value('Operates On', 'Array Attribute')
    pdf.label_value('Mode 1', 'Create new entity: UNWIND_PS entity.array[] INTO new_entity')
    pdf.label_value('Mode 2', 'Expand in place: UNWIND_PS entity.array (array -> scalar)')
    pdf.label_value('Reverse', 'WIND')
    pdf.ln(1)
    pdf._font('B', 9); pdf.cell(0, 5, 'Example (Mode 1 - Create new entity):', new_x="LMARGIN", new_y="NEXT")
    pdf.code_block(UNWIND_M1_CODE)
    pdf._font('B', 9); pdf.cell(0, 5, 'Example (Mode 2 - Expand in place):', new_x="LMARGIN", new_y="NEXT")
    pdf.code_block(UNWIND_M2_CODE)

    # ── Summary ──
    pdf.ln(2)
    pdf._font('B', 11)
    pdf.cell(0, 8, 'Inverse Pairs Summary', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.table_header([('Forward', 45), ('Reverse', 45), ('Scope', 0)])
    for i, (f, r, s) in enumerate([
        ('FLATTEN', 'UNFLATTEN', 'Within same entity (object <-> flat fields)'),
        ('NEST', 'UNNEST', 'Across entities (merge <-> split)'),
        ('WIND', 'UNWIND', 'Type only (scalar <-> array)'),
    ]):
        pdf.table_row([(f, 45, 'code'), (r, 45, 'code'), (s, 0, '')], i)

    pdf.ln(4)
    pdf._font('B', 11)
    pdf.cell(0, 8, 'Cross-Model Migration Patterns', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.table_header([('Migration', 42), ('Key Operations', 48), ('Strategy', 0)])
    for i, (m, o, d) in enumerate([
        ('Relational -> Document', 'UNFLATTEN + NEST', 'Flat fields -> objects, then merge tables into document'),
        ('Document -> Relational', 'UNNEST + FLATTEN', 'Split embedded -> tables, then flatten nested objects'),
        ('Relational -> Columnar', 'WIND + key ops', 'Add array types, partition/clustering keys'),
        ('Columnar -> Document', 'Del keys + UNFLATTEN + NEST', 'Remove Cassandra keys, then build document'),
        ('Relational -> Graph', 'UNNEST + edge ops', 'Create nodes and relationship types'),
        ('Document -> Graph', 'UNNEST + edge ops', 'Extract embedded into nodes and edges'),
    ]):
        pdf.table_row([(m, 42, 'sm'), (o, 48, 'code_sm'), (d, 0, 'sm')], i)

    pdf.output(path)
    print(f"EN PDF saved: {path}")


def generate_zh(path):
    pdf = OpsPDF('zh')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf._font('B', 20)
    pdf.cell(0, 14, 'SMEL - 6\u5927\u6838\u5fc3\u7ed3\u6784\u64cd\u4f5c', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf._font('', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, 'Schema Migration & Evolution Language', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    # ── Overview ──
    pdf._font('B', 11)
    pdf.cell(0, 8, '\u6982\u89c8\uff1a\u4e09\u4e2a\u6b63\u4ea4\u53d8\u6362\u7ef4\u5ea6', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.table_header([('\u53d8\u6362\u7ef4\u5ea6', 35), ('\u64cd\u4f5c\u5bf9', 50), ('\u4f5c\u7528\u5bf9\u8c61', 25), ('\u8bf4\u660e', 0)])
    rows = [
        [('\u7ed3\u6784\u6df1\u5ea6', 35, ''), ('FLATTEN / UNFLATTEN', 50, 'code'), ('Object', 25, 'bold'), ('\u5d4c\u5957\u5bf9\u8c61 <-> \u5e73\u94fa\u5b57\u6bb5\uff08\u540c\u4e00\u5b9e\u4f53\u5185\uff09', 0, '')],
        [('\u5b9e\u4f53\u8fb9\u754c', 35, ''), ('NEST / UNNEST', 50, 'code'), ('Entity', 25, 'bold'), ('\u72ec\u7acb\u5b9e\u4f53 <-> \u5d4c\u5165\u5bf9\u8c61/\u6570\u7ec4\uff08\u8de8\u5b9e\u4f53\uff09', 0, '')],
        [('\u7c7b\u578b\u7ef4\u5ea6', 35, ''), ('WIND / UNWIND', 50, 'code'), ('Array', 25, 'bold'), ('\u6807\u91cf\u5c5e\u6027 <-> \u6570\u7ec4\u5c5e\u6027\uff08\u7c7b\u578b\u53d8\u6362\uff09', 0, '')],
    ]
    for i, r in enumerate(rows):
        pdf.table_row(r, i)
    pdf.ln(4)

    # ── Object vs Entity vs Array ──
    pdf._font('B', 11)
    pdf.cell(0, 8, 'Object / Entity / Array\uff1a\u54ea\u4e2a\u64cd\u4f5c\u5904\u7406\u4ec0\u4e48\uff1f', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.body_text(
        '6\u4e2a\u64cd\u4f5c\u5904\u7406\u4e09\u79cd\u4e0d\u540c\u7684\u7ed3\u6784\u6982\u5ff5\uff1a\n'
        '  - Object\uff08\u5d4c\u5957\u5bf9\u8c61\uff09\uff1a\u5b9e\u4f53\u5185\u90e8\u7684\u5b50\u7ed3\u6784\uff08\u5982 person \u91cc\u7684 address\uff09\n'
        '  - Entity\uff08\u72ec\u7acb\u5b9e\u4f53\uff09\uff1a\u62e5\u6709\u72ec\u7acb\u8eab\u4efd\u7684\u5b9e\u4f53\uff08\u5982 customers \u8868\uff09\n'
        '  - Array\uff08\u6570\u7ec4/\u96c6\u5408\uff09\uff1a\u591a\u503c\u5c5e\u6027\uff08\u5982 tags[], details[]\uff09')
    pdf.ln(1)
    pdf.table_header([('\u64cd\u4f5c', 28), ('\u8f93\u5165', 22), ('\u8f93\u51fa', 22), ('\u4f5c\u7528', 0)])
    detail = [
        [('FLATTEN', 28, 'code'), ('Object', 22, ''), ('Fields', 22, ''), ('\u5c06\u5d4c\u5957\u5bf9\u8c61\u5c55\u5e73\u4e3a\u5e26\u524d\u7f00\u7684\u5e73\u94fa\u5b57\u6bb5', 0, '')],
        [('UNFLATTEN', 28, 'code'), ('Fields', 22, ''), ('Object', 22, ''), ('\u5c06\u5e73\u94fa\u5b57\u6bb5\u7ec4\u5408\u4e3a\u65b0\u7684\u5d4c\u5957\u5bf9\u8c61', 0, '')],
        [('NEST', 28, 'code'), ('Entity', 22, ''), ('Obj/Array', 22, ''), ('\u5c06\u72ec\u7acb\u5b9e\u4f53\u5438\u6536\u4e3a\u5d4c\u5165\u5bf9\u8c61\u6216\u6570\u7ec4', 0, '')],
        [('UNNEST', 28, 'code'), ('Obj/Array', 22, ''), ('Entity', 22, ''), ('\u5c06\u5d4c\u5165\u5bf9\u8c61/\u6570\u7ec4\u63d0\u53d6\u4e3a\u72ec\u7acb\u5b9e\u4f53', 0, '')],
        [('WIND', 28, 'code'), ('Scalar', 22, ''), ('Array', 22, ''), ('\u5c06\u6807\u91cf\u5c5e\u6027\u5305\u88c5\u4e3a\u6570\u7ec4\u7c7b\u578b', 0, '')],
        [('UNWIND', 28, 'code'), ('Array', 22, ''), ('Scalar', 22, ''), ('\u5c06\u6570\u7ec4\u5c55\u5f00\u4e3a\u6807\u91cf\uff0c\u6216\u63d0\u53d6\u4e3a\u65b0\u5b9e\u4f53', 0, '')],
    ]
    for i, r in enumerate(detail):
        pdf.table_row(r, i)
    pdf.ln(4)

    # ── NEST: object vs array ──
    pdf._font('B', 11)
    pdf.cell(0, 8, 'NEST\uff1a\u4ec0\u4e48\u65f6\u5019\u662f Object\uff0c\u4ec0\u4e48\u65f6\u5019\u662f Array\uff1f', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.body_text('NEST \u6839\u636e\u5916\u952e\u65b9\u5411\u81ea\u52a8\u51b3\u5b9a\u5d4c\u5165\u4e3a object\uff081:1\uff09\u8fd8\u662f array\uff081:N\uff09\uff1a')
    pdf.code_block(NEST_FK_CODE)
    pdf.ln(2)

    # ── 6 operations ──
    pdf.section_title(1, 'FLATTEN  --  \u5d4c\u5957\u5bf9\u8c61 -> \u5e73\u94fa\u5b57\u6bb5', (0, 122, 255))
    pdf.label_value('\u4f5c\u7528\u5bf9\u8c61', '\u5d4c\u5957\u5bf9\u8c61\uff08Embedded Object\uff09')
    pdf.label_value('\u65b9\u5411', '\u6587\u6863\u98ce\u683c -> \u5173\u7cfb\u578b\u98ce\u683c\uff08\u51cf\u5c11\u5d4c\u5957\u6df1\u5ea6 1 \u5c42\uff09')
    pdf.label_value('\u8bed\u6cd5', 'FLATTEN_PS entity.nested_name')
    pdf.label_value('\u9006\u64cd\u4f5c', 'UNFLATTEN')
    pdf.ln(1)
    pdf._font('B', 9); pdf.cell(0, 5, '\u793a\u4f8b\uff1a', new_x="LMARGIN", new_y="NEXT")
    pdf.code_block(FLATTEN_CODE)

    pdf.section_title(2, 'UNFLATTEN  --  \u5e73\u94fa\u5b57\u6bb5 -> \u5d4c\u5957\u5bf9\u8c61', (0, 122, 255))
    pdf.label_value('\u4f5c\u7528\u5bf9\u8c61', '\u5e73\u94fa\u5b57\u6bb5\uff08\u521b\u5efa Object\uff09')
    pdf.label_value('\u65b9\u5411', '\u5173\u7cfb\u578b\u98ce\u683c -> \u6587\u6863\u98ce\u683c\uff08\u589e\u52a0\u5d4c\u5957\u6df1\u5ea6 1 \u5c42\uff09')
    pdf.label_value('\u8bed\u6cd5', 'UNFLATTEN_PS entity:field1, field2, ... AS nested_name')
    pdf.label_value('\u9006\u64cd\u4f5c', 'FLATTEN')
    pdf.ln(1)
    pdf._font('B', 9); pdf.cell(0, 5, '\u793a\u4f8b\uff1a', new_x="LMARGIN", new_y="NEXT")
    pdf.code_block(UNFLATTEN_CODE)

    pdf.section_title(3, 'NEST  --  \u72ec\u7acb\u5b9e\u4f53 -> \u5d4c\u5165\u5bf9\u8c61/\u6570\u7ec4', (255, 59, 48))
    pdf.label_value('\u4f5c\u7528\u5bf9\u8c61', '\u72ec\u7acb\u5b9e\u4f53\uff08\u5408\u5e76\u5230\u7236\u5b9e\u4f53\uff09')
    pdf.label_value('\u8f93\u51fa', 'Object\uff081:1 FK\uff09\u6216 Array\uff081:N FK\uff09-- \u81ea\u52a8\u5224\u5b9a')
    pdf.label_value('\u65b9\u5411', '\u89c4\u8303\u5316\uff08\u591a\u8868\uff09-> \u53cd\u89c4\u8303\u5316\uff08\u5355\u6587\u6863\uff09')
    pdf.label_value('\u8bed\u6cd5', 'NEST_PS source:fields IN target.alias WHERE cond [WITH DELETION]')
    pdf.label_value('\u9006\u64cd\u4f5c', 'UNNEST')
    pdf.ln(1)
    pdf._font('B', 9); pdf.cell(0, 5, '\u793a\u4f8b A\uff1a\u5d4c\u5165\u4e3a Object\uff08target \u6301\u6709 FK\uff09', new_x="LMARGIN", new_y="NEXT")
    pdf.code_block(NEST_OBJ_CODE)
    pdf._font('B', 9); pdf.cell(0, 5, '\u793a\u4f8b B\uff1a\u5d4c\u5165\u4e3a Array\uff08source \u6301\u6709 FK\uff09', new_x="LMARGIN", new_y="NEXT")
    pdf.code_block(NEST_ARR_CODE)

    pdf.section_title(4, 'UNNEST  --  \u5d4c\u5165\u5bf9\u8c61/\u6570\u7ec4 -> \u72ec\u7acb\u5b9e\u4f53', (255, 59, 48))
    pdf.label_value('\u4f5c\u7528\u5bf9\u8c61', '\u5d4c\u5165\u5bf9\u8c61\u6216\u6570\u7ec4\uff08Embedded\uff09')
    pdf.label_value('\u8f93\u51fa', '\u65b0\u7684\u72ec\u7acb\u5b9e\u4f53\uff08\u901a\u8fc7 WITH \u5b50\u53e5\u5efa\u7acb FK\uff09')
    pdf.label_value('\u65b9\u5411', '\u53cd\u89c4\u8303\u5316\uff08\u5355\u6587\u6863\uff09-> \u89c4\u8303\u5316\uff08\u591a\u8868\uff09')
    pdf.label_value('\u8bed\u6cd5', 'UNNEST_PS parent.nested:fields AS entity WITH pk TO fk')
    pdf.label_value('\u9006\u64cd\u4f5c', 'NEST')
    pdf.ln(1)
    pdf._font('B', 9); pdf.cell(0, 5, '\u793a\u4f8b\uff1a', new_x="LMARGIN", new_y="NEXT")
    pdf.code_block(UNNEST_CODE)

    pdf.section_title(5, 'WIND  --  \u6807\u91cf -> \u6570\u7ec4', (52, 199, 89))
    pdf.label_value('\u4f5c\u7528\u5bf9\u8c61', '\u6807\u91cf\u5c5e\u6027\uff08\u8f6c\u6362\u4e3a\u6570\u7ec4\u7c7b\u578b\uff09')
    pdf.label_value('\u65b9\u5411', '\u5173\u7cfb\u578b\uff08\u591a\u884c\u5b58\u50a8\uff09-> \u6587\u6863/\u5217\u5f0f\uff08\u5355\u884c\u6570\u7ec4\uff09')
    pdf.label_value('\u8bed\u6cd5', 'WIND_PS entity.property')
    pdf.label_value('\u9006\u64cd\u4f5c', 'UNWIND')
    pdf.ln(1)
    pdf._font('B', 9); pdf.cell(0, 5, '\u793a\u4f8b\uff1a', new_x="LMARGIN", new_y="NEXT")
    pdf.code_block(WIND_CODE)

    pdf.section_title(6, 'UNWIND  --  \u6570\u7ec4 -> \u6807\u91cf / \u65b0\u5b9e\u4f53', (52, 199, 89))
    pdf.label_value('\u4f5c\u7528\u5bf9\u8c61', '\u6570\u7ec4\u5c5e\u6027')
    pdf.label_value('\u6a21\u5f0f 1', '\u521b\u5efa\u65b0\u5b9e\u4f53\uff1aUNWIND_PS entity.array[] INTO new_entity')
    pdf.label_value('\u6a21\u5f0f 2', '\u539f\u5730\u5c55\u5f00\uff1aUNWIND_PS entity.array\uff08\u6570\u7ec4 -> \u6807\u91cf\uff09')
    pdf.label_value('\u9006\u64cd\u4f5c', 'WIND')
    pdf.ln(1)
    pdf._font('B', 9); pdf.cell(0, 5, '\u793a\u4f8b\uff08\u6a21\u5f0f 1 - \u521b\u5efa\u65b0\u5b9e\u4f53\uff09\uff1a', new_x="LMARGIN", new_y="NEXT")
    pdf.code_block(UNWIND_M1_CODE)
    pdf._font('B', 9); pdf.cell(0, 5, '\u793a\u4f8b\uff08\u6a21\u5f0f 2 - \u539f\u5730\u5c55\u5f00\uff09\uff1a', new_x="LMARGIN", new_y="NEXT")
    pdf.code_block(UNWIND_M2_CODE)

    # ── Summary ──
    pdf.ln(2)
    pdf._font('B', 11)
    pdf.cell(0, 8, '\u9006\u64cd\u4f5c\u5173\u7cfb\u603b\u7ed3', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.table_header([('\u6b63\u5411\u64cd\u4f5c', 45), ('\u9006\u5411\u64cd\u4f5c', 45), ('\u4f5c\u7528\u8303\u56f4', 0)])
    for i, (f, r, s) in enumerate([
        ('FLATTEN', 'UNFLATTEN', '\u540c\u4e00\u5b9e\u4f53\u5185\uff08\u5d4c\u5957\u5bf9\u8c61 <-> \u5e73\u94fa\u5b57\u6bb5\uff09'),
        ('NEST', 'UNNEST', '\u8de8\u5b9e\u4f53\uff08\u5408\u5e76 <-> \u62c6\u5206\uff09'),
        ('WIND', 'UNWIND', '\u7c7b\u578b\u53d8\u6362\uff08\u6807\u91cf <-> \u6570\u7ec4\uff09'),
    ]):
        pdf.table_row([(f, 45, 'code'), (r, 45, 'code'), (s, 0, '')], i)

    pdf.ln(4)
    pdf._font('B', 11)
    pdf.cell(0, 8, '\u8de8\u6a21\u578b\u8fc1\u79fb\u6a21\u5f0f', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.table_header([('\u8fc1\u79fb\u65b9\u5411', 42), ('\u6838\u5fc3\u64cd\u4f5c', 48), ('\u7b56\u7565', 0)])
    for i, (m, o, d) in enumerate([
        ('\u5173\u7cfb\u578b -> \u6587\u6863\u578b', 'UNFLATTEN + NEST', '\u5e73\u94fa\u5b57\u6bb5\u7ec4\u5408\u4e3a\u5bf9\u8c61\uff0c\u7136\u540e\u5408\u5e76\u8868\u4e3a\u6587\u6863'),
        ('\u6587\u6863\u578b -> \u5173\u7cfb\u578b', 'UNNEST + FLATTEN', '\u5d4c\u5165\u5bf9\u8c61\u62c6\u5206\u4e3a\u8868\uff0c\u7136\u540e\u5c55\u5e73\u5d4c\u5957'),
        ('\u5173\u7cfb\u578b -> \u5217\u5f0f', 'WIND + key ops', '\u6dfb\u52a0\u6570\u7ec4\u7c7b\u578b + \u5206\u533a/\u805a\u7c07\u952e'),
        ('\u5217\u5f0f -> \u6587\u6863\u578b', 'Del keys + UNFLATTEN + NEST', '\u5220\u9664 Cassandra \u952e\uff0c\u7136\u540e\u6784\u5efa\u6587\u6863'),
        ('\u5173\u7cfb\u578b -> \u56fe', 'UNNEST + edge ops', '\u521b\u5efa\u8282\u70b9\u548c\u5173\u7cfb\u7c7b\u578b'),
        ('\u6587\u6863\u578b -> \u56fe', 'UNNEST + edge ops', '\u63d0\u53d6\u5d4c\u5165\u5bf9\u8c61\u4e3a\u8282\u70b9\u548c\u8fb9'),
    ]):
        pdf.table_row([(m, 42, 'sm'), (o, 48, 'code_sm'), (d, 0, 'sm')], i)

    pdf.output(path)
    print(f"ZH PDF saved: {path}")


if __name__ == '__main__':
    base = r"C:\Users\baoba\PycharmProjects\MA_Hagen_Lu\schema_evolution_language"
    generate_en(f"{base}\\SMEL_Operations_Reference_EN.pdf")
    generate_zh(f"{base}\\SMEL_Operations_Reference_ZH.pdf")
