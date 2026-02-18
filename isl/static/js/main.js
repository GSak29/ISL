document.addEventListener('DOMContentLoaded', function () {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const clearBtn = document.getElementById('clearBtn');
    const videoFeed = document.getElementById('videoFeed');
    const detectedWords = document.getElementById('detectedWords');
    const fullSentence = document.getElementById('fullSentence');
    const translation = document.getElementById('translation');
    const showBoxes = document.getElementById('showBoxes');
    const enableSpeech = document.getElementById('enableSpeech');
    const loadingOverlay = document.getElementById('videoLoading');

    // New status elements from sidebar
    const statusText = document.getElementById('statusText');
    const statusIndicatorIcon = document.getElementById('statusIndicator');

    // Check if browser supports speech synthesis
    if (!('speechSynthesis' in window)) {
        console.warn('Your browser does not support speech synthesis. Text-to-speech will be disabled.');
        enableSpeech.checked = false;
        enableSpeech.disabled = true;
        enableSpeech.parentElement.appendChild(document.createTextNode(' (Not supported in this browser)'));
    } else {
        console.log('Speech synthesis is supported in this browser.');
    }

    let isDetectionRunning = false;
    let detectedWordsList = [];
    let videoFeedInterval = null;

    // Function to show loading state
    function showLoading() {
        if (loadingOverlay) {
            loadingOverlay.style.display = 'flex';
            // videoFeed.style.display = 'none'; // Keep video feed placeholder visible but overlaid
        }
    }

    // Function to hide loading state
    function hideLoading() {
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
            // videoFeed.style.display = 'block';
        }
    }

    // Function to update video feed
    function updateVideoFeed() {
        if (isDetectionRunning) {
            const timestamp = new Date().getTime();
            let videoUrl = '/video_feed';
            videoUrl += `?show_boxes=${showBoxes.checked}`;
            videoUrl += `&t=${timestamp}`;

            // Add error handling for video feed
            videoFeed.onerror = function () {
                console.error('Error loading video feed');

                // Update sidebar status
                if (statusText && statusIndicatorIcon) {
                    statusText.textContent = "Camera Error";
                    statusIndicatorIcon.className = "d-flex align-items-center text-danger";
                }

                // Show error message in loading overlay
                if (loadingOverlay) {
                    loadingOverlay.innerHTML = '<div class="text-white text-center"><i class="fas fa-exclamation-triangle fa-2x mb-2"></i><p>Camera Error</p></div>';
                    loadingOverlay.style.display = 'flex';
                }

                // Try to reconnect after 2 seconds
                setTimeout(() => {
                    if (isDetectionRunning) {
                        updateVideoFeed();
                    }
                }, 2000);
            };

            videoFeed.onload = function () {
                if (statusText && statusIndicatorIcon) {
                    statusText.textContent = "Active";
                    statusIndicatorIcon.className = "d-flex align-items-center text-success";
                }
                hideLoading();
            };

            videoFeed.src = videoUrl;
        }
    }

    // Function to update button states
    function updateButtonStates() {
        startBtn.disabled = isDetectionRunning;
        stopBtn.disabled = !isDetectionRunning;

        // We rely on CSS classes for styling, just toggle disabled state is enough usually,
        // but let's keep the logic if we want visual feedback beyond disabled attribute
        if (isDetectionRunning) {
            startBtn.classList.add('opacity-50');
            stopBtn.classList.remove('opacity-50');
        } else {
            startBtn.classList.remove('opacity-50');
            stopBtn.classList.add('opacity-50');
        }
    }

    // Start detection
    startBtn.addEventListener('click', async function () {
        if (!isDetectionRunning) {
            showLoading();
            startBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Initializing...';

            try {
                const response = await fetch('/start_detection', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        show_boxes: showBoxes.checked
                    })
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.message || 'Failed to start');
                }

                isDetectionRunning = true;
                updateButtonStates();

                startBtn.innerHTML = '<i class="fas fa-camera"></i> Active';
                setTimeout(() => {
                    startBtn.innerHTML = '<i class="fas fa-play"></i> Start';
                }, 2000);

                // Start video feed updates
                updateVideoFeed();
                videoFeedInterval = setInterval(updateVideoFeed, 1000);

                if (statusText && statusIndicatorIcon) {
                    statusText.textContent = "Running";
                    statusIndicatorIcon.className = "d-flex align-items-center text-success";
                }

            } catch (error) {
                console.error('Camera initialization error:', error);
                alert('Error starting detection: ' + error.message);
                startBtn.innerHTML = '<i class="fas fa-play"></i> Start';
                hideLoading();

                if (statusText && statusIndicatorIcon) {
                    statusText.textContent = "Error";
                    statusIndicatorIcon.className = "d-flex align-items-center text-danger";
                }

                // Show error message in loading overlay
                if (loadingOverlay) {
                    loadingOverlay.innerHTML = '<div class="text-white text-center">Camera Failed</div>';
                    loadingOverlay.style.display = 'flex';
                }
            }
        }
    });

    // Stop detection
    stopBtn.addEventListener('click', async function () {
        if (isDetectionRunning) {
            showLoading();
            stopBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Stopping...';

            try {
                const response = await fetch('/stop_detection', {
                    method: 'POST'
                });

                if (!response.ok) {
                    throw new Error('Failed to stop detection');
                }

                isDetectionRunning = false;
                updateButtonStates();
                videoFeed.src = ''; // Clear source

                // Clear the video feed update interval
                if (videoFeedInterval) {
                    clearInterval(videoFeedInterval);
                    videoFeedInterval = null;
                }

                // Reset speech-related variables
                lastTranslation = "";
                translationStableStartTime = null;
                spokenSentences.clear();

                // Cancel any ongoing speech
                if (isSpeaking) {
                    window.speechSynthesis.cancel();
                    isSpeaking = false;
                    const indicator = document.getElementById('speechIndicator');
                    if (indicator) indicator.remove();
                }

                // Update Sidebar Status
                if (statusText && statusIndicatorIcon) {
                    statusText.textContent = "Stopped";
                    statusIndicatorIcon.className = "d-flex align-items-center text-muted";
                }

                stopBtn.innerHTML = '<i class="fas fa-check"></i> Stopped';
                setTimeout(() => {
                    stopBtn.innerHTML = '<i class="fas fa-stop"></i> Stop';
                }, 2000);
            } catch (error) {
                alert('Error stopping detection: ' + error.message);
                stopBtn.innerHTML = '<i class="fas fa-stop"></i> Stop';
            } finally {
                hideLoading();
            }
        }
    });

    // Clear words
    clearBtn.addEventListener('click', async function () {
        clearBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Clearing...';

        try {
            const response = await fetch('/clear_words', {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('Failed to clear words');
            }

            // Clear UI elements
            detectedWordsList = [];
            detectedWords.innerHTML = '';
            fullSentence.innerHTML = '';
            translation.innerHTML = '';

            // Reset speech-related variables
            lastTranslation = "";
            translationStableStartTime = null;
            spokenSentences.clear();

            if (isSpeaking) {
                window.speechSynthesis.cancel();
                isSpeaking = false;
                const indicator = document.getElementById('speechIndicator');
                if (indicator) indicator.remove();
            }

            clearBtn.innerHTML = '<i class="fas fa-check"></i> Cleared';
            setTimeout(() => {
                clearBtn.innerHTML = '<i class="fas fa-eraser"></i> Clear';
            }, 2000);
        } catch (error) {
            alert('Error clearing words: ' + error.message);
            clearBtn.innerHTML = '<i class="fas fa-eraser"></i> Clear';
        }
    });

    // Settings change handlers
    showBoxes.addEventListener('change', function () {
        if (isDetectionRunning) {
            updateVideoFeed();
        }
    });

    enableSpeech.addEventListener('change', function () {
        if (!enableSpeech.checked) {
            window.speechSynthesis.cancel();
            spokenSentences.clear();
            const indicator = document.getElementById('speechIndicator');
            if (indicator) indicator.remove();
            console.log('Text-to-speech disabled');
        } else {
            console.log('Text-to-speech enabled');
            translationStableStartTime = Date.now();

            const testSpeech = () => {
                const testUtterance = new SpeechSynthesisUtterance('Text to speech is now enabled');
                testUtterance.volume = 0.5;
                testUtterance.rate = 1.0;
                window.speechSynthesis.speak(testUtterance);
            };

            // Simple notification
            const notification = document.createElement('div');
            notification.className = 'badge bg-info mb-2';
            notification.innerHTML = '<i class="fas fa-volume-up"></i> Testing speech...';
            // Insert before translation
            if (translation && translation.parentNode) {
                translation.parentNode.insertBefore(notification, translation);
            }

            setTimeout(() => {
                notification.remove();
                testSpeech();
            }, 500);
        }
    });

    // Variables for speech synthesis tracking
    let lastTranslation = "";
    let translationStableStartTime = null;
    let isSpeaking = false;
    const SPEECH_DELAY = 3000;
    let spokenSentences = new Set();

    // Function to speak text actions
    function speakText(text) {
        if (!enableSpeech.checked) return;
        window.speechSynthesis.cancel();

        if (!text || text.trim() === "") return;

        const quoteMatch = text.match(/"([^"]*)"/);

        let quotedText;
        if (!quoteMatch || !quoteMatch[1] || quoteMatch[1].trim() === "") {
            quotedText = text.trim();
        } else {
            quotedText = quoteMatch[1].trim();
        }

        if (spokenSentences.has(quotedText)) return;

        spokenSentences.add(quotedText);
        console.log('New sentence to speak:', quotedText);

        const utterance = new SpeechSynthesisUtterance(quotedText);
        utterance.lang = 'en-US';
        utterance.volume = 1.0;
        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        utterance.onstart = () => {
            isSpeaking = true;
            // Visual indicator
            const speechIndicator = document.createElement('div');
            speechIndicator.id = 'speechIndicator';
            speechIndicator.className = 'badge bg-success mt-2'; // Use bootstrap badge
            speechIndicator.innerHTML = '<i class="fas fa-volume-up"></i> Speaking...';
            if (translation && translation.parentElement) {
                translation.parentElement.appendChild(speechIndicator);
            }
        };

        utterance.onend = () => {
            isSpeaking = false;
            const indicator = document.getElementById('speechIndicator');
            if (indicator) indicator.remove();
        };

        utterance.onerror = (event) => {
            console.error('Speech synthesis error:', event);
            isSpeaking = false;
            const indicator = document.getElementById('speechIndicator');
            if (indicator) indicator.remove();
        };

        window.speechSynthesis.speak(utterance);
    }

    // Update detection output periodically
    function updateDetectionOutput() {
        if (isDetectionRunning) {
            fetch('/get_detected_words')
                .then(response => response.json())
                .then(data => {
                    // Update detected words
                    detectedWords.innerHTML = '';
                    data.words.forEach(word => {
                        if (!detectedWordsList.includes(word)) {
                            detectedWordsList.push(word);
                        }
                        // Always rebuild to show all words
                        const wordElement = document.createElement('span');
                        // Custom styling or bootstrap
                        wordElement.className = 'badge bg-primary me-1 mb-1';
                        wordElement.textContent = word;
                        detectedWords.appendChild(wordElement);
                    });

                    // Update full sentence and translation
                    fullSentence.textContent = data.full_sentence;
                    translation.textContent = data.translation;

                    // Handle text-to-speech
                    const currentTranslation = data.translation;

                    if (currentTranslation && currentTranslation.trim() !== "") {
                        const currentQuoteMatch = currentTranslation.match(/"([^"]*)"/);
                        const lastQuoteMatch = lastTranslation.match(/"([^"]*)"/);

                        const currentQuotedText = currentQuoteMatch ? currentQuoteMatch[1].trim() : currentTranslation.trim();
                        const lastQuotedText = lastQuoteMatch ? lastQuoteMatch[1].trim() : lastTranslation.trim();

                        if (currentQuotedText === lastQuotedText) {
                            if (translationStableStartTime === null) {
                                translationStableStartTime = Date.now();
                            }
                            else if (!isSpeaking && (Date.now() - translationStableStartTime >= SPEECH_DELAY)) {
                                speakText(currentTranslation);
                            }
                        } else {
                            lastTranslation = currentTranslation;
                            translationStableStartTime = Date.now();
                        }
                    } else {
                        lastTranslation = "";
                        translationStableStartTime = null;
                    }
                })
                .catch(error => console.error('Error updating detection output:', error));
        }
    }

    // Check API Key Status
    async function checkAPIKey() {
        const aiStatusText = document.getElementById('aiStatusText');
        const aiStatusIcon = document.getElementById('aiStatus').querySelector('i');

        try {
            const response = await fetch('/api/grok-key');
            const data = await response.json();

            if (response.ok && data.status === 'online') {
                console.log("AI Service: Online");
                if (aiStatusText) aiStatusText.textContent = "AI Online";
                if (aiStatusIcon) aiStatusIcon.className = "fas fa-robot me-2 small text-success";
            } else {
                throw new Error(data.message || "Invalid Status");
            }
        } catch (error) {
            console.warn("AI Service Warning:", error);
            if (aiStatusText) aiStatusText.textContent = "AI Offline (Key Error)";
            if (aiStatusIcon) aiStatusIcon.className = "fas fa-robot me-2 small text-danger";

            // Optional: Show a toast or small alert
            // alert("AI Translation is offline: " + error.message);
        }
    }

    updateButtonStates();
    setInterval(updateDetectionOutput, 1000);
    checkAPIKey(); // Check on load
});