"""
SMEL Web Server - Web interface for schema migration visualization.
Run this file and open http://localhost:5582 in your browser.
"""
import sys
import json
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs
import threading
import webbrowser

sys.path.insert(0, str(Path(__file__).parent))

from core import run_migration
from config import MIGRATION_CONFIGS, DB_TYPE_EXPORT_LABEL

PORT = 5586


class SMELHandler(SimpleHTTPRequestHandler):
    """HTTP request handler for SMEL web interface."""

    def do_GET(self):
        try:
            if self.path == '/' or self.path == '/index.html':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                self.end_headers()
                self.wfile.write(get_html().encode())
            elif self.path.startswith('/api/schemas'):
                schema_files = {
                    'postgresql': 'tests/northwind_postgresql.sql',
                    'mongodb': 'tests/northwind_mongodb.json',
                    'neo4j': 'tests/northwind_neo4j.cypher',
                    'cassandra': 'tests/northwind_cassandra.cql',
                }
                result = {}
                base = Path(__file__).parent
                for key, rel_path in schema_files.items():
                    fpath = base / rel_path
                    try:
                        result[key] = fpath.read_text(encoding='utf-8')
                    except Exception as e:
                        result[key] = f'Error reading {rel_path}: {e}'

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            elif self.path.startswith('/api/migrate'):
                query = self.path.split('?')[1] if '?' in self.path else ''
                params = parse_qs(query)
                direction = params.get('direction', ['person_d2r_pauschalisiert'])[0]

                try:
                    result = run_migration(direction)
                except Exception as e:
                    result = {"error": f"Migration failed: {e}"}

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            else:
                super().do_GET()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass  # Browser closed connection early — harmless on Windows

    def log_message(self, format, *args):
        pass


def _build_dropdown_options() -> str:
    """Generate <optgroup>/<option> HTML tags from MIGRATION_CONFIGS."""
    person, nw_evo, nw_cross = [], [], []
    for key, cfg in MIGRATION_CONFIGS.items():
        display = cfg["display_name"]
        selected = ' selected' if key == "person_d2r_pauschalisiert" else ''
        tag = f'<option value="{key}"{selected}>{display}</option>'
        if key.startswith("person_"):
            person.append(tag)
        elif key.startswith("northwind_") and cfg["source_type"] == cfg["target_type"]:
            nw_evo.append(tag)
        else:
            nw_cross.append(tag)
    nl = '\n                        '
    html = f'<optgroup label="Person (Mini-Beispiel)">{nl}{nl.join(person)}{nl}</optgroup>'
    if nw_evo:
        html += f'\n                    <optgroup label="Northwind (Schema Evolution)">{nl}{nl.join(nw_evo)}{nl}</optgroup>'
    if nw_cross:
        html += f'\n                    <optgroup label="Northwind (Cross-Model Migration)">{nl}{nl.join(nw_cross)}{nl}</optgroup>'
    return html


def _build_config_js() -> str:
    """Generate JavaScript constant for DB_TYPE_EXPORT_LABEL from config.py."""
    return f"const DB_TYPE_EXPORT_LABEL = {json.dumps(DB_TYPE_EXPORT_LABEL)};"


def get_html():
    """Return the HTML page with Apple-style design."""
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>SMEL - Schema Migration Viewer</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, sans-serif;
            background: #FFFFFF;
            min-height: 100vh;
            color: #1D1D1F;
            -webkit-font-smoothing: antialiased;
        }

        .header {
            background: #FFFFFF;
            border-bottom: 1px solid #E8E8ED;
            padding: 32px 48px;
            position: sticky;
            top: 0;
            z-index: 100;
            text-align: center;
        }

        .header h1 { font-size: 28px; font-weight: 600; color: #1D1D1F; letter-spacing: -0.3px; }
        .header p { font-size: 14px; color: #636366; margin-top: 8px; }

        .controls {
            display: flex;
            align-items: center;
            gap: 24px;
            padding: 24px 48px;
            background: #FFFFFF;
            border-bottom: 1px solid #E8E8ED;
        }

        .control-group { display: flex; align-items: center; gap: 12px; }
        .control-label { font-size: 15px; font-weight: 500; color: #636366; }

        .dropdown { position: relative; min-width: 380px; }
        .dropdown select {
            width: 100%;
            padding: 12px 44px 12px 16px;
            border: 1px solid #E8E8ED;
            border-radius: 12px;
            background: #F5F5F7;
            font-size: 15px;
            font-weight: 500;
            color: #1D1D1F;
            cursor: pointer;
            appearance: none;
            transition: all 0.2s;
        }
        .dropdown select:hover { border-color: #0066CC; }
        .dropdown select:focus { outline: none; border-color: #0066CC; }
        .dropdown select optgroup { font-weight: 600; font-size: 13px; color: #636366; }
        .dropdown select option { font-weight: 400; font-size: 14px; color: #1D1D1F; padding: 4px 8px; }
        .dropdown::after {
            content: '';
            position: absolute;
            right: 16px;
            top: 50%;
            transform: translateY(-50%);
            border: 5px solid transparent;
            border-top-color: #636366;
            pointer-events: none;
        }

        .run-btn {
            padding: 12px 28px;
            background: #0066CC;
            border: none;
            border-radius: 12px;
            color: white;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .run-btn:hover { background: #0055AA; }

        .tab-nav {
            display: none;
            gap: 0;
            padding: 0 48px;
            background: #FFFFFF;
            border-bottom: 1px solid #E8E8ED;
        }
        .tab-nav.show { display: flex; }

        .tab-btn {
            padding: 16px 28px;
            background: none;
            border: none;
            font-size: 15px;
            font-weight: 500;
            color: #636366;
            cursor: pointer;
            position: relative;
            transition: all 0.2s;
        }
        .tab-btn:hover { color: #1D1D1F; }
        .tab-btn.active { color: #0066CC; }
        .tab-btn.active::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: #0066CC;
        }

        .tab-content { display: none; }
        .tab-content.active { display: block; }

        .loading {
            display: none;
            padding: 120px 48px;
            text-align: center;
            color: #636366;
        }
        .loading.show { display: block; }
        .loading .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid #E8E8ED;
            border-top-color: #0066CC;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        .welcome { padding: 160px 48px; text-align: center; }
        .welcome h2 { font-size: 28px; color: #1D1D1F; margin-bottom: 12px; font-weight: 600; }
        .welcome p { font-size: 17px; color: #636366; }

        .schema-compare {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1px;
            background: #E8E8ED;
            min-height: calc(100vh - 200px);
        }

        .schema-panel { background: #FFFFFF; padding: 32px; overflow-y: auto; }

        .panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 32px;
        }
        .panel-title { font-size: 22px; font-weight: 600; color: #1D1D1F; }

        .schema-badge {
            padding: 6px 14px;
            border-radius: 16px;
            font-size: 13px;
            font-weight: 600;
            background: #F5F5F7;
            color: #636366;
        }
        .schema-badge.relational { background: #F5F5F7; color: #0066CC; }
        .schema-badge.document { background: #F5F5F7; color: #BF4800; }
        .schema-badge.graph { background: #F5F5F7; color: #34A853; }
        .schema-badge.columnar { background: #F5F5F7; color: #8E24AA; }

        .er-section { margin-bottom: 40px; }
        .section-title {
            font-size: 13px;
            font-weight: 600;
            color: #636366;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 16px;
        }

        .er-diagram {
            background: #F5F5F7;
            border-radius: 16px;
            padding: 24px;
            min-height: 300px;
            overflow: auto;
        }
        .er-diagram svg { display: block; margin: 0 auto; }
        .er-diagram .node circle { fill: #E8F5E9; stroke: #34A853; }
        .er-diagram .edgeLabel { font-size: 12px; background: #fff; }

        /* Graph SVG Circular Layout */
        .graph-svg-container { display: flex; justify-content: center; padding: 8px 0; }
        .graph-svg-container svg { max-height: 600px; }
        /* Compact graph in 4-column target column */
        .graph-compact .graph-svg-container svg { max-height: 260px; }
        .graph-compact { min-height: auto; padding: 8px; }

        /* Chebotko Diagram (Cassandra) */
        .chebotko-diagram {
            display: flex;
            flex-wrap: wrap;
            gap: 24px;
            padding: 24px;
            background: #F5F5F7;
            border-radius: 16px;
        }
        .chebotko-table {
            background: #fff;
            border-radius: 10px;
            border: 2px solid #8E24AA;
            overflow: hidden;
            min-width: 180px;
            max-width: 240px;
            flex: 1;
        }
        .chebotko-header {
            background: #8E24AA;
            color: #fff;
            font-weight: 600;
            font-size: 14px;
            padding: 8px 16px;
            text-align: center;
        }
        .chebotko-cols { width: 100%; border-collapse: collapse; }
        .chebotko-cols tr { border-bottom: 1px solid #E8E8ED; }
        .chebotko-cols tr:last-child { border-bottom: none; }
        .chebotko-cols td { padding: 6px 10px; font-size: 13px; }
        .ck-marker-cell { width: 30px; text-align: center; }
        .ck-marker { font-weight: 700; font-size: 12px; }
        .ck-marker.pk { color: #8E24AA; }
        .ck-marker.ck { color: #0066CC; }
        .ck-name { font-weight: 500; }
        .ck-type { color: #636366; font-family: 'SF Mono', monospace; font-size: 12px; }

        .document-view {
            background: #F5F5F7;
            border-radius: 16px;
            padding: 24px;
            overflow-x: auto;
            border: 1px solid #E8E8ED;
        }

        .json-display {
            font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
            font-size: 13px;
            line-height: 1.7;
            color: #1D1D1F;
            white-space: pre-wrap;
            word-break: break-word;
        }
        .json-key { color: #0066CC; }
        .json-string { color: #BF4800; }
        .json-number { color: #34C759; }
        .json-bracket { color: #AF52DE; }

        .sql-section { margin-bottom: 40px; }
        .sql-code-view {
            background: #F5F5F7;
            border-radius: 16px;
            padding: 24px;
            overflow-x: auto;
            border: 1px solid #E8E8ED;
        }
        .sql-code-view pre {
            font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
            font-size: 13px;
            line-height: 1.7;
            color: #1D1D1F;
            white-space: pre-wrap;
            word-break: break-word;
            margin: 0;
        }
        .schema-view {
            background: #F5F5F7;
            border-radius: 12px;
            padding: 16px;
            overflow-x: auto;
            max-height: 600px;
            overflow-y: auto;
            border: 1px solid #E8E8ED;
        }
        .schema-code {
            font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
            font-size: 11px;
            line-height: 1.6;
            color: #1D1D1F;
            white-space: pre-wrap;
            word-break: break-word;
            margin: 0;
        }

        .migration-content { padding: 32px 48px; }

        .legend { display: flex; gap: 32px; margin-bottom: 32px; }
        .legend-item { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #636366; }
        .legend-dot { width: 10px; height: 10px; border-radius: 50%; }
        .legend-dot.new { background: #34C759; }
        .legend-dot.reference { background: #0066CC; }
        .legend-dot.embedded { background: #BF4800; }
        .legend-dot.edge { background: #8B5CF6; }
        .legend-dot.pk { background: #AF52DE; }

        .migration-layout { display: flex; gap: 24px; align-items: flex-start; }
        .meta-columns { flex: 3; min-width: 0; }
        .target-column {
            flex: 1;
            min-width: 320px;
            max-width: 400px;
            background: #F5F5F7;
            border-radius: 16px;
            overflow: hidden;
        }

        .target-header { padding: 20px; background: #0066CC; text-align: center; }
        .target-header h3 { font-size: 17px; font-weight: 600; color: #FFFFFF; }
        .target-header .subtitle { font-size: 14px; color: rgba(255, 255, 255, 0.7); margin-top: 4px; }

        .target-content { padding: 16px; max-height: 800px; overflow-y: auto; }

        .sql-display {
            background: #FFFFFF;
            border-radius: 12px;
            padding: 16px;
            border: 1px solid #E8E8ED;
        }
        .sql-display pre {
            font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
            font-size: 12px;
            line-height: 1.6;
            color: #1D1D1F;
            white-space: pre-wrap;
            word-break: break-word;
            margin: 0;
        }

        .json-display-box {
            background: #FFFFFF;
            border-radius: 12px;
            padding: 16px;
            border: 1px solid #E8E8ED;
            font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
            font-size: 12px;
            line-height: 1.6;
            color: #1D1D1F;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .target-er-section { margin-bottom: 16px; }
        .target-sql-section { margin-top: 16px; }
        .target-section-title {
            font-size: 12px;
            font-weight: 600;
            color: #636366;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
        }
        .target-er-diagram {
            background: #FFFFFF;
            border-radius: 12px;
            padding: 16px;
            border: 1px solid #E8E8ED;
            overflow: auto;
            min-height: 200px;
        }
        .target-er-diagram svg { display: block; margin: 0 auto; max-width: 100%; }

        .schema-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1px;
            background: #E8E8ED;
            border-radius: 16px;
            overflow: hidden;
        }

        /* Four-column layout for Migration Process */
        .four-column-layout {
            display: flex;
            gap: 12px;
            padding: 0;
        }

        .independent-column {
            flex: 1;
            min-width: 200px;
            max-width: 280px;
            background: #F5F5F7;
            border-radius: 16px;
            overflow: hidden;
        }

        .independent-column .column-header {
            padding: 12px;
            background: #FFFFFF;
            border-bottom: 1px solid #E8E8ED;
            text-align: center;
        }

        .independent-column .column-content {
            padding: 12px;
            max-height: 700px;
            overflow-y: auto;
        }

        .independent-column .entity-card {
            margin-bottom: 8px;
        }

        /* Dense layout for schemas with 7+ entities */
        .four-column-layout.dense-layout .independent-column { max-width: 320px; }
        .four-column-layout.dense-layout .column-content { max-height: 900px; }
        .four-column-layout.dense-layout .attribute { padding: 3px 0; font-size: 13px; }
        .four-column-layout.dense-layout .attr-name { font-size: 13px; }
        .four-column-layout.dense-layout .entity-name { padding: 10px 12px; font-size: 14px; }
        .four-column-layout.dense-layout .entity-body { padding: 8px 12px; }
        .four-column-layout.dense-layout .entity-card { margin-bottom: 6px; }

        .meta-aligned-columns {
            flex: 2;
            min-width: 0;
        }

        .meta-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1px;
            background: #E8E8ED;
            border-radius: 16px;
            overflow: hidden;
        }

        .meta-grid .column-header {
            padding: 12px;
            background: #F5F5F7;
            text-align: center;
        }

        .meta-grid .grid-cell {
            background: #FFFFFF;
            padding: 8px;
        }

        .sql-code-box {
            background: #FFFFFF;
            border-radius: 12px;
            padding: 16px;
            border: 1px solid #E8E8ED;
            overflow-x: auto;
        }

        .sql-code-box pre {
            font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
            font-size: 11px;
            line-height: 1.5;
            color: #1D1D1F;
            white-space: pre-wrap;
            word-break: break-word;
            margin: 0;
        }

        .grid-cell { background: #FFFFFF; padding: 12px; }

        .column-header { padding: 20px; background: #F5F5F7; text-align: center; }
        .column-header h3 { font-size: 17px; font-weight: 600; color: #1D1D1F; }
        .column-header .subtitle { font-size: 14px; color: #636366; margin-top: 4px; }

        .entity-card { background: #F5F5F7; border-radius: 12px; margin-bottom: 12px; overflow: hidden; }
        .entity-card.new { background: #F0FFF4; border: 1px solid #34C759; }

        .entity-name {
            padding: 12px 14px;
            background: #FFFFFF;
            border-bottom: 1px solid #E8E8ED;
            font-weight: 600;
            font-size: 15px;
            color: #1D1D1F;
        }
        .entity-name.new { color: #34C759; }

        .entity-body { padding: 10px 14px; }

        .attribute { display: flex; align-items: center; padding: 4px 0; font-size: 14px; }
        .attr-name { flex: 1; font-weight: 500; color: #1D1D1F; font-size: 14px; }
        .attr-type { color: #636366; font-size: 13px; }

        /* Nested object styling - makes hierarchy obvious like JSON */
        .attribute.nested-object {
            background: #F5F5F7;
            padding: 6px 8px;
            border-radius: 6px;
            margin: 4px 0;
            font-weight: 600;
        }
        .attribute.nested-object .attr-type {
            color: #AF52DE;
            font-weight: 600;
        }
        .nested-level-1 { margin-left: 16px; border-left: 3px solid #E8E8ED; padding-left: 12px; }
        .nested-level-2 { margin-left: 32px; border-left: 3px solid #D1D1D6; padding-left: 12px; }
        .nested-level-3 { margin-left: 48px; border-left: 3px solid #C7C7CC; padding-left: 12px; }
        .attr-badge {
            font-size: 9px;
            font-weight: 600;
            padding: 2px 5px;
            border-radius: 3px;
            margin-left: 4px;
        }
        .attr-badge.pk { background: #AF52DE; color: white; }
        .attr-badge.optional { background: #E8E8ED; color: #636366; }

        .reference-item {
            display: flex;
            align-items: center;
            padding: 6px 10px;
            margin: 4px 0;
            background: rgba(0, 102, 204, 0.08);
            border-radius: 6px;
            font-size: 13px;
            color: #0066CC;
        }

        .embedded-item {
            display: flex;
            align-items: center;
            padding: 6px 10px;
            margin: 4px 0;
            background: rgba(191, 72, 0, 0.08);
            border-radius: 6px;
            font-size: 13px;
            color: #BF4800;
        }

        .edge-item {
            display: flex;
            align-items: center;
            padding: 6px 10px;
            margin: 4px 0;
            background: rgba(139, 92, 246, 0.08);
            border-radius: 6px;
            font-size: 13px;
            color: #8B5CF6;
        }

        .placeholder { padding: 14px; text-align: center; color: #636366; font-size: 14px; background: #F5F5F7; border-radius: 12px; margin-bottom: 12px; }
        .placeholder-card { background: #F5F5F7; opacity: 0.6; }
        .placeholder-name { color: #636366; font-style: italic; }
        .placeholder-body { padding: 20px 14px; text-align: center; color: #636366; font-size: 13px; }

        .validation { margin-top: 40px; padding: 28px; background: #F5F5F7; border-radius: 16px; }
        .validation-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
        .validation h2 { font-size: 18px; font-weight: 600; color: #1D1D1F; }
        .validation-status { padding: 8px 16px; border-radius: 16px; font-weight: 600; font-size: 14px; }
        .validation-status.passed { background: rgba(52, 199, 89, 0.1); color: #34C759; }
        .validation-status.failed { background: rgba(255, 59, 48, 0.1); color: #FF3B30; }

        .validation-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
        .stat-card { padding: 20px; background: #FFFFFF; border-radius: 12px; text-align: center; }
        .stat-value { font-size: 28px; font-weight: 700; color: #1D1D1F; }
        .stat-label { font-size: 13px; color: #636366; margin-top: 4px; }

        .footer { text-align: center; padding: 48px; color: #636366; font-size: 13px; }

        /* SMEL Script Tab Styles */
        .smel-content { padding: 32px 48px; }

        .smel-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }

        .smel-panel {
            background: #FFFFFF;
            border-radius: 16px;
            border: 1px solid #E8E8ED;
            overflow: hidden;
        }

        .smel-panel-header {
            padding: 20px 24px;
            background: #F5F5F7;
            border-bottom: 1px solid #E8E8ED;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .smel-panel-title {
            font-size: 17px;
            font-weight: 600;
            color: #1D1D1F;
        }

        .smel-file-badge {
            padding: 6px 12px;
            background: #0066CC;
            color: white;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
        }

        .smel-panel-body {
            padding: 24px;
            max-height: 600px;
            overflow-y: auto;
        }

        .smel-code {
            font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
            font-size: 13px;
            line-height: 1.8;
            color: #1D1D1F;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .smel-keyword { color: #0066CC; font-weight: 600; }
        .smel-comment { color: #636366; font-style: italic; }
        .smel-string { color: #BF4800; }
        .smel-number { color: #34C759; }
        .smel-type { color: #AF52DE; }

        .operations-list { display: flex; flex-direction: column; gap: 12px; }

        .operation-item {
            background: #F5F5F7;
            border-radius: 12px;
            padding: 16px;
            border-left: 4px solid #0066CC;
        }

        .operation-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
        }

        .operation-step {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .step-number {
            width: 28px;
            height: 28px;
            background: #0066CC;
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
            font-weight: 600;
        }

        .operation-type {
            font-size: 15px;
            font-weight: 600;
            color: #1D1D1F;
        }

        .operation-badge {
            padding: 4px 10px;
            background: #E8E8ED;
            border-radius: 6px;
            font-size: 12px;
            color: #636366;
        }

        .operation-badge.changed { background: rgba(52, 199, 89, 0.15); color: #34C759; }

        .operation-params {
            font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
            font-size: 13px;
            color: #636366;
            padding-left: 38px;
        }

        .operation-param { margin: 4px 0; }
        .param-key { color: #0066CC; }
        .param-value { color: #1D1D1F; }

        .smel-summary {
            margin-top: 24px;
            padding: 20px;
            background: #F5F5F7;
            border-radius: 12px;
            display: flex;
            gap: 32px;
        }

        .summary-item { text-align: center; }
        .summary-value { font-size: 24px; font-weight: 700; color: #0066CC; }
        .summary-label { font-size: 13px; color: #636366; margin-top: 4px; }

        .validation-section {
            margin-top: 24px;
            padding: 20px 24px;
            background: #FFFFFF;
            border-radius: 12px;
            border: 1px solid #E8E8ED;
        }
        .validation-section-title {
            font-size: 15px;
            font-weight: 600;
            color: #1D1D1F;
            margin-bottom: 16px;
        }
        .validation-layer {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 0;
            border-bottom: 1px solid #F0F0F5;
        }
        .validation-layer:last-child { border-bottom: none; }
        .validation-layer-label {
            font-size: 13px;
            font-weight: 500;
            color: #636366;
            min-width: 180px;
        }
        .validation-badge {
            padding: 4px 12px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
        }
        .validation-badge.pass { background: rgba(52, 199, 89, 0.12); color: #248A3D; }
        .validation-badge.fail { background: rgba(255, 59, 48, 0.12); color: #D70015; }
        .validation-badge.na { background: #F0F0F5; color: #8E8E93; }
        .validation-details {
            margin-top: 8px;
            padding: 12px 16px;
            background: #FFF5F5;
            border-radius: 8px;
            font-size: 12px;
            color: #636366;
            font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
        }
        .validation-details .detail-entity {
            margin: 4px 0;
            padding-left: 8px;
            border-left: 2px solid #FF3B30;
        }
        .validation-warnings {
            margin-top: 8px;
            padding: 12px 16px;
            background: #FFFAF0;
            border-radius: 8px;
            font-size: 12px;
            color: #636366;
            font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
        }
        .validation-warnings .detail-entity {
            margin: 4px 0;
            padding-left: 8px;
            border-left: 2px solid #F39C12;
        }

        /* Expand/Collapse styles */
        .toggle-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            margin-top: 8px;
            margin-left: 38px;
            background: #E8E8ED;
            border: none;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
            color: #636366;
            cursor: pointer;
            transition: all 0.2s;
        }
        .toggle-btn:hover { background: #D1D1D6; color: #1D1D1F; }
        .toggle-btn .arrow { font-size: 10px; }

        .changes-detail {
            display: none;
            margin-top: 12px;
            margin-left: 38px;
            padding: 16px;
            background: #FFFFFF;
            border-radius: 10px;
            border: 1px solid #E8E8ED;
        }
        .changes-detail.show { display: block; }

        .affected-entity {
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid #F5F5F7;
        }
        .affected-entity:last-child { margin-bottom: 0; padding-bottom: 0; border-bottom: none; }

        .entity-name-header {
            font-size: 14px;
            font-weight: 600;
            color: #1D1D1F;
            margin-bottom: 8px;
        }
        .entity-name-header.new { color: #34C759; }
        .entity-name-header.deleted { color: #FF3B30; text-decoration: line-through; }

        .change-item {
            display: flex;
            align-items: center;
            padding: 4px 0;
            font-size: 13px;
            font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
        }
        .change-item.new { color: #34C759; }
        .change-item.deleted { color: #FF3B30; text-decoration: line-through; }

        .change-prefix {
            width: 20px;
            font-weight: 600;
        }
        .change-prefix.add { color: #34C759; }
        .change-prefix.remove { color: #FF3B30; }

        .change-label {
            margin-left: 8px;
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
            background: rgba(52, 199, 89, 0.15);
            color: #34C759;
        }
        .change-label.deleted {
            background: rgba(255, 59, 48, 0.15);
            color: #FF3B30;
        }

        .no-changes {
            font-size: 13px;
            color: #636366;
            font-style: italic;
        }

        /* Source Schemas Tab */
        .source-schemas-page { padding: 32px 48px; }
        .source-schemas-page .schema-section {
            margin-bottom: 48px;
            padding-bottom: 48px;
            border-bottom: 1px solid #E8E8ED;
        }
        .source-schemas-page .schema-section:last-child { border-bottom: none; margin-bottom: 0; }
        .schema-section-header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 24px;
        }
        .schema-section-header h2 {
            font-size: 22px;
            font-weight: 600;
            color: #1D1D1F;
        }
        .schema-section-header .schema-badge { font-size: 14px; }
        .schema-section-subtitle {
            font-size: 14px;
            color: #636366;
            margin-bottom: 24px;
        }
        .schema-section .vis-and-code {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }
        .schema-section .vis-block,
        .schema-section .code-block-wrapper {
            min-width: 0;
        }
        .schema-section .code-block-wrapper .sql-code-view {
            max-height: 600px;
            overflow-y: auto;
        }
        /* Full-width code block when no side-by-side visualization */
        .schema-section .vis-and-code.full-width { grid-template-columns: 1fr; }

        /* Document tree for MongoDB source schemas */
        .document-tree {
            font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
            font-size: 13px;
            line-height: 1.8;
            color: #1D1D1F;
            background: #F5F5F7;
            border-radius: 16px;
            padding: 24px;
            border: 1px solid #E8E8ED;
            white-space: pre-wrap;
        }
        .document-tree .dt-key { color: #0066CC; font-weight: 600; }
        .document-tree .dt-type { color: #636366; }
        .document-tree .dt-obj { color: #AF52DE; font-weight: 600; }
        .document-tree .dt-arr { color: #BF4800; font-weight: 600; }
        .document-tree .dt-comment { color: #636366; font-style: italic; font-size: 12px; }
    </style>
</head>
<body>
    <header class="header">
        <h1>Schema Migration & Evolution Viewer</h1>
        <p>SMEL - Schema Migration & Evolution Language</p>
    </header>

    <div class="controls">
        <div class="control-group">
            <span class="control-label">Migration Direction</span>
            <div class="dropdown">
                <select id="directionSelect">
                    <!-- DROPDOWN_OPTIONS -->
                </select>
            </div>
        </div>
        <button class="run-btn" onclick="runMigration()">Run</button>
    </div>

    <div class="loading" id="loading">
        <div class="spinner"></div>
        <p>Running schema transformation...</p>
    </div>

    <div class="welcome" id="welcome" style="display:none;">
        <h2>Select migration or evolution and click Run</h2>
        <p>Compare source and target schemas side by side</p>
    </div>

    <nav class="tab-nav show" id="tabNav">
        <button class="tab-btn active" data-tab="schemas">Source Schemas</button>
        <button class="tab-btn" data-tab="compare">Schema Comparison</button>
        <button class="tab-btn" data-tab="smel">SMEL Script</button>
        <button class="tab-btn" data-tab="migration">Migration / Evolution Process</button>
    </nav>

    <div class="tab-content active" id="tab-schemas"></div>
    <div class="tab-content" id="tab-compare"></div>
    <div class="tab-content" id="tab-smel"></div>
    <div class="tab-content" id="tab-migration"></div>

    <footer class="footer">SMEL - Schema Migration & Evolution Language</footer>

    <script>
        // INJECT_CONFIG
        let mermaidReady = false;
        try {
            if (typeof mermaid !== 'undefined') {
                mermaid.initialize({
                    startOnLoad: false,
                    theme: 'base',
                    themeVariables: {
                        primaryColor: '#E8F0FE',
                        primaryTextColor: '#1D1D1F',
                        primaryBorderColor: '#007AFF',
                        lineColor: '#007AFF',
                        secondaryColor: '#FFFFFF',
                        tertiaryColor: '#F5F5F7',
                        background: '#FFFFFF',
                        mainBkg: '#FFFFFF',
                        fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
                        fontSize: '14px'
                    },
                    er: { useMaxWidth: true, layoutDirection: 'LR', entityPadding: 12, fontSize: 13 }
                });
                mermaidReady = true;
            }
        } catch (e) { console.warn('Mermaid init failed:', e); }

        let migrationData = null;

        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
            });
        });

        async function runMigration() {
            const direction = document.getElementById('directionSelect').value;
            document.getElementById('welcome').style.display = 'none';
            document.getElementById('loading').classList.add('show');
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            try {
                const response = await fetch('/api/migrate?direction=' + direction + '&t=' + Date.now());
                migrationData = await response.json();
                document.getElementById('loading').classList.remove('show');

                if (migrationData.error) { alert(migrationData.error); return; }

                renderCompareView();
                renderSmelScript();
                renderMigrationProcess();
                document.querySelector('.tab-btn[data-tab="compare"]').click();
            } catch (error) {
                document.getElementById('loading').classList.remove('show');
                alert('Error: ' + error.message);
            }
        }

        function getBadgeClass(sourceType) {
            return sourceType ? sourceType.toLowerCase() : 'document';
        }

        function isDDLType(sourceType) {
            return sourceType === 'Relational' || sourceType === 'Columnar';
        }

        function renderCompareView() {
            const container = document.getElementById('tab-compare');
            const sourceType = migrationData.source_type;
            const targetType = migrationData.target_type;

            let html = '<div class="schema-compare">';
            html += '<div class="schema-panel">';
            html += '<div class="panel-header"><span class="panel-title">Source Schema</span>';
            html += '<span class="schema-badge ' + getBadgeClass(sourceType) + '">' + sourceType + '</span></div>';

            if (sourceType === 'Relational') {
                // Relational Source: Original SQL DDL
                html += '<div class="sql-section"><div class="section-title">Original DDL</div>';
                html += '<div class="sql-code-view"><pre>' + escapeHtml(migrationData.raw_source) + '</pre></div></div>';
            } else if (sourceType === 'Graph') {
                // Graph Source: Graph Diagram + Original Cypher DDL
                const sourceEntities = migrationData.meta_v1 || {};
                html += '<div class="er-section"><div class="section-title">Graph Diagram</div>';
                html += '<div class="er-diagram">' + generateGraphDiagram(sourceEntities) + '</div></div>';
                html += '<div class="sql-section"><div class="section-title">Neo4j Cypher</div>';
                html += '<div class="sql-code-view"><pre>' + escapeHtml(migrationData.raw_source) + '</pre></div></div>';
            } else if (sourceType === 'Columnar') {
                // Columnar Source: Chebotko Diagram + Original CQL
                const sourceEntities = migrationData.meta_v1 || {};
                html += '<div class="er-section"><div class="section-title">Chebotko Diagram</div>';
                html += generateChebotkoDiagram(sourceEntities);
                html += '</div>';
                html += '<div class="sql-section"><div class="section-title">Original CQL</div>';
                html += '<div class="sql-code-view"><pre>' + escapeHtml(migrationData.raw_source) + '</pre></div></div>';
            } else {
                // Document Source: Original JSON schema
                html += '<div class="document-view"><div class="json-display">' + syntaxHighlightJSON(migrationData.raw_source) + '</div></div>';
            }
            html += '</div>';

            html += '<div class="schema-panel">';
            html += '<div class="panel-header"><span class="panel-title">Target Schema</span>';
            html += '<span class="schema-badge ' + getBadgeClass(targetType) + '">' + targetType + '</span></div>';

            // Use centralized export label from config (injected by Python)
            const exportLabel = (typeof DB_TYPE_EXPORT_LABEL !== 'undefined' && DB_TYPE_EXPORT_LABEL[targetType])
                ? DB_TYPE_EXPORT_LABEL[targetType]
                : (targetType + ' Schema');

            if (targetType === 'Relational') {
                // Relational Target: ER Diagram + Generated DDL
                const targetEntities = migrationData.target_with_db_types || migrationData.result;
                html += '<div class="er-section"><div class="section-title">ER Diagram</div>';
                html += '<div class="er-diagram">' + generateERDiagram(targetEntities) + '</div></div>';
                html += '<div class="sql-section"><div class="section-title">' + exportLabel + '</div>';
                html += '<div class="sql-code-view"><pre>' + escapeHtml(migrationData.exported_target) + '</pre></div></div>';
            } else if (targetType === 'Graph') {
                // Graph Target: Graph Diagram + Generated Cypher
                const targetEntities = migrationData.target_with_db_types || migrationData.result;
                html += '<div class="er-section"><div class="section-title">Graph Diagram</div>';
                html += '<div class="er-diagram">' + generateGraphDiagram(targetEntities) + '</div></div>';
                html += '<div class="sql-section"><div class="section-title">' + exportLabel + '</div>';
                html += '<div class="sql-code-view"><pre>' + escapeHtml(migrationData.exported_target) + '</pre></div></div>';
            } else if (targetType === 'Columnar') {
                // Columnar Target: Chebotko Diagram + Generated CQL
                const targetEntities = migrationData.target_with_db_types || migrationData.result;
                html += '<div class="er-section"><div class="section-title">Chebotko Diagram</div>';
                html += generateChebotkoDiagram(targetEntities);
                html += '</div>';
                html += '<div class="sql-section"><div class="section-title">' + exportLabel + '</div>';
                html += '<div class="sql-code-view"><pre>' + escapeHtml(migrationData.exported_target) + '</pre></div></div>';
            } else {
                // Document Target: card view + JSON Schema
                const targetNested = filterEntities(migrationData.target_nested || {});
                if (Object.keys(targetNested).length > 0) {
                    html += '<div class="document-view">';
                    Object.values(targetNested).forEach(entity => {
                        html += renderNestedEntityCard(entity);
                    });
                    html += '</div>';
                }
                html += '<div class="document-view"><div class="section-title">' + exportLabel + '</div><div class="json-display">' + syntaxHighlightJSON(migrationData.exported_target) + '</div></div>';
            }
            html += '</div></div>';
            container.innerHTML = html;

            if (mermaidReady) {
                setTimeout(() => { try { mermaid.run({ nodes: container.querySelectorAll('.mermaid') }); } catch (e) {} }, 100);
            }
        }

        function renderSmelScript() {
            const container = document.getElementById('tab-smel');
            const smelContent = migrationData.smel_content || '';
            const smelFile = migrationData.smel_file || 'script.smel';
            const operations = migrationData.operations_detail || [];

            let html = '<div class="smel-content">';
            html += '<div class="smel-layout">';

            // Left panel: SMEL Script
            html += '<div class="smel-panel">';
            html += '<div class="smel-panel-header">';
            html += '<span class="smel-panel-title">SMEL Script</span>';
            html += '<span class="smel-file-badge">' + escapeHtml(smelFile) + '</span>';
            html += '</div>';
            html += '<div class="smel-panel-body">';
            html += '<div class="smel-code">' + highlightSmelSyntax(smelContent) + '</div>';
            html += '</div></div>';

            // Right panel: Operations List
            html += '<div class="smel-panel">';
            html += '<div class="smel-panel-header">';
            html += '<span class="smel-panel-title">Parsed Operations</span>';
            // Show execution stats
            const execStats = migrationData.execution_stats || {total: operations.length, success: 0, skipped: 0};
            if (execStats.skipped > 0) {
                html += '<span class="smel-file-badge" style="background:#f39c12;color:#fff;">' + execStats.success + '/' + execStats.total + ' OK</span>';
            } else {
                html += '<span class="smel-file-badge" style="background:#27ae60;color:#fff;">All ' + execStats.total + ' OK</span>';
            }
            html += '</div>';
            html += '<div class="smel-panel-body">';
            html += '<div class="operations-list">';

            operations.forEach((op, index) => {
                const hasChanges = op.changes && op.changes.affected_entities && op.changes.affected_entities.length > 0;
                const isSuccess = op.status === 'success';
                html += '<div class="operation-item">';
                html += '<div class="operation-header">';
                html += '<div class="operation-step">';
                html += '<span class="step-number">' + op.step + '</span>';
                html += '<span class="operation-type">' + (op.original_keyword || op.type) + '</span>';
                html += '</div>';
                // Show execution status instead of entity count
                if (isSuccess) {
                    html += '<span class="operation-badge" style="background:#27ae60;color:#fff;">OK</span>';
                } else {
                    html += '<span class="operation-badge" style="background:#e74c3c;color:#fff;">SKIP</span>';
                }
                html += '</div>';
                html += '<div class="operation-params">';
                html += formatOperationParams(op.type, op.params);
                html += '</div>';

                // Add toggle button and changes detail
                if (hasChanges) {
                    html += '<button class="toggle-btn" onclick="toggleChanges(' + index + ')">';
                    html += '<span class="arrow" id="arrow-' + index + '">▶</span> Show Changes';
                    html += '</button>';
                    html += '<div class="changes-detail" id="changes-' + index + '">';
                    html += renderChangesDetail(op.changes);
                    html += '</div>';
                }

                html += '</div>';
            });

            html += '</div></div></div>';

            // Summary
            html += '<div class="smel-summary">';
            html += '<div class="summary-item"><div class="summary-value">' + ((migrationData.stats || {}).source_count || 0) + '</div><div class="summary-label">Source Entities</div></div>';
            html += '<div class="summary-item"><div class="summary-value">' + operations.length + '</div><div class="summary-label">Operations</div></div>';
            html += '<div class="summary-item"><div class="summary-value">' + ((migrationData.stats || {}).result_count || 0) + '</div><div class="summary-label">Result Entities</div></div>';
            html += '<div class="summary-item"><div class="summary-value">' + migrationData.source_type + ' → ' + migrationData.target_type + '</div><div class="summary-label">Direction</div></div>';
            html += '</div>';

            // Validation Results
            html += renderValidation(migrationData);

            html += '</div></div>';
            container.innerHTML = html;
        }

        function renderValidation(data) {
            var vMeta = data.validation_meta || {};
            var vExport = data.validation_export || {};
            // Skip if both N/A
            if (vMeta.passed == null && vExport.passed == null) return '';

            var html = '<div class="validation-section">';
            html += '<div class="validation-section-title">Validation</div>';

            html += renderValidationLayer('Layer 1 — SMEL Script', vMeta);
            html += renderValidationLayer('Layer 2 — Adapter Export', vExport);

            html += '</div>';
            return html;
        }

        function renderValidationLayer(label, v) {
            if (!v || v.passed == null) {
                return '<div class="validation-layer">' +
                    '<span class="validation-layer-label">' + label + '</span>' +
                    '<span class="validation-badge na">' + (v && v.summary ? v.summary : 'N/A') + '</span>' +
                    '</div>';
            }
            var badge = v.passed
                ? '<span class="validation-badge pass">PASS</span>'
                : '<span class="validation-badge fail">FAIL</span>';
            var html = '<div class="validation-layer">' +
                '<span class="validation-layer-label">' + label + '</span>' +
                badge +
                '<span style="font-size:12px;color:#8E8E93;">' + escapeHtml(v.summary || '') + '</span>' +
                '</div>';
            // Details for failures
            if (!v.passed && v.details) {
                var d = v.details;
                var hasDetails = (d.missing_entities && d.missing_entities.length) ||
                    (d.extra_entities && d.extra_entities.length) ||
                    (d.entity_diffs && Object.keys(d.entity_diffs).length);
                if (hasDetails) {
                    html += '<div class="validation-details">';
                    if (d.missing_entities && d.missing_entities.length)
                        html += '<div>Missing entities: ' + d.missing_entities.join(', ') + '</div>';
                    if (d.extra_entities && d.extra_entities.length)
                        html += '<div>Extra entities: ' + d.extra_entities.join(', ') + '</div>';
                    if (d.entity_diffs) {
                        for (var ename in d.entity_diffs) {
                            var ed = d.entity_diffs[ename];
                            var parts = [];
                            var ad = ed.attributes || {};
                            if (ad.missing && ad.missing.length) parts.push('missing attrs: ' + ad.missing.join(', '));
                            if (ad.extra && ad.extra.length) parts.push('extra attrs: ' + ad.extra.join(', '));
                            if (ad.type_mismatches && ad.type_mismatches.length) {
                                ad.type_mismatches.forEach(function(tm) {
                                    parts.push(tm.attr + ': ' + tm.actual + ' != ' + tm.expected);
                                });
                            }
                            var rd = ed.references || {};
                            if (rd.missing && rd.missing.length) parts.push('missing refs: ' + rd.missing.join(', '));
                            if (rd.extra && rd.extra.length) parts.push('extra refs: ' + rd.extra.join(', '));
                            var emd = ed.embedded || {};
                            if (emd.missing && emd.missing.length) parts.push('missing embedded: ' + emd.missing.join(', '));
                            if (emd.extra && emd.extra.length) parts.push('extra embedded: ' + emd.extra.join(', '));
                            if (parts.length) html += '<div class="detail-entity">' + escapeHtml(ename) + ': ' + escapeHtml(parts.join('; ')) + '</div>';
                        }
                    }
                    html += '</div>';
                }
                // Warnings
                var hasWarnings = d.entity_warnings && Object.keys(d.entity_warnings).length;
                if (hasWarnings) {
                    html += renderValidationWarnings(d.entity_warnings);
                }
            }
            // Warnings for passed results
            if (v.passed && v.details && v.details.entity_warnings && Object.keys(v.details.entity_warnings).length) {
                html += renderValidationWarnings(v.details.entity_warnings);
            }
            return html;
        }

        function renderValidationWarnings(warnings) {
            var html = '<div class="validation-warnings">';
            html += '<div style="color:#F39C12;font-weight:600;margin-bottom:4px;">Warnings:</div>';
            for (var ename in warnings) {
                var w = warnings[ename];
                var parts = [];
                if (w.entity_kind) parts.push('kind: ' + w.entity_kind);
                if (w.cardinality && w.cardinality.length) {
                    w.cardinality.forEach(function(c) { parts.push(c); });
                }
                if (w.key_type && w.key_type.length) {
                    w.key_type.forEach(function(k) { parts.push(k); });
                }
                if (w.fk_constraints) parts.push('FK constraints differ');
                if (parts.length) html += '<div class="detail-entity">' + escapeHtml(ename) + ': ' + escapeHtml(parts.join('; ')) + '</div>';
            }
            html += '</div>';
            return html;
        }

        function highlightSmelSyntax(code) {
            if (!code) return '';
            let result = escapeHtml(code);

            // Comments (-- ...)
            result = result.replace(/(--[^\\n]*)/g, '<span class="smel-comment">$1</span>');

            // Keywords
            const keywords = ['MIGRATION', 'FROM', 'TO', 'USING', 'AS', 'INTO', 'WITH', 'WHERE', 'IN', 'KEY', 'AND', 'BETWEEN', 'PREFIX', 'SERIAL',
                'RELATIONAL', 'DOCUMENT', 'GRAPH', 'COLUMNAR',
                'NEST', 'UNNEST', 'FLATTEN', 'UNFLATTEN', 'UNWIND', 'WIND',
                'DELETE', 'ADD', 'RENAME', 'COPY', 'MOVE', 'MERGE', 'SPLIT', 'CAST', 'TRANSFORM',
                'REFERENCE', 'REFERENCES', 'ATTRIBUTE', 'ATTRIBUTES', 'EMBEDDED', 'ENTITY', 'RELATIONSHIP',
                'COLUMNS', 'STRUCTURE', 'LABEL',
                'CARDINALITY', 'ONE_TO_ONE', 'ONE_TO_MANY', 'ZERO_TO_ONE', 'ZERO_TO_MANY',
                'PRIMARY', 'UNIQUE', 'FOREIGN', 'PARTITION', 'CLUSTERING',
                // Specific grammar keywords
                'ADD_ATTRIBUTE', 'ADD_CONSTRAINT', 'ADD_EMBEDDED', 'ADD_ENTITY', 'ADD_LABEL',
                'ADD_PRIMARY_KEY', 'ADD_FOREIGN_KEY', 'ADD_UNIQUE_KEY',
                'DELETE_ATTRIBUTE', 'DELETE_CONSTRAINT', 'DELETE_EMBEDDED', 'DELETE_ENTITY', 'DELETE_LABEL',
                'DELETE_PRIMARY_KEY', 'DELETE_UNIQUE_KEY', 'DELETE_FOREIGN_KEY',
                'REMOVE_FOREIGN_KEY', 'REMOVE_UNIQUE_KEY', 'REMOVE_KEY', 'REMOVE_LABEL',
                'RENAME_ATTRIBUTE', 'RENAME_ENTITY',
                'COPY_ATTRIBUTE', 'COPY_ENTITY', 'MOVE_ATTRIBUTE', 'CAST_ATTRIBUTE', 'CAST_CONSTRAINT', 'RECARD',
                'ADD_RELTYPE', 'DELETE_RELTYPE', 'RENAME_RELTYPE',
                'ADD_PARTITION_KEY', 'ADD_CLUSTERING_KEY', 'DELETE_PARTITION_KEY', 'DELETE_CLUSTERING_KEY',
                'DELETION', 'CONSTRAINT',
                // Pauschalisiert grammar keywords
                'ADD_PS', 'DELETE_PS', 'REMOVE_PS', 'RENAME_PS', 'RELTYPE',
                'FLATTEN_PS', 'UNFLATTEN_PS', 'NEST_PS', 'UNNEST_PS', 'UNWIND_PS', 'WIND_PS',
                'COPY_PS', 'MOVE_PS', 'MERGE_PS', 'SPLIT_PS', 'CAST_PS', 'RECARD_PS', 'TRANSFORM_PS'];
            keywords.forEach(kw => {
                result = result.replace(new RegExp('\\\\b' + kw + '\\\\b', 'g'), '<span class="smel-keyword">' + kw + '</span>');
            });

            // Data types
            const types = ['String', 'Text', 'Int', 'Integer', 'Long', 'Double', 'Float', 'Decimal', 'Boolean', 'Date', 'DateTime', 'Timestamp', 'UUID', 'Binary'];
            types.forEach(t => {
                result = result.replace(new RegExp('\\\\b' + t + '\\\\b', 'g'), '<span class="smel-type">' + t + '</span>');
            });

            // Version numbers
            result = result.replace(/:(\\d+\\.\\d+(\\.\\d+)?)/g, ':<span class="smel-number">$1</span>');
            result = result.replace(/:(\\d+)/g, ':<span class="smel-number">$1</span>');

            return result;
        }

        function toggleChanges(index) {
            const detail = document.getElementById('changes-' + index);
            const arrow = document.getElementById('arrow-' + index);
            const btn = arrow.parentElement;

            if (detail.classList.contains('show')) {
                detail.classList.remove('show');
                arrow.textContent = '▶';
                btn.innerHTML = '<span class="arrow" id="arrow-' + index + '">▶</span> Show Changes';
            } else {
                detail.classList.add('show');
                arrow.textContent = '▼';
                btn.innerHTML = '<span class="arrow" id="arrow-' + index + '">▼</span> Hide Changes';
            }
        }

        function renderChangesDetail(changes) {
            if (!changes || !changes.affected_entities || changes.affected_entities.length === 0) {
                return '<div class="no-changes">No structural changes</div>';
            }

            let html = '';
            changes.affected_entities.forEach(affected => {
                html += '<div class="affected-entity">';

                // Entity name with status
                let nameClass = '';
                let statusLabel = '';
                if (affected.status === 'new') {
                    nameClass = 'new';
                    statusLabel = '<span class="change-label">new</span>';
                } else if (affected.status === 'deleted') {
                    nameClass = 'deleted';
                    statusLabel = '<span class="change-label deleted">deleted</span>';
                }
                html += '<div class="entity-name-header ' + nameClass + '">' + affected.name + ' ' + statusLabel + '</div>';

                if (affected.status === 'new' || affected.status === 'modified') {
                    const entity = affected.entity;

                    // Show attributes
                    if (entity.attributes && entity.attributes.length > 0) {
                        entity.attributes.forEach(attr => {
                            const isNew = affected.new_attributes && affected.new_attributes.some(a => a.name === attr.name);
                            html += '<div class="change-item' + (isNew ? ' new' : '') + '">';
                            html += '<span class="change-prefix' + (isNew ? ' add' : '') + '">' + (isNew ? '+' : ' ') + '</span>';
                            html += attr.name + ': ' + attr.type;
                            if (attr.is_key) html += ' [PK]';
                            if (attr.is_optional) html += ' ?';
                            if (isNew) html += '<span class="change-label">new</span>';
                            html += '</div>';
                        });
                    }

                    // Show new embedded
                    if (affected.new_embedded && affected.new_embedded.length > 0) {
                        affected.new_embedded.forEach(emb => {
                            html += '<div class="change-item new">';
                            html += '<span class="change-prefix add">+</span>';
                            html += '&lt;&gt; ' + emb.name + ' [' + emb.cardinality + ']';
                            html += '<span class="change-label">new</span>';
                            html += '</div>';
                        });
                    } else if (entity.embedded && entity.embedded.length > 0 && affected.status === 'new') {
                        entity.embedded.forEach(emb => {
                            html += '<div class="change-item new">';
                            html += '<span class="change-prefix add">+</span>';
                            html += '&lt;&gt; ' + emb.name + ' [' + emb.cardinality + ']';
                            html += '<span class="change-label">new</span>';
                            html += '</div>';
                        });
                    }

                    // Show new references
                    if (affected.new_references && affected.new_references.length > 0) {
                        affected.new_references.forEach(ref => {
                            html += '<div class="change-item new">';
                            html += '<span class="change-prefix add">+</span>';
                            html += '→ ' + ref.name + ' → ' + ref.target;
                            html += '<span class="change-label">new</span>';
                            html += '</div>';
                        });
                    }

                    // Show deleted embedded
                    if (affected.deleted_embedded && affected.deleted_embedded.length > 0) {
                        affected.deleted_embedded.forEach(name => {
                            html += '<div class="change-item deleted">';
                            html += '<span class="change-prefix remove">-</span>';
                            html += '&lt;&gt; ' + name;
                            html += '<span class="change-label deleted">deleted</span>';
                            html += '</div>';
                        });
                    }

                    // Show deleted references
                    if (affected.deleted_references && affected.deleted_references.length > 0) {
                        affected.deleted_references.forEach(name => {
                            html += '<div class="change-item deleted">';
                            html += '<span class="change-prefix remove">-</span>';
                            html += '→ ' + name;
                            html += '<span class="change-label deleted">deleted</span>';
                            html += '</div>';
                        });
                    }

                    // Show type changed attributes (for CAST and UNWIND operations)
                    if (affected.type_changed_attributes && affected.type_changed_attributes.length > 0) {
                        affected.type_changed_attributes.forEach(attr => {
                            html += '<div class="change-item" style="color:#AF52DE;">';
                            html += '<span class="change-prefix" style="color:#AF52DE;">~</span>';
                            html += attr.name + ': <s style="color:#636366;">' + attr.old_type + '</s> → ' + attr.new_type;
                            html += '<span class="change-label" style="background:rgba(175,82,222,0.15);color:#AF52DE;">type changed</span>';
                            html += '</div>';
                        });
                    }
                }

                html += '</div>';
            });

            return html;
        }

        function formatOperationParams(type, params) {
            if (!params) return '';
            // Helper: escape HTML to prevent XSS and handle null/undefined
            function esc(v) { return escapeHtml(String(v != null ? v : '')); }
            let html = '';

            switch(type) {
                case 'NEST':
                    html = '<span class="param-key">source:</span> <span class="param-value">' + esc(params.source) + '</span> → ';
                    html += '<span class="param-key">target:</span> <span class="param-value">' + esc(params.target) + '</span>';
                    if (params.alias) html += ' <span class="param-key">as:</span> <span class="param-value">' + esc(params.alias) + '</span>';
                    break;
                case 'DELETE_CONSTRAINT':
                    html = '<span class="param-key">reference:</span> <span class="param-value">' + esc(params.reference) + '</span>';
                    break;
                case 'DELETE_ENTITY':
                    html = '<span class="param-key">entity:</span> <span class="param-value">' + esc(params.name) + '</span>';
                    break;
                case 'RENAME':
                    html = '<span class="param-key">rename:</span> <span class="param-value">' + esc(params.old_name) + '</span> → <span class="param-value">' + esc(params.new_name) + '</span>';
                    if (params.entity) html += ' <span class="param-key">in:</span> <span class="param-value">' + esc(params.entity) + '</span>';
                    break;
                case 'FLATTEN':
                    html = '<span class="param-key">source:</span> <span class="param-value">' + esc(params.source) + '</span>';
                    html += ' <span style="color:#636366;font-size:12px;">(flatten to same table with prefix)</span>';
                    break;
                case 'UNNEST':
                    html = '<span class="param-value">' + esc(params.source_path) + '</span>';
                    if (params.attributes && params.attributes.length > 0) {
                        html += ':' + params.attributes.map(a => esc(a)).join(',');
                    }
                    html += ' <span class="param-key">AS</span> <span class="param-value">' + esc(params.target) + '</span>';
                    if (params.carry_fields && params.carry_fields.length > 0) {
                        html += ' <span class="param-key">WITH</span> ';
                        html += params.carry_fields.map(cf =>
                            '<span class="param-value">' + esc(cf.source) + '</span> <span class="param-key">TO</span> <span class="param-value">' + esc(cf.target) + '</span>'
                        ).join(', ');
                    }
                    break;
                case 'UNWIND':
                    html = '<span class="param-value">' + esc(params.source) + '</span>';
                    if (params.mode === 'create_table' && params.target) {
                        html += ' → <span class="param-key">INTO</span> <span class="param-value">' + esc(params.target) + '</span>';
                    } else {
                        html += ' <span class="param-key">(expand in place)</span>';
                    }
                    break;
                case 'UNFLATTEN':
                    html = '<span class="param-value">' + esc(params.entity) + '</span>';
                    html += '(' + (params.fields || []).map(f => esc(f)).join(', ') + ')';
                    html += ' <span class="param-key">AS</span> <span class="param-value">' + esc(params.nested_name) + '</span>';
                    break;
                case 'WIND':
                    html = '<span class="param-value">' + esc(params.source) + '</span>';
                    html += ' <span class="param-key">(scalar → array)</span>';
                    break;
                case 'SPLIT':
                case 'SPLIT_FLAT':
                    html = '<span class="param-value">' + esc(params.source) + '</span> <span class="param-key">INTO</span> ';
                    if (params.parts && params.parts.length > 0) {
                        html += params.parts.map(p => '<span class="param-value">' + esc(p.name) + '</span>(' + (p.fields || []).map(f => esc(f)).join(', ') + ')').join(', ');
                    }
                    break;
                case 'ADD_KEY':
                    html = '<span class="param-key">key_type:</span> <span class="param-value">' + esc(params.key_type || 'PRIMARY') + '</span> ';
                    if (params.key_columns) {
                        const cols = params.key_columns.length > 1 ? '(' + params.key_columns.map(c => esc(c)).join(', ') + ')' : esc(params.key_columns[0]);
                        html += '<span class="param-key">columns:</span> <span class="param-value">' + cols + '</span>';
                    }
                    if (params.data_type) html += ' <span class="param-key">AS</span> <span class="param-value">' + esc(params.data_type) + '</span>';
                    if (params.entity) html += ' <span class="param-key">TO</span> <span class="param-value">' + esc(params.entity) + '</span>';
                    break;
                case 'DELETE_KEY':
                    html = '<span class="param-key">key_type:</span> <span class="param-value">' + esc(params.key_type) + '</span> ';
                    if (params.key_columns) {
                        const cols = params.key_columns.length > 1 ? '(' + params.key_columns.map(c => esc(c)).join(', ') + ')' : esc(params.key_columns[0]);
                        html += '<span class="param-key">columns:</span> <span class="param-value">' + cols + '</span>';
                    }
                    if (params.entity) html += ' <span class="param-key">FROM</span> <span class="param-value">' + esc(params.entity) + '</span>';
                    break;
                case 'ADD_CONSTRAINT':
                    if (params.field_name) {
                        html = '<span class="param-key">field:</span> <span class="param-value">' + esc(params.field_name) + '</span> ';
                        html += '<span class="param-key">REFERENCES</span> <span class="param-value">' + esc(params.target_table) + '(' + esc(params.target_column) + ')</span>';
                    } else {
                        html = '<span class="param-key">reference:</span> <span class="param-value">' + esc(params.reference) + '</span> → ';
                        html += '<span class="param-key">target:</span> <span class="param-value">' + esc(params.target) + '</span>';
                    }
                    break;
                case 'DELETE_EMBEDDED':
                    html = '<span class="param-key">embedded:</span> <span class="param-value">' + esc(params.embedded) + '</span>';
                    break;
                case 'ADD_RELTYPE':
                    html = '<span class="param-key">reltype:</span> <span class="param-value">' + esc(params.name) + '</span> ';
                    html += '<span class="param-key">BETWEEN</span> <span class="param-value">' + esc(params.source_entity) + '</span> ';
                    html += '<span class="param-key">AND</span> <span class="param-value">' + esc(params.target_entity) + '</span>';
                    break;
                case 'DELETE_RELTYPE':
                    html = '<span class="param-key">reltype:</span> <span class="param-value">' + esc(params.name) + '</span>';
                    break;
                case 'RENAME_RELTYPE':
                    html = '<span class="param-key">rename:</span> <span class="param-value">' + esc(params.old_name) + '</span> → <span class="param-value">' + esc(params.new_name) + '</span>';
                    break;
                case 'ADD_ATTRIBUTE':
                    html = '<span class="param-key">attribute:</span> <span class="param-value">' + esc(params.name) + '</span>';
                    if (params.data_type) html += ' <span class="param-key">type:</span> <span class="param-value">' + esc(params.data_type) + '</span>';
                    if (params.entity) html += ' <span class="param-key">TO</span> <span class="param-value">' + esc(params.entity) + '</span>';
                    break;
                case 'ADD_EMBEDDED':
                    html = '<span class="param-key">embedded:</span> <span class="param-value">' + esc(params.name) + '</span>';
                    if (params.entity) html += ' <span class="param-key">TO</span> <span class="param-value">' + esc(params.entity) + '</span>';
                    break;
                case 'ADD_ENTITY':
                    html = '<span class="param-key">entity:</span> <span class="param-value">' + esc(params.name) + '</span>';
                    break;
                case 'ADD_LABEL':
                    html = '<span class="param-key">label:</span> <span class="param-value">' + esc(params.label) + '</span>';
                    if (params.entity) html += ' <span class="param-key">TO</span> <span class="param-value">' + esc(params.entity) + '</span>';
                    break;
                case 'DELETE_ATTRIBUTE':
                    html = '<span class="param-key">target:</span> <span class="param-value">' + esc(params.target) + '</span>';
                    break;
                case 'DELETE_LABEL':
                    html = '<span class="param-key">label:</span> <span class="param-value">' + esc(params.label) + '</span>';
                    if (params.entity) html += ' <span class="param-key">FROM</span> <span class="param-value">' + esc(params.entity) + '</span>';
                    break;
                case 'REMOVE_KEY':
                    html = '<span class="param-key">key_type:</span> <span class="param-value">' + esc(params.key_type || 'PRIMARY') + '</span>';
                    if (params.key_columns) {
                        html += ' <span class="param-key">columns:</span> <span class="param-value">' + params.key_columns.map(c => esc(c)).join(', ') + '</span>';
                    }
                    if (params.entity) html += ' <span class="param-key">FROM</span> <span class="param-value">' + esc(params.entity) + '</span>';
                    break;
                case 'REMOVE_LABEL':
                    html = '<span class="param-key">label:</span> <span class="param-value">' + esc(params.label) + '</span>';
                    if (params.entity) html += ' <span class="param-key">FROM</span> <span class="param-value">' + esc(params.entity) + '</span>';
                    break;
                case 'RENAME_ENTITY':
                    html = '<span class="param-key">rename:</span> <span class="param-value">' + esc(params.old_name) + '</span> → <span class="param-value">' + esc(params.new_name) + '</span>';
                    break;
                case 'COPY':
                    html = '<span class="param-value">' + esc(params.source) + '</span>';
                    html += ' <span class="param-key">TO</span> <span class="param-value">' + esc(params.target) + '</span>';
                    break;
                case 'COPY_ENTITY':
                    html = '<span class="param-key">entity:</span> <span class="param-value">' + esc(params.source) + '</span>';
                    html += ' <span class="param-key">AS</span> <span class="param-value">' + esc(params.target) + '</span>';
                    break;
                case 'MOVE':
                    html = '<span class="param-value">' + esc(params.source) + '</span>';
                    html += ' <span class="param-key">TO</span> <span class="param-value">' + esc(params.target) + '</span>';
                    break;
                case 'MERGE':
                    html = '<span class="param-value">' + esc(params.source1) + '</span>, ';
                    html += '<span class="param-value">' + esc(params.source2) + '</span>';
                    html += ' <span class="param-key">INTO</span> <span class="param-value">' + esc(params.target) + '</span>';
                    if (params.alias) html += ' <span class="param-key">AS</span> <span class="param-value">' + esc(params.alias) + '</span>';
                    break;
                case 'CAST':
                    html = '<span class="param-key">target:</span> <span class="param-value">' + esc(params.target) + '</span>';
                    html += ' <span class="param-key">TO</span> <span class="param-value">' + esc(params.type || params.data_type) + '</span>';
                    break;
                case 'CAST_CONSTRAINT':
                    html = '<span class="param-key">target:</span> <span class="param-value">' + esc(params.target) + '</span>';
                    html += ' <span class="param-key">TO</span> <span class="param-value">' + esc(params.constraint_type) + '</span>';
                    break;
                case 'RECARD':
                    html = '<span class="param-key">target:</span> <span class="param-value">' + esc(params.target) + '</span>';
                    html += ' <span class="param-key">TO</span> <span class="param-value">' + esc(params.cardinality) + '</span>';
                    break;
                case 'TRANSFORM':
                    html = '<span class="param-key">entity:</span> <span class="param-value">' + esc(params.name) + '</span>';
                    html += ' <span class="param-key">TO</span> <span class="param-value">' + esc(params.target_type) + '</span>';
                    if (params.source_entity) html += ' <span class="param-key">BETWEEN</span> <span class="param-value">' + esc(params.source_entity) + '</span> <span class="param-key">AND</span> <span class="param-value">' + esc(params.target_entity) + '</span>';
                    break;
                default:
                    html = Object.entries(params).map(([k, v]) => {
                        if (typeof v === 'object') return '';
                        return '<span class="param-key">' + esc(k) + ':</span> <span class="param-value">' + esc(v) + '</span>';
                    }).filter(x => x).join(' ');
            }
            return html;
        }

        function escapeHtml(text) {
            if (!text) return '';
            return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }

        // Filter out __relationship_types__ special key from entity dicts
        function filterEntities(entities) {
            if (!entities) return {};
            const filtered = {};
            Object.entries(entities).forEach(([k, v]) => {
                if (!k.startsWith('__')) filtered[k] = v;
            });
            return filtered;
        }

        function generateMermaidSyntax(entities) {
            let syntax = 'erDiagram\\n';
            const entityList = Object.values(filterEntities(entities));
            const addedRels = new Set();

            entityList.forEach(entity => {
                const safeName = entity.name.replace(/[^a-zA-Z0-9_]/g, '_');
                syntax += '    ' + safeName + ' {\\n';
                entity.attributes.forEach(attr => {
                    const safeAttr = attr.name.replace(/[^a-zA-Z0-9_]/g, '_');
                    const safeType = attr.type.replace(/[^a-zA-Z0-9_]/g, '_');
                    const isFk = (entity.references || []).some(r => r.name === attr.name);
                    // Mermaid only supports one key type, PK takes precedence
                    // If both PK and FK, show PK with comment indicating FK
                    let key = '';
                    if (attr.is_key && isFk) {
                        key = ' PK "FK"';  // Composite PK that is also FK
                    } else if (attr.is_key) {
                        key = ' PK';
                    } else if (isFk) {
                        key = ' FK';
                    }
                    syntax += '        ' + safeAttr + ' ' + safeType + key + '\\n';
                });
                syntax += '    }\\n';
            });

            entityList.forEach(entity => {
                const src = entity.name.replace(/[^a-zA-Z0-9_]/g, '_');
                (entity.references || []).forEach(ref => {
                    const tgt = ref.target.replace(/[^a-zA-Z0-9_]/g, '_');
                    const key = tgt + '-' + src + '-' + ref.name;
                    if (!addedRels.has(key)) {
                        addedRels.add(key);
                        // Use cardinality from reference to determine ER notation
                        // Cardinality values from unified_meta_schema.py:
                        // ONE_TO_ONE = "1..1", ONE_TO_MANY = "1..n"
                        // ZERO_TO_ONE = "0..1", ZERO_TO_MANY = "0..n"
                        const cardinality = ref.cardinality || '1..n';
                        let relSymbol = '||--o{'; // default: ONE_TO_MANY (1..n)
                        if (cardinality === '1..1') {
                            relSymbol = '||--||';  // ONE_TO_ONE
                        } else if (cardinality === '0..1') {
                            relSymbol = '|o--||';  // ZERO_TO_ONE
                        } else if (cardinality === '0..n') {
                            relSymbol = '|o--o{';  // ZERO_TO_MANY
                        }
                        syntax += '    ' + tgt + ' ' + relSymbol + ' ' + src + ' : "' + ref.name + '"\\n';
                    }
                });
                (entity.embedded || []).forEach(emb => {
                    const tgt = emb.target.replace(/[^a-zA-Z0-9_]/g, '_');
                    const key = src + '-' + tgt;
                    if (!addedRels.has(key)) {
                        addedRels.add(key);
                        const rel = emb.cardinality === '1..1' ? '||--||' : '||--o{';
                        syntax += '    ' + src + ' ' + rel + ' ' + tgt + ' : "embedded"\\n';
                    }
                });
                (entity.edges || []).forEach(edge => {
                    const tgt = edge.target.replace(/[^a-zA-Z0-9_]/g, '_');
                    const key = src + '-' + tgt + '-' + edge.name;
                    if (!addedRels.has(key)) {
                        addedRels.add(key);
                        const rel = edge.cardinality === '1..1' ? '||--||' : '||--o{';
                        syntax += '    ' + src + ' ' + rel + ' ' + tgt + ' : "' + edge.name + '"\\n';
                    }
                });
            });
            return syntax;
        }

        function generateERDiagram(entities) {
            return '<div class="mermaid">' + generateMermaidSyntax(entities) + '</div>';
        }

        function generateGraphDiagram(entities) {
            const entityList = Object.values(filterEntities(entities));
            if (entityList.length === 0) return '';

            // ── Step 1: Collect all edges ──
            const allEdges = [];
            const addedEdges = new Set();
            entityList.forEach(entity => {
                (entity.edges || []).forEach(edge => {
                    const key = entity.name + '->' + edge.target + ':' + edge.name;
                    if (!addedEdges.has(key)) {
                        addedEdges.add(key);
                        allEdges.push({ source: entity.name, target: edge.target, name: edge.name });
                    }
                });
            });
            const relTypes = entities['__relationship_types__'] || {};
            Object.entries(relTypes).forEach(([name, rt]) => {
                const key = (rt.source_entity||'') + '->' + (rt.target_entity||'') + ':' + (rt.rel_name||name);
                if (rt.source_entity && rt.target_entity && !addedEdges.has(key)) {
                    addedEdges.add(key);
                    allEdges.push({ source: rt.source_entity, target: rt.target_entity, name: rt.rel_name || name });
                }
            });

            // ── Step 2: Count connections per node ──
            const connCount = {};
            entityList.forEach(e => { connCount[e.name] = 0; });
            allEdges.forEach(e => {
                if (connCount[e.source] !== undefined) connCount[e.source]++;
                if (connCount[e.target] !== undefined) connCount[e.target]++;
            });

            // ── Step 3: Pick hub nodes (top N by connection count) ──
            const sorted = Object.entries(connCount).sort((a, b) => b[1] - a[1]);
            let numHubs = entityList.length >= 10 ? 3 : (entityList.length >= 5 ? 2 : 1);
            numHubs = Math.min(numHubs, sorted.length);
            const hubNames = sorted.slice(0, numHubs).map(e => e[0]);

            // ── Step 4: Assign each non-hub node to its most-connected hub ──
            const clusters = {};
            hubNames.forEach(h => { clusters[h] = []; });

            entityList.forEach(entity => {
                if (hubNames.includes(entity.name)) return;
                let bestHub = hubNames[0];
                let bestScore = -1;
                hubNames.forEach(hub => {
                    let score = 0;
                    allEdges.forEach(edge => {
                        if ((edge.source === entity.name && edge.target === hub) ||
                            (edge.target === entity.name && edge.source === hub)) {
                            score += 2;
                        }
                    });
                    if (score > bestScore || (score === bestScore && clusters[hub].length < clusters[bestHub].length)) {
                        bestScore = score;
                        bestHub = hub;
                    }
                });
                clusters[bestHub].push(entity.name);
            });

            // ── Step 5: Calculate positions ──
            const W = 960, H = entityList.length >= 7 ? 760 : 700;
            const hubR = 30, satR = 22;
            const pos = {};

            const hubCenters = numHubs === 1
                ? [{ x: W/2, y: H/2 }]
                : numHubs === 2
                    ? [{ x: W*0.25, y: H*0.5 }, { x: W*0.75, y: H*0.5 }]
                    : [{ x: W*0.28, y: H*0.50 }, { x: W*0.72, y: H*0.25 }, { x: W*0.72, y: H*0.75 }];

            hubNames.forEach((hub, i) => {
                const hc = hubCenters[i];
                pos[hub] = { x: hc.x, y: hc.y, isHub: true, hubIdx: i };
                const sats = clusters[hub];
                if (sats.length === 0) return;
                const ringR = Math.max(95, Math.min(180, sats.length * 22 + 10));
                sats.forEach((name, j) => {
                    const angle = (2 * Math.PI * j / sats.length) - Math.PI / 2;
                    pos[name] = {
                        x: hc.x + ringR * Math.cos(angle),
                        y: hc.y + ringR * Math.sin(angle),
                        isHub: false, hubIdx: i
                    };
                });
            });

            // ── Step 6: Build SVG ──
            const hubThemes = [
                { fill:'#DBEAFE', stroke:'#3B82F6', text:'#1E40AF', satFill:'#EFF6FF', satStroke:'#93C5FD', satText:'#1E3A5F' },
                { fill:'#FEF3C7', stroke:'#F59E0B', text:'#92400E', satFill:'#FFFBEB', satStroke:'#FCD34D', satText:'#78350F' },
                { fill:'#D1FAE5', stroke:'#10B981', text:'#065F46', satFill:'#ECFDF5', satStroke:'#6EE7B7', satText:'#064E3B' }
            ];
            const interEdge = '#94A3B8';
            const selfEdge = '#E11D48';
            const labelColor = '#475569';

            let svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" style="width:100%;max-width:960px;height:auto;font-family:-apple-system,BlinkMacSystemFont,sans-serif;">';

            // Arrowhead markers
            svg += '<defs>';
            svg += '<marker id="ahG" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="' + interEdge + '"/></marker>';
            svg += '<marker id="ahS" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="' + selfEdge + '"/></marker>';
            for (let i = 0; i < numHubs; i++) {
                svg += '<marker id="ahC' + i + '" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="' + hubThemes[i].stroke + '" opacity="0.6"/></marker>';
            }
            svg += '</defs>';

            // Cluster background circles (subtle dashed)
            hubNames.forEach((hub, i) => {
                const hc = hubCenters[i];
                const sats = clusters[hub];
                if (sats.length === 0) return;
                const bgR = Math.max(115, sats.length * 20 + 48);
                svg += '<circle cx="' + hc.x + '" cy="' + hc.y + '" r="' + bgR + '" fill="' + hubThemes[i].satFill + '" stroke="' + hubThemes[i].satStroke + '" stroke-width="1" stroke-dasharray="6,3" opacity="0.4"/>';
            });

            // Group edges by pair for parallel offset
            const edgesByPair = {};
            allEdges.forEach(edge => {
                const pairKey = [edge.source, edge.target].sort().join('|');
                if (!edgesByPair[pairKey]) edgesByPair[pairKey] = [];
                edgesByPair[pairKey].push(edge);
            });

            // Draw edges
            allEdges.forEach(edge => {
                const s = pos[edge.source], t = pos[edge.target];
                if (!s || !t) return;
                const isSelf = edge.source === edge.target;
                const sameCluster = s.hubIdx === t.hubIdx;
                let eColor, marker, eOpacity;
                if (isSelf) {
                    eColor = selfEdge; marker = 'url(#ahS)'; eOpacity = '0.8';
                } else if (sameCluster) {
                    eColor = hubThemes[s.hubIdx].stroke; marker = 'url(#ahC' + s.hubIdx + ')'; eOpacity = '0.4';
                } else {
                    eColor = interEdge; marker = 'url(#ahG)'; eOpacity = '0.65';
                }

                const pairKey = [edge.source, edge.target].sort().join('|');
                const pairEdges = edgesByPair[pairKey] || [];
                const edgeIdx = pairEdges.indexOf(edge);

                if (isSelf) {
                    const nodeR = s.isHub ? hubR : satR;
                    const loopR = 25 + edgeIdx * 12;
                    svg += '<path d="M ' + (s.x-8) + ' ' + (s.y-nodeR) + ' C ' + (s.x-loopR*1.2) + ' ' + (s.y-nodeR-loopR*1.5) + ', ' + (s.x+loopR*1.2) + ' ' + (s.y-nodeR-loopR*1.5) + ', ' + (s.x+8) + ' ' + (s.y-nodeR) + '" fill="none" stroke="' + eColor + '" stroke-width="1.3" opacity="' + eOpacity + '" marker-end="' + marker + '"/>';
                    svg += '<text x="' + s.x + '" y="' + (s.y-nodeR-loopR*0.8) + '" text-anchor="middle" font-size="7" fill="' + eColor + '" font-weight="500">' + escapeHtml(edge.name) + '</text>';
                } else {
                    const dx = t.x-s.x, dy = t.y-s.y;
                    const dist = Math.sqrt(dx*dx+dy*dy);
                    if (dist < 0.1) return;
                    const nx = dx/dist, ny = dy/dist;
                    const sR = s.isHub ? hubR : satR;
                    const tR = t.isHub ? hubR : satR;
                    const x1 = s.x + nx*(sR+2), y1 = s.y + ny*(sR+2);
                    const x2 = t.x - nx*(tR+10), y2 = t.y - ny*(tR+10);
                    const offset = pairEdges.length > 1 ? (edgeIdx-(pairEdges.length-1)/2)*18 : 0;
                    const mx = (x1+x2)/2 + (-ny)*offset;
                    const my = (y1+y2)/2 + nx*offset;

                    if (Math.abs(offset) > 0.1) {
                        svg += '<path d="M '+x1+' '+y1+' Q '+mx+' '+my+' '+x2+' '+y2+'" fill="none" stroke="'+eColor+'" stroke-width="1.1" opacity="'+eOpacity+'" marker-end="'+marker+'"/>';
                    } else {
                        svg += '<line x1="'+x1+'" y1="'+y1+'" x2="'+x2+'" y2="'+y2+'" stroke="'+eColor+'" stroke-width="1.1" opacity="'+eOpacity+'" marker-end="'+marker+'"/>';
                    }
                    svg += '<text x="'+mx+'" y="'+(my-3)+'" text-anchor="middle" font-size="7" fill="'+labelColor+'" opacity="0.8">'+escapeHtml(edge.name)+'</text>';
                }
            });

            // Draw hub nodes (larger, bold colors)
            hubNames.forEach((hub, i) => {
                const p = pos[hub];
                const th = hubThemes[i];
                svg += '<circle cx="'+p.x+'" cy="'+p.y+'" r="'+hubR+'" fill="'+th.fill+'" stroke="'+th.stroke+'" stroke-width="2.5"/>';
                const fs = hub.length > 10 ? 9 : (hub.length > 7 ? 10 : 11);
                svg += '<text x="'+p.x+'" y="'+(p.y+4)+'" text-anchor="middle" font-size="'+fs+'" font-weight="700" fill="'+th.text+'">'+escapeHtml(hub)+'</text>';
            });

            // Draw satellite nodes (smaller, lighter colors matching their hub)
            entityList.forEach(entity => {
                if (hubNames.includes(entity.name)) return;
                const p = pos[entity.name];
                if (!p) return;
                const th = hubThemes[p.hubIdx];
                svg += '<circle cx="'+p.x+'" cy="'+p.y+'" r="'+satR+'" fill="'+th.satFill+'" stroke="'+th.satStroke+'" stroke-width="1.5"/>';
                const fs = entity.name.length > 11 ? 7.5 : (entity.name.length > 8 ? 8.5 : 9.5);
                svg += '<text x="'+p.x+'" y="'+(p.y+3)+'" text-anchor="middle" font-size="'+fs+'" font-weight="600" fill="'+th.satText+'">'+escapeHtml(entity.name)+'</text>';
            });

            // Summary label at bottom
            svg += '<text x="' + (W/2) + '" y="' + (H-12) + '" text-anchor="middle" font-size="11" fill="#94A3B8" font-weight="500">' + entityList.length + ' Nodes, ' + allEdges.length + ' Relationships</text>';

            svg += '</svg>';
            return '<div class="graph-svg-container">' + svg + '</div>';
        }

        function generateChebotkoDiagram(entities) {
            const entityList = Object.values(filterEntities(entities));
            if (entityList.length === 0) return '';

            let html = '<div class="chebotko-diagram">';
            entityList.forEach(entity => {
                html += '<div class="chebotko-table">';
                html += '<div class="chebotko-header">' + escapeHtml(entity.name) + '</div>';
                html += '<table class="chebotko-cols">';

                (entity.attributes || []).forEach(attr => {
                    let marker = '';
                    const keyType = attr.key_type || null;
                    if (keyType === 'partition') {
                        marker = '<span class="ck-marker pk">K&#x2191;</span>';
                    } else if (keyType === 'clustering') {
                        marker = '<span class="ck-marker ck">C&#x2191;</span>';
                    } else if (attr.is_key) {
                        marker = '<span class="ck-marker pk">K&#x2191;</span>';
                    }
                    html += '<tr>';
                    html += '<td class="ck-marker-cell">' + marker + '</td>';
                    html += '<td class="ck-name">' + escapeHtml(attr.name) + '</td>';
                    html += '<td class="ck-type">' + escapeHtml(attr.type) + '</td>';
                    html += '</tr>';
                });

                html += '</table></div>';
            });
            html += '</div>';
            return html;
        }

        function syntaxHighlightJSON(json) {
            if (!json) return '';
            if (typeof json === 'string') { try { json = JSON.stringify(JSON.parse(json), null, 2); } catch (e) {} }
            else { json = JSON.stringify(json, null, 2); }
            return json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                .replace(/"([^"]+)":/g, '<span class="json-key">"$1"</span>:')
                .replace(/: "([^"]*)"/g, ': <span class="json-string">"$1"</span>')
                .replace(/: (\\d+)/g, ': <span class="json-number">$1</span>')
                .replace(/[{}\\[\\]]/g, '<span class="json-bracket">$&</span>');
        }

        function renderMigrationProcess() {
            const container = document.getElementById('tab-migration');
            const targetType = migrationData.target_type;

            // Meta V1 and Meta V2 entities (must be aligned)
            const metaEntities = new Set([...Object.keys(filterEntities(migrationData.meta_v1 || {})), ...Object.keys(filterEntities(migrationData.result || {}))]);
            const newEntities = new Set((migrationData.changes || []).filter(c => c.startsWith('FLATTEN:') || c.startsWith('NEST:') || c.startsWith('UNWIND:') || c.startsWith('ADD_ENTITY:')).map(c => {
                const p = c.split(':');
                const val = p[1] || '';
                if (val.includes('->')) return val.split('->').pop();
                if (val.includes('.')) return val;
                return val;
            }).filter(x => x));

            let html = '<div class="migration-content"><div class="legend">';
            html += '<div class="legend-item"><span class="legend-dot new"></span>New Entity</div>';
            html += '<div class="legend-item"><span class="legend-dot reference"></span>Reference (FK)</div>';
            html += '<div class="legend-item"><span class="legend-dot embedded"></span>Embedded</div>';
            html += '<div class="legend-item"><span class="legend-dot edge"></span>Edge (Graph)</div>';
            html += '<div class="legend-item"><span class="legend-dot pk"></span>Primary Key</div></div>';

            // Four-column layout (dense for 7+ entities)
            const entityCount = Object.keys(filterEntities(migrationData.result || {})).length;
            const denseClass = entityCount >= 7 ? ' dense-layout' : '';
            html += '<div class="four-column-layout' + denseClass + '">';

            // Column 1: Source Schema (original nested structure before reverse eng)
            html += '<div class="independent-column source-column">';
            html += '<div class="column-header"><h3>Source</h3><div class="subtitle">' + migrationData.source_type + '</div></div>';
            html += '<div class="column-content">';
            const sourceDataRaw = migrationData.original_source && Object.keys(migrationData.original_source).length > 0
                ? migrationData.original_source
                : migrationData.source;
            const sourceData = filterEntities(sourceDataRaw || {});
            Object.values(sourceData).forEach(entity => {
                html += renderNestedEntityCard(entity);
            });
            html += '</div></div>';

            // Column 2 & 3: Meta V1 and Meta V2 (aligned)
            html += '<div class="meta-aligned-columns">';
            html += '<div class="meta-grid">';

            // Headers
            html += '<div class="column-header"><h3>Meta V1</h3><div class="subtitle">Unified Meta</div></div>';
            html += '<div class="column-header"><h3>Meta V2</h3><div class="subtitle">Result</div></div>';

            // Aligned entity rows
            Array.from(metaEntities).sort().forEach(name => {
                // Meta V1 cell
                const v1Entity = (migrationData.meta_v1 || {})[name];
                html += '<div class="grid-cell">';
                if (!v1Entity) {
                    html += '<div class="entity-card placeholder-card"><div class="entity-name placeholder-name">' + name + '</div>';
                    html += '<div class="entity-body placeholder-body">(--)</div></div>';
                } else {
                    html += renderEntityCard(v1Entity, false, false);
                }
                html += '</div>';

                // Meta V2 cell
                const v2Entity = (migrationData.result || {})[name];
                html += '<div class="grid-cell">';
                if (!v2Entity) {
                    html += '<div class="entity-card placeholder-card"><div class="entity-name placeholder-name">' + name + '</div>';
                    html += '<div class="entity-body placeholder-body">(--)</div></div>';
                } else {
                    const isNew = newEntities.has(name);
                    html += renderEntityCard(v2Entity, isNew, false);
                }
                html += '</div>';
            });

            html += '</div></div>';

            // Column 4: Target Schema (Forward Engineering result - Schema format)
            html += '<div class="independent-column target-column">';
            html += '<div class="column-header"><h3>Target</h3><div class="subtitle">' + targetType + '</div></div>';
            html += '<div class="column-content">';
            if (targetType === 'Relational') {
                // Relational: ER Diagram + DDL
                const targetEntities = migrationData.target_with_db_types || migrationData.result;
                html += '<div class="er-section"><div class="section-title">ER Diagram</div>';
                html += '<div class="er-diagram">' + generateERDiagram(targetEntities) + '</div></div>';
                html += '<div class="schema-view"><pre class="schema-code">' + escapeHtml(migrationData.exported_target) + '</pre></div>';
            } else if (targetType === 'Graph') {
                // Graph: Entity cards with edge indicators + Cypher DDL
                // (full graph diagram is shown in Compare view; cards are clearer in narrow column)
                const targetEntities = migrationData.target_with_db_types || migrationData.result;
                const graphEntities = Object.values(filterEntities(targetEntities));
                const graphRts = targetEntities['__relationship_types__'] || {};
                const rtCount = Object.keys(graphRts).length;
                html += '<div class="er-section"><div class="section-title">Graph Schema (' + graphEntities.length + ' Nodes, ' + rtCount + ' Relationships)</div>';
                html += '<div class="er-diagram graph-compact">' + generateGraphDiagram(targetEntities) + '</div></div>';
                graphEntities.forEach(entity => {
                    html += renderEntityCard(entity, newEntities.has(entity.name), false);
                });
                html += '<div class="schema-view"><pre class="schema-code">' + escapeHtml(migrationData.exported_target) + '</pre></div>';
            } else if (targetType === 'Columnar') {
                // Columnar: Chebotko Diagram + CQL
                const targetEntities = migrationData.target_with_db_types || migrationData.result;
                html += '<div class="er-section"><div class="section-title">Chebotko Diagram</div>';
                html += generateChebotkoDiagram(targetEntities);
                html += '</div>';
                html += '<div class="schema-view"><pre class="schema-code">' + escapeHtml(migrationData.exported_target) + '</pre></div>';
            } else {
                // Document: card view + JSON Schema
                const targetNested = filterEntities(migrationData.target_nested || {});
                if (Object.keys(targetNested).length > 0) {
                    Object.values(targetNested).forEach(entity => {
                        html += renderNestedEntityCard(entity);
                    });
                } else {
                    html += '<div class="json-view">' + syntaxHighlightJSON(migrationData.exported_target) + '</div>';
                }
            }
            html += '</div></div>';

            html += '</div>'; // end four-column-layout

            html += '<div class="validation"><div class="validation-header"><h2>Transformation Summary</h2>';
            html += '<div class="validation-status passed">Complete</div></div><div class="validation-stats">';
            html += '<div class="stat-card"><div class="stat-value">' + migrationData.operations_count + '</div><div class="stat-label">Operations</div></div>';
            html += '<div class="stat-card"><div class="stat-value">' + ((migrationData.stats || {}).source_count || 0) + '</div><div class="stat-label">Source Entities</div></div>';
            html += '<div class="stat-card"><div class="stat-value">' + ((migrationData.stats || {}).result_count || 0) + '</div><div class="stat-label">Result Entities</div></div>';
            html += '<div class="stat-card"><div class="stat-value">' + targetType + '</div><div class="stat-label">Target Format</div></div>';
            html += '</div></div></div>';
            container.innerHTML = html;

            if (mermaidReady) {
                setTimeout(() => { try { mermaid.run({ nodes: container.querySelectorAll('.mermaid') }); } catch (e) {} }, 100);
            }
        }

        function renderEntityCard(entity, isNew, isSource) {
            let html = '<div class="entity-card' + (isNew ? ' new' : '') + '"><div class="entity-name' + (isNew ? ' new' : '') + '">' + entity.name + '</div><div class="entity-body">';

            const refMap = {};
            (entity.references || []).forEach(r => { refMap[r.name] = r.target; });

            // Get key_registry info for this entity (with defensive checks)
            let keyInfo = null;
            try {
                if (migrationData && migrationData.key_registry && migrationData.key_registry[entity.name]) {
                    keyInfo = migrationData.key_registry[entity.name];
                }
            } catch(e) { keyInfo = null; }

            (entity.attributes || []).forEach(a => {
                html += '<div class="attribute"><span class="attr-name">' + a.name + '</span><span class="attr-type">' + a.type;
                // Show key format for PK with generated prefix
                if (a.is_key && keyInfo && keyInfo.generated && keyInfo.prefix) {
                    html += ' <span style="color:#34C759;font-size:10px;">= "' + keyInfo.prefix + '_{uuid6}"</span>';
                }
                // Show reference target for FK
                if (refMap[a.name]) {
                    let targetKeyInfo = null;
                    try {
                        if (migrationData && migrationData.key_registry && migrationData.key_registry[refMap[a.name]]) {
                            targetKeyInfo = migrationData.key_registry[refMap[a.name]];
                        }
                    } catch(e) { targetKeyInfo = null; }
                    if (targetKeyInfo && targetKeyInfo.prefix) {
                        html += ' <span style="color:#007AFF;font-size:10px;">→ ' + refMap[a.name] + ' ("' + targetKeyInfo.prefix + '_...")</span>';
                    } else {
                        html += ' <span style="color:#007AFF;font-size:10px;">→ ' + refMap[a.name] + '</span>';
                    }
                }
                html += '</span>';
                if (a.is_key) html += '<span class="attr-badge pk">PK</span>';
                if (a.is_optional) html += '<span class="attr-badge optional">?</span>';
                html += '</div>';
            });

            (entity.embedded || []).forEach(e => { html += '<div class="embedded-item">&lt;&gt; ' + e.name + ' [' + e.cardinality + ']</div>'; });

            if (!isSource) {
                (entity.references || []).forEach(r => { html += '<div class="reference-item">' + r.name + ' &rarr; ' + r.target + '</div>'; });
            }
            (entity.edges || []).forEach(e => { html += '<div class="edge-item">&#x2194; ' + e.name + ' &rarr; ' + e.target + ' [' + e.cardinality + ']</div>'; });
            html += '</div></div>';
            return html;
        }

        function renderNestedEntityCard(entity) {
            // Render entity card with nested structure support (for original source)
            let html = '<div class="entity-card"><div class="entity-name">' + entity.name;
            if (entity.type) html += ' <span class="entity-type-badge">' + entity.type + '</span>';
            html += '</div><div class="entity-body">';

            function renderAttributes(attrs, indent) {
                let result = '';
                attrs.forEach(a => {
                    const levelClass = indent > 0 ? ' nested-level-' + Math.min(indent, 3) : '';
                    if (a.nested) {
                        // Nested object - highlighted with special styling
                        result += '<div class="attribute nested-object' + levelClass + '">';
                        result += '<span class="attr-name">' + a.name + '</span>';
                        result += '<span class="attr-type">{object}</span></div>';
                        // Recursively render nested attributes with increased indent
                        result += renderAttributes(a.nested, indent + 1);
                    } else {
                        // Regular attribute
                        result += '<div class="attribute' + levelClass + '">';
                        result += '<span class="attr-name">' + a.name + '</span>';
                        result += '<span class="attr-type">' + a.type + '</span>';
                        if (a.is_key) result += '<span class="attr-badge pk">PK</span>';
                        if (a.is_fk) result += '<span class="attr-badge fk">FK</span>';
                        result += '</div>';
                    }
                });
                return result;
            }

            if (entity.attributes) {
                html += renderAttributes(entity.attributes, 0);
            }

            // Fallback for non-nested structure
            if (entity.embedded) {
                entity.embedded.forEach(e => { html += '<div class="embedded-item">&lt;&gt; ' + e.name + ' [' + e.cardinality + ']</div>'; });
            }
            if (entity.references) {
                entity.references.forEach(r => { html += '<div class="reference-item">' + r.name + ' &rarr; ' + r.target + '</div>'; });
            }
            if (entity.edges) {
                entity.edges.forEach(e => { html += '<div class="edge-item">&#x2194; ' + e.name + ' &rarr; ' + e.target + ' [' + e.cardinality + ']</div>'; });
            }

            html += '</div></div>';
            return html;
        }
        // ═══════════════════════════════════════════════════════
        // Source Schemas Tab - auto-loaded on page open
        // ═══════════════════════════════════════════════════════
        async function loadSourceSchemas() {
            const container = document.getElementById('tab-schemas');
            container.innerHTML = '<div class="loading show"><div class="spinner"></div><p>Loading schemas...</p></div>';
            try {
                const resp = await fetch('/api/schemas?t=' + Date.now());
                const data = await resp.json();
                renderSourceSchemas(data);
            } catch (e) {
                container.innerHTML = '<div class="welcome"><h2>Failed to load schemas</h2><p>' + e.message + '</p></div>';
            }
        }

        function renderSourceSchemas(data) {
            const container = document.getElementById('tab-schemas');
            let html = '<div class="source-schemas-page">';

            // ── Section 1: PostgreSQL ──
            html += '<div class="schema-section">';
            html += '<div class="schema-section-header"><h2>PostgreSQL</h2><span class="schema-badge relational">Relational</span></div>';
            html += '<div class="schema-section-subtitle">8 Tables, 8 Foreign Keys, 69 Fields — Normalized 3NF Design</div>';
            html += '<div class="vis-and-code">';
            html += '<div class="vis-block"><div class="section-title">ER Diagram</div>';
            html += '<div class="er-diagram"><div class="mermaid">' + getStaticERDiagram() + '</div></div></div>';
            html += '<div class="code-block-wrapper"><div class="section-title">DDL (SQL)</div>';
            html += '<div class="sql-code-view"><pre>' + escapeHtml(data.postgresql) + '</pre></div></div>';
            html += '</div></div>';

            // ── Section 2: MongoDB ──
            html += '<div class="schema-section">';
            html += '<div class="schema-section-header"><h2>MongoDB</h2><span class="schema-badge document">Document</span></div>';
            html += '<div class="schema-section-subtitle">1 Root Document "orders", 4-Level Nesting — Fully Denormalized</div>';
            html += '<div class="vis-and-code">';
            html += '<div class="vis-block"><div class="section-title">Document Structure</div>';
            html += '<div class="document-tree">' + renderMongoDocTree() + '</div></div>';
            html += '<div class="code-block-wrapper"><div class="section-title">JSON Schema</div>';
            html += '<div class="sql-code-view"><pre>' + syntaxHighlightJSON(data.mongodb) + '</pre></div></div>';
            html += '</div></div>';

            // ── Section 3: Neo4j ──
            html += '<div class="schema-section">';
            html += '<div class="schema-section-header"><h2>Neo4j</h2><span class="schema-badge graph">Graph</span></div>';
            html += '<div class="schema-section-subtitle">7 Nodes, 7 Relationships, 61 Properties — Property Graph Model</div>';
            html += '<div class="vis-and-code">';
            html += '<div class="vis-block"><div class="section-title">Graph Diagram</div>';
            html += '<div class="er-diagram">' + getStaticGraphDiagram() + '</div></div>';
            html += '<div class="code-block-wrapper"><div class="section-title">Cypher Schema</div>';
            html += '<div class="sql-code-view"><pre>' + escapeHtml(data.neo4j) + '</pre></div></div>';
            html += '</div></div>';

            // ── Section 4: Cassandra ──
            html += '<div class="schema-section">';
            html += '<div class="schema-section-header"><h2>Cassandra</h2><span class="schema-badge columnar">Columnar</span></div>';
            html += '<div class="schema-section-subtitle">8 Tables, Query-Driven Design, 69 Fields — Denormalized Wide-Column</div>';
            html += '<div class="vis-and-code">';
            html += '<div class="vis-block"><div class="section-title">Chebotko Diagram</div>';
            html += getStaticChebotkoDiagram();
            html += '</div>';
            html += '<div class="code-block-wrapper"><div class="section-title">CQL</div>';
            html += '<div class="sql-code-view"><pre>' + escapeHtml(data.cassandra) + '</pre></div></div>';
            html += '</div></div>';

            html += '</div>';
            container.innerHTML = html;

            // Render Mermaid diagrams
            if (mermaidReady) {
                setTimeout(() => { try { mermaid.run({ nodes: container.querySelectorAll('.mermaid') }); } catch(e) { console.warn('Mermaid render error:', e); } }, 100);
            }
        }

        // ── Static ER Diagram (PostgreSQL Northwind) ──
        function getStaticERDiagram() {
            return `erDiagram
    categories {
        string category_id PK
        string category_name
        string description
    }
    suppliers {
        string supplier_id PK
        string company_name
        string contact_name
        string contact_title
        string phone
        string fax
        string street
        string city
        string region
        string postal_code
        string country
    }
    shippers {
        string shipper_id PK
        string company_name
        string phone
    }
    employees {
        string employee_id PK
        string last_name
        string first_name
        string title
        string birth_date
        string hire_date
        string phone
        string notes
        string street
        string city
        string region
        string postal_code
        string country
        string reports_to FK
    }
    customers {
        string customer_id PK
        string company_name
        string contact_name
        string contact_title
        string phone
        string fax
        string street
        string city
        string region
        string postal_code
        string country
    }
    products {
        string product_id PK
        string product_name
        double unit_price
        integer units_in_stock
        boolean discontinued
        string quantity_per_unit
        string supplier_id FK
        string category_id FK
    }
    orders {
        string order_id PK
        string order_date
        string required_date
        string shipped_date
        double freight
        string ship_name
        string ship_address
        string ship_city
        string ship_region
        string ship_postal_code
        string ship_country
        string customer_id FK
        string employee_id FK
        string shipper_id FK
    }
    order_details {
        string order_id PK "FK"
        string product_id PK "FK"
        double unit_price
        integer quantity
        double discount
    }
    categories ||--o{ products : "category_id"
    suppliers ||--o{ products : "supplier_id"
    customers ||--o{ orders : "customer_id"
    employees ||--o{ orders : "employee_id"
    shippers ||--o{ orders : "shipper_id"
    employees |o--o{ employees : "reports_to"
    orders ||--o{ order_details : "order_id"
    products ||--o{ order_details : "product_id"`;
        }

        // ── Static Graph Diagram (Neo4j Northwind) ──
        function getStaticGraphDiagram() {
            // Build a static SVG using the same layout engine as generateGraphDiagram
            const W = 960, H = 700;
            const nodes = [
                { name: 'orders', x: W*0.28, y: H*0.45, hub: true, theme: 0 },
                { name: 'products', x: W*0.72, y: H*0.30, hub: true, theme: 1 },
                { name: 'customers', x: W*0.08, y: H*0.20, hub: false, theme: 0 },
                { name: 'employees', x: W*0.08, y: H*0.70, hub: false, theme: 0 },
                { name: 'shippers', x: W*0.42, y: H*0.78, hub: false, theme: 0 },
                { name: 'categories', x: W*0.92, y: H*0.12, hub: false, theme: 1 },
                { name: 'suppliers', x: W*0.92, y: H*0.52, hub: false, theme: 1 },
            ];
            const edges = [
                { from: 'customers', to: 'orders', label: 'PURCHASED' },
                { from: 'employees', to: 'orders', label: 'SOLD' },
                { from: 'orders', to: 'shippers', label: 'SHIPPED_VIA' },
                { from: 'orders', to: 'products', label: 'CONTAINS' },
                { from: 'suppliers', to: 'products', label: 'SUPPLIES' },
                { from: 'products', to: 'categories', label: 'PART_OF' },
                { from: 'employees', to: 'employees', label: 'REPORTS_TO' },
            ];
            const hubR = 30, satR = 22;
            const themes = [
                { fill:'#DBEAFE', stroke:'#3B82F6', text:'#1E40AF', satFill:'#EFF6FF', satStroke:'#93C5FD', satText:'#1E3A5F' },
                { fill:'#FEF3C7', stroke:'#F59E0B', text:'#92400E', satFill:'#FFFBEB', satStroke:'#FCD34D', satText:'#78350F' }
            ];
            const posMap = {};
            nodes.forEach(n => { posMap[n.name] = n; });

            let svg = '<div class="graph-svg-container"><svg viewBox="0 0 '+W+' '+H+'" style="width:100%;max-width:960px;height:auto;font-family:-apple-system,BlinkMacSystemFont,sans-serif;">';
            svg += '<defs><marker id="ahSS" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="#94A3B8"/></marker>';
            svg += '<marker id="ahSelf" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="#E11D48"/></marker></defs>';

            // Draw edges
            edges.forEach(e => {
                const s = posMap[e.from], t = posMap[e.to];
                if (e.from === e.to) {
                    // Self-loop
                    const loopR = 28;
                    svg += '<path d="M '+(s.x-8)+' '+(s.y-satR)+' C '+(s.x-loopR*1.2)+' '+(s.y-satR-loopR*1.5)+', '+(s.x+loopR*1.2)+' '+(s.y-satR-loopR*1.5)+', '+(s.x+8)+' '+(s.y-satR)+'" fill="none" stroke="#E11D48" stroke-width="1.3" opacity="0.8" marker-end="url(#ahSelf)"/>';
                    svg += '<text x="'+s.x+'" y="'+(s.y-satR-loopR*0.8)+'" text-anchor="middle" font-size="8" fill="#E11D48" font-weight="500">'+e.label+'</text>';
                } else {
                    const dx = t.x-s.x, dy = t.y-s.y;
                    const dist = Math.sqrt(dx*dx+dy*dy);
                    const nx = dx/dist, ny = dy/dist;
                    const sR = s.hub ? hubR : satR;
                    const tR = t.hub ? hubR : satR;
                    const x1 = s.x+nx*(sR+2), y1 = s.y+ny*(sR+2);
                    const x2 = t.x-nx*(tR+10), y2 = t.y-ny*(tR+10);
                    const mx = (x1+x2)/2, my = (y1+y2)/2;
                    svg += '<line x1="'+x1+'" y1="'+y1+'" x2="'+x2+'" y2="'+y2+'" stroke="#94A3B8" stroke-width="1.1" opacity="0.65" marker-end="url(#ahSS)"/>';
                    svg += '<text x="'+mx+'" y="'+(my-4)+'" text-anchor="middle" font-size="8" fill="#475569" opacity="0.85">'+e.label+'</text>';
                }
            });

            // Draw nodes
            nodes.forEach(n => {
                const th = themes[n.theme];
                if (n.hub) {
                    svg += '<circle cx="'+n.x+'" cy="'+n.y+'" r="'+hubR+'" fill="'+th.fill+'" stroke="'+th.stroke+'" stroke-width="2.5"/>';
                    const fs = n.name.length > 7 ? 10 : 11;
                    svg += '<text x="'+n.x+'" y="'+(n.y+4)+'" text-anchor="middle" font-size="'+fs+'" font-weight="700" fill="'+th.text+'">'+n.name+'</text>';
                } else {
                    svg += '<circle cx="'+n.x+'" cy="'+n.y+'" r="'+satR+'" fill="'+th.satFill+'" stroke="'+th.satStroke+'" stroke-width="1.5"/>';
                    const fs = n.name.length > 8 ? 8.5 : 9.5;
                    svg += '<text x="'+n.x+'" y="'+(n.y+3)+'" text-anchor="middle" font-size="'+fs+'" font-weight="600" fill="'+th.satText+'">'+n.name+'</text>';
                }
            });

            svg += '<text x="'+(W/2)+'" y="'+(H-12)+'" text-anchor="middle" font-size="11" fill="#94A3B8" font-weight="500">7 Nodes, 7 Relationships</text>';
            svg += '</svg></div>';
            return svg;
        }

        // ── MongoDB Document Tree ──
        function renderMongoDocTree() {
            return '<span class="dt-key">orders</span> <span class="dt-comment">(root document)</span>\\n'
                + '<span class="dt-key">|-- _id</span>: <span class="dt-type">string</span> <span class="dt-comment">(order_id, primary key)</span>\\n'
                + '<span class="dt-key">|-- order_date</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|-- required_date</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|-- shipped_date</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|-- freight</span>: <span class="dt-type">double</span>\\n'
                + '<span class="dt-key">|-- ship_name</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|-- ship_destination</span>: <span class="dt-obj">{object}</span> <span class="dt-comment">Level 1</span>\\n'
                + '<span class="dt-key">|   |-- ship_address</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|   |-- ship_city</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|   |-- ship_region</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|   |-- ship_postal_code</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|   +-- ship_country</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|</span>\\n'
                + '<span class="dt-key">|-- customer</span>: <span class="dt-obj">{object}</span> <span class="dt-comment">Level 1, required</span>\\n'
                + '<span class="dt-key">|   |-- company_name</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|   |-- contact_name</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|   |-- contact_title</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|   |-- phone</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|   |-- fax</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|   +-- address</span>: <span class="dt-obj">{object}</span> <span class="dt-comment">Level 2</span>\\n'
                + '<span class="dt-key">|       |-- street</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|       |-- city</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|       |-- region</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|       |-- postal_code</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|       +-- country</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|</span>\\n'
                + '<span class="dt-key">|-- employee</span>: <span class="dt-obj">{object}</span> <span class="dt-comment">Level 1, required</span>\\n'
                + '<span class="dt-key">|   |-- last_name</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|   |-- first_name</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|   |-- title</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|   |-- birth_date</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|   |-- hire_date</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|   |-- phone</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|   |-- notes</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|   |-- reports_to</span>: <span class="dt-type">string</span> <span class="dt-comment">(self-ref)</span>\\n'
                + '<span class="dt-key">|   +-- address</span>: <span class="dt-obj">{object}</span> <span class="dt-comment">Level 2</span>\\n'
                + '<span class="dt-key">|       |-- street</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|       |-- city</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|       |-- region</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|       |-- postal_code</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|       +-- country</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|</span>\\n'
                + '<span class="dt-key">|-- shipper</span>: <span class="dt-obj">{object}</span> <span class="dt-comment">Level 1, required</span>\\n'
                + '<span class="dt-key">|   |-- company_name</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|   +-- phone</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">|</span>\\n'
                + '<span class="dt-key">+-- details</span>: <span class="dt-arr">[array]</span> <span class="dt-comment">Level 1, order line items</span>\\n'
                + '<span class="dt-key">    +-- [each item]</span>:\\n'
                + '<span class="dt-key">        |-- unit_price</span>: <span class="dt-type">double</span>\\n'
                + '<span class="dt-key">        |-- quantity</span>: <span class="dt-type">int</span>\\n'
                + '<span class="dt-key">        |-- discount</span>: <span class="dt-type">double</span>\\n'
                + '<span class="dt-key">        +-- product</span>: <span class="dt-obj">{object}</span> <span class="dt-comment">Level 2, required</span>\\n'
                + '<span class="dt-key">            |-- product_name</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">            |-- unit_price</span>: <span class="dt-type">double</span>\\n'
                + '<span class="dt-key">            |-- units_in_stock</span>: <span class="dt-type">int</span>\\n'
                + '<span class="dt-key">            |-- discontinued</span>: <span class="dt-type">bool</span>\\n'
                + '<span class="dt-key">            |-- quantity_per_unit</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">            |-- category</span>: <span class="dt-obj">{object}</span> <span class="dt-comment">Level 3, required</span>\\n'
                + '<span class="dt-key">            |   |-- category_name</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">            |   +-- description</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">            +-- supplier</span>: <span class="dt-obj">{object}</span> <span class="dt-comment">Level 3, required</span>\\n'
                + '<span class="dt-key">                |-- company_name</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">                |-- contact_name</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">                |-- contact_title</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">                |-- phone</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">                |-- fax</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">                +-- address</span>: <span class="dt-obj">{object}</span> <span class="dt-comment">Level 4 (deepest)</span>\\n'
                + '<span class="dt-key">                    |-- street</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">                    |-- city</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">                    |-- region</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">                    |-- postal_code</span>: <span class="dt-type">string</span>\\n'
                + '<span class="dt-key">                    +-- country</span>: <span class="dt-type">string</span>';
        }

        // ── Static Chebotko Diagram (Cassandra Northwind) ──
        function getStaticChebotkoDiagram() {
            const tables = [
                { name: 'categories', cols: [
                    { name: 'category_id', type: 'TEXT', key: 'pk' },
                    { name: 'category_name', type: 'TEXT', key: '' },
                    { name: 'description', type: 'TEXT', key: '' }
                ]},
                { name: 'suppliers', cols: [
                    { name: 'supplier_id', type: 'TEXT', key: 'pk' },
                    { name: 'company_name', type: 'TEXT', key: '' },
                    { name: 'contact_name', type: 'TEXT', key: '' },
                    { name: 'contact_title', type: 'TEXT', key: '' },
                    { name: 'phone', type: 'TEXT', key: '' },
                    { name: 'fax', type: 'TEXT', key: '' },
                    { name: 'street', type: 'TEXT', key: '' },
                    { name: 'city', type: 'TEXT', key: '' },
                    { name: 'region', type: 'TEXT', key: '' },
                    { name: 'postal_code', type: 'TEXT', key: '' },
                    { name: 'country', type: 'TEXT', key: '' }
                ]},
                { name: 'shippers', cols: [
                    { name: 'shipper_id', type: 'TEXT', key: 'pk' },
                    { name: 'company_name', type: 'TEXT', key: '' },
                    { name: 'phone', type: 'TEXT', key: '' }
                ]},
                { name: 'employees', cols: [
                    { name: 'employee_id', type: 'TEXT', key: 'pk' },
                    { name: 'last_name', type: 'TEXT', key: '' },
                    { name: 'first_name', type: 'TEXT', key: '' },
                    { name: 'title', type: 'TEXT', key: '' },
                    { name: 'birth_date', type: 'TEXT', key: '' },
                    { name: 'hire_date', type: 'TEXT', key: '' },
                    { name: 'phone', type: 'TEXT', key: '' },
                    { name: 'notes', type: 'TEXT', key: '' },
                    { name: 'street', type: 'TEXT', key: '' },
                    { name: 'city', type: 'TEXT', key: '' },
                    { name: 'region', type: 'TEXT', key: '' },
                    { name: 'postal_code', type: 'TEXT', key: '' },
                    { name: 'country', type: 'TEXT', key: '' },
                    { name: 'reports_to', type: 'TEXT', key: '' }
                ]},
                { name: 'customers', cols: [
                    { name: 'customer_id', type: 'TEXT', key: 'pk' },
                    { name: 'company_name', type: 'TEXT', key: '' },
                    { name: 'contact_name', type: 'TEXT', key: '' },
                    { name: 'contact_title', type: 'TEXT', key: '' },
                    { name: 'phone', type: 'TEXT', key: '' },
                    { name: 'fax', type: 'TEXT', key: '' },
                    { name: 'street', type: 'TEXT', key: '' },
                    { name: 'city', type: 'TEXT', key: '' },
                    { name: 'region', type: 'TEXT', key: '' },
                    { name: 'postal_code', type: 'TEXT', key: '' },
                    { name: 'country', type: 'TEXT', key: '' }
                ]},
                { name: 'products', cols: [
                    { name: 'category_id', type: 'TEXT', key: 'pk' },
                    { name: 'supplier_id', type: 'TEXT', key: 'pk' },
                    { name: 'product_id', type: 'TEXT', key: 'ck' },
                    { name: 'product_name', type: 'TEXT', key: '' },
                    { name: 'unit_price', type: 'DOUBLE', key: '' },
                    { name: 'units_in_stock', type: 'INT', key: '' },
                    { name: 'discontinued', type: 'BOOLEAN', key: '' },
                    { name: 'quantity_per_unit', type: 'TEXT', key: '' }
                ]},
                { name: 'orders', cols: [
                    { name: 'customer_id', type: 'TEXT', key: 'pk' },
                    { name: 'order_date', type: 'TEXT', key: 'ck' },
                    { name: 'order_id', type: 'TEXT', key: 'ck' },
                    { name: 'required_date', type: 'TEXT', key: '' },
                    { name: 'shipped_date', type: 'TEXT', key: '' },
                    { name: 'freight', type: 'DOUBLE', key: '' },
                    { name: 'ship_name', type: 'TEXT', key: '' },
                    { name: 'ship_address', type: 'TEXT', key: '' },
                    { name: 'ship_city', type: 'TEXT', key: '' },
                    { name: 'ship_region', type: 'TEXT', key: '' },
                    { name: 'ship_postal_code', type: 'TEXT', key: '' },
                    { name: 'ship_country', type: 'TEXT', key: '' },
                    { name: 'employee_id', type: 'TEXT', key: '' },
                    { name: 'shipper_id', type: 'TEXT', key: '' }
                ]},
                { name: 'order_details', cols: [
                    { name: 'order_id', type: 'TEXT', key: 'pk' },
                    { name: 'product_id', type: 'TEXT', key: 'pk' },
                    { name: 'unit_price', type: 'DOUBLE', key: '' },
                    { name: 'quantity', type: 'INT', key: '' },
                    { name: 'discount', type: 'DOUBLE', key: '' }
                ]}
            ];
            let html = '<div class="chebotko-diagram">';
            tables.forEach(t => {
                html += '<div class="chebotko-table"><div class="chebotko-header">' + t.name + '</div>';
                html += '<table class="chebotko-cols">';
                t.cols.forEach(c => {
                    let marker = '';
                    if (c.key === 'pk') marker = '<span class="ck-marker pk">K&#x2191;</span>';
                    else if (c.key === 'ck') marker = '<span class="ck-marker ck">C&#x2191;</span>';
                    html += '<tr><td class="ck-marker-cell">' + marker + '</td>';
                    html += '<td class="ck-name">' + c.name + '</td>';
                    html += '<td class="ck-type">' + c.type + '</td></tr>';
                });
                html += '</table></div>';
            });
            html += '</div>';
            return html;
        }

        // Load Source Schemas on page load
        loadSourceSchemas();
    </script>
</body>
</html>'''
    # Inject dynamic content from config.py
    html = html.replace('<!-- DROPDOWN_OPTIONS -->', _build_dropdown_options())
    html = html.replace('// INJECT_CONFIG', _build_config_js())
    return html


def main():
    server = HTTPServer(('localhost', PORT), SMELHandler)
    print(f"\n  SMEL Web Server running at http://localhost:{PORT}")
    print(f"  Press Ctrl+C to stop\n")

    threading.Timer(1.0, lambda: webbrowser.open(f'http://localhost:{PORT}')).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
