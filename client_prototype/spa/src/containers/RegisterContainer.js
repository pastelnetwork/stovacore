import {connect} from 'react-redux';

import {Register} from '../components/RegisterComponent';

const mapStateToProps = state => ({
});

const mapDispatchToProps = dispatch => ({
    dispatch
});


export const RegisterContainer = connect(mapStateToProps, mapDispatchToProps)(Register);
