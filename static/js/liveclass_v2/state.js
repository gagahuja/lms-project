export const state = {

    client: null,

    localTracks: {

        audio: null,
        video: null
    },

    screenTrack: null,

    localUid: null,

    participants: {},

    activeSpeaker: null,

    lastSpeakerChange: 0,

    screenShare: {

        active: false,

        owner: null
    }
};