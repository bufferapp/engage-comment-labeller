FROM python:3.7.2

EXPOSE 8080

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY app.py /app/app.py

WORKDIR /app

CMD ["streamlit", "run", "--server.port", "8080", "--server.enableCORS", "false", "app.py"]
