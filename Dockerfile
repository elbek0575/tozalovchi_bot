FROM python:3.11-slim

WORKDIR /app

# requirements.txt ва код файлларини нусхалаш
COPY . .

# pip'ни янгилаш ва керакли пакетларни ўрнатиш

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-rus \
    libgl1 \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Порт ва ишга тушириш буйруғи
EXPOSE 5000
CMD ["python", "bot.py"]
