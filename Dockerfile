FROM alexdobrushskiy/animecoin:0.1

COPY . /opt/python_layer

RUN cd /opt/python_layer; pip3 install -r requirements.txt
RUN ln /usr/bin/python3 /usr/bin/python
RUN cd /opt/python_layer/client_prototype/django_frontend; PYTHONPATH="/opt/python_layer" python manage.py migrate
RUN cd /opt/python_layer

# TODO: serve it
# TODO: install node, npm, npm -i <all from package.json>
# TODO: run static server on spa/dist folder
# TODO: JS app should somehow have access to api inside docker (but first need to open JS app from browser outside docker



# TODO: add nginx which will proxy 80 port to django or serve static
RUN apt-get update && apt-get install -y nginx
COPY ./client_prototype/nginx_config/nginx.conf /etc/nginx/nginx.conf
COPY ./client_prototype/nginx_config/uwsgi_params /etc/nginx/uwsgi_params
COPY ./client_prototype/spa/dist/ /var/www/static/

COPY ./client_prototype/nginx_config/docker_entrypoint.sh /
ENTRYPOINT ["/docker_entrypoint.sh"]

