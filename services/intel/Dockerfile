FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --system --no-create-home edgebook

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py migrate.py ./
COPY intel/ intel/
COPY migrations/ migrations/
COPY fixtures/ fixtures/

USER edgebook
EXPOSE 8000
CMD ["python", "app.py"]
