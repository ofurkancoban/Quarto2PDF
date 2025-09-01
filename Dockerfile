FROM python:3.11-slim

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    chromium nodejs npm ca-certificates fonts-liberation \
    libasound2 libatk-bridge2.0-0 libatk1.0-0 libcups2 libdrm2 \
    libxkbcommon0 libgtk-3-0 libnss3 libnspr4 libxcomposite1 libxrandr2 \
    libxdamage1 libgbm1 libxshmfence1 wget gnupg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY package*.json /app/
RUN npm install puppeteer

COPY . /app

ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_PORT=8504
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

EXPOSE 8504

# Exec form: her argüman ayrı
CMD ["python", "-m", "streamlit", "run", "main.py", "--server.address=0.0.0.0", "--server.port=8504"]