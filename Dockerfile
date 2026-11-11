FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.production.txt ./
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.production.txt

RUN addgroup --system tudun && adduser --system --ingroup tudun tudun

COPY --chown=tudun:tudun manage.py ./
COPY --chown=tudun:tudun config ./config
COPY --chown=tudun:tudun identity ./identity
COPY --chown=tudun:tudun communities ./communities
COPY --chown=tudun:tudun audit ./audit
COPY --chown=tudun:tudun templates ./templates
COPY --chown=tudun:tudun static ./static
COPY --chown=tudun:tudun scripts/production.py ./scripts/production.py

RUN python -m compileall -q config identity communities audit scripts/production.py && \
    mkdir -p /app/.collected_static && chown -R tudun:tudun /app/.collected_static

USER tudun
EXPOSE 8000

CMD ["python", "scripts/production.py"]
