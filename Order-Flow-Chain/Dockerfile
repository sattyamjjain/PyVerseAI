# Use an official Python runtime as the parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Set the working directory in the container
WORKDIR /app

# Install system packages required by Django and the database client
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc default-libmysqlclient-dev pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the content of the local src directory to the working directory
COPY . /app/

# Copy wait-for-it script and make it executable
COPY wait-for-it.sh /usr/local/bin/wait-for-it
RUN chmod +x /usr/local/bin/wait-for-it

# Specify the command to run on container start
CMD ["gunicorn", "orderflowchain.wsgi:application", "--bind", "0.0.0.0:8000"]
