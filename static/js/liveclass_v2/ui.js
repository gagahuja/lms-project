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

    // TEACHER FIRST
    participants.sort(
        (a, b) => {

        if(
            a.uid ===
            state.localUid
        ) return -1;

        if(
            b.uid ===
            state.localUid
        ) return 1;

        return 0;
    });

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

        // FIX SCREEN MAIN
        const mainTile =
            createTile(
                screenUser,
                true
            );

        mainStage
            .appendChild(
                mainTile
            );

        playTrack(
            screenUser
        );

        // GRID:
        // TEACHER FIRST
        participants
        .filter(
            p =>
            !p.isScreen
        )
        .forEach(p => {

            const tile =
                createTile(
                    p,
                    false
                );

            grid
            .appendChild(
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

    const track =

        participant.videoTrack ||

        participant.cameraTrack;

    if(!track)
        return;

    const player =
        document.getElementById(
            `player-${participant.uid}`
        );

    if(!player)
        return;

    track.play(player);
}