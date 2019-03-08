import React, {Component} from 'react';
import {Form, FormGroup, Input, Button} from 'reactstrap';
import {getRenderedErrors} from "../utils";
import * as settings from '../settings';
import * as ajaxEntities from '../ajaxEntities';
import * as constants from '../constants';
import Avatar from 'react-avatar-edit'
import axios from 'axios';
import {changeUserProfile, fetchUserProfile, saveAPIToken, startAjax, stopAjax} from "../actions";

export class UserProfile extends Component {
    constructor(props) {
        super(props);
        this.emptyErrors = {
            non_field_errors: []
        };
        this.state = {
            errors: this.emptyErrors
        }
    }

    onClose = () => {
        this.setState({preview: null})
    };

    onCrop = (preview) => {
        this.props.dispatch(changeUserProfile(constants.USER_PROFILE_FIELD_PICTURE, preview));
    };

    chaingeBio = (e) => {
        this.props.dispatch(changeUserProfile(constants.USER_PROFILE_FIELD_BIO, e.target.value))
    };

    handleSubmit = () => {
        this.props.dispatch(startAjax(ajaxEntities.USER_PROFILE));
        axios.put(settings.USER_PROFILE_URL, this.props.userProfile,
            {headers: {Authorization: 'Token ' + this.props.token}}).then((resp) => {
            this.props.dispatch(stopAjax(ajaxEntities.USER_PROFILE));
        }).catch((err) => {
            const errors = err.response.data;
            this.setState({errors: {...this.state.errors, ...errors}});
            this.props.dispatch(stopAjax(ajaxEntities.USER_PROFILE));
        });
    };

    render() {
        if (!this.props.userProfile) {
            this.props.dispatch(fetchUserProfile());
            return null;
        }
        let nonFieldErrors = getRenderedErrors(this.state.errors.non_field_errors);
        const picture = this.props.userProfile[constants.USER_PROFILE_FIELD_PICTURE];
        return <Form>
            <FormGroup>
                <Avatar
                    width={390}
                    height={295}
                    onCrop={this.onCrop}
                    onClose={this.onClose}
                />
                {picture && <img src={picture} alt="Preview"/>}
            </FormGroup>
            <FormGroup>
                <Input type="textarea" name="shortBio" id="idShortBio" placeholder="Short Bio"
                       value={this.props.userProfile[constants.USER_PROFILE_FIELD_BIO]} onChange={this.chaingeBio}/>
            </FormGroup>
            {nonFieldErrors}
            <Button color="info" onClick={this.handleSubmit} className="float-right ml-4"
                    disabled={this.props.ajaxInProgress}>Update</Button>
        </Form>

    }
}
