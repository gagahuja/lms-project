import {
    state
}
from "./state.js";


export function renderParticipants(){

    const container =
        document.getElementById(
            "video-container"
        );

    if(!container)
        return;

    container.innerHTML = "";

    const participants =
        Object.values(
            state.participants
        );

    participants.forEach(
        participant => {

        const tile =
            document.createElement(
                "div"
            );

        tile.className =
            "video-tile";

        tile.innerHTML = `

            <div
                id="player-${participant.uid}"
                class="video-player">
            </div>

            <div class="video-name">

                ${
                    participant
                    .username
                }

            </div>
        `;

        container
            .appendChild(tile);

        if(
            participant
            .videoTrack
        ){

            participant
            .videoTrack
            .play(
                `player-${participant.uid}`
            );
        }
    });
}