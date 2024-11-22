document.addEventListener("DOMContentLoaded", () => {
    const toggleButton = document.getElementById("btn-toggle");
    let isListening = false;

    toggleButton.addEventListener("click", () => {
        isListening = !isListening;
        if (isListening) {
            toggleButton.classList.add("active");
            recordAudio();
        } else {
            toggleButton.classList.remove("active");
        }
    });

    async function recordAudio() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            alert("Your browser does not support audio recording.");
            return;
        }

        const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            if (window.MediaRecorder) {
                recordWithMediaRecorder(stream);
            } else if (isSafari) {
                recordWithWebAudioAPI(stream);
            } else {
                alert("Recording not supported on this browser.");
            }
        } catch (error) {
            console.error("Error accessing audio device:", error);
            alert("Could not access audio device. Please check your permissions.");
        }
    }

    function recordWithMediaRecorder(stream) {
        const mimeType = /^((?!chrome|android).)*safari/i.test(navigator.userAgent)
            ? "audio/wav"
            : "audio/webm";
        const mediaRecorder = new MediaRecorder(stream, { mimeType });
        const audioChunks = [];

        mediaRecorder.ondataavailable = (event) => audioChunks.push(event.data);

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: mimeType });
            await uploadAudio(audioBlob);
            stream.getTracks().forEach((track) => track.stop());
        };

        mediaRecorder.start();
        setTimeout(() => mediaRecorder.stop(), 3500); // Record for 3.5 seconds
    }

    function recordWithWebAudioAPI(stream) {
        const audioContext = new AudioContext();
        const source = audioContext.createMediaStreamSource(stream);
        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        const audioData = [];

        processor.onaudioprocess = (event) => {
            const channelData = event.inputBuffer.getChannelData(0);
            audioData.push(new Float32Array(channelData));
        };

        source.connect(processor);
        processor.connect(audioContext.destination);

        setTimeout(async () => {
            processor.disconnect();
            source.disconnect();

            const audioBlob = createWAVBlob(audioData, audioContext.sampleRate);
            await uploadAudio(audioBlob);
            stream.getTracks().forEach((track) => track.stop());
        }, 3500);
    }

    async function uploadAudio(audioBlob) {
        const formData = new FormData();
        formData.append("audio", audioBlob, "recording.wav");

        try {
            const response = await fetch("/upload-audio", {
                method: "POST",
                body: formData,
            });

            if (response.ok) {
                const responseData = await response.json();
                if (responseData.endLoop) {
                    const redirectUrl = `/detected?key=${responseData.key}`;
                    window.location.href = redirectUrl;
                }
            } else {
                console.error("Error uploading audio:", await response.text());
            }
        } catch (error) {
            console.error("Upload failed:", error);
        }
    }

    function createWAVBlob(audioData, sampleRate) {
        const buffer = mergeBuffers(audioData);
        const wav = encodeWAV(buffer, sampleRate);
        return new Blob([wav], { type: "audio/wav" });
    }

    function mergeBuffers(buffers) {
        let length = 0;
        buffers.forEach((b) => (length += b.length));
        const merged = new Float32Array(length);
        let offset = 0;
        buffers.forEach((b) => {
            merged.set(b, offset);
            offset += b.length;
        });
        return merged;
    }

    function encodeWAV(buffer, sampleRate) {
        const bitDepth = 16;
        const numChannels = 1;
        const format = 1; // PCM
        const resultBuffer = new ArrayBuffer(44 + buffer.length * numChannels * (bitDepth / 8));
        const view = new DataView(resultBuffer);

        // WAV Header
        writeString(view, 0, "RIFF");
        view.setUint32(4, 36 + buffer.length * numChannels * (bitDepth / 8), true);
        writeString(view, 8, "WAVE");
        writeString(view, 12, "fmt ");
        view.setUint32(16, 16, true);
        view.setUint16(20, format, true);
        view.setUint16(22, numChannels, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * numChannels * (bitDepth / 8), true);
        view.setUint16(32, numChannels * (bitDepth / 8), true);
        view.setUint16(34, bitDepth, true);
        writeString(view, 36, "data");
        view.setUint32(40, buffer.length * numChannels * (bitDepth / 8), true);

        // Write samples
        let offset = 44;
        for (let i = 0; i < buffer.length; i++) {
            const sample = Math.max(-1, Math.min(1, buffer[i]));
            view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
            offset += 2;
        }

        return view.buffer;
    }

    function writeString(view, offset, string) {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    }
});
