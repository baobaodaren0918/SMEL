"""Generate PDF of all 16 Northwind Pauschalisiert SMEL scripts for printing."""
from fpdf import FPDF
from pathlib import Path

class SmelPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 6, "Northwind SMEL Scripts (Pauschalisiert)", align="C", new_x="LMARGIN", new_y="NEXT")
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
    "northwind_pg1_to_pg2.smel_ps",
    "northwind_mongo1_to_mongo2.smel_ps",
    "northwind_graph1_to_graph2.smel_ps",
    "northwind_cass1_to_cass2.smel_ps",
    # Cross-model R<->D (2)
    "northwind_pg_to_mongo.smel_ps",
    "northwind_mongo_to_pg.smel_ps",
    # Cross-model R<->G (2)
    "northwind_pg_to_neo4j.smel_ps",
    "northwind_neo4j_to_pg.smel_ps",
    # Cross-model R<->C (2)
    "northwind_pg_to_cass.smel_ps",
    "northwind_cass_to_pg.smel_ps",
    # Cross-model D<->G (2)
    "northwind_mongo_to_neo4j.smel_ps",
    "northwind_neo4j_to_mongo.smel_ps",
    # Cross-model D<->C (2)
    "northwind_mongo_to_cass.smel_ps",
    "northwind_cass_to_mongo.smel_ps",
    # Cross-model G<->C (2)
    "northwind_neo4j_to_cass.smel_ps",
    "northwind_cass_to_neo4j.smel_ps",
]

base = Path(__file__).parent / "tests" / "pauschalisiert"

pdf = SmelPDF(orientation="P", unit="mm", format="A4")
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

out_path = "tests/Northwind_SMEL_16_Pauschalisiert_v2.pdf"
pdf.output(out_path)
print(f"PDF generated: {out_path}  ({len(scripts)} scripts, {pdf.page_no()} pages)")
