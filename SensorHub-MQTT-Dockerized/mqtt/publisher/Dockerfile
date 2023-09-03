FROM python:3.10
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY publisher.py publisher.py
CMD ["python", "publisher.py"]
