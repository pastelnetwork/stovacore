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
    if [ $PYNODE_STATUS -eq $STOPPED ];
    then
        echo "Stopped"
    else
        echo "Running"
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

case $1 in
    "start") start;;
    "status") status;;
    "stop") kill_pynode;;
esac
