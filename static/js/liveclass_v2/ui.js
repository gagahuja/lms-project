import {
    state
}
from "./state.js";


export function renderParticipants(){

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


    // ==========================
    // SCREEN SHARE MODE
    // ==========================

    const screenUser =
        participants.find(
            p => p.isScreen
        );

    if(screenUser){

        // FIX SCREEN
        const screenTile =
            createTile(
                screenUser,
                true
            );

        mainStage
            .appendChild(
                screenTile
            );

        playTrack(
            screenUser
        );

        // EVERYONE IN GRID
        participants.forEach(
            p => {

            if(
                p.isScreen
            ) return;

            const tile =
                createTile(
                    p,
                    false
                );

            grid.appendChild(
                tile
            );

            playTrack(p);
        });

        // VERY IMPORTANT
        return;
    }


    // ==========================
    // NORMAL SPEAKER MODE
    // ==========================

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
                state.activeSpeaker
            ];
    }

    if(!mainUser){

        mainUser =
            participants[0];
    }

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
    );

    participants.forEach(
        p => {

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
            p
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
    participant
){

    if(
        !participant.videoTrack
    ) return;

    const player =
        document.getElementById(
            `player-${participant.uid}`
        );

    if(!player)
        return;

    try{

        participant
            .videoTrack
            .play(player);

    }catch(err){

        console.error(
            "PLAY ERROR",
            err
        );
    }
}