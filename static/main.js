const inputFile = document.getElementById('inputFile');

function upload(file) {
    var data = new FormData()
    data.append('file', file)

    fetch('/api/upload/', {
        method: 'POST',
        body: data
    }).then(data => data.json())
    .then(body => {
        if (body.file_id) {
            window.location.pathname = '/d/' + body.file_id;
        }
    })
}

// Event handler executed when a file is selected
const onSelectFile = () => upload(inputFile.files[0]);

// Add a listener on your input
// It will be triggered when a file will be selected
inputFile.addEventListener('change', onSelectFile, false);