import React, {Component} from 'react';
import {Form, FormGroup, Input, Button} from 'reactstrap';
import {getRenderedErrors} from "../utils";
import * as settings from '../settings';
import * as ajaxEntities from '../ajaxEntities';
import axios from 'axios';
import {saveAPIToken, startAjax, stopAjax} from "../actions";

export class Register extends Component {
    constructor(props) {
        super(props);
        this.emptyErrors = {
            non_field_errors: [],
            username: [],
            password1: [],
            password2: []
        };
        this.state = {
            username: '',
            password1: '',
            password2: '',
            errors: this.emptyErrors,
            submitDisabled: false
        }
    }

    onChange = (e) => {
        this.setState({[e.target.name]: e.target.value, errors: this.emptyErrors});
    };
    getDataForAjax = () => ({
        username: this.state.username,
        password1: this.state.password1,
        password2: this.state.password2
    });

    handleSubmit = () => {
        this.props.dispatch(startAjax(ajaxEntities.REGISTER));
        axios.post(settings.SIGN_RESOURCE_URL, this.getDataForAjax()).then((resp) => {
            let data = resp.data;
            return axios.post(settings.REGISTER_RESOURCE_URL, data)
        }).then((resp) => {
            const key = resp.data.key;
            this.props.dispatch(saveAPIToken(key));
            this.props.dispatch(stopAjax(ajaxEntities.REGISTER));
        }).catch((err) => {
            const errors = err.response.data;
            this.setState({errors: {...this.state.errors, ...errors}});
            this.props.dispatch(stopAjax(ajaxEntities.REGISTER));
        });
    };

    render() {
        let nonFieldErrors = getRenderedErrors(this.state.errors.non_field_errors);
        let usernameErrors = getRenderedErrors(this.state.errors.username);
        let password1Errors = getRenderedErrors(this.state.errors.password1);
        let password2Errors = getRenderedErrors(this.state.errors.password2);

        return <Form>
            <FormGroup>
                <Input type="text" name="username" id="idUsername" placeholder="Login"
                       value={this.state.username} onChange={this.onChange}/>
                {usernameErrors}
            </FormGroup>
            <FormGroup>
                <Input type="password" name="password1" id="idPassword1" placeholder="Password"
                       value={this.state.password1} onChange={this.onChange} autoComplete="new-password"/>
                {password1Errors}
            </FormGroup>
            <FormGroup>
                <Input type="password" name="password2" id="idPassword2" placeholder="Repeat password"
                       value={this.state.password2} onChange={this.onChange} autoComplete="new-password"/>
                {password2Errors}
            </FormGroup>
            {nonFieldErrors}
            <Button color="info" onClick={this.handleSubmit} className="float-right ml-4"
                    disabled={this.state.submitDisabled}>Register</Button>
        </Form>
    }
}
