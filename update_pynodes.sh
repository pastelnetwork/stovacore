mkdir -p for_dist/StoVaCore/keys
cp -a masternode_prototype for_dist/StoVaCore/
cp -a core_modules for_dist/StoVaCore/
cp -a utils for_dist/StoVaCore/
cp -a debug for_dist/StoVaCore/
cp -a pynode for_dist/StoVaCore/
# model is heavy - so it's copied from previous version
# if model should be updated - uncomment the following line
#cp -a misc for_dist/StoVaCore/
cp * for_dist/StoVaCore/

rm -rf for_dist/StoVaCore/core_modules/__pycache__
rm -rf for_dist/StoVaCore/core_modules/blackbox_modules/__pycache__

rm for_dist/StoVaCore/prepare_dist.sh
rm for_dist/StoVaCore/install_node.sh
rm for_dist/StoVaCore/rm.spec
rm for_dist/StoVaCore/wallet_api.spec

cd for_dist
tar -czf StoVaCore.tar.gz StoVaCore
scp StoVaCore.tar.gz do:/var/www/static/
scp update.sh do:/var/www/static/
cd ..

echo 'Updating StoVaCore on all masternodes..'
HOSTS="mn2 mn3 mn4 mn5 mn6 mn7 mn8 mn9 mn10 mn11"
#HOSTS="mn2"
SCRIPT="source <(curl -s https://dobrushskiy.name/static/update.sh)"
for HOSTNAME in ${HOSTS} ; do
    ssh ${HOSTNAME} "${SCRIPT}" &
done
echo 'Done..'
# finally:
rm for_dist/StoVaCore.tar.gz
rm -rf for_dist/StoVaCore
