import random
import string
import werkzeug

from flask import Flask, render_template, request, send_file
from google.cloud import storage, spanner
import tempfile


app = Flask(
    __name__, 
    static_folder='static/',
    static_url_path='/static',
)

# init Google Storage
storage_client = storage.Client()
bucket = storage_client.get_bucket('del-st-storage')

# init Google Spanner
spanner_client = spanner.Client()
spanner_db = spanner_client.instance('del-st-production').database('dels-st-meta')


@app.route('/')
def main():
    return render_template('main.html')


@app.route('/s/<file_id>')
def storage_proxy(file_id):
    bucket = storage_client.get_bucket('del-st-storage')
    blob = bucket.blob(file_id)
    with tempfile.NamedTemporaryFile() as temp:
        blob.download_to_filename(temp.name)
        return send_file(temp.name, attachment_filename=file_id)


@app.route('/d/<file_id>')
def download(file_id):
    def get_file(transaction):
        result = transaction.execute_sql(
            f"SELECT FileId, BucketName, FileName FROM Files WHERE FileId = '{file_id}'"
        ).one_or_none()

        return result
    result = spanner_db.run_in_transaction(get_file)

    if not result:
        return render_template('404.html')
    return render_template('download.html', file_name=result[2], file_id=result[0])


@app.route('/api/upload/', methods=['POST'])
def upload():
    f = request.files['file']
    original_filename = werkzeug.utils.secure_filename(f.filename)
    generated_filename = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    file_path = '/tmp/' + generated_filename
    f.save(file_path)

    # check file for viruses
    # ...
    # end check for viruses

    blob = bucket.blob(generated_filename)
    blob.upload_from_filename(file_path)

    def insert_new_file(transaction):
        transaction.execute_update(
            f"INSERT Files (FileId, BucketName, FileName) "
            f" VALUES ('{generated_filename}', '{blob.bucket.name}', '{original_filename}')"
        )

    spanner_db.run_in_transaction(insert_new_file)

    return {
        'file_id': generated_filename
    }




if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
