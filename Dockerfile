# Use a lightweight Python image
FROM python:3.10

# Install required system packages
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    libgl1 \
    libegl1 \
    libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*
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