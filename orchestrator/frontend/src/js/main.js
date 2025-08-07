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

    const ui = new firebaseui.auth.AuthUI(auth);
    let isUpgrading = false;

    auth.onAuthStateChanged(async user => {
        if (user) {
            showChat(user.isAnonymous);
            initializeApp(user);
        } else {
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

    signOutButton.addEventListener('click', () => {
        auth.signOut();
    });

    loginButton.addEventListener('click', () => {
        isUpgrading = true;
        auth.signOut();
    });

    async function initializeApp(user) {
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

        let rundownSystem = await getRundownSystem();
        updateRundownSlider(rundownSystem);

        rundownSlider.addEventListener('change', async () => {
            rundownSystem = rundownSlider.checked ? 'sofie' : 'cuez';
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
        });


        let api;
        let isAudio = false;
        let currentMessageId = null;

        function getToken() {
            return user.getIdToken();
        }

        function initializeConnection(audioEnabled) {
            if (api) {
                api.disconnect();
            }

            isAudio = audioEnabled;

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
                    console.log(`WebSocket connected in ${isAudio ? 'audio' : 'text'} mode.`);
                    sendButton.disabled = false;
                    micButton.disabled = false;
                },
                onDisconnect: () => {
                    console.log('WebSocket disconnected.');
                    sendButton.disabled = true;
                    micButton.disabled = true;
                },
            }, isAudio, user.uid, getToken);
        }

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

        // Initial connection in text mode
        initializeConnection(false);

        sendButton.addEventListener('click', sendTextMessage);

        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendTextMessage();
            }
        });

        micButton.addEventListener('click', () => {
            if (!isAudio) {
                initializeConnection(true);
                setMicButtonRecording(true);
                initAudio((pcmData) => {
                    if (api) {
                        api.sendMessage({
                            mime_type: 'audio/pcm',
                            data: pcmData,
                        });
                    }
                });
            } else {
                stopAudioRecording();
                setMicButtonRecording(false);
                initializeConnection(false);
            }
        });
    }
});