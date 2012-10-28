from django.conf.urls import patterns, include, url

from django.conf import settings

# Uncomment the next two lines to enable the admin:
#from django.contrib import admin
#admin.autodiscover()

import reittiopas.views

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'opentraveltime.views.home', name='home'),
    # url(r'^opentraveltime/', include('opentraveltime.foo.urls')),

    url(r'^$', reittiopas.views.routes),

    url(r'^finland$', reittiopas.views.routes, dict(api="Matka.fi")),

    # Uncomment the admin/doc line below to enable admin documentation:
    #url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    #url(r'^admin/', include(admin.site.urls)),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^static/ol/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': 'reittiopas/static/ol'}),
    )
