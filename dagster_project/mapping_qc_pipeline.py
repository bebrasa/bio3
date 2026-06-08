"""Dagster pipeline for mapping quality assessment (ONT + minimap2)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from dagster import Definitions, MetadataValue, asset

PROJECT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_DIR / "scripts"
DATA_DIR = PROJECT_DIR / "data"
RESULTS_DIR = PROJECT_DIR / "results" / "dagster_pipeline"

DEFAULT_FASTQ = DATA_DIR / "reads" / "SRR39004285.fastq"
DEFAULT_REFERENCE = DATA_DIR / "reference" / "GCF_000005845.2_ASM584v2_genomic.fna"
MAPPING_THRESHOLD = 90.0

MAPPED_PATTERN = re.compile(
    r"^\s*(\d+)\s+\+\s+\d+\s+mapped\s+\(([\d.]+)%",
    re.MULTILINE,
)


def _run_command(
    context,
    command: list[str],
    *,
    stdout_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    context.log.info("Running: %s", " ".join(command))
    if stdout_path is not None:
        with stdout_path.open("w") as handle:
            result = subprocess.run(
                command,
                check=True,
                text=True,
                stdout=handle,
                stderr=subprocess.PIPE,
            )
        return result

    return subprocess.run(command, check=True, text=True, capture_output=True)


def _parse_mapped_percent(flagstat_text: str) -> float:
    match = MAPPED_PATTERN.search(flagstat_text)
    if not match:
        raise ValueError("Mapped percentage not found in flagstat output")
    return float(match.group(2))


@asset(
    description="Run FastQC on Oxford Nanopore FASTQ reads",
    compute_kind="fastqc",
)
def fastqc_report(context) -> Path:
    fastq = DEFAULT_FASTQ
    output_dir = RESULTS_DIR / "fastqc"
    output_dir.mkdir(parents=True, exist_ok=True)

    _run_command(
        context,
        ["fastqc", "-o", str(output_dir), "-t", "2", str(fastq)],
    )

    reports = list(output_dir.glob("*.html"))
    context.add_output_metadata(
        {
            "fastq": MetadataValue.path(str(fastq)),
            "reports": MetadataValue.json([str(p) for p in reports]),
        }
    )
    return output_dir


@asset(
    description="Build minimap2 index for the reference genome",
    compute_kind="minimap2",
)
def reference_index(context) -> Path:
    reference = DEFAULT_REFERENCE
    index_path = Path(f"{reference}.mmi")

    if not index_path.exists():
        _run_command(context, ["minimap2", "-d", str(index_path), str(reference)])

    context.add_output_metadata({"index": MetadataValue.path(str(index_path))})
    return index_path


@asset(
    deps=[reference_index],
    description="Map ONT reads to reference with minimap2",
    compute_kind="minimap2",
)
def alignment_sam(
    context,
    reference_index: Path,
) -> Path:
    fastq = DEFAULT_FASTQ
    sam_path = RESULTS_DIR / f"{fastq.stem}.sam"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    _run_command(
        context,
        ["minimap2", "-ax", "map-ont", str(reference_index), str(fastq)],
        stdout_path=sam_path,
    )
    context.add_output_metadata({"sam": MetadataValue.path(str(sam_path))})
    return sam_path


@asset(
    deps=[alignment_sam],
    description="Convert SAM to BAM and create index",
    compute_kind="samtools",
)
def alignment_bam(context, alignment_sam: Path) -> Path:
    bam_path = alignment_sam.with_suffix(".bam")

    _run_command(
        context,
        ["samtools", "view", "-bS", str(alignment_sam), "-o", str(bam_path)],
    )

    context.add_output_metadata({"bam": MetadataValue.path(str(bam_path))})
    return bam_path


@asset(
    deps=[alignment_bam],
    description="Compute mapping statistics with samtools flagstat",
    compute_kind="samtools",
)
def flagstat_report(context, alignment_bam: Path) -> Path:
    flagstat_path = alignment_bam.with_suffix(".flagstat.txt")
    with flagstat_path.open("w") as handle:
        subprocess.run(
            ["samtools", "flagstat", str(alignment_bam)],
            check=True,
            text=True,
            stdout=handle,
        )

    text = flagstat_path.read_text()
    mapped_percent = _parse_mapped_percent(text)
    status = "OK" if mapped_percent > MAPPING_THRESHOLD else "not OK"

    context.add_output_metadata(
        {
            "mapped_percent": MetadataValue.float(mapped_percent),
            "threshold": MetadataValue.float(MAPPING_THRESHOLD),
            "status": MetadataValue.text(status),
        }
    )
    return flagstat_path


@asset(
    deps=[flagstat_report],
    description="Parse flagstat and produce QC summary report",
    compute_kind="python",
)
def mapping_qc_summary(context, flagstat_report: Path) -> Path:
    text = flagstat_report.read_text()
    mapped_percent = _parse_mapped_percent(text)
    status = "OK" if mapped_percent > MAPPING_THRESHOLD else "not OK"

    sample_name = DEFAULT_FASTQ.stem
    summary_path = RESULTS_DIR / f"{sample_name}_qc_summary.txt"
    summary_path.write_text(
        "\n".join(
            [
                f"Sample: {sample_name}",
                "Instrument: Oxford Nanopore (GridION/MinION/PromethION)",
                "Mapper: minimap2 (-ax map-ont)",
                f"Mapped reads: {mapped_percent:.2f}%",
                f"Threshold: {MAPPING_THRESHOLD:.2f}%",
                f"Status: {status}",
                "",
                "=== samtools flagstat ===",
                text,
            ]
        )
    )

    context.add_output_metadata(
        {
            "mapped_percent": MetadataValue.float(mapped_percent),
            "status": MetadataValue.text(status),
            "report": MetadataValue.path(str(summary_path)),
        }
    )
    return summary_path


@asset(
    deps=[mapping_qc_summary],
    description="Sort BAM and call variants if mapping quality is OK",
    compute_kind="freebayes",
)
def variant_calling(
    context,
    mapping_qc_summary: Path,
    alignment_bam: Path,
) -> Path | None:
    summary_text = mapping_qc_summary.read_text()
    if "Status: OK" not in summary_text:
        context.log.warning("Mapping quality is not OK — skipping variant calling")
        return None

    sorted_bam = alignment_bam.with_name(alignment_bam.stem + ".sorted.bam")
    _run_command(
        context,
        ["samtools", "sort", str(alignment_bam), "-o", str(sorted_bam)],
    )
    _run_command(context, ["samtools", "index", str(sorted_bam)])

    vcf_path = sorted_bam.with_suffix(".vcf")
    with vcf_path.open("w") as handle:
        subprocess.run(
            ["freebayes", "-f", str(DEFAULT_REFERENCE), str(sorted_bam)],
            check=True,
            text=True,
            stdout=handle,
        )

    context.add_output_metadata(
        {
            "sorted_bam": MetadataValue.path(str(sorted_bam)),
            "vcf": MetadataValue.path(str(vcf_path)),
        }
    )
    return vcf_path


defs = Definitions(
    assets=[
        fastqc_report,
        reference_index,
        alignment_sam,
        alignment_bam,
        flagstat_report,
        mapping_qc_summary,
        variant_calling,
    ],
    jobs=[],
)
