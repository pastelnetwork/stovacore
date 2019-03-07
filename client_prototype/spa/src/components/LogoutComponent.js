import {Component} from 'react';
import history from '../history';
import {forgetAPIToken, resetStore} from "../actions";

export class Logout extends Component {
    componentDidMount() {
        this.props.dispatch(forgetAPIToken());
        this.props.dispatch(resetStore());
        history.push('/login');
    }
    render() {
        return null;
    }
}
