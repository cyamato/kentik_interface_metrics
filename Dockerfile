FROM python:3

ARG KENTIK_HARPERDB_SCHEMA
ARG KENTIK_HARPERDB_TABLE
ARG KENTIK_HARPERDB_URL
ARG KENTIK_QUERY_TIME_AMOUNT
ARG KENTIK_QUERY_TIME_INCROMENT
ARG KENTIK_URL

LABEL maintainer="Craig Yamato <craig.yamato2@gmail.com>"

WORKDIR /usr/src/app

COPY * ./
RUN pip install --no-cache-dir -r requirements.txt 
    
CMD [ "python", "./kentikQueryInterfaceMetrics.py" ]
