FROM python:3

WORKDIR /app

# portaudio19-dev: pyaudio用
RUN apt update && apt -y install portaudio19-dev pulseaudio alsa-utils

COPY ./requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt