import {connect} from 'react-redux';

import {Login} from '../components/LoginComponent';

const mapStateToProps = state => ({
});

const mapDispatchToProps = dispatch => ({
    dispatch
});


export const LoginContainer = connect(mapStateToProps, mapDispatchToProps)(Login);
