FROM python:3

LABEL maintainer="Craig Yamato <craig.yamato2@gmail.com>"

WORKDIR /usr/src/app

COPY * ./
RUN pip install --no-cache-dir -r requirements.txt \
    && python ./harperDBSetup.py
    
CMD [ "python", "./kentikQueryInterfaceMetrics.py" ]