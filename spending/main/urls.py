from django.conf.urls import patterns, include, url
from django.contrib.auth.views import login
from . import views


urlpatterns = patterns('',
    url('^$', views.home, name='home'),
    #url('^mobile/$', views.mobile, name='mobile'),
    #url('^mobile/auth/$', views.mobile_auth, name='mobile_auth'),
    #url('^mobile/appcache.manifest$', views.mobile_appcache,
    #    name='mobile_appcache'),
    url('^expenses/$', views.expenses, name='expenses'),
    url('^expenses.json$', views.expenses_json, name='expenses_json'),
    url('^expenses/(\d+)/edit/$', views.edit_expense, name='edit_expense'),
    url('^expenses/(\d+)/delete/$', views.delete_expense, name='delete_expense'),
    url('^categories.json$', views.categories_json, name='categories_json'),
    url('^login/$', login, {'template_name': 'login.html'}, name='login'),
    url('^charts/$', views.charts, name='charts'),
    url('^charts/timeline/$', views.charts_timeline, name='charts_timeline'),
    url('^calendar/$', views.calendar, name='calendar'),
    url('^compare/$', views.compare, name='compare'),
    url('^categories/$', views.categories, name='categories'),
    url('^categories/(\d+)/$', views.category, name='category'),
    url('^categories/(\d+)/delete/$', views.delete_category, name='delete_category'),
    url('^categories/(\d+)/edit/$', views.edit_category, name='edit_category'),
    url('^categories/(\d+)/move/$', views.move_category, name='move_category'),
)
