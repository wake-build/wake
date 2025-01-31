FROM base-py:1.0 AS base

RUN mkdir /app
WORKDIR /app
RUN echo "Hello from service2" > index.html

ENTRYPOINT ["python3", "-m", "http.server", "8080"]
