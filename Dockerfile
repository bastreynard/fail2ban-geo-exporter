# Use the official Python image from the Docker Hub
FROM python:3.11-slim

WORKDIR /app

COPY app/requirements.txt .
COPY app/f2b-geo-parser.py .

# Copy the entrypoint script into the container
COPY app/entrypoint.sh /usr/local/bin/
# Make the entrypoint script executable
RUN chmod +x /usr/local/bin/entrypoint.sh
# Set the entrypoint to the script
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

RUN apt update && apt install cron -y
RUN pip install --no-cache-dir -r requirements.txt
