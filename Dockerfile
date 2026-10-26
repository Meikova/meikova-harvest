# Use python 3.10-slim as base image to keep image size small
FROM python:3.10-slim

# Prevent Python from writing pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb \
    && dpkg -i /tmp/cloudflared.deb \
    && rm -f /tmp/cloudflared.deb \
    && rm -rf /var/lib/apt/lists/*

# Install Deno (official recommended JS engine for yt-dlp signature decryption)
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno

# Copy requirements file first to take advantage of Docker cache layering
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application codebase
COPY . /app/

# Ensure the downloads directory exists and has correct permissions
RUN mkdir -p /app/downloads/cookies

# Expose port 18650 for Flask
EXPOSE 18650

# Set default start command
CMD ["python", "app.py"]
