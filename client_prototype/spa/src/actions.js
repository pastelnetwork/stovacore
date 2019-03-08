import * as actionTypes from './actionTypes';
import * as ajaxEntities from './ajaxEntities';
import axios from 'axios';
import * as settings from './settings';
import history from './history';

export const saveAPIToken = (token) => ({
    type: actionTypes.SAVE_API_TOKEN,
    token
});

export const forgetAPIToken = () => saveAPIToken('');

export const startAjax = (entity) => ({
    type: actionTypes.START_AJAX,
    entity
});

export const stopAjax = (entity) => ({
    type: actionTypes.STOP_AJAX,
    entity
});

export const resetStore = () => ({
    type: actionTypes.RESET_STORE
});

export const saveUserProfile = (profile) => ({
    type: actionTypes.SAVE_USER_PROFILE,
    profile
});

export const fetchUserProfile = () => {
    return (dispatch, getState) => {
        const {token} = getState();
        dispatch(startAjax(ajaxEntities.USER_PROFILE));
        return axios.get(settings.USER_PROFILE_URL, {headers: {Authorization: 'Token ' + token}}).then((r) => {
            dispatch(saveUserProfile(r.data));
            return dispatch(stopAjax(ajaxEntities.USER_PROFILE));
        }, (err) => {
            if ([401, 403].some(i => i === err.response.status)) {
                history.push('/logout');
            }
            return dispatch(ajaxEntities.USER_PROFILE);
        });
    }
};

export const changeUserProfile = (field, value) => ({
    type: actionTypes.CHANGE_USER_PROFILE,
    field,
    value
});