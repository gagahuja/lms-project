import {
    state
}
from "./state.js";

// PREVENT LOOP
let isRendering =
    false;
export function renderParticipants(){

    if(isRendering)
        return;

    isRendering = true;

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

    // CLEAR ONLY
    // WHEN NOT SHARE

    if(
        !state.shareMode
    ){

        mainStage
            .innerHTML = "";

        grid
            .innerHTML = "";
    }

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

        if(
            sharer &&
            sharer.screenTrack
        ){

            // CREATE SCREEN ONLY ONCE
            if(
                !document.getElementById(
                    "player-screen"
                )
            ){

                mainStage.innerHTML =
                    "";

                const screenTile =
                    createTile({

                        uid:
                            "screen",

                        username:
                            "Screen Share"

                    }, true);

                mainStage.appendChild(
                    screenTile
                );

                setTimeout(() => {

                    playTrack(

                        sharer
                        .screenTrack,

                        "player-screen"
                    );

                }, 100);
            }
        }

        // RESET GRID
        grid.innerHTML = "";

        // SHOW PARTICIPANTS
        participants.forEach(p => {

            const tile =
                createTile(
                    p,
                    false
                );

            grid.appendChild(
                tile
            );

            playTrack(

                p.cameraTrack,

                `player-${p.uid}`
            );
        });

        isRendering =
            false;

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
    isRendering = false;
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