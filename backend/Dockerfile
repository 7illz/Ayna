FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock ./requirements.lock
RUN pip install --no-cache-dir -r requirements.lock
RUN useradd --create-home --uid 10001 ayna && chown ayna:ayna /app
COPY --chown=ayna:ayna . .
USER ayna
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
