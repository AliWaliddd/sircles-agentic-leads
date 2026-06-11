from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from sircles_agents.models import FinalRunOutput
from sircles_agents.orchestrator import Orchestrator
from sircles_agents.tools.mock_lead_scanner import fetch_lead_by_id, fetch_new_leads


app = typer.Typer(
    help="Sircles agentic inbound-lead workflow.",
    add_completion=False,
)
console = Console(width=140)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """
    Show help when the module is run without a command.
    """
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()


@app.command("list-leads")
def list_leads() -> None:
    """
    List the available mocked lead fixtures.
    """
    leads = fetch_new_leads()

    table = Table(title="Available Mock Leads")
    table.add_column("Lead ID", style="bold", no_wrap=True)
    table.add_column("Name", no_wrap=True)
    table.add_column("Company", no_wrap=True)
    table.add_column("Role", no_wrap=True)
    table.add_column("Source", no_wrap=True)

    for lead in leads:
        table.add_row(
            lead.lead_id,
            f"{lead.first_name} {lead.last_name}",
            lead.company_name,
            lead.role_title,
            lead.source,
        )

    console.print(table)


@app.command("run")
def run_lead(
    lead_id: str = typer.Argument(
        ...,
        help="Lead ID to run, for example: lead_saas_pursue",
    ),
    trace_dir: Path = typer.Option(
        Path("traces"),
        "--trace-dir",
        "-t",
        help="Directory where JSON run traces should be written.",
    ),
    no_write_trace: bool = typer.Option(
        False,
        "--no-write-trace",
        help="Run without writing a JSON trace file.",
    ),
    show_trace: bool = typer.Option(
        False,
        "--show-trace",
        help="Print the readable trace events in the terminal.",
    ),
) -> None:
    """
    Run the full agent workflow for one lead.
    """
    try:
        raw_lead = fetch_lead_by_id(lead_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    orchestrator = Orchestrator(trace_dir=trace_dir)
    output = orchestrator.run(raw_lead, write_trace=not no_write_trace)

    _render_detailed_output(output, show_trace=show_trace)

    if not no_write_trace:
        trace_path = trace_dir / f"{output.lead_id}_trace.json"
        console.print(f"\n[green]Trace written to:[/green] {trace_path}")


@app.command("run-all")
def run_all(
    trace_dir: Path = typer.Option(
        Path("traces"),
        "--trace-dir",
        "-t",
        help="Directory where JSON run traces should be written.",
    ),
    no_write_trace: bool = typer.Option(
        False,
        "--no-write-trace",
        help="Run without writing JSON trace files.",
    ),
    details: bool = typer.Option(
        False,
        "--details",
        help="Print detailed output for every lead.",
    ),
) -> None:
    """
    Run the full workflow for all mocked lead fixtures.
    """
    orchestrator = Orchestrator(trace_dir=trace_dir)
    outputs: list[FinalRunOutput] = []

    for raw_lead in fetch_new_leads():
        outputs.append(
            orchestrator.run(raw_lead, write_trace=not no_write_trace)
        )

    _render_summary_table(outputs)

    if details:
        for output in outputs:
            _render_detailed_output(output, show_trace=False)

    if not no_write_trace:
        console.print(f"\n[green]Trace files written to:[/green] {trace_dir}")


def _render_summary_table(outputs: list[FinalRunOutput]) -> None:
    table = Table(title="Sircles Agent Workflow Summary")
    table.add_column("Lead ID", style="bold")
    table.add_column("Company")
    table.add_column("Score")
    table.add_column("Lead Intel Proposal")
    table.add_column("Final")
    table.add_column("CRM Stage")
    table.add_column("Outreach")
    table.add_column("Human Review")

    for output in outputs:
        table.add_row(
            output.lead_id,
            output.lead_intelligence.company.company_name,
            str(output.lead_intelligence.score.total_score),
            output.lead_intelligence.score.proposed_disposition.value,
            output.final_disposition.value,
            output.crm_record.deal_stage.value,
            "yes" if output.outreach else "no",
            "yes" if output.crm_record.human_review_flag else "no",
        )

    console.print(table)


def _render_detailed_output(
    output: FinalRunOutput,
    show_trace: bool,
) -> None:
    console.rule(f"[bold]Lead: {output.lead_id}")

    summary = Table(title="Final Decision")
    summary.add_column("Field", style="bold")
    summary.add_column("Value")

    summary.add_row("Company", output.lead_intelligence.company.company_name)
    summary.add_row("Contact", output.lead_intelligence.contact.full_name)
    summary.add_row("Role", output.lead_intelligence.contact.role_title)
    summary.add_row("Industry", output.lead_intelligence.company.industry)
    summary.add_row("Score", f"{output.lead_intelligence.score.total_score}/100")
    summary.add_row(
        "Lead Intelligence Proposal",
        output.lead_intelligence.score.proposed_disposition.value,
    )
    summary.add_row("Final Disposition", output.final_disposition.value)
    summary.add_row("Resolution Confidence", str(output.resolution.confidence))
    summary.add_row("CRM Stage", output.crm_record.deal_stage.value)
    summary.add_row(
        "Human Review",
        "yes" if output.crm_record.human_review_flag else "no",
    )

    console.print(summary)

    debate = Table(title="Debate Positions")
    debate.add_column("Agent", style="bold")
    debate.add_column("Recommendation")
    debate.add_column("Confidence")
    debate.add_column("Thesis")

    for position in output.debate_positions:
        debate.add_row(
            position.agent.value,
            position.recommendation.value,
            str(position.confidence),
            position.thesis,
        )

    console.print(debate)

    console.print(
        Panel(
            output.resolution.rationale,
            title="Resolution Rationale",
            expand=False,
        )
    )

    if output.resolution.human_review_reason:
        console.print(
            Panel(
                output.resolution.human_review_reason,
                title="Human Review Reason",
                expand=False,
            )
        )

    if output.outreach is not None:
        console.print(
            Panel(
                output.outreach.subject,
                title="Draft Email Subject",
                expand=False,
            )
        )
        console.print(
            Panel(
                output.outreach.email_body,
                title="Draft Email Body",
                expand=False,
            )
        )
        console.print(
            Panel(
                output.outreach.linkedin_note,
                title="Draft LinkedIn Note",
                expand=False,
            )
        )
    else:
        console.print(
            Panel(
                "No outreach was drafted because the final disposition was not pursue.",
                title="Outreach",
                expand=False,
            )
        )

    if show_trace:
        trace_table = Table(title="Readable Run Trace")
        trace_table.add_column("#")
        trace_table.add_column("Actor", style="bold")
        trace_table.add_column("Action")
        trace_table.add_column("Summary")

        for index, event in enumerate(output.trace, start=1):
            trace_table.add_row(
                str(index),
                event.actor.value,
                event.action,
                event.summary,
            )

        console.print(trace_table)


def cli() -> None:
    app()


if __name__ == "__main__":
    app()