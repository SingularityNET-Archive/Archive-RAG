"""Evaluate CLI command for running evaluation suite."""

from pathlib import Path
from typing import Optional
import typer

from ..services.evaluation_runner import create_evaluation_runner
from ..services.report_generator import generate_report
from ..services.audit_writer import AuditWriter
from ..lib.config import DEFAULT_SEED
from ..lib.logging import get_logger

logger = get_logger(__name__)


def evaluate_command(
    index_file: str = typer.Argument(..., help="Path to FAISS index file"),
    benchmark_file: str = typer.Argument(..., help="Path to evaluation benchmark JSON file"),
    output_dir: str = typer.Argument(..., help="Directory to write evaluation results"),
    model: Optional[str] = typer.Option(None, "--model", help="LLM model name"),
    model_version: Optional[str] = typer.Option(None, "--model-version", help="LLM model version"),
    seed: int = typer.Option(DEFAULT_SEED, "--seed", help="Random seed for reproducibility"),
    output_format: str = typer.Option("report", "--output-format", help="Results format: json or report")
):
    """
    Run evaluation suite to measure factuality and citation compliance.
    """
    try:
        # Create evaluation runner
        evaluation_runner = create_evaluation_runner(
            index_name=index_file,
            model_name=model,
            model_version=model_version,
            seed=seed
        )
        
        # Run evaluation
        benchmark_path = Path(benchmark_file)
        results = evaluation_runner.run_evaluation(benchmark_path)
        
        # Generate report
        output_path = Path(output_dir)
        report_file = generate_report(results, output_path, output_format)
        
        # Create audit log
        audit_writer = AuditWriter()
        audit_writer.write_index_audit_log(
            operation="evaluate",
            input_dir=index_file,
            output_index=str(report_file),
            metadata={
                "benchmark_file": benchmark_file,
                "total_cases": results.get("total_cases", 0),
                "citation_accuracy": results.get("citation_accuracy", 0.0),
                "factuality_score": results.get("factuality_score", 0.0),
                "hallucination_count": results.get("hallucination_count", 0)
            }
        )
        
        # Display summary
        typer.echo(f"Evaluation complete: {report_file}")
        typer.echo(f"Total Cases: {results.get('total_cases', 0)}")
        typer.echo(f"Citation Accuracy: {results.get('citation_accuracy', 0.0):.2%} (≥90% required per SC-001)")
        typer.echo(f"Factuality Score: {results.get('factuality_score', 0.0):.2%}")
        typer.echo(f"Hallucination Count: {results.get('hallucination_count', 0)} (0 required per SC-002)")
        typer.echo(f"Retrieval Latency: {results.get('retrieval_latency_avg', 0.0):.2f}s (<2s required per SC-003)")
        
        # Check success criteria
        success_criteria = results.get("success_criteria", {})
        all_passed = all(sc.get("met", False) for sc in success_criteria.values())
        
        if all_passed:
            typer.echo("\n✓ All success criteria met!")
        else:
            typer.echo("\n✗ Some success criteria not met. See report for details.", err=True)
        
    except Exception as e:
        logger.error("evaluation_failed", error=str(e))
        typer.echo(f"Evaluation failed: {e}", err=True)
        raise typer.Exit(code=1)

