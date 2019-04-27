FROM python:3

ARG KENTIK_API_TOKEN
ARG KENTIK_API_USER
ARG KENTIK_HARPERDB_PASSWORD
ARG KENTIK_HARPERDB_SCHEMA
ARG KENTIK_HARPERDB_TABLE
ARG KENTIK_HARPERDB_URL
ARG KENTIK_HARPERDB_USER
ARG KENTIK_QUERY_TIME_AMOUNT
ARG KENTIK_QUERY_TIME_INCROMENT
ARG KENTIK_URL

LABEL maintainer="Craig Yamato <craig.yamato2@gmail.com>"

WORKDIR /usr/src/app

COPY * ./
RUN pip install --no-cache-dir -r requirements.txt \
    && ping harperdb -c 4 \
    && python ./harperDBSetup.py \
    --harperdb_url=$KENTIK_HARPERDB_URL \
    --harperdb_user=$KENTIK_HARPERDB_USER \
    --harperdb_password=$KENTIK_HARPERDB_PASSWORD \
    --harperdb_schema=$KENTIK_HARPERDB_SCHEMA \
    --harperdb_table=$KENTIK_HARPERDB_TABLE
    
CMD [ "python", "./kentikQueryInterfaceMetrics.py" ]
