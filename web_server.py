"""
SMEL Web Server - Web interface for schema migration visualization.
Run this file and open http://localhost:5567 in your browser.
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

PORT = 5573


class SMELHandler(SimpleHTTPRequestHandler):
    """HTTP request handler for SMEL web interface."""

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            self.wfile.write(get_html().encode())
        elif self.path.startswith('/api/migrate'):
            query = self.path.split('?')[1] if '?' in self.path else ''
            params = parse_qs(query)
            direction = params.get('direction', ['2'])[0]

            result = run_migration(direction)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            super().do_GET()

    def log_message(self, format, *args):
        pass


def get_html():
    """Return the HTML page with Apple-style design."""
    return '''<!DOCTYPE html>
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

        .dropdown { position: relative; min-width: 240px; }
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

        .tables-section { margin-bottom: 40px; }
        .tables-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
        }

        .table-card { background: #F5F5F7; border-radius: 16px; overflow: hidden; }
        .table-header {
            padding: 14px 18px;
            background: #FFFFFF;
            border-bottom: 1px solid #E8E8ED;
            font-weight: 600;
            font-size: 15px;
            color: #1D1D1F;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .table-icon {
            width: 24px;
            height: 24px;
            background: #0066CC;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 12px;
            font-weight: 700;
        }

        .table-body { padding: 8px 0; }
        .table-row {
            display: flex;
            align-items: center;
            padding: 8px 18px;
            font-size: 14px;
        }
        .col-name { flex: 1; font-weight: 500; color: #1D1D1F; }
        .col-type { color: #636366; font-size: 13px; margin-right: 10px; }
        .col-badge {
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
            margin-left: 4px;
        }
        .col-badge.pk { background: #0066CC; color: white; }
        .col-badge.fk { background: #BF4800; color: white; }
        .col-badge.null { background: #E8E8ED; color: #636366; }

        .fk-section {
            padding: 10px 18px;
            background: #FFFFFF;
            border-top: 1px solid #E8E8ED;
            font-size: 12px;
            color: #0066CC;
        }

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

        .target-tables-grid {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

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
                    <option value="r2d">Relational &rarr; Document</option>
                    <option value="d2r" selected>Document &rarr; Relational</option>
                    <option value="r2r">Relational &rarr; Relational (v1 &rarr; v2)</option>
                    <option value="d2d">Document &rarr; Document (v1 &rarr; v2)</option>
                    <option value="person_d2r">Person: MongoDB &rarr; PostgreSQL (Mini Example)</option>
                </select>
            </div>
        </div>
        <button class="run-btn" onclick="runMigration()">Run</button>
    </div>

    <div class="loading" id="loading">
        <div class="spinner"></div>
        <p>Running schema transformation...</p>
    </div>

    <div class="welcome" id="welcome">
        <h2>Select migration or evolution and click Run</h2>
        <p>Compare source and target schemas side by side</p>
    </div>

    <nav class="tab-nav" id="tabNav">
        <button class="tab-btn active" data-tab="compare">Schema Comparison</button>
        <button class="tab-btn" data-tab="smel">SMEL Script</button>
        <button class="tab-btn" data-tab="migration">Migration Process</button>
    </nav>

    <div class="tab-content active" id="tab-compare"></div>
    <div class="tab-content" id="tab-smel"></div>
    <div class="tab-content" id="tab-migration"></div>

    <footer class="footer">SMEL - Schema Migration & Evolution Language</footer>

    <script>
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
                    er: { useMaxWidth: true, layoutDirection: 'LR', entityPadding: 15, fontSize: 14 }
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
            document.getElementById('tabNav').classList.remove('show');
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            try {
                const response = await fetch('/api/migrate?direction=' + direction + '&t=' + Date.now());
                migrationData = await response.json();
                document.getElementById('loading').classList.remove('show');

                if (migrationData.error) { alert(migrationData.error); return; }

                renderCompareView();
                renderSmelScript();
                renderMigrationProcess();
                document.getElementById('tabNav').classList.add('show');
                document.querySelector('.tab-btn[data-tab="compare"]').click();
            } catch (error) {
                document.getElementById('loading').classList.remove('show');
                alert('Error: ' + error.message);
            }
        }

        function renderCompareView() {
            const container = document.getElementById('tab-compare');
            const isSourceRelational = migrationData.source_type === 'Relational';
            const isTargetRelational = migrationData.target_type === 'Relational';

            let html = '<div class="schema-compare">';
            html += '<div class="schema-panel">';
            html += '<div class="panel-header"><span class="panel-title">Source Schema</span>';
            html += '<span class="schema-badge ' + (isSourceRelational ? 'relational' : 'document') + '">' + migrationData.source_type + '</span></div>';

            if (isSourceRelational) {
                // Relational Source: Show original DDL with database-specific types
                html += '<div class="sql-section"><div class="section-title">Original DDL</div>';
                html += '<div class="sql-code-view"><pre>' + escapeHtml(migrationData.raw_source) + '</pre></div></div>';
            } else {
                // Document Source: Show original JSON schema
                html += '<div class="document-view"><div class="json-display">' + syntaxHighlightJSON(migrationData.raw_source) + '</div></div>';
            }
            html += '</div>';

            html += '<div class="schema-panel">';
            html += '<div class="panel-header"><span class="panel-title">Target Schema</span>';
            html += '<span class="schema-badge ' + (isTargetRelational ? 'relational' : 'document') + '">' + migrationData.target_type + '</span></div>';

            if (isTargetRelational) {
                // Relational Target: Show ER Diagram + Generated DDL
                const targetEntities = migrationData.target_with_db_types || migrationData.result;
                html += '<div class="er-section"><div class="section-title">ER Diagram</div>';
                html += '<div class="er-diagram">' + generateERDiagram(targetEntities) + '</div></div>';
                html += '<div class="sql-section"><div class="section-title">Generated DDL</div>';
                html += '<div class="sql-code-view"><pre>' + escapeHtml(migrationData.exported_target) + '</pre></div></div>';
            } else {
                // Document Target: JSON structure view
                html += '<div class="document-view"><div class="json-display">' + syntaxHighlightJSON(migrationData.exported_target) + '</div></div>';
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
            html += '<span class="smel-file-badge">' + operations.length + ' operations</span>';
            html += '</div>';
            html += '<div class="smel-panel-body">';
            html += '<div class="operations-list">';

            operations.forEach((op, index) => {
                const changed = op.entity_count_before !== op.entity_count_after;
                const hasChanges = op.changes && op.changes.affected_entities && op.changes.affected_entities.length > 0;
                html += '<div class="operation-item">';
                html += '<div class="operation-header">';
                html += '<div class="operation-step">';
                html += '<span class="step-number">' + op.step + '</span>';
                html += '<span class="operation-type">' + op.type + '</span>';
                html += '</div>';
                if (changed) {
                    html += '<span class="operation-badge changed">' + op.entity_count_before + ' → ' + op.entity_count_after + ' entities</span>';
                } else {
                    html += '<span class="operation-badge">' + op.entity_count_after + ' entities</span>';
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
            html += '<div class="summary-item"><div class="summary-value">' + migrationData.stats.source_count + '</div><div class="summary-label">Source Entities</div></div>';
            html += '<div class="summary-item"><div class="summary-value">' + operations.length + '</div><div class="summary-label">Operations</div></div>';
            html += '<div class="summary-item"><div class="summary-value">' + migrationData.stats.result_count + '</div><div class="summary-label">Result Entities</div></div>';
            html += '<div class="summary-item"><div class="summary-value">' + migrationData.source_type + ' → ' + migrationData.target_type + '</div><div class="summary-label">Direction</div></div>';
            html += '</div>';

            html += '</div></div>';
            container.innerHTML = html;
        }

        function highlightSmelSyntax(code) {
            if (!code) return '';
            let result = escapeHtml(code);

            // Comments (-- ...)
            result = result.replace(/(--[^\\n]*)/g, '<span class="smel-comment">$1</span>');

            // Keywords
            const keywords = ['MIGRATION', 'FROM', 'TO', 'USING', 'AS', 'INTO', 'WITH', 'WHERE', 'IN', 'KEY', 'AND',
                'RELATIONAL', 'DOCUMENT', 'GRAPH', 'COLUMNAR',
                'NEST', 'UNNEST', 'FLATTEN', 'DELETE', 'ADD', 'RENAME', 'COPY', 'MOVE', 'MERGE', 'SPLIT', 'CAST', 'DROP', 'EXTRACT',
                'REFERENCE', 'ATTRIBUTE', 'EMBEDDED', 'ENTITY', 'VARIATION', 'RELTYPE',
                'CARDINALITY', 'ONE_TO_ONE', 'ONE_TO_MANY', 'ZERO_TO_ONE', 'ZERO_TO_MANY',
                'PRIMARY', 'UNIQUE', 'FOREIGN', 'PARTITION', 'CLUSTERING'];
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
                }

                html += '</div>';
            });

            return html;
        }

        function formatOperationParams(type, params) {
            if (!params) return '';
            let html = '';

            switch(type) {
                case 'NEST':
                    html = '<span class="param-key">source:</span> <span class="param-value">' + params.source + '</span> → ';
                    html += '<span class="param-key">target:</span> <span class="param-value">' + params.target + '</span>';
                    if (params.alias) html += ' <span class="param-key">as:</span> <span class="param-value">' + params.alias + '</span>';
                    break;
                case 'DELETE_REFERENCE':
                    html = '<span class="param-key">reference:</span> <span class="param-value">' + params.reference + '</span>';
                    break;
                case 'DELETE_ENTITY':
                    html = '<span class="param-key">entity:</span> <span class="param-value">' + params.name + '</span>';
                    break;
                case 'RENAME':
                    html = '<span class="param-key">rename:</span> <span class="param-value">' + params.old_name + '</span> → <span class="param-value">' + params.new_name + '</span>';
                    if (params.entity) html += ' <span class="param-key">in:</span> <span class="param-value">' + params.entity + '</span>';
                    break;
                case 'FLATTEN':
                    // Unified FLATTEN: handles embedded objects, value arrays, and M:N reference arrays
                    html = '<span class="param-key">FLATTEN</span> ';
                    html += '<span class="param-value">' + params.source + '</span> → ';
                    html += '<span class="param-key">AS</span> <span class="param-value">' + params.target + '</span>';
                    // Indicate PK type based on presence of GENERATE KEY clause
                    if (params.clauses) {
                        const hasGenerateKey = params.clauses.some(c => c.type === 'GENERATE_KEY');
                        if (hasGenerateKey) {
                            html += ' <span class="param-key">(single PK)</span>';
                        } else {
                            html += ' <span class="param-key">(composite PK)</span>';
                        }
                    }
                    break;
                case 'ADD_KEY':
                    html = '<span class="param-key">key_type:</span> <span class="param-value">' + params.key_type + '</span> ';
                    if (params.key_columns) {
                        const cols = params.key_columns.length > 1 ? '(' + params.key_columns.join(', ') + ')' : params.key_columns[0];
                        html += '<span class="param-key">columns:</span> <span class="param-value">' + cols + '</span>';
                    }
                    if (params.entity) html += ' <span class="param-key">TO</span> <span class="param-value">' + params.entity + '</span>';
                    break;
                case 'DROP_KEY':
                    html = '<span class="param-key">key_type:</span> <span class="param-value">' + params.key_type + '</span> ';
                    if (params.key_columns) {
                        const cols = params.key_columns.length > 1 ? '(' + params.key_columns.join(', ') + ')' : params.key_columns[0];
                        html += '<span class="param-key">columns:</span> <span class="param-value">' + cols + '</span>';
                    }
                    if (params.entity) html += ' <span class="param-key">FROM</span> <span class="param-value">' + params.entity + '</span>';
                    break;
                case 'ADD_REFERENCE':
                    html = '<span class="param-key">reference:</span> <span class="param-value">' + params.reference + '</span> → ';
                    html += '<span class="param-key">target:</span> <span class="param-value">' + params.target + '</span>';
                    break;
                case 'DELETE_EMBEDDED':
                    html = '<span class="param-key">embedded:</span> <span class="param-value">' + params.embedded + '</span>';
                    break;
                default:
                    html = Object.entries(params).map(([k, v]) => {
                        if (typeof v === 'object') return '';
                        return '<span class="param-key">' + k + ':</span> <span class="param-value">' + v + '</span>';
                    }).filter(x => x).join(' ');
            }
            return html;
        }

        function escapeHtml(text) {
            if (!text) return '';
            return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }

        function renderRelationalPanel(entities, type) {
            let html = '<div class="er-section"><div class="section-title">ER Diagram</div>';
            html += '<div class="er-diagram">' + generateERDiagram(entities) + '</div></div>';
            html += '<div class="tables-section"><div class="section-title">Tables</div><div class="tables-grid">';
            Object.values(entities).forEach(entity => { html += renderTableCard(entity); });
            html += '</div></div>';
            return html;
        }

        function generateMermaidSyntax(entities) {
            let syntax = 'erDiagram\\n';
            const entityList = Object.values(entities);
            const addedRels = new Set();

            entityList.forEach(entity => {
                const safeName = entity.name.replace(/[^a-zA-Z0-9_]/g, '_');
                syntax += '    ' + safeName + ' {\\n';
                entity.attributes.forEach(attr => {
                    const safeAttr = attr.name.replace(/[^a-zA-Z0-9_]/g, '_');
                    const safeType = attr.type.replace(/[^a-zA-Z0-9_]/g, '_');
                    const isFk = (entity.references || []).some(r => r.name === attr.name);
                    let key = attr.is_key ? ' PK' : (isFk ? ' FK' : '');
                    syntax += '        ' + safeAttr + ' ' + safeType + key + '\\n';
                });
                syntax += '    }\\n';
            });

            entityList.forEach(entity => {
                const src = entity.name.replace(/[^a-zA-Z0-9_]/g, '_');
                (entity.references || []).forEach(ref => {
                    const tgt = ref.target.replace(/[^a-zA-Z0-9_]/g, '_');
                    const key = tgt + '-' + src;
                    if (!addedRels.has(key)) {
                        addedRels.add(key);
                        syntax += '    ' + tgt + ' ||--o{ ' + src + ' : "' + ref.name + '"\\n';
                    }
                });
                (entity.embedded || []).forEach(emb => {
                    const tgt = emb.target.replace(/[^a-zA-Z0-9_]/g, '_');
                    const key = src + '-' + tgt;
                    if (!addedRels.has(key)) {
                        addedRels.add(key);
                        const rel = emb.cardinality === 'ONE_TO_ONE' ? '||--||' : '||--o{';
                        syntax += '    ' + src + ' ' + rel + ' ' + tgt + ' : "1:N"\\n';
                    }
                });
            });
            return syntax;
        }

        function generateERDiagram(entities) {
            return '<div class="mermaid">' + generateMermaidSyntax(entities) + '</div>';
        }

        function renderTableCard(entity) {
            const refs = entity.references || [];
            const refNames = new Set(refs.map(r => r.name));
            let html = '<div class="table-card"><div class="table-header"><span class="table-icon">T</span>' + entity.name + '</div><div class="table-body">';
            (entity.attributes || []).forEach(attr => {
                const isFk = refNames.has(attr.name);
                html += '<div class="table-row"><span class="col-name">' + attr.name + '</span><span class="col-type">' + attr.type + '</span>';
                if (attr.is_key) html += '<span class="col-badge pk">PK</span>';
                if (isFk) html += '<span class="col-badge fk">FK</span>';
                if (attr.is_optional) html += '<span class="col-badge null">NULL</span>';
                html += '</div>';
            });
            html += '</div>';
            if (refs.length > 0) {
                html += '<div class="fk-section">';
                refs.forEach(r => { html += '<div>' + r.name + ' &rarr; ' + r.target + '</div>'; });
                html += '</div>';
            }
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
            const isSourceRelational = migrationData.source_type === 'Relational';
            const isTargetRelational = migrationData.target_type === 'Relational';

            // Meta V1 and Meta V2 entities (must be aligned)
            const metaEntities = new Set([...Object.keys(migrationData.meta_v1), ...Object.keys(migrationData.result)]);
            const newEntities = new Set(migrationData.changes.filter(c => c.startsWith('FLATTEN:') || c.startsWith('NEST:')).map(c => c.split(':')[1]));

            // Source entities (independent)
            const sourceEntities = Object.values(migrationData.source);

            // Target: use exported_target for display

            let html = '<div class="migration-content"><div class="legend">';
            html += '<div class="legend-item"><span class="legend-dot new"></span>New Entity</div>';
            html += '<div class="legend-item"><span class="legend-dot reference"></span>Reference (FK)</div>';
            html += '<div class="legend-item"><span class="legend-dot embedded"></span>Embedded</div>';
            html += '<div class="legend-item"><span class="legend-dot pk"></span>Primary Key</div></div>';

            // Four-column layout
            html += '<div class="four-column-layout">';

            // Column 1: Source Schema (original nested structure before reverse eng)
            html += '<div class="independent-column source-column">';
            html += '<div class="column-header"><h3>Source</h3><div class="subtitle">' + migrationData.source_type + '</div></div>';
            html += '<div class="column-content">';
            console.log('original_source:', migrationData.original_source);
            console.log('source:', migrationData.source);
            const sourceData = migrationData.original_source && Object.keys(migrationData.original_source).length > 0
                ? migrationData.original_source
                : migrationData.source;
            console.log('Using sourceData:', sourceData);
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
                const v1Entity = migrationData.meta_v1[name];
                html += '<div class="grid-cell">';
                if (!v1Entity) {
                    html += '<div class="entity-card placeholder-card"><div class="entity-name placeholder-name">' + name + '</div>';
                    html += '<div class="entity-body placeholder-body">(--)</div></div>';
                } else {
                    html += renderEntityCard(v1Entity, false, false);
                }
                html += '</div>';

                // Meta V2 cell
                const v2Entity = migrationData.result[name];
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
            html += '<div class="column-header"><h3>Target</h3><div class="subtitle">' + migrationData.target_type + '</div></div>';
            html += '<div class="column-content">';
            if (isTargetRelational) {
                // Show schema format
                html += '<div class="schema-view"><pre class="schema-code">' + escapeHtml(migrationData.exported_target) + '</pre></div>';
            } else {
                // Show generated JSON
                html += '<div class="json-view">' + syntaxHighlightJSON(migrationData.exported_target) + '</div>';
            }
            html += '</div></div>';

            html += '</div>'; // end four-column-layout

            html += '<div class="validation"><div class="validation-header"><h2>Transformation Summary</h2>';
            html += '<div class="validation-status passed">Complete</div></div><div class="validation-stats">';
            html += '<div class="stat-card"><div class="stat-value">' + migrationData.operations_count + '</div><div class="stat-label">Operations</div></div>';
            html += '<div class="stat-card"><div class="stat-value">' + migrationData.stats.source_count + '</div><div class="stat-label">Source Entities</div></div>';
            html += '<div class="stat-card"><div class="stat-value">' + migrationData.stats.result_count + '</div><div class="stat-label">Result Entities</div></div>';
            html += '<div class="stat-card"><div class="stat-value">' + migrationData.target_type + '</div><div class="stat-label">Target Format</div></div>';
            html += '</div></div></div>';
            container.innerHTML = html;

            if (mermaidReady) {
                setTimeout(() => { try { mermaid.run({ nodes: container.querySelectorAll('.mermaid') }); } catch (e) {} }, 100);
            }
        }

        function renderEntityCard(entity, isNew, isSource) {
            let html = '<div class="entity-card' + (isNew ? ' new' : '') + '"><div class="entity-name' + (isNew ? ' new' : '') + '">' + entity.name + '</div><div class="entity-body">';

            const refMap = {};
            entity.references.forEach(r => { refMap[r.name] = r.target; });

            entity.attributes.forEach(a => {
                html += '<div class="attribute"><span class="attr-name">' + a.name + '</span><span class="attr-type">' + a.type;
                if (isSource && refMap[a.name]) {
                    html += ' &rarr; ' + refMap[a.name];
                }
                html += '</span>';
                if (a.is_key) html += '<span class="attr-badge pk">PK</span>';
                if (a.is_optional) html += '<span class="attr-badge optional">?</span>';
                html += '</div>';
            });

            entity.embedded.forEach(e => { html += '<div class="embedded-item">&lt;&gt; ' + e.name + ' [' + e.cardinality + ']</div>'; });

            if (!isSource) {
                entity.references.forEach(r => { html += '<div class="reference-item">' + r.name + ' &rarr; ' + r.target + '</div>'; });
            }
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
                    const indentStr = '&nbsp;'.repeat(indent * 2);
                    if (a.nested) {
                        // Nested object
                        result += '<div class="attribute nested-object">' + indentStr + '<span class="attr-name">' + a.name + '</span>';
                        result += '<span class="attr-type">{object}</span></div>';
                        result += renderAttributes(a.nested, indent + 1);
                    } else {
                        // Regular attribute
                        result += '<div class="attribute">' + indentStr + '<span class="attr-name">' + a.name + '</span>';
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

            html += '</div></div>';
            return html;
        }
    </script>
</body>
</html>'''


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
