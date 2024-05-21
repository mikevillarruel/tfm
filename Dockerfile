FROM apache/airflow:2.9.1-python3.10

COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

RUN python3 -c "import stanza; stanza.download('es')"
