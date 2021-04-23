const inputFile = document.getElementById('inputFile');

function upload(file) {
    document.getElementById("fa-upload").className = "fa fa-cog fa-spin";
    var data = new FormData()
    data.append('file', file)

    fetch('/api/upload/', {
        method: 'POST',
        body: data
    }).then(data => data.json())
    .then(body => {
        if (body.status === 'infected') {
            window.location.pathname = '/virus_found';
            return;
        }

        if (body.status === 'failed') {
            window.localtion.pathame = '/error';
            return;
        }

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