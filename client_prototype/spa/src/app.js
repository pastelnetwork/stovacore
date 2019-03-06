import React from 'react';
import ReactDOM from 'react-dom';
import {Provider} from 'react-redux';
import {createStore} from 'redux';
import {Router} from 'react-router-dom';
import reducer from './reducers';

// import './index.css';
import 'bootstrap/dist/css/bootstrap.min.css';
// import '@fortawesome/fontawesome-free/css/all.min.css';

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
