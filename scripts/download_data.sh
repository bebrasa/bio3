#!/usr/bin/env bash
# Download ONT E. coli reads from NCBI SRA and reference genome

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

READS_DIR="${PROJECT_DIR}/data/reads"
REF_DIR="${PROJECT_DIR}/data/reference"
SRA_RUN="${SRA_RUN:-SRR39004285}"
REF_URL="https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/005/845/GCF_000005845.2_ASM584v2/GCF_000005845.2_ASM584v2_genomic.fna.gz"
REF_FILE="${REF_DIR}/GCF_000005845.2_ASM584v2_genomic.fna"

mkdir -p "${READS_DIR}" "${REF_DIR}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Downloading reference genome E. coli K-12 MG1655 (GCF_000005845.2)"
if [[ ! -f "${REF_FILE}" ]]; then
    curl -L "${REF_URL}" -o "${REF_DIR}/reference.fna.gz"
    gunzip -c "${REF_DIR}/reference.fna.gz" > "${REF_FILE}"
    log "Reference saved to ${REF_FILE}"
else
    log "Reference already exists: ${REF_FILE}"
fi

log "Downloading ONT reads from SRA: ${SRA_RUN}"
log "SRA link: https://trace.ncbi.nlm.nih.gov/Traces/?run=${SRA_RUN}"

FASTQ="${READS_DIR}/${SRA_RUN}.fastq"
if [[ ! -f "${FASTQ}" ]]; then
    cd "${READS_DIR}"
    prefetch "${SRA_RUN}"
    fasterq-dump "${SRA_RUN}" --threads 4 --progress
    log "Reads saved to ${FASTQ}"
else
    log "Reads already exist: ${FASTQ}"
fi

echo ""
echo "Data download complete."
echo "SRA accession: ${SRA_RUN}"
echo "Reference: ${REF_FILE}"
echo "FASTQ: ${FASTQ}"
