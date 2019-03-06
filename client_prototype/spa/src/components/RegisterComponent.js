import React, {Component} from 'react';
import {Form, FormGroup, Input, Button} from 'reactstrap';
import {getRenderedErrors} from "../utils";

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

    handleSubmit = () => {
        // TODO: maybe local validation
        // TODO: send data local BE
        // TODO: render errors (if any)
        // TODO: get new data with PK and signature
        // TODO: send data to cloud BE
        // TODO: render errors (if any)
    };
    render() {
        let nonFieldErrors = getRenderedErrors(this.state.errors.non_field_errors);
        let usernameErrors = getRenderedErrors(this.state.errors.username);
        let password1Errors = getRenderedErrors(this.state.errors.password1);
        let password2Errors = getRenderedErrors(this.state.errors.password2);

        return <Form>
            <FormGroup>
                <Input type="text" name="username" id="idUsername" placeholder="Login"
                       value={this.state.login} onChange={this.onChange}/>
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
