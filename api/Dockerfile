FROM python:3.10 AS base

# Create a user and group named 'user'
# RUN groupadd -r user && useradd -m -r -g user user

# Set the working directory and user
WORKDIR /app
# USER user

# install popular Python packages
COPY requirements.txt ../requirements.txt
RUN pip3 install -r ../requirements.txt

EXPOSE 80