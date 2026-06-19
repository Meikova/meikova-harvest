function oFunc(callback) {
    const fpPromise = import('/Content/JS/o.js').then(FingerprintJS => FingerprintJS.load())
    fpPromise
        .then(fp => fp.get())
        .then(result => {
            const visitorId = result.visitorId
            var canvas = document.createElement('canvas');
            var gl;
            var debugInfo;
            var renderer;
            try {
                gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            } catch (e) {
            }
            if (gl) {
                debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
            }
            callback(visitorId, renderer)
        })
        .catch(error => console.error(error))
}

function SentData(url, formData, callback) {
    $.ajax({
        type: "POST",
        url: url,
        data: formData,
        contentType: false,
        processData: false,
        success: function (data) {
            callback(data)
        },
        error: function (error) {
            callback(error)
        }
    });
}

function Phone() {
    var isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    if (!isMobile) {
        return false
    } else {
        return true
    }
}

function Android() {
    var isAndroid = /Android/i.test(navigator.userAgent);
    if (!isAndroid) {
        return false
    } else {
        return true
    }
}

// HIỆN LOADING
function ShowLoading() {
    $('body').loadingModal({ text: 'Loading...' });
    var delay = function (ms) { return new Promise(function (r) { setTimeout(r, ms) }) };
    var time = 2000;
    delay(time)
        .then(function () { $('body').loadingModal('animation', 'rotatingPlane'); return delay(time); })
        .then(function () { $('body').loadingModal('animation', 'wave'); return delay(time); })
        .then(function () { $('body').loadingModal('animation', 'wanderingCubes'); return delay(time); })
        .then(function () { $('body').loadingModal('animation', 'spinner'); return delay(time); })
        .then(function () { $('body').loadingModal('animation', 'chasingDots'); return delay(time); })
        .then(function () { $('body').loadingModal('animation', 'threeBounce'); return delay(time); })
        .then(function () { $('body').loadingModal('animation', 'circle'); return delay(time); })
        .then(function () { $('body').loadingModal('animation', 'cubeGrid'); return delay(time); })
        .then(function () { $('body').loadingModal('animation', 'fadingCircle'); return delay(time); })
        .then(function () { $('body').loadingModal('animation', 'foldingCube'); return delay(time); })
}

// ẨN LOADING
function HideLoading() {
    // Tắt loading
    $('body').loadingModal('destroy')
}