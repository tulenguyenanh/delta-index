FROM python:3.13.16-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# requirements first: the dependency layer is cached across source edits.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY data/ ./data/
COPY main.py .

# Exec form: signals reach Python directly. The container exits when this
# process exits -- that is the whole deliverable, not a failure.
ENTRYPOINT ["python", "main.py"]
