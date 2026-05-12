FROM python:3.11-slim

# Use /app/backend as the application root so the repo build context (.) can be used
WORKDIR /app/backend

# Copy only the requirements first for better layer caching
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy the backend source into the image
COPY backend/ /app/backend/

# Ensure Python can import the `app` package
ENV PYTHONPATH=/app/backend

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
