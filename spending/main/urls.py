from django.conf.urls.defaults import patterns, include, url
from django.contrib.auth.views import login
from . import views


urlpatterns = patterns('',
    url('^$', views.home, name='home'),
    url('^expenses/$', views.expenses, name='expenses'),
    url('^expenses/(\d+)/edit/$', views.edit_expense, name='edit_expense'),
    url('^expenses/(\d+)/delete/$', views.delete_expense, name='delete_expense'),
    url('^login/$',
    login, {'template_name': 'login.html'},
    name='login'),
    url('^charts/$', views.charts, name='charts'),
    url('^charts/timeline/$', views.charts_timeline, name='charts_timeline'),
)
