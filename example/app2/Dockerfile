FROM base-py:1.0 AS base

RUN mkdir /app
WORKDIR /app

ENTRYPOINT ["python3", "-m", "http.server", "8080"]

FROM base AS service1
RUN echo "This is app2 service1" > index.html

FROM base AS service2
ARG SERVICE_MESSAGE
RUN echo "This is app2 service2" > index.html
RUN echo "Secret message: ${SERVICE_MESSAGE}" >> index.html
