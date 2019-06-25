# first - clone StoVaCore repo to /home/animecoinuser

sudo apt install -y python-pip && sudo apt-get install -y software-properties-common && sudo pip install virtualenv
mkdir ~/.virtualenvs
sudo pip install virtualenvwrapper
export WORKON_HOME=~/.virtualenvs
echo '. /usr/local/bin/virtualenvwrapper.sh' >> ~/.bashrc
sudo apt install -y python3-distutils
source ~/.bashrc
mkvirtualenv StoVaCore -p python3
cd StoVaCore
rm keys/*
pip install -r requirements.txt
python update_masternode_conf.py
python start_single_masternode.py &
