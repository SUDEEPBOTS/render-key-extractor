FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install Tor and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    tor \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Configure Tor ControlPort
RUN echo "ControlPort 9051\nCookieAuthentication 0\n" >> /etc/tor/torrc

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser
RUN playwright install chromium

# Copy application files
COPY . .

# Ensure start script is executable
RUN chmod +x start.sh

# Render sets PORT dynamically
EXPOSE 8090

CMD ["./start.sh"]
