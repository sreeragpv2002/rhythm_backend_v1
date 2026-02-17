FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project
COPY . /app/

# Create media and static directories
RUN mkdir -p /app/media /app/staticfiles

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Run migrations
RUN python manage.py migrate || true

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "rhythm_backend.wsgi:application"]
