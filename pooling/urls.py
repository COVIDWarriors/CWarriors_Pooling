# -*- coding: utf-8 -*-
# vim:ts=4:expandtab:ai
# $Id: urls.py 44 2020-05-02 18:20:46Z root $

from django.conf.urls import url
from . import views
from .models import Rack

app_name = 'pooling'

racktypes = ''.join(['{0}'.format(t[0]) for t in Rack.TYPE])
urlpatterns = [
    url(r'history', views.history, name='history'),
    url(r'finish', views.finish, name='finish'),
    url(r'refresh', views.refresh, name='refresh'),
    url(r'movesample', views.moveSample, name='movesample'),
    url(r'move', views.move, name='move'),
    url(r'batch', views.batch, name='batch'),
    url(r'loadsample', views.loadSample, name='loadsample'),
    url(r'loadtube', views.loadTube, name='loadtube'),
    url(r'show/(?P<rackid>\d+)', views.show, name='show'),
    url(r'tube/(?P<tubeid>\d+)', views.viewtube, name='tube'),
    url(r'upload', views.upload, name='upload'),
    url(r'^$', views.index, name='inicio'),
]
