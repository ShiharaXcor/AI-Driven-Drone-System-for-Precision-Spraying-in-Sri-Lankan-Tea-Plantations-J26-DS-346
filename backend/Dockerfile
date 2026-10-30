FROM python:3.11-slim

WORKDIR /app

COPY requirements/ requirements/
RUN pip install --no-cache-dir \
    -r requirements/base.txt \
    -r requirements/c1.txt \
    -r requirements/c2.txt \
    -r requirements/c3.txt \
    -r requirements/c4.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]