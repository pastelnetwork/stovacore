node_ips = ['51.15.198.10',
            '51.158.75.245',
            '163.172.141.171',
            '163.172.177.214',
            '163.172.165.125',
            '212.47.238.191',
            '51.15.201.181',
            '51.15.216.229',
            '51.158.114.227',
            '212.47.252.173', ]

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
        f.write('    IdentityFile /Users/mac/.ssh/pastel_testnet_rsa\n')
        f.write('\n')

    for i in range(0, 10):
        f.write('Host _alexmn{}\n'.format(i + 1))
        f.write('    HostName {}\n'.format(node_ips[i]))
        f.write('    User animecoinuser\n')
        f.write('    StrictHostKeyChecking no\n')
        f.write('    IdentityFile /Users/mac/.ssh/pastel_testnet_rsa\n')
        f.write('\n')

with open('pastel.conf', 'w') as f:
    f.write(pastel_conf.format(*node_ips))
