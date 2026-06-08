#!/usr/bin/env bash
# Алгоритм оценки качества картирования (ONT + minimap2)
# Домашнее задание 3, вариант 7: Oxford Nanopore / minimap2 / Dagster

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

FASTQ="${1:-${PROJECT_DIR}/data/reads/SRR39004285.fastq}"
REFERENCE="${2:-${PROJECT_DIR}/data/reference/GCF_000005845.2_ASM584v2_genomic.fna}"
OUTPUT_DIR="${3:-${PROJECT_DIR}/results/bash_pipeline}"
THRESHOLD="${THRESHOLD:-90}"

REF_INDEX="${REFERENCE}.mmi"
SAMPLE_NAME="$(basename "${FASTQ}" .fastq)"
SAMPLE_NAME="${SAMPLE_NAME%.fastq.gz}"

SAM="${OUTPUT_DIR}/${SAMPLE_NAME}.sam"
BAM="${OUTPUT_DIR}/${SAMPLE_NAME}.bam"
SORTED_BAM="${OUTPUT_DIR}/${SAMPLE_NAME}.sorted.bam"
FLAGSTAT="${OUTPUT_DIR}/${SAMPLE_NAME}.flagstat.txt"
VCF="${OUTPUT_DIR}/${SAMPLE_NAME}.vcf"
FASTQC_DIR="${OUTPUT_DIR}/fastqc"
PARSE_SCRIPT="${SCRIPT_DIR}/parse_flagstat.py"

mkdir -p "${OUTPUT_DIR}" "${FASTQC_DIR}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

require_tool() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "ERROR: required tool '$1' not found in PATH" >&2
        exit 1
    fi
}

for tool in fastqc minimap2 samtools python3; do
    require_tool "${tool}"
done

log "Step 1/8: FastQC quality control"
fastqc -o "${FASTQC_DIR}" -t 2 "${FASTQ}"

log "Step 2/8: Index reference genome with minimap2"
if [[ ! -f "${REF_INDEX}" ]]; then
    minimap2 -d "${REF_INDEX}" "${REFERENCE}"
else
    log "Reference index already exists: ${REF_INDEX}"
fi

log "Step 3/8: Map reads with minimap2 (ONT preset map-ont)"
minimap2 -ax map-ont "${REF_INDEX}" "${FASTQ}" > "${SAM}"

log "Step 4/8: Convert SAM to BAM"
samtools view -bS "${SAM}" -o "${BAM}"

log "Step 5/8: Run samtools flagstat"
samtools flagstat "${BAM}" > "${FLAGSTAT}"
cat "${FLAGSTAT}"

log "Step 6/8: Parse mapped percentage and evaluate threshold"
PARSE_OUTPUT="$(python3 "${PARSE_SCRIPT}" "${FLAGSTAT}" --threshold "${THRESHOLD}" || true)"
echo "${PARSE_OUTPUT}"

MAPPED_PERCENT="$(echo "${PARSE_OUTPUT}" | awk '/Mapped reads:/ {print $3}' | tr -d '%')"
STATUS="$(echo "${PARSE_OUTPUT}" | tail -n 1)"

log "Step 7/8: Rename and save QC report"
QC_REPORT="${OUTPUT_DIR}/${SAMPLE_NAME}_qc_report.txt"
{
    echo "Sample: ${SAMPLE_NAME}"
    echo "Instrument: Oxford Nanopore (GridION/MinION/PromethION)"
    echo "Mapper: minimap2 (-ax map-ont)"
    echo "Mapped reads: ${MAPPED_PERCENT}%"
    echo "Threshold: ${THRESHOLD}%"
    echo "Status: ${STATUS}"
    echo ""
    echo "=== samtools flagstat ==="
    cat "${FLAGSTAT}"
} > "${QC_REPORT}"

log "QC report saved to ${QC_REPORT}"

if [[ "${STATUS}" == "OK" ]]; then
    log "Step 8/8: Mapping OK (> ${THRESHOLD}%) — sort BAM and call variants"
    samtools sort "${BAM}" -o "${SORTED_BAM}"
    samtools index "${SORTED_BAM}"

    if command -v freebayes >/dev/null 2>&1; then
        freebayes -f "${REFERENCE}" "${SORTED_BAM}" > "${VCF}"
        log "Variant calling finished: ${VCF}"
    else
        log "freebayes not installed — skipping variant calling"
    fi

    echo "Finished" > "${OUTPUT_DIR}/${SAMPLE_NAME}.status"
    log "Pipeline status: Finished"
else
    echo "not OK" > "${OUTPUT_DIR}/${SAMPLE_NAME}.status"
    log "Pipeline status: not OK (mapped ${MAPPED_PERCENT}% <= ${THRESHOLD}%)"
    exit 1
fi
