var inputEncryptionKey = document.getElementById('encryption-key');
var buttonDownload = document.getElementById('download');
var fileName = document.getElementById('file_name');

function convertWordArrayToUint8Array(wordArray) {
    var arrayOfWords = wordArray.hasOwnProperty("words") ? wordArray.words : [];
    var length = wordArray.hasOwnProperty("sigBytes") ? wordArray.sigBytes : arrayOfWords.length * 4;
    var uInt8Array = new Uint8Array(length), index=0, word, i;
    for (i=0; i<length; i++) {
        word = arrayOfWords[i];
        uInt8Array[index++] = word >> 24;
        uInt8Array[index++] = (word >> 16) & 0xff;
        uInt8Array[index++] = (word >> 8) & 0xff;
        uInt8Array[index++] = word & 0xff;
    }
    return uInt8Array;
}

function onDownload() {
    key_for_server = window.location.pathname.slice(3);

    fetch('/s/' + key_for_server)
    .then(data => data.text())
    .then(data => {
        var decrypted = CryptoJS.AES.decrypt(data, inputEncryptionKey.value);
        var typedArray = convertWordArrayToUint8Array(decrypted);
        var fileDec = new Blob([typedArray]); 
        saveAs(fileDec, fileName.innerHTML);
    })
}

if (buttonDownload) {
    buttonDownload.addEventListener('click', onDownload);
}
