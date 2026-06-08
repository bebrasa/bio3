# Установка и развёртывание Dagster

**Вариант задания:** 7 — Oxford Nanopore / minimap2 / **Dagster**

## Требования

- Linux или macOS
- Python 3.10+
- Установленные биоинформатические утилиты: `fastqc`, `minimap2`, `samtools`, `freebayes`

## 1. Установка биоинформатических инструментов

### macOS (Homebrew)

```bash
brew install minimap2 samtools fastqc freebayes sratoolkit
```

### Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y fastqc samtools
# minimap2 и freebayes — из исходников или bioconda
```

### Conda (универсальный способ)

```bash
conda create -n bioinf-hw3 -c bioconda -c conda-forge \
  minimap2 samtools fastqc freebayes sra-tools python=3.11 -y
conda activate bioinf-hw3
```

## 2. Клонирование репозитория

```bash
git clone <URL_ВАШЕГО_РЕПОЗИТОРИЯ>
cd bioinf
```

## 3. Установка Dagster

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
# или: pip install dagster dagster-webserver
```

Проверка:

```bash
dagster --version
python -c "import dagster; print(dagster.__version__)"
```

## 4. Загрузка данных

```bash
chmod +x scripts/*.sh
./scripts/download_data.sh
```

Будут скачаны:
- **Риды:** SRR39004285 (ONT WGS, *E. coli*, GridION) — [NCBI SRA](https://trace.ncbi.nlm.nih.gov/Traces/?run=SRR39004285)
- **Референс:** GCF_000005845.2 (*E. coli* K-12 MG1655)

## 5. Запуск тестового пайплайна Hello World

```bash
source .venv/bin/activate
dagster asset materialize -m dagster_project.definitions \
  --select hello_world_message,hello_world_greeting
```

## 6. Запуск пайплайна оценки качества картирования

```bash
dagster asset materialize -m dagster_project.definitions --select '*'
```

Результаты сохраняются в `results/dagster_pipeline/`.

## 7. Визуализация пайплайна (Dagster UI)

```bash
dagster dev -m dagster_project.definitions
```

Откройте http://127.0.0.1:3000 → раздел **Assets** → граф зависимостей.

## 8. Экспорт DAG в графический файл

```bash
pip install graphviz
brew install graphviz   # macOS, нужен системный dot
python scripts/generate_dag_visualization.py
```

Файл: `results/dagster_pipeline/asset_dag.png`

## 9. Bash-версия алгоритма (без Dagster)

```bash
./scripts/mapping_qc.sh
```

## Полезные ссылки

- [Dagster Documentation](https://docs.dagster.io/)
- [Dagster Tutorial](https://docs.dagster.io/tutorial)
- [minimap2](https://github.com/lh3/minimap2)
- [samtools](https://github.com/samtools/samtools)
