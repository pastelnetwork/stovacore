import React, {Component} from 'react';
import {Form, FormGroup, Input, Button} from 'reactstrap';
import {getRenderedErrors} from "../utils";
import * as settings from '../settings';
import * as ajaxEntities from '../ajaxEntities';
import axios from 'axios';
import {saveAPIToken, startAjax, stopAjax} from "../actions";

export class Login extends Component {
    constructor(props) {
        super(props);
        this.emptyErrors = {
            non_field_errors: [],
            username: [],
            password: []
        };
        this.state = {
            username: '',
            password: '',
            errors: this.emptyErrors,
            submitDisabled: false
        }
    }
    onChange = (e) => {
        this.setState({[e.target.name]: e.target.value, errors: this.emptyErrors});
    };
    handleSubmit = () => {
        const data = (({ username, password }) => ({ username, password }))(this.state);
        this.props.dispatch(startAjax(ajaxEntities.LOGIN));
        axios.post(settings.LOGIN_URL, data).then((resp) => {
            const key = resp.data.key;
            this.props.dispatch(saveAPIToken(key));
            this.props.dispatch(stopAjax(ajaxEntities.LOGIN));
        }).catch((err) => {
            const errors = err.response.data;
            this.setState({errors: {...this.state.errors, ...errors}});
            this.props.dispatch(stopAjax(ajaxEntities.LOGIN));
        });
    };
    render() {
        let nonFieldErrors = getRenderedErrors(this.state.errors.non_field_errors);
        let usernameErrors = getRenderedErrors(this.state.errors.username);
        let passwordErrors = getRenderedErrors(this.state.errors.password);

        return <Form>
            <FormGroup>
                <Input type="text" name="username" id="idUsername" placeholder="Login"
                       value={this.state.username} onChange={this.onChange}/>
                {usernameErrors}
            </FormGroup>
            <FormGroup>
                <Input type="password" name="password" id="idPassword" placeholder="Password"
                       value={this.state.password} onChange={this.onChange}/>
                {passwordErrors}
            </FormGroup>
            {nonFieldErrors}
            <Button color="info" onClick={this.handleSubmit} className="float-right ml-4"
                    disabled={this.state.submitDisabled}>Login</Button>
        </Form>

    }
};
