FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy the service files
COPY . .

# Install dependencies
RUN pip install -r requirements.txt

# Specify the command to run the aggregator service
CMD ["python", "aggregator_service.py"]
