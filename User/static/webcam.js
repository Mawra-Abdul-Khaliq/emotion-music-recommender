let stream = null;
let captureInterval = null;

async function getMedia() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true });
        const videoElement = document.getElementById('videoElement');
        videoElement.srcObject = stream;
    } catch (error) {
        console.error('Error accessing the webcam:', error);
    }
}

function stopMediaTracks(stream) {
    stream.getTracks().forEach(track => {
        track.stop();
    });
}

function stopCapturing() {
    if (captureInterval) {
        clearInterval(captureInterval);
        captureInterval = null;
    }
    if (stream) {
        stopMediaTracks(stream);
        stream = null;
    }
}

function displayResult(data) {
    const emotionLabel = document.getElementById('emotionLabel');
    if (data.status === 'success') {
        window.location.href = `/recommendations`;
    } else {
        emotionLabel.textContent = data.message || 'Emotion could not be detected';
        console.error('Error:', data.message);
    }
}

function captureFrame() {
    const videoElement = document.getElementById('videoElement');
    const canvas = document.createElement('canvas');
    canvas.width = videoElement.videoWidth;
    canvas.height = videoElement.videoHeight;
    const context = canvas.getContext('2d');
    context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

    const frame = canvas.toDataURL('image/png');
    fetch('/process_frames', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ frame: frame })
    })
    .then(response => response.json())
    .then(data => displayResult(data))
    .catch(error => {
        console.error('Error:', error);
        const emotionLabel = document.getElementById('emotionLabel');
        emotionLabel.textContent = 'Error processing the frame';
    });
}

function requestCameraAccess() {
    let choice = confirm("Allow camera access? Click 'OK' for Yes, 'Cancel' for No");
    if (choice) {
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(stream => {
                saveCameraAccessPreference('always');
                startWebcam(stream);
            })
            .catch(err => {
                alert("Camera access denied.");
            });
    } else {
        saveCameraAccessPreference('never');
        alert("Camera access denied.");
    }
}

function startWebcam() {
    getMedia().then(() => {
        captureInterval = setInterval(captureFrame, 5000); // Capture a frame every 5 seconds
    });
}

function saveCameraAccessPreference(preference) {
    fetch('/camera_access', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ camera_access: preference })
    }).then(response => response.json()).then(data => {
        if (data.status === 'success') {
            console.log('Camera access preference saved.');
        }
    });
}

document.getElementById('webcam').addEventListener('click', () => {
    fetch('/get_camera_access_preference')
        .then(response => response.json())
        .then(data => {
            let accessPreference = data.camera_access;
            if (!accessPreference || accessPreference === 'this_session') {
                requestCameraAccess();
            } else if (accessPreference === 'always') {
                startWebcam();
            } else {
                alert("Camera access is denied. Please update your settings to allow camera access.");
            }
        })
        .catch(error => {
            console.error('Error fetching camera access preference:', error);
            requestCameraAccess(); // Default to asking for camera access if there's an error
        });
});