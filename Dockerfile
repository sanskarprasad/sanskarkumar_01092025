# Use an official Python 3.11 slim image as the base
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the dependency files first to leverage Docker's layer caching
COPY ./requirements.txt /app/requirements.txt

# Install the Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy your application code into the container
COPY ./store_monitoring /app/store_monitoring

# Expose port 8000 to allow communication with the server
EXPOSE 8000

# The command to run when the container starts
CMD ["uvicorn", "store_monitoring.main:app", "--host", "0.0.0.0", "--port", "8000"]