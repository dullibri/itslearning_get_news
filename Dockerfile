FROM python:3.9-slim

WORKDIR /app

# Installieren Sie notwendige Pakete
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Kopieren Sie die Anwendungsdateien
COPY requirements.txt .
COPY lambda_function.py .

# Installieren Sie Python-Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt

# Setzen Sie die Umgebungsvariable für den Selenium-Host
ENV SELENIUM_HOST=selenium

CMD ["python", "lambda_function.py"]