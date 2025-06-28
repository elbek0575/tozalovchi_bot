# Python базавий имидж
FROM python:3.10-slim

# Систем пакеттерни янгилаймиз ва кераклиларини ўрнатамиз
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    tesseract-ocr-rus \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt ни нусхалаш ва пакетларни ўрнатиш
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Кодни контейнер ичига нусхалаш
COPY . /app
WORKDIR /app

# Bot'ни ишга тушириш
CMD ["python", "bot.py"]

