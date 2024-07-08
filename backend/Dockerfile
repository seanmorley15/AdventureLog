# Dockerfile

FROM python:3.10-slim

LABEL Developers="Sean Morley"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /code

# Install system dependencies
RUN apt-get update \
    && apt-get install -y git postgresql-client \
    && apt-get clean

# Install Python dependencies
COPY ./server/requirements.txt /code/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the Django project code into the Docker image
COPY ./server /code/

# Set the entrypoint script
COPY ./entrypoint.sh /code/entrypoint.sh
RUN chmod +x /code/entrypoint.sh
ENTRYPOINT ["/code/entrypoint.sh"]