"""frontend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from core import views
from api import urls as api_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^api/', include(api_urls)),
    url(r'^tasks/$', views.tasks, name='tasks'),
    url(r'^walletinfo/$', views.walletinfo, name='walletinfo'),
    url(r'^identity/$', views.identity, name='identity'),
    url(r'^portfolio/$', views.portfolio, name='portfolio'),
    url(r'^artwork/(?P<artid_hex>.*)$', views.artwork, name='artwork'),
    url(r'^exchange/$', views.exchange, name='exchange'),
    url(r'^trending/$', views.trending, name='trending'),
    url(r'^browse/(?P<txid>.*)$', views.browse, name='browse'),
    url(r'^register/$', views.register, name='register'),
    url(r'^download/(?P<artid>.*)$', views.download, name='download'),
    url(r'^console/$', views.console, name='console'),
    url(r'^explorer/(?P<functionality>(chaininfo|block|transaction|address))/?(?P<id>.*)?$', views.explorer, name='explorer'),
    url(r'^chunk/(?P<chunkid_hex>.*?)$', views.chunk, name='chunk'),
    url(r'^$', views.index, name='index'),
]

# static files
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
