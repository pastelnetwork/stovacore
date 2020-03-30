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

function get_cnode_status()
{
    line=`ps aux | grep [p]asteld`
    if [ -z "$line" ];
    then
        CNODE_STATUS=$STOPPED
    else
        CNODE_STATUS=$RUNNING
    fi

}

function cnode_status()
{
    get_cnode_status
    if [[ CNODE_STATUS -eq $STOPPED ]];
    then
        echo "PastelD Stopped"
    else
        echo "PastelD Running"
    fi
}

function start()
{
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

function stop_cnode()
{
    cd /home/animecoinuser/pastel
    ./pastel-cli stop
}


function start_cnode()
{
    cd /home/animecoinuser/pastel
    source start_mn.sh &
}

function clear_tmp_storage()
{
    cd /home/animecoinuser/StoVaCore
    rm -rf tmpstorage
    mkdir tmpstorage
}


case $1 in
    "start") start;;
    "status") status;;
    "stop") kill_pynode;;
    "generate_cert") generate_cert;;
    "create_tables") create_tables;;
    "update_requirements") update_requirements;;
    "drop_db") drop_db;;
    "stop_cnode") stop_cnode;;
    "start_cnode") start_cnode;;
    "cnode_status") cnode_status;;
    "clear_tmp_storage") clear_tmp_storage;;
esac