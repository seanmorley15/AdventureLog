# Use an official Python image as a base
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install required Python packages
RUN pip install --no-cache-dir requests osm2geojson

# Copy the script into the container
COPY main.py /app/main.py

# Run the script to generate the data folder and GeoJSON files (this runs inside the container)
RUN python -u /app/main.py

# Install Nginx
RUN apt update && apt install -y nginx && rm -rf /var/lib/apt/lists/*

# Copy the entire generated data folder to the Nginx serving directory
RUN mkdir -p /var/www/html/data && cp -r /app/data/* /var/www/html/data/

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy the index.html file to the Nginx serving directory
COPY index.html /usr/share/nginx/html/index.html

# Expose port 80 for Nginx
EXPOSE 80

# Copy the entrypoint script into the container
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set the entrypoint script as the default command
ENTRYPOINT ["/app/entrypoint.sh"]
