import * as actionTypes from './actionTypes';
import {initialState} from "./app";


const reducer  = (state = {}, action) => {
    switch (action.type) {
        case actionTypes.SAVE_API_TOKEN:
            return {...state, token: action.token};
        case actionTypes.SAVE_USER_PROFILE:
            return {...state, userProfile: action.profile};
        case actionTypes.CHANGE_USER_PROFILE:
            return {...state, userProfile: {...state.userProfile, [action.field]: action.value}};
        case actionTypes.START_AJAX:
            return {...state, ajaxInProgress: {...state.ajaxInProgress, [action.entity]: true}};
        case actionTypes.STOP_AJAX:
            return {...state, ajaxInProgress: {...state.ajaxInProgress, [action.entity]: false}};
        case actionTypes.RESET_STORE:
            return {...initialState};
        default:
            return state;
    }
};

export default reducer;
