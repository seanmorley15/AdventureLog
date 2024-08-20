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
    && apt-get install -y git postgresql-client cron \
    && apt-get clean

# Install Python dependencies
COPY ./server/requirements.txt /code/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the Django project code into the Docker image
COPY ./server /code/

# Collect static files
RUN python3 manage.py collectstatic --noinput --verbosity 2

# Setup cron to run python3 manage.py worldtravel-seed every day at 00:00
RUN echo "0 0 * * * python3 /code/manage.py worldtravel-seed --force >> /var/log/cron.log 2>&1" > /etc/cron.d/worldtravel-seed

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/worldtravel-seed

# Apply cron job
RUN crontab /etc/cron.d/worldtravel-seed

# Ensure cron is started in the foreground when the container starts
CMD ["cron", "-f"]

# Set the entrypoint script
COPY ./entrypoint.sh /code/entrypoint.sh
RUN chmod +x /code/entrypoint.sh
ENTRYPOINT ["/code/entrypoint.sh"]
