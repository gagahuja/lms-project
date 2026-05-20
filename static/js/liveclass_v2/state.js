export const state = {

    client: null,

    localUid: null,

    localTracks: {

        audio: null,
        camera: null,
        screen: null
    },

    participants: {},

    activeSpeaker: null,

    lastSpeakerChange: 0,

    shareMode: false,

    sharedScreenUid: null
};