FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir --editable .
COPY . .
CMD ["python", "-m", "pytest", "-q"]
