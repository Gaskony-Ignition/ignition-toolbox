"""
FAT report generation step handlers

Handles Factory Acceptance Test report generation and export.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ignition_toolkit.playbook.exceptions import StepExecutionError
from ignition_toolkit.playbook.executors.base import StepHandler

logger = logging.getLogger(__name__)


class FATGenerateReportHandler(StepHandler):
    """Handle fat.generate_report step - Generate FAT report"""

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        test_results = params.get("test_results", {})
        visual_analysis = params.get("visual_analysis", {})
        screenshots_dir = params.get("screenshots_dir", "./data/screenshots")
        format_type = params.get("format", "html")
        template = params.get("template", "default")
        metadata = params.get("metadata", {})

        # Validate test results
        if not test_results or not isinstance(test_results, dict):
            raise StepExecutionError(
                "fat",
                "Invalid or missing test_results parameter"
            )

        results_list = test_results.get("results", [])
        total_tests = test_results.get("total", len(results_list))
        passed_tests = test_results.get("passed", 0)
        failed_tests = test_results.get("failed", 0)
        skipped_tests = test_results.get("skipped", 0)

        # Extract visual analysis data
        visual_issues = 0
        if visual_analysis and isinstance(visual_analysis, dict):
            visual_issues = visual_analysis.get("issues_count", 0)

        # Generate report HTML
        report_html = self._generate_html_report(
            test_results=results_list,
            total=total_tests,
            passed=passed_tests,
            failed=failed_tests,
            skipped=skipped_tests,
            visual_issues=visual_issues,
            visual_analysis=visual_analysis,
            metadata=metadata,
            screenshots_dir=screenshots_dir
        )

        # Save report to file
        report_id = f"fat_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report_dir = Path("./data/reports")
        report_dir.mkdir(parents=True, exist_ok=True)

        report_path = report_dir / f"{report_id}.html"

        with open(report_path, "w") as f:
            f.write(report_html)

        logger.info(
            f"FAT report generated: {report_path} "
            f"({passed_tests}/{total_tests} passed, {failed_tests} failed, "
            f"{visual_issues} visual issues)"
        )

        return {
            "status": "generated",
            "report_id": report_id,
            "report_path": str(report_path),
            "format": format_type,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "visual_issues": visual_issues
        }

    def _generate_html_report(
        self,
        test_results: list[dict],
        total: int,
        passed: int,
        failed: int,
        skipped: int,
        visual_issues: int,
        visual_analysis: dict,
        metadata: dict,
        screenshots_dir: str
    ) -> str:
        """Generate HTML report"""

        # Extract metadata
        project_name = metadata.get("project_name", "Perspective Project")
        test_date = metadata.get("test_date", datetime.now().isoformat())
        tester = metadata.get("tester", "Unknown")
        client = metadata.get("client", "")

        # Calculate pass rate
        pass_rate = (passed / total * 100) if total > 0 else 0

        # Generate test result rows
        test_rows = []
        for idx, result in enumerate(test_results, 1):
            status = result.get("status", "unknown")
            status_class = "pass" if status == "passed" else "fail"
            status_icon = "✓" if status == "passed" else "✗"

            component_id = result.get("component_id", "unknown")
            action = result.get("action", "unknown")
            expected = result.get("expected", "")
            actual = result.get("actual", "")
            error = result.get("error", "")

            screenshot = result.get("screenshot", "")
            screenshot_link = ""
            if screenshot:
                screenshot_link = f'<a href="{screenshot}" target="_blank">View</a>'

            test_rows.append(f"""
            <tr class="{status_class}">
                <td>{idx}</td>
                <td>{status_icon}</td>
                <td>{component_id}</td>
                <td>{action}</td>
                <td>{expected}</td>
                <td>{actual}</td>
                <td>{error if error else '-'}</td>
                <td>{screenshot_link}</td>
            </tr>
            """)

        test_rows_html = "\n".join(test_rows)

        # Visual analysis section
        visual_section = ""
        if visual_analysis:
            report = visual_analysis.get("report", {})
            compliance = report.get("compliance", {})

            passed_guidelines = compliance.get("passed", [])
            failed_guidelines = compliance.get("failed", [])
            warnings = compliance.get("warnings", [])

            passed_html = "<li>" + "</li><li>".join(passed_guidelines) + "</li>" if passed_guidelines else "<li>None</li>"
            failed_html = "<li>" + "</li><li>".join(failed_guidelines) + "</li>" if failed_guidelines else "<li>None</li>"
            warnings_html = "<li>" + "</li><li>".join(warnings) + "</li>" if warnings else "<li>None</li>"

            visual_section = f"""
            <div class="section">
                <h2>Visual Consistency Analysis</h2>
                <div class="visual-summary">
                    <div class="visual-stat">
                        <span class="stat-label">Issues Found:</span>
                        <span class="stat-value {' critical' if visual_issues > 0 else ''}">{visual_issues}</span>
                    </div>
                </div>

                <h3>Passed Guidelines</h3>
                <ul class="guidelines pass">{passed_html}</ul>

                <h3>Failed Guidelines</h3>
                <ul class="guidelines fail">{failed_html}</ul>

                <h3>Warnings</h3>
                <ul class="guidelines warning">{warnings_html}</ul>
            </div>
            """

        # Generate full HTML
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FAT Report - {project_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        header {{
            border-bottom: 3px solid #0066CC;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}

        h1 {{
            color: #0066CC;
            font-size: 32px;
            margin-bottom: 10px;
        }}

        .metadata {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 4px;
        }}

        .metadata-item {{
            display: flex;
            flex-direction: column;
        }}

        .metadata-label {{
            font-weight: 600;
            color: #666;
            font-size: 12px;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}

        .metadata-value {{
            font-size: 16px;
            color: #333;
        }}

        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}

        .stat-card.pass {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }}

        .stat-card.fail {{
            background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        }}

        .stat-card.skip {{
            background: linear-gradient(135deg, #757F9A 0%, #D7DDE8 100%);
        }}

        .stat-value {{
            display: block;
            font-size: 42px;
            font-weight: bold;
            margin-bottom: 5px;
        }}

        .stat-label {{
            display: block;
            font-size: 14px;
            opacity: 0.9;
        }}

        .section {{
            margin-bottom: 40px;
        }}

        h2 {{
            color: #0066CC;
            font-size: 24px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }}

        h3 {{
            color: #333;
            font-size: 18px;
            margin: 20px 0 10px 0;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            font-size: 14px;
        }}

        th {{
            background: #0066CC;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}

        td {{
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }}

        tr.pass {{
            background: #f0fdf4;
        }}

        tr.fail {{
            background: #fef2f2;
        }}

        tr:hover {{
            background: #f9f9f9;
        }}

        .guidelines {{
            list-style: none;
            padding-left: 0;
        }}

        .guidelines li {{
            padding: 8px 12px;
            margin-bottom: 5px;
            border-radius: 4px;
        }}

        .guidelines.pass li {{
            background: #f0fdf4;
            border-left: 4px solid #10b981;
        }}

        .guidelines.fail li {{
            background: #fef2f2;
            border-left: 4px solid #ef4444;
        }}

        .guidelines.warning li {{
            background: #fffbeb;
            border-left: 4px solid #f59e0b;
        }}

        .visual-summary {{
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }}

        .visual-stat {{
            background: #f9f9f9;
            padding: 15px 20px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .visual-stat .stat-value.critical {{
            color: #ef4444;
            font-weight: bold;
        }}

        footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            text-align: center;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Factory Acceptance Test Report</h1>
            <div class="subtitle">{project_name}</div>
        </header>

        <div class="metadata">
            <div class="metadata-item">
                <span class="metadata-label">Project</span>
                <span class="metadata-value">{project_name}</span>
            </div>
            <div class="metadata-item">
                <span class="metadata-label">Test Date</span>
                <span class="metadata-value">{test_date}</span>
            </div>
            <div class="metadata-item">
                <span class="metadata-label">Tester</span>
                <span class="metadata-value">{tester}</span>
            </div>
            <div class="metadata-item">
                <span class="metadata-label">Client</span>
                <span class="metadata-value">{client}</span>
            </div>
            <div class="metadata-item">
                <span class="metadata-label">Pass Rate</span>
                <span class="metadata-value">{pass_rate:.1f}%</span>
            </div>
        </div>

        <div class="summary">
            <div class="stat-card">
                <span class="stat-value">{total}</span>
                <span class="stat-label">Total Tests</span>
            </div>
            <div class="stat-card pass">
                <span class="stat-value">{passed}</span>
                <span class="stat-label">Passed</span>
            </div>
            <div class="stat-card fail">
                <span class="stat-value">{failed}</span>
                <span class="stat-label">Failed</span>
            </div>
            <div class="stat-card skip">
                <span class="stat-value">{skipped}</span>
                <span class="stat-label">Skipped</span>
            </div>
        </div>

        <div class="section">
            <h2>Component Test Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Status</th>
                        <th>Component</th>
                        <th>Action</th>
                        <th>Expected</th>
                        <th>Actual</th>
                        <th>Error</th>
                        <th>Screenshot</th>
                    </tr>
                </thead>
                <tbody>
                    {test_rows_html}
                </tbody>
            </table>
        </div>

        {visual_section}

        <footer>
            <p>Generated by Ignition Automation Toolkit - FAT Testing Module</p>
            <p>Report ID: {datetime.now().strftime('%Y%m%d-%H%M%S')}</p>
        </footer>
    </div>
</body>
</html>
        """

        return html


class FATExportReportHandler(StepHandler):
    """Handle fat.export_report step - Export FAT report to different formats"""

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        report_id = params.get("report_id")
        format_type = params.get("format", "pdf")
        output_path = params.get("output_path")

        if not report_id:
            raise StepExecutionError(
                "fat",
                "No report_id provided for export"
            )

        # For prototype, just copy the HTML report to specified location
        report_dir = Path("./data/reports")
        source_path = report_dir / f"{report_id}.html"

        if not source_path.exists():
            raise StepExecutionError(
                "fat",
                f"Report not found: {report_id}"
            )

        if output_path:
            dest_path = Path(output_path)
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # For HTML format, just copy
            if format_type == "html":
                import shutil
                shutil.copy(source_path, dest_path)

            # For PDF format (future enhancement)
            elif format_type == "pdf":
                logger.warning("PDF export not yet implemented - copying HTML instead")
                dest_path = dest_path.with_suffix(".html")
                import shutil
                shutil.copy(source_path, dest_path)

            logger.info(f"FAT report exported to: {dest_path}")

            return {
                "status": "exported",
                "format": format_type,
                "output_path": str(dest_path),
                "report_id": report_id
            }

        else:
            # No output path specified - return source path
            return {
                "status": "exported",
                "format": "html",
                "output_path": str(source_path),
                "report_id": report_id
            }
