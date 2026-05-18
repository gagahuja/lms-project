import { appState } from "./state.js?v=3";

export function renderLayout(){

    const mainStage =
        document.getElementById("main-stage");

    const videoGrid =
        document.getElementById("video-grid");

    if(!mainStage || !videoGrid)
        return;

    // DON'T RESET SCREEN SHARE
    if(!appState.screenShare.active){

        mainStage.innerHTML = "";
    }

    videoGrid.innerHTML = "";

    const participants =
        Object.values(appState.participants);

    if(participants.length === 0)
        return;

    let mainParticipant = null;

    // SCREEN SHARE PRIORITY
    if(
        appState.screenShare.active &&
        appState.screenShare.owner
    ){

        // FIXED MAIN SCREEN
        renderScreenShare(mainStage);

        // ALL USERS IN GRID
        participants.forEach(p => {

            const tile =
                createVideoTile(
                    p,
                    false
                );

            videoGrid.appendChild(tile);

            playVideo(p);
        });

        // VERY IMPORTANT
        // STOP SPEAKER SWITCHING
        return;
    }

    // ACTIVE SPEAKER
    if(appState.activeSpeaker){

        mainParticipant =
            appState.participants[
                appState.activeSpeaker
            ];
    }

    // FALLBACK
    if(!mainParticipant){

        mainParticipant = participants[0];
    }

    // MAIN VIDEO
    const mainTile =
        createVideoTile(mainParticipant, true);

    mainStage.appendChild(mainTile);

    playVideo(mainParticipant);

    // GRID
    participants.forEach(p => {

        if(p.uid === mainParticipant.uid)
            return;

        const tile =
            createVideoTile(p, false);

        videoGrid.appendChild(tile);


        playVideo(p);
    });
}

function createVideoTile(
    participant,
    isMain
){

    const tile =
        document.createElement("div");

    tile.className =
        isMain
        ? "main-video-tile"
        : "grid-video-tile";

    const player =
        document.createElement("div");

    player.id =
        `player-${participant.uid}`;

    player.className =
        "video-player";

    const label =
        document.createElement("div");

    label.className =
        "video-label";

    label.innerText =
        participant.name || "User";

    tile.appendChild(player);

    tile.appendChild(label);

    return tile;
}

function playVideo(participant){

    if(!participant.videoTrack)
        return;

    const container =
        document.getElementById(
            `player-${participant.uid}`
        );

    if(!container)
        return;

    participant.videoTrack.play(container);
}

function renderScreenShare(mainStage){

    // RESET MAIN
    mainStage.innerHTML = "";

    // WRAPPER
    const wrapper =
        document.createElement("div");

    wrapper.className =
        "screen-wrapper";

    // SCREEN PLAYER
    const screenPlayer =
        document.createElement("div");

    screenPlayer.id =
        "screen-player";

    screenPlayer.className =
        "screen-player";

    wrapper.appendChild(
        screenPlayer
    );

    mainStage.appendChild(
        wrapper
    );

    // PLAY TRACK
    if(appState.screenShare.track){

        appState.screenShare.track.play(
            screenPlayer
        );
    }
}
