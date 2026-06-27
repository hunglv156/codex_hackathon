# Data Generator Tool

Real-time metrics, logs, and traces generator for ClickHouse-backed AIOps demos.

The tool only writes to:

- `aiops.metrics`
- `aiops.logs`
- `aiops.traces`

It refuses writes to other tables, including backend-owned anomaly or alert tables.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configure ClickHouse with environment variables:

```bash
export CH_HOST=localhost
export CH_PORT=9000
export CH_USER=default
export CH_PASSWORD=
```

## Run

```bash
python -m src.main --scenario normal
python -m src.main --scenario normal --inject spike
python -m src.main --scenario normal --auto-inject --inject-interval 60
python -m src.main --scenario normal --duration 30
```

## Test

```bash
pytest tests/ -v --tb=short
```
# codex_hackathon
