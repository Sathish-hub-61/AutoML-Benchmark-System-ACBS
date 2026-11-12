import json
from pathlib import Path
from acbs.reporting.report import build_html_report, export_pdf
from acbs.benchmark.engine import run_benchmark

# Run a quick benchmark (reuse existing dataset)
result = run_benchmark(dataset='breast_cancer', tuning='none')
# Build HTML report
html = build_html_report(result)
# Write HTML to file for inspection
Path('report.html').write_text(html, encoding='utf-8')
# Export PDF
pdf_bytes = export_pdf(html)
if pdf_bytes:
    Path('report.pdf').write_bytes(pdf_bytes)
    print('PDF generated, size', len(pdf_bytes))
else:
    print('PDF generation failed')

# Run a quick benchmark (reuse existing dataset)
runner = BenchmarkRunner()
result = runner.run(dataset='breast_cancer', tuning='none')
# Build HTML report
html = build_html_report(result)
# Write HTML to file for inspection
Path('report.html').write_text(html, encoding='utf-8')
# Export PDF
pdf_bytes = export_pdf(html)
if pdf_bytes:
    Path('report.pdf').write_bytes(pdf_bytes)
    print('PDF generated, size', len(pdf_bytes))
else:
    print('PDF generation failed')

