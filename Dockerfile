FROM python:3

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY app.py /app/app.py

WORKDIR /app

CMD ["streamlit", "run", "--server.enableCORS", "false", "app.py"]
