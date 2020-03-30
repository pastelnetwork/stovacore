# first - clone StoVaCore repo to /home/animecoinuser

sudo apt install -y python3-pip && sudo apt-get install -y software-properties-common && sudo pip install virtualenv
mkdir ~/.virtualenvs
sudo pip install virtualenvwrapper
export WORKON_HOME=~/.virtualenvs
echo '. /usr/local/bin/virtualenvwrapper.sh' >> ~/.bashrc
sudo apt install -y python3-distutils
source ~/.bashrc
mkvirtualenv StoVaCore -p python3
cd StoVaCore
pip3 install -r requirements.txt
mkdir /home/animecoinuser/.pastel/testnet3/pastelkeys