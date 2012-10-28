
import re

from django.shortcuts import render

from reittiopas.routeswww import route, reverse_geocode

def routes(request, api=None):
    keya = request.GET.get('from', "")
    keyb = request.GET.get('to', "")
    time = request.GET.get('time')

    # handle any WGS84 coordinates from HTML5 geocoding in the From field:
    if re.match(r"\d+(\.\d+)?,\d+(\.\d+)?", keya):
	keya = reverse_geocode(keya, api=api)

    # try to route:
    result = route(keya, keyb, time=time, api=api)

    return render(request, 'reittiopas/routes.html',
		  dict(field_from=keya, field_to=keyb,
		       result=result, api=api))
