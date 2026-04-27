FROM sennet/api-base-image:1.4.2

LABEL description="SenNet Senotype API Service"

ARG HOST_GID
ARG HOST_UID

USER root

# Change to directory that contains the Dockerfile
WORKDIR /usr/src/app

# Update outdated package
RUN apt-get update -y && \
    apt-get dist-upgrade -y && \
    apt-get install -y curl ca-certificates

# Copy from host to image
COPY requirements.txt ./requirements.txt

# Update Python packages. uwsgi is installed by the base image.
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r ./requirements.txt && \
    rm -rf /root/.cache/pip && \
    rm requirements.txt

COPY src ./src

# Modify the UID and GID of codcc to match the host
RUN groupmod --gid $HOST_GID codcc && \
    usermod --uid $HOST_UID codcc

USER codcc

CMD ["uwsgi", "--ini", "/usr/src/app/src/uwsgi.ini"]
