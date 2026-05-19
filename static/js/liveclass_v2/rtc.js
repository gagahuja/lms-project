import { state }
from "./state.js";

import {
    renderParticipants
}
from "./ui.js";


export async function initRTC(){

    state.client =
        AgoraRTC.createClient({

            mode: "rtc",
            codec: "vp8"
        });

    registerEvents();
}


export async function joinRoom({

    appId,
    channel,
    token,
    uid,
    username
}){

    const client =
        state.client;

    // JOIN
    await client.join(
        appId,
        channel,
        token,
        uid
    );

    state.localUid =
        uid;

    // LOCAL TRACKS
    const tracks =
        await AgoraRTC
        .createMicrophoneAndCameraTracks();

    state.localTracks.audio =
        tracks[0];

    state.localTracks.video =
        tracks[1];

    // SAVE LOCAL USER
    state.participants[uid] = {

        uid,
        username,

        videoTrack:
            state.localTracks.video,

        audioTrack:
            state.localTracks.audio
    };

    // PUBLISH
    await client.publish([
        state.localTracks.audio,
        state.localTracks.video
    ]);

    renderParticipants();
}


function registerEvents(){

    const client =
        state.client;

    // REMOTE USER JOIN
    client.on(
        "user-published",
        async (
            user,
            mediaType
        ) => {

            await client.subscribe(
                user,
                mediaType
            );

            const uid =
                String(user.uid);

            // CREATE USER
            if(
                !state.participants[uid]
            ){

                state.participants[
                    uid
                ] = {

                    uid,

                    username:
                        "User",

                    videoTrack:
                        null,

                    audioTrack:
                        null
                };
            }

            // VIDEO
            if(
                mediaType ===
                "video"
            ){

                state
                .participants[
                    uid
                ]
                .videoTrack =
                    user.videoTrack;
            }

            // AUDIO
            if(
                mediaType ===
                "audio"
            ){

                state
                .participants[
                    uid
                ]
                .audioTrack =
                    user.audioTrack;

                user.audioTrack.play();
            }

            renderParticipants();
        }
    );

    // USER LEFT
    client.on(
        "user-left",
        user => {

            delete state
            .participants[
                user.uid
            ];

            renderParticipants();
        }
    );

    // AUDIO LEVEL DETECTION
    client.enableAudioVolumeIndicator();

    client.on(
        "volume-indicator",
        volumes => {

        let loudest = null;

        let highest = 0;

        volumes.forEach(v => {

            if(
                v.level > highest
            ){

                highest =
                    v.level;

                loudest =
                    String(v.uid);
            }
        });

        // SPEAKER THRESHOLD
        if(
            highest > 5 &&
            loudest
        ){

            const now =
                Date.now();

            // ANTI-FLICKER
            if(

                state.activeSpeaker
                !== loudest &&

                now -
                state
                .lastSpeakerChange
                > 500

            ){

                state
                .activeSpeaker =
                    loudest;

                state
                .lastSpeakerChange =
                    now;

                renderParticipants();
            }
        }
    });
}