# ChatGP-TB API: FastAPI + the design library, no per-isolate data (it reads resources/snapshot_windows.npz).
# Run from the source tree, not as an installed package: the code finds ref/, resources/ and web/data/ relative to it.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    GENOHACK_SNAPSHOT=/app/resources/snapshot_windows.npz

WORKDIR /app
COPY deploy/requirements.txt deploy/requirements.txt
RUN pip install --no-cache-dir -r deploy/requirements.txt

COPY src ./src
COPY resources ./resources
COPY ref/NC_000962.3.fasta ref/mask.bed ./ref/
COPY web/data/report.json ./web/data/report.json

RUN useradd --system --no-create-home app
USER app

# Cloud Run sets PORT. Set GENOHACK_ORIGINS to the address of the hosted web page (comma separated).
CMD exec uvicorn genohack.api:app --host 0.0.0.0 --port "${PORT:-8080}"
