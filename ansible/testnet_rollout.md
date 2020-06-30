 - Create 10 instances, put IPs to `generate_ssh_config_from_ip_list.py`, include result to ssh config
 (cp mn_config ~/.ssh/). It will also generate pastel.conf - put it to 3rd party place: 
  - scp pastel.conf do:/var/www/static/

 - execute playbook 'prepare_instance.yaml'
 `ansible-playbook -i hosts.yaml prepare_instance.yaml -v`
 - run cNodes (ansible ad-hoc command shell `cd ~/pastel && ./start_node.sh &`)
 Whole command: `ansible -i hosts.yaml mns -m shell -a 'cd ~/pastel && ./start_node.sh &'`
 
 (mine coins for some time to have enough coins for pasteleid registration)
 - run `pynode_install.yaml` playbook
 `ansible-playbook -i hosts.yaml pynode_install.yaml -v`

 - send 1000000 coins to each MN 
 
 - run `update_masternode_conf.yaml` playbook,
 - run `convert_nodes_to_mn.yaml` playbook to convert nodes to masternodes. It will take about 5-6 hours for testnet of 10 masternodes. 
