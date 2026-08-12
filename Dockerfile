FROM python:3.12-slim

WORKDIR /app

# Copy dependency/package metadata first.
COPY pyproject.toml ./
COPY app/__init__.py ./app/__init__.py

# Install Python dependencies.
RUN python -m pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu .

# Copy application source
COPY app ./app

ENV PORT=8080

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]