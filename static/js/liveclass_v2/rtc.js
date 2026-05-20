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

    await client.join(
        appId,
        channel,
        token,
        uid
    );

    state.localUid =
        uid;

    const tracks =
        await AgoraRTC
        .createMicrophoneAndCameraTracks();

    state.localTracks.audio =
        tracks[0];

    state.localTracks.video =
        tracks[1];

    state.participants[uid] = {

        uid,

        username,

        videoTrack:
            state.localTracks.video,

        audioTrack:
            state.localTracks.audio,

        isScreen:
            false
    };

    await client.publish([

        state.localTracks.audio,
        state.localTracks.video
    ]);

    renderParticipants();
}


export async function startScreenShare(){

    try{

        const tracks =
            await AgoraRTC
            .createScreenVideoTrack();

        state.screenTrack =
            Array.isArray(tracks)
            ? tracks[0]
            : tracks;

        // CAMERA OFF
        await state.client
            .unpublish(
                state
                .localTracks
                .video
            );

        // PUBLISH SCREEN
        await state.client
            .publish(
                state
                .screenTrack
            );

        // SCREEN USER
        state.participants[
            "screen"
        ] = {

            uid: "screen",

            username:
                "Screen",

            videoTrack:
                state.screenTrack,

            isScreen:
                true
        };

        state.screenShare = {

            active: true,

            owner:
                state.localUid
        };

        renderParticipants();

        state.screenTrack.on(
            "track-ended",
            async () => {

                await stopScreenShare();
            }
        );

    }catch(err){

        console.error(
            err
        );
    }
}


export async function stopScreenShare(){

    if(
        !state.screenTrack
    ) return;

    await state.client
        .unpublish(
            state.screenTrack
        );

    state.screenTrack
        .close();

    state.screenTrack =
        null;

    delete state
        .participants[
            "screen"
        ];

    await state.client
        .publish(
            state
            .localTracks
            .video
        );

    state.screenShare = {

        active:false,

        owner:null
    };

    renderParticipants();
}


function registerEvents(){

    const client =
        state.client;


    client.on(
        "user-published",
        async (
            user,
            mediaType
        ) => {

            await client
                .subscribe(
                    user,
                    mediaType
                );

            const uid =
                String(
                    user.uid
                );

            if(
                !state
                .participants[
                    uid
                ]
            ){

                state
                .participants[
                    uid
                ] = {

                    uid,

                    username:
                        "User",

                    cameraTrack:
                        null,

                    screenTrack:
                        null,

                    audioTrack:
                        null
                };
            }

            if(
                mediaType ===
                "video"
            ){

                const trackId =
                    user.videoTrack
                    ?._mediaStreamTrack
                    ?.id || "";

                // =========================
                // SCREEN SHARE TRACK
                // =========================

                if(
                    trackId.includes(
                        "video"
                    )
                ){

                    state.participants[
                        "screen-share"
                    ] = {

                        uid:
                            "screen-share",

                        username:
                            "Screen Share",

                        videoTrack:
                            user.videoTrack,

                        isScreen:
                            true
                    };

                    state.screenShare = {

                        active:true,

                        owner:uid
                    };

                }else{

                    // =========================
                    // NORMAL CAMERA
                    // =========================

                    state
                    .participants[
                        uid
                    ]
                    .cameraTrack =
                        user.videoTrack;
                }

                renderParticipants();
            }

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

                user
                .audioTrack
                .play();
            }

            renderParticipants();
        }
    );


    client.on(
        "user-left",
        user => {

            delete state
                .participants[
                    user.uid
                ];

            delete state
                .participants[
                    "screen-share"
                ];

            state.screenShare = {

                active:false,

                owner:null
            };

            renderParticipants();
        }
    );


    client.enableAudioVolumeIndicator();

    client.on(
        "volume-indicator",
        volumes => {

        // DISABLE
        // DURING SHARE
        if(
            state
            .screenShare
            .active
        ) return;

        let loudest =
            null;

        let highest =
            0;

        volumes.forEach(v => {

            if(
                v.level >
                highest
            ){

                highest =
                    v.level;

                loudest =
                    String(
                        v.uid
                    );
            }
        });

        if(
            highest > 5 &&
            loudest
        ){

            const now =
                Date.now();

            if(

                state
                .activeSpeaker
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