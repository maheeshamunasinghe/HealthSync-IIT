# Use the official Python image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy application code and dependencies
COPY . .

# Install dependencies
RUN pip install -r requirements.txt

# Expose the application port
EXPOSE 5002

# Run the application
CMD ["python", "appointment_service.py"]

