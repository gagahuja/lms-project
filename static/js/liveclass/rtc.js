import { appState } from "./state.js?v=3";
import { renderLayout } from "./layout.js?v=3";

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

                    // CAMERA RETURNED
                    if(
                        appState.screenShare.owner === uid
                    ){

                        let label =
                            user.videoTrack
                            ._mediaStreamTrack
                            ?.label || "";

                        // NOT SCREEN ANYMORE
                        if(
                            !label
                            .toLowerCase()
                            .includes("screen")
                        ){

                            appState.screenShare = {

                                active:false,

                                owner:null,

                                track:null
                            };
                        }
                    }

                // DETECT REMOTE SCREEN SHARE
                if(user.videoTrack){

                    let trackLabel =
                        user.videoTrack
                        ._mediaStreamTrack
                        ?.label || "";

                    // SCREEN TRACK
                    if(
                        trackLabel
                        .toLowerCase()
                        .includes("screen")
                    ){

                        appState.screenShare = {

                            active: true,

                            owner: uid,

                            track: user.videoTrack
                        };
                    }
                }
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

        // RESET SCREEN SHARE
        if(
            appState.screenShare.owner === uid
        ){

            appState.screenShare = {

                active:false,

                owner:null,

                track:null
            };
        }

        renderLayout();
    });

    // SPEAKER DETECTION
    let lastSpeaker = null;

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

            // FAST SWITCH
            if(
                highest > 3 &&
                loudest &&
                loudest !== lastSpeaker
            ){

                lastSpeaker = loudest;

                appState.activeSpeaker =
                    loudest;

                // DON'T RERENDER MAIN SCREEN
                // DURING SCREEN SHARE

                if(!appState.screenShare.active){

                    requestAnimationFrame(() => {

                        renderLayout();
                    });
                }
            }
        }
    );
}


export async function startScreenShare(){

    try{

        // CREATE SCREEN TRACK
        screenTrack =
            await AgoraRTC
            .createScreenVideoTrack();

        // UNPUBLISH CAMERA VIDEO
        await client.unpublish(
            localTracks.video
        );

        // PUBLISH SCREEN
        await client.publish(
            screenTrack
        );

        // SAVE STATE
        appState.screenShare = {

            active: true,

            owner: appState.localUser,

            track: screenTrack
        };

        renderLayout();

        // AUTO STOP
        screenTrack.on(
            "track-ended",
            async () => {

                await stopScreenShare();
            }
        );

    }catch(err){

        console.error(
            "Screen share error:",
            err
        );
    }
}

export async function stopScreenShare(){

    try{

        if(!screenTrack)
            return;

        // UNPUBLISH SCREEN
        await client.unpublish(
            screenTrack
        );

        // CLOSE TRACK
        screenTrack.close();

        screenTrack = null;

        // REPUBLISH CAMERA
        await client.publish(
            localTracks.video
        );

        // RESET STATE
        appState.screenShare = {

            active: false,

            owner: null,

            track: null
        };

        renderLayout();

    }catch(err){

        console.error(
            "Stop share error:",
            err
        );
    }
}