# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose a default port (Render will map $PORT)
EXPOSE 10000

# Start the FastAPI app with Uvicorn, using $PORT from environment
CMD ["sh", "-c", "uvicorn chat_api:app --host 0.0.0.0 --port $PORT"]
