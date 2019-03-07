import {connect} from 'react-redux';

import {Logout} from '../components/LogoutComponent';

const mapDispatchToProps = dispatch => ({
    dispatch
});

export const LogoutContainer = connect(null, mapDispatchToProps)(Logout);
