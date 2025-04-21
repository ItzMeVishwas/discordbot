# 1. Base image with Python
FROM python:3.11-slim

# 2. Install ffmpeg (and clean up apt caches)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# 3. Set working directory inside container
WORKDIR /app

# 4. Copy your code into the container
COPY . /app

# 5. Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 6. Expose the port your keep_alive.py uses
EXPOSE 8080

# 7. This is what runs when the container starts
CMD ["python", "bot.py"]
