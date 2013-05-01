from django.conf.urls import patterns, include, url
from . import views


urlpatterns = patterns('',
    url('^$', views.home, name='home'),
    url('^submit/$', views.submit),
    url('^auth/$', views.auth, name='auth'),
    url('^categories/$', views.categories, name='categories'),
)
