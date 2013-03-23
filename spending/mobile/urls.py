from django.conf.urls.defaults import patterns, include, url
#from django.contrib.auth.views import login
from . import views


urlpatterns = patterns('',
    url('^$', views.home, name='home'),
)
