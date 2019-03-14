### Manual node installation

 - create instance with Ubuntu 18.04 (say, in digital ocean)
 - ssh to the instance
 - mkdir animecoin_blockchain; cd animecoin_blockchain
 - clone repo: `git clone https://github.com/ANIME-AnimeCoin/AnimeCoin.git`
 - `apt update`
 - `apt install python3 python3-pip build-essential automake libtool pkg-config libcap-dev`
 - `apt install git-lfs`
 - cd ~
 - `git clone https://github.com/ANIME-AnimeCoin/python_layer.git` 
 - cd ~/animecoin_blockchain/AnimeCoin
 - ./acutil/build.sh
 - cd ~/animecoin_blockchain/AnimeCoin
 - ./acutil/fetch-params.sh
 - ln ~/Animecoin/src/animecoind /usr/local/bin/animecoind
 - cd ~/python_layer
 - git lfs pull
 - pip3 install -r requirements.txt
 - `ln /usr/bin/python3 /usr/bin/python`
 - cd ~/AnimeCoin/src/python_layer/client_prototype/django_frontend
 - PYTHONPATH="~/python_layer" python manage.py migrate
 - cd ~/python_layer 
 - mkdir ~/sim
 - cp -r config_sample/* ~/sim/
 - python start_simulator.py ~/sim/
 - simulator is running, available only from localhost. Django UI is available on ports 14239, 14240, 14241] for each node respectively.
 - to make UI available from outside - you need to setup some proxy (nginx is suitable, for example) to bypass request from outer world to django UI ports.


### Docker image installation (any OS, suitable for local machine)
 - Install docker to the local machine
 - `docker run -d -p 80:80 alexdobrushskiy/python_layer:0.1`
 - (This will download image and run it in detached mode. )
 - Open browser, try `127.0.0.1` in address string. 

### Building docker image
 
 A `python_layer` docker image depends on `animecoind` docker image, which can be build from AnimeCoin repository
 - Go to python_layer directory
 - cd `client_prototype/spa`
 - `npm i`
 - `npm run build`
 - `cd .. ; cd ..;`
 - `docker build .`
 - Then docker image can be tagged and pushed to dockerhub.
