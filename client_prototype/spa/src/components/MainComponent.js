import React from 'react';
import {Switch, Route, Redirect, withRouter} from 'react-router-dom'
import {RegisterContainer} from "../containers/RegisterContainer";
import {LoginContainer} from "../containers/LoginContainer";
import {LogoutContainer} from "../containers/LogoutContainer";

const Main = () => {
    return <div className="container">
        <div className="col-5 offset-3 mt-4">
        <Switch>
            <Route path='/login' component={LoginContainer}/>
            <Route path='/register' component={RegisterContainer}/>
            <Route path='/logout' component={LogoutContainer}/>
            <Redirect to='/login'/>
        </Switch>
        </div>
    </div>;
};

export default withRouter(Main);
