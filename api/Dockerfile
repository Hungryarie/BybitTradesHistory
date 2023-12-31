FROM python:3.10 AS base

#ADD . /app
RUN mkdir /app

WORKDIR /app

#install popular Python packages
#COPY test-req-minimal.txt ../requirements.txt
COPY requirements.txt ../requirements.txt
RUN pip3 install -r ../requirements.txt


EXPOSE 80

RUN pip install debugpy

EXPOSE 5678

ENTRYPOINT [ "python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "-m"]