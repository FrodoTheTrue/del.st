const inputFile = document.getElementById('inputFile');

var reader = new FileReader();

function upload(file) {
    document.getElementById("fa-upload").className = "fa fa-cog fa-spin";

    var generated_random = CryptoJS.lib.WordArray.random(16).toString();
    var key_for_server = CryptoJS.MD5(generated_random);

    var reader = new FileReader();

    reader.onload = (e) => {        
        var wordArray = CryptoJS.lib.WordArray.create(reader.result);
        var encrypted = CryptoJS.AES.encrypt(wordArray, generated_random).toString();
   
        var fileEnc = new Blob([encrypted]);  

        var data = new FormData();
        data.append('file', new File([fileEnc], file.name));

        fetch('/api/upload-crypto/' + key_for_server, {
            method: 'POST',
            body: data
        })
        .then(data => data.json())
        .then(body => {
            var container = document.getElementById('main-container');
            container.innerHTML = `
                <div class="slogan">Link to your file: ${window.location.origin + '/d/' + key_for_server.toString()}</div>
                <div class="slogan">Please, save your secret to decrypt file: ${generated_random}</div>
            `
      })
    }
      
    reader.readAsArrayBuffer(file)
}

const onSelectFile = () => upload(inputFile.files[0]);

inputFile.addEventListener('change', onSelectFile, false);
