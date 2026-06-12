# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-warn-script-location -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

# Create non-root user
RUN useradd -m appuser

WORKDIR /app

COPY --from=builder /root/.local /home/appuser/.local
COPY app /app/app

# Set env path for installed packages
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PORT=8000

USER appuser

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:$PORT/health || exit 1

EXPOSE $PORT

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
