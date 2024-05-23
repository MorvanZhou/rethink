FROM python:3.11.9-slim-bullseye
MAINTAINER morvanzhou@hotmail.com

WORKDIR /

COPY . /
ENV PYTHONPATH=/src
RUN python3 -m pip install --no-cache-dir -e .

EXPOSE 8080

ENV APP_LANGUAGE en
ENV APP_PASSWORD ""
ENV API_URL "http://127.0.0.1:8080"

ENTRYPOINT ["python3", "run_in_docker.py"]
