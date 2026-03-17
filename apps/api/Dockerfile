FROM python:3.12-slim

ARG APP_VERSION=dev
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=${APP_VERSION}

WORKDIR /app

COPY apps/api/requirements.txt /app/apps/api/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/api/requirements.txt

COPY packages/core-engine /app/packages/core-engine
RUN pip install --no-cache-dir -e /app/packages/core-engine

COPY apps/api /app/apps/api
COPY apps/web/lib /app/apps/web/lib
COPY docs/rules /app/docs/rules
COPY importers /app/importers
COPY programs /app/programs

WORKDIR /app/apps/api
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
