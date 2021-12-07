import os
import random
import string
import werkzeug
import requests
import time

from flask import Flask, render_template, request, send_file
from azure.storage.blob import BlobServiceClient, BlobClient
from azure.cosmos import CosmosClient
import tempfile


app = Flask(
    __name__, 
    static_folder='static/',
    static_url_path='/static',
)

connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
AZURE_CONTAINER = os.environ.get('AZURE_CONTAINER', 'delst-storage')

AZURE_ACCOUNT_URI = os.environ.get('AZURE_ACCOUNT_URI')
AZURE_ACCOUNT_KEY = os.environ.get('AZURE_ACCOUNT_KEY')
AZURE_COSMOS_DB_NAME = os.environ.get('AZURE_COSMOS_DB_NAME', 'delst-db')
AZURE_COSMOS_DB_CONTAINER = os.environ.get('AZURE_COSMOS_DB_CONTAINER', 'Files')

MALWARE_SCANNER_HOST = os.environ.get('MALWARE_SCANNER_HOST', 'https://malware-scanner-xwqqlm3wva-uc.a.run.app')

def humanbytes(B):
   'Return the given bytes as a human friendly KB, MB, GB, or TB string'
   B = float(B)
   KB = float(1024)
   MB = float(KB ** 2) # 1,048,576
   GB = float(KB ** 3) # 1,073,741,824
   TB = float(KB ** 4) # 1,099,511,627,776

   if B < KB:
      return '{0} {1}'.format(B,'Bytes' if B > 1 else 'Byte')
   elif KB <= B < MB:
      return '{0:.2f} KB'.format(B/KB)
   elif MB <= B < GB:
      return '{0:.2f} MB'.format(B/MB)
   elif GB <= B < TB:
      return '{0:.2f} GB'.format(B/GB)
   elif TB <= B:
      return '{0:.2f} TB'.format(B/TB)

blob_service_client = BlobServiceClient.from_connection_string(connect_str)
container_client = blob_service_client.get_container_client(AZURE_CONTAINER)

client = CosmosClient(AZURE_ACCOUNT_URI, credential=AZURE_ACCOUNT_KEY)
database = client.get_database_client(AZURE_COSMOS_DB_NAME)
container = database.get_container_client(AZURE_COSMOS_DB_CONTAINER)

@app.route('/api/upload-crypto/<key>', methods=['POST'])
def upload_crypto(key):
    f = request.files['file']
    file_path = '/tmp/' + key
    original_filename = werkzeug.utils.secure_filename(f.filename)
    f.save(file_path)

    blob_client = blob_service_client.get_blob_client(container=AZURE_CONTAINER, blob=key)

    with open(file_path, "rb") as data:
        blob_client.upload_blob(data)

    container.upsert_item({
        'FileId': key,
        'BucketName': AZURE_CONTAINER,
        'FileName': original_filename,
        'Timestamp': str(time.time()),
        'Outdated': False,
        'Encrypted': True,
    })

    return {}

@app.route('/crypto')
def crypto():
    return render_template('crypto.html')

@app.route('/virus_found')
def virus_found():
    return render_template('virus_found.html'), 403


@app.route('/error')
def error():
    return render_template('error.html'), 400

@app.route('/')
def main():
    return render_template('main.html')

@app.route('/s/<file_id>')
def storage_proxy(file_id):
    blob_client = BlobClient.from_connection_string(conn_str=connect_str, container_name=AZURE_CONTAINER, blob_name=file_id)

    with tempfile.NamedTemporaryFile() as download_file:
        download_file.write(blob_client.download_blob().readall())
        return send_file(download_file.name, attachment_filename=file_id)


@app.route('/d/<id>')
def download(id):
    result = False

    for item in container.query_items(
        query=f"SELECT * FROM Files WHERE Files.FileId = '{id}' AND Files.Outdated = false",
    ):
        result = True

        file_id = item["FileId"]
        file_name = item["FileName"]
        encrypted = item["Encrypted"]

        blob_client = blob_service_client.get_blob_client(container=AZURE_CONTAINER, blob=file_id)

        file_size = humanbytes(blob_client.get_blob_properties().size)

        return render_template(
            'download.html', 
            file_name=file_name, 
            file_id=file_id, 
            file_size=file_size,
            encrypted=encrypted,
        )

    if not result:
        return render_template('404.html'), 404


@app.route('/api/upload/', methods=['POST'])
def upload():
    f = request.files['file']
    original_filename = werkzeug.utils.secure_filename(f.filename)
    generated_filename = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    file_path = '/tmp/' + generated_filename
    f.save(file_path)

    blob_client = blob_service_client.get_blob_client(container=AZURE_CONTAINER, blob=generated_filename)

    with open(file_path, "rb") as data:
        blob_client.upload_blob(data)
    
    res = requests.post(f'{MALWARE_SCANNER_HOST}/scan', json = {'filename': generated_filename}).json()

    if not res or not res['status'] or res['status'] != 'clean':
        if res['status'] == 'infected':
            return {'status': 'infected'}
        return {'status': 'failed'}

    container.upsert_item({
        'FileId': generated_filename,
        'BucketName': AZURE_CONTAINER,
        'FileName': original_filename,
        'Timestamp': str(time.time()),
        'Outdated': False,
        'Encrypted': False,
    })

    return {
        'status': 'ok',
        'file_id': generated_filename
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
