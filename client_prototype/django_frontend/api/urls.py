from django.conf.urls import url
from api import views

urlpatterns = [
    url(r'^sign_user_data/$', views.SignUserDataView.as_view()),
]
