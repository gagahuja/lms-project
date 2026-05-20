import { state }
from "./state.js";

import {
    renderParticipants
}
from "./ui.js";


export async function initRTC(){

    state.client =
        AgoraRTC.createClient({

            mode:"rtc",
            codec:"vp8"
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
        String(uid);

    const tracks =
        await AgoraRTC
        .createMicrophoneAndCameraTracks();

    state.localTracks
        .audio =
            tracks[0];

    state.localTracks
        .camera =
            tracks[1];

    state.participants[
        uid
    ] = {

        uid:
            String(uid),

        username,

        cameraTrack:
            state
            .localTracks
            .camera,

        screenTrack:
            null,

        audioTrack:
            state
            .localTracks
            .audio
    };

    await client.publish([

        state.localTracks
            .audio,

        state.localTracks
            .camera
    ]);

    renderParticipants();
}


export async function startScreenShare(){

    try{

        const screenTracks =
            await AgoraRTC
            .createScreenVideoTrack({

                encoderConfig:
                    "1080p_1"
            });

        // HANDLE ARRAY
        const screenTrack =

            Array.isArray(
                screenTracks
            )

            ? screenTracks[0]

            : screenTracks;

        state.localTracks
            .screen =
                screenTrack;

        // PUBLISH
        await state.client
            .publish(
                screenTrack
            );

        // SHARE MODE
        state.shareMode =
            true;

        state.sharedScreenUid =
            state.localUid;

        // SAVE SCREEN
        state.participants[
            state.localUid
        ]
        .screenTrack =
            screenTrack;

        renderParticipants();

        // AUTO STOP
        screenTrack.on(

            "track-ended",

            async () => {

                await
                stopScreenShare();
            }
        );

    }catch(err){

        console.error(
            "SCREEN ERROR",
            err
        );
    }
}


export async function stopScreenShare(){

    const screen =
        state
        .localTracks
        .screen;

    if(!screen)
        return;

    await state.client
        .unpublish(
            screen
        );

    screen.close();

    state.localTracks
        .screen = null;

    state.shareMode =
        false;

    state.sharedScreenUid =
        null;

    if(
        state.participants[
            state.localUid
        ]
    ){

        state.participants[
            state.localUid
        ]
        .screenTrack =
            null;
    }

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

            const id =
                user.videoTrack
                ?._mediaStreamTrack
                ?.id || "";

            // SCREEN
            if(
                id.includes(
                    "video"
                )
            ){

                state
                .participants[
                    uid
                ]
                .screenTrack =
                    user.videoTrack;

                state.shareMode =
                    true;

                state.sharedScreenUid =
                    uid;

            }else{

                // CAMERA
                state
                .participants[
                    uid
                ]
                .cameraTrack =
                    user.videoTrack;
            }
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
    });


    client.on(

        "user-left",

        user => {

        const uid =
            String(
                user.uid
            );

        delete state
            .participants[
                uid
            ];

        state.shareMode =
            false;

        state.sharedScreenUid =
            null;

        renderParticipants();
    });


    client.enableAudioVolumeIndicator();

    client.on(

        "volume-indicator",

        volumes => {

        // DISABLE
        // DURING SHARE
        if(
            state.shareMode
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

                loudest !==
                state
                .activeSpeaker &&

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