cd ~
rm StoVaCore.tar.gz
wget https://dobrushskiy.name/static/StoVaCore.tar.gz
rm -rf keys_backup
rm -rf model_backup
mkdir keys_backup
mkdir model_backup
cp ~/StoVaCore/keys/* keys_backup/
cp ~/StoVaCore/misc/* model_backup/
rm -rf StoVaCore
tar -xzf StoVaCore.tar.gz
mkdir StoVaCore/misc
cp keys_backup/* StoVaCore/keys/
cp model_backup/* StoVaCore/misc/
rm StoVaCore.tar.gz
rm -rf keys_backup
rm -rf model_backup
