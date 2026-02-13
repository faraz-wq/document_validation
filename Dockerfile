FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Create startup script that runs migrations then starts the app
RUN echo '#!/bin/bash\nset -e\necho "Running database migrations..."\nalembic upgrade head\necho "Starting application..."\nexec uvicorn app.main:app --host 0.0.0.0 --port 8000' > /start.sh && \
    chmod +x /start.sh

CMD ["/start.sh"]
