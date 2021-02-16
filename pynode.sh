#!/bin/bash

readonly STOPPED=0
readonly RUNNING=1

function kill_pynode()
{
    line=`ps aux | grep [s]ingle_masternode`
    if [ -z "$line" ];
    then
        echo "Already killed"
    else
        line_array=($line)
        pid=${line_array[1]}
        kill -9 ${pid}
        echo "Killed"
    fi
}

function get_status()
{
    line=`ps aux | grep [s]ingle_masternode`
    if [ -z "$line" ];
    then
        PYNODE_STATUS=$STOPPED
    else
        PYNODE_STATUS=$RUNNING
    fi

}
function status()
{
    get_status
    if [[ $PYNODE_STATUS -eq $STOPPED ]];
    then
        echo "Stopped"
    else
        echo "Running"
    fi
}

function start()
{
    export CONFIG_FILE=/home/animecoinuser/StoVaCore/pynode.ini
    line=`ps aux | grep [s]ingle_masternode`
    if [ -z "$line" ];
    then
        cd ~/StoVaCore
        nohup /home/animecoinuser/.virtualenvs/StoVaCore/bin/python /home/animecoinuser/StoVaCore/start_single_masternode.py > nohup.out 2> nohup.err < /dev/null &
        echo "Started"
    else
        echo "Already started"
    fi
}

function generate_cert()
{
    mkdir /home/animecoinuser/.pastel/pynode_https_cert
    cd /home/animecoinuser/.pastel/pynode_https_cert
    openssl req -newkey rsa:2048 -nodes -keyout privkey.pem -x509 -days 36500 -out certificate.pem -subj "/C=US"
}

function create_tables()
{
    cd ~/StoVaCore/utils
    PYTHONPATH=/home/animecoinuser/StoVaCore/ /home/animecoinuser/.virtualenvs/StoVaCore/bin/python create_tables.py
}

function drop_db()
{
    rm /home/animecoinuser/.pastel/masternode.db
}

function update_requirements()
{
    /home/animecoinuser/.virtualenvs/StoVaCore/bin/pip install -r ~/StoVaCore/requirements.txt
}


function clear_tmp_storage()
{
    cd /home/animecoinuser/StoVaCore
    rm -rf tmpstorage
    mkdir tmpstorage
}

function create_pastelid()
{
    cd ~/StoVaCore/utils
    PYTHONPATH=/home/animecoinuser/StoVaCore/ CONFIG_FILE=/home/animecoinuser/StoVaCore/pynode.ini /home/animecoinuser/.virtualenvs/StoVaCore/bin/python create_pastelid.py
}

function register_mnid()
{
    cd ~/StoVaCore/utils
    PYTHONPATH=/home/animecoinuser/StoVaCore/ CONFIG_FILE=/home/animecoinuser/StoVaCore/pynode.ini /home/animecoinuser/.virtualenvs/StoVaCore/bin/python register_mnid.py
}

case $1 in
    "start") start;;
    "status") status;;
    "stop") kill_pynode;;
    "generate_cert") generate_cert;;
    "create_tables") create_tables;;
    "update_requirements") update_requirements;;
    "drop_db") drop_db;;
    "clear_tmp_storage") clear_tmp_storage;;
    "create_pastelid") create_pastelid;;
    "register_mnid") register_mnid;;
esac
