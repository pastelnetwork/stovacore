import json
import urllib.request
import base64

with open('/home/animecoinuser/.pastel/testnet3/masternode.conf', 'r') as f:
    config_data = f.read()
json_config_data = json.loads(config_data)
if 'pyAddress' in json_config_data:
    del json_config_data['pyAddress']
if 'pyPubKey' in json_config_data:
    del json_config_data['pyPubKey']

mn_key = list(json_config_data.keys())[0]
ip = urllib.request.urlopen('https://ipinfo.io/ip').read()
ip = ip.decode('utf-8')
ip = ip.strip()

json_config_data[mn_key]['pyAddress'] = '{}:4444'.format(ip)
with open('/home/animecoinuser/StoVaCore/keys/public.key', 'rb') as pk_file:
    pk = pk_file.read()
py_pub_key = base64.b64encode(pk).decode()
json_config_data[mn_key]['pyPubKey'] = py_pub_key
final_data = json.dumps(json_config_data, indent=4, sort_keys=True)
with open('/home/animecoinuser/.pastel/testnet3/masternode.conf', 'w') as f:
    f.write(final_data)
