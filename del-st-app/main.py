import os
import random
import string
import werkzeug
import requests

from flask import Flask, render_template, request, send_file
from google.cloud import storage, spanner
import tempfile


app = Flask(
    __name__, 
    static_folder='static/',
    static_url_path='/static',
)

GCP_BUCKET = os.environ.get('GCP_BUCKET', 'del-st-storage')
GCP_SPANNER_INSTANCE = os.environ.get('GCP_SPANNER_INSTANCE', 'del-st-production')
GCP_SPANNER_DATABASE = os.environ.get('GCP_SPANNER_DATABASE', 'dels-st-meta')
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

# init Google Storage
storage_client = storage.Client()
bucket = storage_client.get_bucket(GCP_BUCKET)

# init Google Spanner
spanner_client = spanner.Client()
spanner_db = spanner_client.instance(GCP_SPANNER_INSTANCE).database(GCP_SPANNER_DATABASE)

@app.route('/api/upload-crypto/<key>', methods=['POST'])
def upload_crypto(key):
    f = request.files['file']
    file_path = '/tmp/' + key
    original_filename = werkzeug.utils.secure_filename(f.filename)
    f.save(file_path)

    blob = bucket.blob(key)
    blob.upload_from_filename(file_path)

    def insert_new_file(transaction):
        transaction.execute_update(
            f"INSERT Files (FileId, BucketName, FileName, Timestamp, Outdated, Encrypted) "
            f" VALUES ('{key}', '{blob.bucket.name}', '{original_filename}', CURRENT_TIMESTAMP, False, True)"
        )

    spanner_db.run_in_transaction(insert_new_file)

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

@app.route('/fresh')
def fresh():
    def set_outdated(transaction):
        row_ct = transaction.execute_update(
            f"UPDATE Files "
            f"SET Outdated = TRUE "
            f"WHERE TIMESTAMP_DIFF(CURRENT_TIMESTAMP, Timestamp, SECOND) > 86400"
        )

        print("{} record(s) updated.".format(row_ct))

    spanner_db.run_in_transaction(set_outdated)

    return 'ok'

@app.route('/s/<file_id>')
def storage_proxy(file_id):
    blob = bucket.blob(file_id)
    with tempfile.NamedTemporaryFile() as temp:
        blob.download_to_filename(temp.name)
        return send_file(temp.name, attachment_filename=file_id)


@app.route('/d/<id>')
def download(id):
    def get_file(transaction):
        result = transaction.execute_sql(
            f"SELECT FileId, FileName, Encrypted FROM Files WHERE FileId = '{id}' AND Outdated = FALSE"
        ).one_or_none()

        return result

    result = spanner_db.run_in_transaction(get_file)

    if not result:
        return render_template('404.html'), 404

    file_id, file_name, encrypted = result

    blob = bucket.blob(file_id)
    blob.reload()

    file_size = humanbytes(blob.size)

    return render_template(
        'download.html', 
        file_name=file_name, 
        file_id=file_id, 
        file_size=file_size,
        encrypted=encrypted,
    )


@app.route('/api/upload/', methods=['POST'])
def upload():
    f = request.files['file']
    original_filename = werkzeug.utils.secure_filename(f.filename)
    generated_filename = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    file_path = '/tmp/' + generated_filename
    f.save(file_path)


    blob = bucket.blob(generated_filename)
    blob.upload_from_filename(file_path)

    res = requests.post(f'{MALWARE_SCANNER_HOST}/scan', json = {'filename': generated_filename}).json()

    if not res or not res['status'] or res['status'] != 'clean':
        if res['status'] == 'infected':
            return {'status': 'infected'}
        return {'status': 'failed'}

    def insert_new_file(transaction):
        transaction.execute_update(
            f"INSERT Files (FileId, BucketName, FileName, Timestamp, Outdated, Encrypted) "
            f" VALUES ('{generated_filename}', '{blob.bucket.name}', '{original_filename}', CURRENT_TIMESTAMP, False, False)"
        )

    spanner_db.run_in_transaction(insert_new_file)

    return {
        'status': 'ok',
        'file_id': generated_filename
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
