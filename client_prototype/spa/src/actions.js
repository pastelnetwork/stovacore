import * as actionTypes from './actionTypes';

export const saveAPIToken = (token) => ({
    type: actionTypes.SAVE_API_TOKEN,
    token
});


export const startAjax = (entity) => ({
   type: actionTypes.START_AJAX,
   entity
});

export const stopAjax = (entity) => ({
   type: actionTypes.STOP_AJAX,
   entity
});
