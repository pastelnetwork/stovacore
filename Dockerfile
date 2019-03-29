FROM alexdobrushskiy/animecoin:0.1

COPY . /opt/python_layer

RUN cd /opt/python_layer; pip3 install -r requirements.txt
RUN ln /usr/bin/python3 /usr/bin/python
RUN cd /opt/python_layer/client_prototype/django_frontend; PYTHONPATH="/opt/python_layer" python manage.py migrate
RUN cd /opt/python_layer/client_prototype/django_frontend; PYTHONPATH="/opt/python_layer" python manage.py collectstatic --noinput
RUN cd /opt/python_layer

RUN apt-get update && apt-get install -y nginx
COPY ./client_prototype/nginx_config/nginx.conf /etc/nginx/nginx.conf
COPY ./client_prototype/nginx_config/uwsgi_params /etc/nginx/uwsgi_params
COPY ./PastelWallet/dist/ /var/www/static/
RUN mkdir -p /opt/python_layer/config_sample/0/pymn/config/

COPY ./client_prototype/nginx_config/docker_entrypoint.sh /
ENTRYPOINT ["/docker_entrypoint.sh"]

