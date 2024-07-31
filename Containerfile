FROM python:3.12-bookworm

ENV PYTHONUNBUFFERED 1

WORKDIR /app
COPY requirements.txt requirements.txt

RUN pip install --root-user-action=ignore --upgrade pip
RUN pip install --root-user-action=ignore -r requirements.txt

RUN playwright install-deps
RUN playwright install firefox

COPY tools.py tools.py
COPY loop_municipalities.py loop_municipalities.py

RUN mkdir /input
RUN mkdir /output

CMD ["python", "loop_municipalities.py"]
