"""Generate PDF of all 16 Northwind Generalized SMILE scripts for printing."""
from fpdf import FPDF
from pathlib import Path

class SmilePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 6, "Northwind SMILE Scripts (Generalized)", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def script_title(self, title):
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(220, 220, 220)
        self.cell(0, 6, title, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def code_block(self, text):
        self.set_font("Courier", "", 6.5)
        for line in text.rstrip().split("\n"):
            # Truncate very long lines
            if len(line) > 160:
                line = line[:157] + "..."
            self.cell(0, 3.2, "  " + line, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)


# Ordered list: same-model first, then cross-model
scripts = [
    # Same-model (4)
    "northwind_pg1_to_pg2.smile_gen",
    "northwind_mongo1_to_mongo2.smile_gen",
    "northwind_graph1_to_graph2.smile_gen",
    "northwind_cass1_to_cass2.smile_gen",
    # Cross-model R<->D (2)
    "northwind_pg_to_mongo.smile_gen",
    "northwind_mongo_to_pg.smile_gen",
    # Cross-model R<->G (2)
    "northwind_pg_to_neo4j.smile_gen",
    "northwind_neo4j_to_pg.smile_gen",
    # Cross-model R<->C (2)
    "northwind_pg_to_cass.smile_gen",
    "northwind_cass_to_pg.smile_gen",
    # Cross-model D<->G (2)
    "northwind_mongo_to_neo4j.smile_gen",
    "northwind_neo4j_to_mongo.smile_gen",
    # Cross-model D<->C (2)
    "northwind_mongo_to_cass.smile_gen",
    "northwind_cass_to_mongo.smile_gen",
    # Cross-model G<->C (2)
    "northwind_neo4j_to_cass.smile_gen",
    "northwind_cass_to_neo4j.smile_gen",
]

base = Path(__file__).parent / "tests" / "generalized"

pdf = SmilePDF(orientation="P", unit="mm", format="A4")
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=12)

for i, fname in enumerate(scripts, 1):
    fpath = base / fname
    content = fpath.read_text(encoding="utf-8")

    pdf.add_page()
    # Display name from first comment line
    first_line = content.split("\n")[0].lstrip("- ").strip()
    title = f"{i}/16  {fname}"
    pdf.script_title(title)
    pdf.code_block(content)

out_path = "tests/Northwind_SMILE_16_Generalized_v2.pdf"
pdf.output(out_path)
print(f"PDF generated: {out_path}  ({len(scripts)} scripts, {pdf.page_no()} pages)")
