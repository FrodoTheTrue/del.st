FROM python:3.8

COPY requirements.txt /app/requirements.txt
COPY static /app/static
COPY templates /app/templates
COPY main.py /app/main.py

WORKDIR /app

RUN pip3 install --upgrade setuptools
RUN pip3 install -r /app/requirements.txt

ENTRYPOINT [ "python3" ]
CMD [ "/app/main.py" ]