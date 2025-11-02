"""Evaluation report generator."""

import json
from pathlib import Path
from typing import Dict, Any

from ..lib.logging import get_logger

logger = get_logger(__name__)


def generate_report(
    results: Dict[str, Any],
    output_dir: Path,
    output_format: str = "report"
) -> Path:
    """
    Generate evaluation report.
    
    Args:
        results: Evaluation results dictionary
        output_dir: Directory to write report
        output_format: Report format ("report" or "json")
        
    Returns:
        Path to generated report file
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if output_format == "json":
        # JSON format
        report_file = output_dir / "evaluation_results.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    else:
        # Text report format
        report_file = output_dir / "evaluation_report.txt"
        report_text = _format_report_text(results)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_text)
    
    logger.info("report_generated", report_file=str(report_file))
    
    return report_file


def _format_report_text(results: Dict[str, Any]) -> str:
    """
    Format evaluation results as text report.
    
    Args:
        results: Evaluation results dictionary
        
    Returns:
        Formatted text report
    """
    lines = []
    lines.append("Evaluation Results")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Total Cases: {results.get('total_cases', 0)}")
    lines.append(f"Citation Accuracy: {results.get('citation_accuracy', 0.0):.2%} (≥90% required per SC-001)")
    lines.append(f"Factuality Score: {results.get('factuality_score', 0.0):.2%}")
    lines.append(f"Hallucination Count: {results.get('hallucination_count', 0)} (0 required per SC-002)")
    lines.append(f"Retrieval Latency: {results.get('retrieval_latency_avg', 0.0):.2f}s (<2s required per SC-003)")
    lines.append("")
    lines.append("Success Criteria:")
    lines.append("-" * 50)
    
    success_criteria = results.get("success_criteria", {})
    for sc_id, sc_data in success_criteria.items():
        met_status = "✓ PASS" if sc_data.get("met") else "✗ FAIL"
        lines.append(f"{sc_id}: {met_status}")
        if "citation_accuracy" in sc_data:
            lines.append(f"  Citation Accuracy: {sc_data['citation_accuracy']:.2%}")
        if "hallucination_count" in sc_data:
            lines.append(f"  Hallucination Count: {sc_data['hallucination_count']}")
        if "latency" in sc_data:
            lines.append(f"  Latency: {sc_data['latency']:.2f}s")
    
    lines.append("")
    lines.append("Per-Case Results:")
    lines.append("-" * 50)
    
    cases = results.get("cases", [])
    for case in cases[:10]:  # Show first 10 cases
        case_id = case.get("case_id", "N/A")
        metrics = case.get("evaluation_metrics", {})
        lines.append(f"Case {case_id}:")
        lines.append(f"  Citation Accuracy: {metrics.get('citation_accuracy', 0.0):.2%}")
        lines.append(f"  Factuality: {metrics.get('factuality', 0.0):.2%}")
        lines.append(f"  Hallucination Count: {metrics.get('hallucination_count', 0)}")
    
    if len(cases) > 10:
        lines.append(f"... and {len(cases) - 10} more cases")
    
    return "\n".join(lines)

