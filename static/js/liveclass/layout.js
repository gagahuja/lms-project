import { appState } from "./state.js";

export function renderLayout(){

    let mainStage =
        document.getElementById("main-stage");

    let videoGrid =
        document.getElementById("video-grid");

    if(!mainStage || !videoGrid) return;

    // CLEAR UI
    mainStage.innerHTML = "";

    videoGrid.innerHTML = "";

    // ALL PARTICIPANTS
    let participants =
        Object.values(appState.participants);

    if(participants.length === 0) return;

    // DETERMINE MAIN USER
    let mainParticipant = null;

    // PRIORITY 1 — SCREEN SHARE
    if(
        appState.screenShare.active &&
        appState.screenShare.owner
    ){

        mainParticipant =
            appState.participants[
                appState.screenShare.owner
            ];

    // PRIORITY 2 — SPOTLIGHT
    } else if(appState.spotlightUser){

        mainParticipant =
            appState.participants[
                appState.spotlightUser
            ];

    // PRIORITY 3 — PINNED
    } else if(appState.pinnedUser){

        mainParticipant =
            appState.participants[
                appState.pinnedUser
            ];

    // PRIORITY 4 — ACTIVE SPEAKER
    } else if(appState.activeSpeaker){

        mainParticipant =
            appState.participants[
                appState.activeSpeaker
            ];
    }

    // FALLBACK
    if(!mainParticipant){

        mainParticipant = participants[0];
    }

    // RENDER MAIN STAGE
    let mainTile =
        createVideoTile(
            mainParticipant,
            true
        );

    mainStage.appendChild(mainTile);

    // PLAY VIDEO
    playParticipantVideo(
        mainParticipant,
        mainTile
    );

    // RENDER GRID
    participants.forEach(p => {

        if(p.uid === mainParticipant.uid)
            return;

        let tile =
            createVideoTile(p, false);

        videoGrid.appendChild(tile);

        playParticipantVideo(p, tile);
    });

    // SCREEN SHARE
    if(appState.screenShare.active){

        renderScreenShare();
    }
}


function createVideoTile(
    participant,
    isMain
){

    let tile =
        document.createElement("div");

    tile.className =
        isMain
        ? "video-tile main-tile"
        : "video-tile grid-tile";

    tile.id =
        "tile-" + participant.uid;

    tile.innerHTML = `

        <div
            class="video-player"
            id="player-${participant.uid}">
        </div>

        <div class="video-info">

            ${participant.name}

        </div>
    `;

    return tile;
}


function playParticipantVideo(
    participant,
    tile
){

    if(
        participant.videoTrack
    ){

        participant.videoTrack.play(
            "player-" + participant.uid
        );
    }
}



function renderScreenShare(){

    let mainStage =
        document.getElementById("main-stage");

    let screenContainer =
        document.createElement("div");

    screenContainer.id =
        "screen-share-container";

    mainStage.innerHTML = "";

    screenContainer.innerHTML = `

        <div
            id="screen-player"
            class="screen-player">
        </div>

        <div class="screen-label">
            Screen Share
        </div>
    `;

    mainStage.appendChild(
        screenContainer
    );

    appState.screenShare.track.play(
        "screen-player"
    );
}