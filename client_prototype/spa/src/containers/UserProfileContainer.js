import {connect} from 'react-redux';
import * as ajaxEntities from '../ajaxEntities';
import {UserProfile} from '../components/UserProfileComponent';

const mapStateToProps = state => ({
    token: state.token,
    userProfile: state.userProfile,
    ajaxInProgress: state.ajaxInProgress[ajaxEntities.USER_PROFILE]
});

const mapDispatchToProps = dispatch => ({
    dispatch
});


export const UserProfileContainer = connect(mapStateToProps, mapDispatchToProps)(UserProfile);
