# Use an official Python image as a base
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install required Python packages
RUN pip install --no-cache-dir requests osm2geojson

# Copy the script and data folder into the container
COPY main.py /app/main.py
COPY data /app/data/

# Ensure the data folder exists
RUN mkdir -p /app/data

# Run the script to generate GeoJSON files
RUN python /app/main.py

# Install Nginx
RUN apt update && apt install -y nginx && rm -rf /var/lib/apt/lists/*

# Copy the entire data folder to the Nginx serving directory
RUN mkdir -p /var/www/html/data && cp -r /app/data/* /var/www/html/data/

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 80 for Nginx
EXPOSE 80

# Start Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]
