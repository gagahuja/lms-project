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

    // RESET UI
    mainStage.innerHTML = "";
    grid.innerHTML = "";

    const participants =
        Object.values(
            state.participants
        );

    if(
        participants.length === 0
    ) return;

    // ACTIVE SPEAKER
    let mainUser = null;

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

    // FALLBACK
    if(!mainUser){

        mainUser =
            participants[0];
    }

    // MAIN TILE
    const mainTile =
        createVideoTile(
            mainUser,
            true
        );

    mainStage.appendChild(
        mainTile
    );

    playTrack(mainUser);

    // GRID USERS
    participants.forEach(
        participant => {

        if(
            participant.uid ===
            mainUser.uid
        ) return;

        const tile =
            createVideoTile(
                participant,
                false
            );

        grid.appendChild(
            tile
        );

        playTrack(
            participant
        );
    });
}


function createVideoTile(
    participant,
    isMain
){

    const tile =
        document.createElement(
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

        <div class="video-name">

            ${participant.username}

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

    participant
        .videoTrack
        .play(
            `player-${participant.uid}`
        );
}