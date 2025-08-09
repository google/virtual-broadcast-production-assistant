import 'firebaseui/dist/firebaseui.css';
import * as firebaseui from 'firebaseui';
import { GoogleAuthProvider, signInAnonymously } from 'firebase/auth';
import { auth, db } from './firebase.js';
import { doc, getDoc, setDoc } from "firebase/firestore";
import {
    messageInput,
    sendButton,
    micButton,
    signOutButton,
    loginButton,
    rundownSlider,
    addMessage,
    initUI,
    setMicButtonRecording,
    showLogin,
    showChat,
    updateRundownSlider,
} from './ui.js';
import {
    initApi
} from './api.js';
import {
    initAudio,
    stopAudioRecording,
    playAudio,
    stopAudioPlayback,
} from './audio.js';

document.addEventListener('DOMContentLoaded', () => {
    initUI();

    // --- State Management ---
    let api = null;
    let currentUser = null;
    let isUpgrading = false;
    const ui = new firebaseui.auth.AuthUI(auth);

    // --- Event Listeners (Initialized once) ---
    signOutButton.addEventListener('click', () => {
        auth.signOut();
    });

    loginButton.addEventListener('click', () => {
        isUpgrading = true;
        auth.signOut();
    });

    function sendTextMessage() {
        const message = messageInput.value.trim();
        if (message && api) {
            addMessage(message, 'user');
            api.sendMessage({
                mime_type: 'text/plain',
                data: message,
            });
            messageInput.value = '';
        }
    }

    sendButton.addEventListener('click', sendTextMessage);

    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendTextMessage();
        }
    });

    micButton.addEventListener('click', () => {
        // The `isAudio` property is added to the api object from api.js
        if (api && api.isAudio) {
            stopAudioRecording();
            setMicButtonRecording(false);
            initializeConnection(false); // Re-init in text mode
        } else {
            initializeConnection(true); // Re-init in audio mode
            setMicButtonRecording(true);
            initAudio((pcmData) => {
                if (api) {
                    api.sendMessage({
                        mime_type: 'audio/pcm',
                        data: pcmData,
                    });
                }
            });
        }
    });

    rundownSlider.addEventListener('change', () => {
        handleRundownChange();
    });

    auth.onAuthStateChanged(async user => {
        currentUser = user; // Set the current user for the module
        if (user) {
            showChat(user.isAnonymous);
            await initializeUserSession(user);
        } else {
            if (api) {
                api.disconnect();
                api = null;
            }
            if (isUpgrading) {
                isUpgrading = false;
                showLogin();
                ui.start('#firebaseui-auth-container', {
                    signInOptions: [
                        GoogleAuthProvider.PROVIDER_ID
                    ],
                    callbacks: {
                        signInSuccessWithAuthResult: function (authResult, redirectUrl) {
                            // User successfully signed in.
                            // Return type determines whether we continue the redirect automatically
                            // or whether we leave that to developer to handle.
                            return false;
                        }
                    }
                });
            } else {
                signInAnonymously(auth).catch(error => {
                    console.error("Anonymous sign-in failed:", error);
                });
            }
        }
    });

    // --- App Initialization Logic ---

    /**
     * Sets up the user's session, fetching preferences and establishing the initial
     * WebSocket connection.
     * @param {User} user The authenticated Firebase user.
     */
    async function initializeUserSession(user) {
        const userDocRef = doc(db, "user_preferences", user.uid);

        async function getRundownSystem() {
            try {
                const docSnap = await getDoc(userDocRef);
                if (docSnap.exists()) {
                    return docSnap.data().rundown_system;
                } else {
                    await setDoc(userDocRef, { rundown_system: "cuez" });
                    return "cuez";
                }
            } catch (error) {
                console.error("Error getting rundown system preference:", error);
                return "cuez";
            }
        }

        const rundownSystem = await getRundownSystem();
        updateRundownSlider(rundownSystem);

        // Initial connection in text mode
        initializeConnection(false);
    }

    /**
     * Handles changes to the rundown system, persisting the preference
     * and re-initializing the connection.
     */
    async function handleRundownChange() {
        if (!currentUser) return;
        const userDocRef = doc(db, "user_preferences", currentUser.uid);
        const rundownSystem = rundownSlider.checked ? 'sofie' : 'cuez';
        updateRundownSlider(rundownSystem);
        try {
            await setDoc(userDocRef, { rundown_system: rundownSystem }, { merge: true });
            // Reset chat
            document.getElementById('chat-messages').innerHTML = '';
            addMessage(`Agent reconfigured for ${rundownSystem.toUpperCase()}`, 'agent');
            initializeConnection(false);
        } catch (error) {
            console.error("Error setting rundown system preference:", error);
        }
    }

    /**
     * Establishes or re-establishes the WebSocket connection.
     * @param {boolean} audioEnabled Whether to connect in audio or text mode.
     */
    function initializeConnection(audioEnabled) {
        if (!currentUser) {
            console.log("Cannot initialize connection, no user.");
            return;
        }
        if (api) {
            api.disconnect();
        }

        let currentMessageId = null;

        function getToken() {
            return currentUser.getIdToken();
        }

        api = initApi({
            onMessage: (message) => {
                if (message.turn_complete) {
                    currentMessageId = null;
                    return;
                }

                if (message.interrupted) {
                    stopAudioPlayback();
                    return;
                }

                if (message.mime_type === 'audio/pcm') {
                    playAudio(message.data);
                }

                if (message.mime_type === 'text/plain') {
                    if (currentMessageId === null) {
                        currentMessageId = `agent-message-${Date.now()}`;
                        addMessage('', 'agent', currentMessageId);
                    }
                    const messageElement = document.getElementById(currentMessageId);
                    if (messageElement) {
                        messageElement.textContent += message.data;
                    }
                }
            },
            onConnect: () => {
                console.log(`WebSocket connected in ${audioEnabled ? 'audio' : 'text'} mode.`);
                sendButton.disabled = false;
                micButton.disabled = false;
            },
            onDisconnect: () => {
                console.log('WebSocket disconnected.');
                sendButton.disabled = true;
                micButton.disabled = true;
            },
        }, audioEnabled, currentUser.uid, getToken);
    }
});
