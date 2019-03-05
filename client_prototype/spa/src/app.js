import React from 'react';
import ReactDOM from 'react-dom';
import {Provider} from 'react-redux';
import {createStore} from 'redux';
import {Router, BrowserRouter, Route, Link} from 'react-router-dom';
import reducer from './reducers';
import Main from "./components/MainComponent";
import history from './history';

const store = createStore(reducer);


ReactDOM.render(
    <Provider store={store}>
        <Router history={history}>
            <Main/>
        </Router>
    </Provider>,

    document.getElementById('root'));
