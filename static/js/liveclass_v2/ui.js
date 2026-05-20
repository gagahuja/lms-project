import {
    state
}
from "./state.js";


export function renderParticipants(){

    console.log(
        "RENDER UI",
        Date.now()
    );

    const mainStage =
        document.getElementById(
            "main-stage"
        );

    const grid =
        document.getElementById(
            "video-grid"
        );

    if(
        !mainStage ||
        !grid
    ) return;

    // RESET UI
    mainStage.innerHTML =
        "";

    grid.innerHTML =
        "";

    const participants =
        Object.values(
            state.participants
        );

    if(
        participants.length
        === 0
    ) return;


    // ==================================
    // SCREEN SHARE MODE
    // ==================================

    if(
        state.shareMode &&
        state.sharedScreenUid
    ){

        const sharer =
            state.participants[
                state
                .sharedScreenUid
            ];

        // FIXED MAIN SCREEN
        if(
            sharer &&
            sharer.screenTrack
        ){

            const screenTile =
                createTile({

                    uid:
                        "screen",

                    username:
                        "Screen Share"

                }, true);

            mainStage
                .appendChild(
                    screenTile
                );

            setTimeout(() => {

                playTrack(

                    sharer
                    .screenTrack,

                    "player-screen"
                );
                return;

            }, 100);
        }

        // TEACHER FIRST
        const sorted =
            participants.sort(
                (a, b) => {

                // sharer first
                if(
                    a.uid ===
                    state
                    .sharedScreenUid
                ) return -1;

                if(
                    b.uid ===
                    state
                    .sharedScreenUid
                ) return 1;

                return 0;
            });

        // GRID
        sorted.forEach(p => {

            const tile =
                createTile(
                    p,
                    false
                );

            grid
                .appendChild(
                    tile
                );

            playTrack(

                p.cameraTrack,

                `player-${p.uid}`
            );
        });

        // LOCK SHARE MODE
        return;
    }


    // ==================================
    // NORMAL MODE
    // ==================================

    let mainUser =
        null;

    if(
        state.activeSpeaker &&
        state.participants[
            state.activeSpeaker
        ]
    ){

        mainUser =
            state.participants[
                state
                .activeSpeaker
            ];
    }

    // FALLBACK
    if(!mainUser){

        mainUser =
            participants[0];
    }

    // MAIN TILE
    const mainTile =
        createTile(
            mainUser,
            true
        );

    mainStage
        .appendChild(
            mainTile
        );

    playTrack(

        mainUser
        .cameraTrack,

        `player-${mainUser.uid}`
    );

    // GRID
    participants.forEach(p => {

        if(
            p.uid ===
            mainUser.uid
        ) return;

        const tile =
            createTile(
                p,
                false
            );

        grid
            .appendChild(
                tile
            );

        playTrack(

            p.cameraTrack,

            `player-${p.uid}`
        );
    });
}


function createTile(
    participant,
    isMain
){

    const tile =
        document
        .createElement(
            "div"
        );

    tile.className =
        isMain
        ? "main-video-tile"
        : "grid-video-tile";

    tile.innerHTML = `

        <div
            id="player-${participant.uid}"
            class="video-player">
        </div>

        <div
            class="video-name">

            ${
                participant
                .username
            }

        </div>
    `;

    return tile;
}


function playTrack(
    track,
    playerId
){

    if(!track)
        return;

    const player =
        document
        .getElementById(
            playerId
        );

    if(!player)
        return;

    try{

        track.play(
            player
        );

    }catch(err){

        console.error(
            err
        );
    }
}