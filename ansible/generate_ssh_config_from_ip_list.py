node_ips = [
    '51.15.41.129',
    '51.15.79.175',
    '51.15.83.99',
    '51.158.176.36',
    '51.158.188.130',
    '51.15.109.152',
    '51.158.183.93',
    '51.158.167.70',
    '51.15.116.190',
    '51.15.38.6',
]

# Host alexmn1
#     HostName 51.15.109.152
#     User animecoinuser
#     StrictHostKeyChecking no

pastel_conf = '''testnet=1
server=1
addnode={}
addnode={}
addnode={}
addnode={}
addnode={}
addnode={}
addnode={}
addnode={}
addnode={}
addnode={}
gen=1
equihashsolver=tromp
rpcuser=rt
rpcpassword=rt
rpcallowip=0.0.0.0/0
'''
with open('mn_config', 'w') as f:
    for i in range(0, 10):
        f.write('Host alexmn{}\n'.format(i + 1))
        f.write('    HostName {}\n'.format(node_ips[i]))
        f.write('    User root\n')
        f.write('    StrictHostKeyChecking no\n')
        f.write('\n')

    for i in range(0, 10):
        f.write('Host _alexmn{}\n'.format(i + 1))
        f.write('    HostName {}\n'.format(node_ips[i]))
        f.write('    User animecoinuser\n')
        f.write('    StrictHostKeyChecking no\n')
        f.write('\n')

with open('pastel.conf', 'w') as f:
    f.write(pastel_conf.format(*node_ips))
