import { appState } from "./state.js";
import { renderLayout } from "./layout.js";

export let client = null;

export let localTracks = {
    audio: null,
    video: null
};

export let screenTrack = null;

export async function initRTC(APP_ID){

    client = AgoraRTC.createClient({
        mode: "rtc",
        codec: "vp8"
    });

    registerRTCEvents();
}

export async function joinRoom({

    appId,
    channel,
    token,
    uid,
    username

}){

    await client.join(
        appId,
        channel,
        token,
        uid
    );

    appState.localUser = uid;

    // CREATE TRACKS
    localTracks.audio =
        await AgoraRTC.createMicrophoneAudioTrack();

    localTracks.video =
        await AgoraRTC.createCameraVideoTrack();

    // SAVE PARTICIPANT
    appState.participants[uid] = {

        uid,
        name: username,

        videoTrack: localTracks.video,
        audioTrack: localTracks.audio,

        isMuted: false,
        isCameraOff: false,
        isSpeaking: false,
        handRaised: false
    };

    // PUBLISH
    await client.publish([
        localTracks.audio,
        localTracks.video
    ]);

    renderLayout();
}


function registerRTCEvents(){

    client.on(
        "user-published",
        async (user, mediaType) => {

            await client.subscribe(
                user,
                mediaType
            );

            let uid = String(user.uid);

            // CREATE PARTICIPANT
            if(!appState.participants[uid]){

                appState.participants[uid] = {

                    uid,

                    name: "User",

                    videoTrack: null,
                    audioTrack: null,

                    isMuted: false,
                    isCameraOff: false,
                    isSpeaking: false,
                    handRaised: false
                };
            }

            // VIDEO
            if(mediaType === "video"){

                appState
                    .participants[uid]
                    .videoTrack = user.videoTrack;
            }

            // AUDIO
            if(mediaType === "audio"){

                appState
                    .participants[uid]
                    .audioTrack = user.audioTrack;

                user.audioTrack.play();
            }

            renderLayout();
        }
    );

    // USER LEFT
    client.on("user-left", user => {

        let uid = String(user.uid);

        delete appState.participants[uid];

        renderLayout();
    });

    // SPEAKER DETECTION
    client.enableAudioVolumeIndicator();

    client.on(
        "volume-indicator",
        volumes => {

            let loudest = null;

            let highest = 0;

            volumes.forEach(v => {

                if(v.level > highest){

                    highest = v.level;

                    loudest = String(v.uid);
                }
            });

            if(highest > 10){

                appState.activeSpeaker =
                    loudest;

                renderLayout();
            }
        }
    );
}