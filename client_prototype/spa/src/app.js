import React from 'react';
import ReactDOM from 'react-dom';
import {SomeComponent} from './components';
import {Provider} from 'react-redux';
import {createStore} from 'redux';
import {Router} from 'react-router-dom';
import reducer from './reducers';

const store = createStore(reducer);

ReactDOM.render(
    <Provider store={store}>
        <SomeComponent/>
    </Provider>,

    document.getElementById('root'));
