# Use a lightweight Python image
FROM python:3.11-slim

# Install required system packages
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the project files into the container
COPY . /app

# Create a virtual environment and install Python packages
RUN python -m venv /venv && \
    /venv/bin/pip install --upgrade pip && \
    /venv/bin/pip install -r polybot/requirements.txt

# Set Python path to your app
ENV PYTHONPATH=/app

# Expose the HTTPS port used by the bot
EXPOSE 8443

# Command to run the bot
CMD ["/venv/bin/python", "polybot/app.py", "--port", "8443"]