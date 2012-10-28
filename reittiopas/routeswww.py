#!/usr/bin/env python2.5
# encoding: utf-8

import sys

from urllib import urlencode
import urllib2

from django.template.loader import render_to_string

from apirequest import *

from poi import *

from htmlutil import html_escape, html_escapes

import warnings

try:
    import json
except ImportError:
    warnings.simplefilter('ignore', DeprecationWarning)
    import simplejson as json
    warnings.resetwarnings()


coords = {}
rev_coords = {}

def capitalize(s):
    return s[0].upper() + s[1:]

def reverse_geocode(keya, api):
    coords = wgs84_to_kkj(keya, api)
	    
    reverse = call_reverse_geocode(*coords.split(","), api=api)[0][0]

    return format_loc_complete(reverse)

def call_kevytliikenne(kkj1, kkj2):
    params = {'profile': 'kleroweighted',
              'from': "location* *%s" % kkj1.replace(",","*"),
              'to': "location* *%s" % kkj2.replace(",","*"),
              'via': ''
              }

    fetch_url = "http://kevytliikenne.ytv.fi/getroute/" + "?" + urlencode(params)

# http://kevytliikenne.ytv.fi/getroute/?_=1288697902778&profile=kleroweighted&from=location*+*2552473*6673691&to=location*+*2559974*6678128&via=

    try:
        resp = None
        resp = urllib2.urlopen(urllib2.Request(fetch_url, headers={}))
        body = resp.read()
    finally:
        if resp:
            resp.close()

    data = json.loads(body)
    return data['data']['route']['length']

def print_utf8(text):
    return text+"\n"

def print_route(route, mapid, api):
    res = ""
    res += "Matka-aika: %s Matkaa: %s" % format_length(
        route.find('LENGTH'))+"\n"
    
    for part in route:
        if part.tag == 'WALK':
            start = rev_coords.get(part[1].get('x')[:-2]
                                   + "," + part[1].get('y')[:-2], "")
            if not start and part[1].find('NAME') is not None:
                start = part[1].find('NAME').get('val')
            if not start:
                start = u"" # XXX loc
            else:
                start = u" " + start
            res += print_utf8(
                u""
                + format_time(part[1].find('DEPARTURE').get('time'))
                + start
                + u" Kävelyä %s %s" % format_length(part.find('LENGTH')))
        elif part.tag == 'LINE':
            start = " " + part[1].find('NAME').get('val')
            res += print_utf8(
                format_time(part[1].find('DEPARTURE').get('time'))
                + start
                + " "
                + capitalize(format_code_and_type(part.get('code'),
                                                  part.get('type'),
                                                  api))
                + ", "
                + u"%s %s" % format_length(part.find('LENGTH')))
    targetname = rev_coords[route[-1].get('x')[:-2]+","+route[-1].get('y')[:-2]]
    res += print_utf8(
        format_time(route[-1].find('ARRIVAL').get('time'))
        + " " + targetname + u" Perillä")

    geometry = geometry_for_route(route, api)
    routemap = render_to_string("reittiopas/routemap.html",
                                dict(mapid=mapid, geometry=geometry))
    
    return ('<tr><td valign="top"><pre>'
            + html_escape(res)
            + '</pre></td><td valign="top">'
            + routemap
            + '</td></tr>')

def geometry_for_route(route, api):
    points = []
    
    for part in route:
        if part.tag == 'WALK':
            for item in part:
                if item.tag in ['POINT', 'MAPLOC', 'STOP']:
                    coords = item.get('x')[:-2]+","+item.get('y')[:-2]
                    points += [coords]
        elif part.tag == 'LINE':
            for item in part:
                if item.tag in ['STOP', 'MAPLOC']:
                    coords = item.get('x')[:-2]+","+item.get('y')[:-2]
                    points += [coords]
    return 'new LineString(\n[%s\n])' % (',\n'.join(
        'new Point(%s)' % wgs84_to_webmercator(kkj_to_wgs84(point, api))
        for point in points))


def print_routes(container, api):
    routes = container.findall('ROUTE')
    return "<table>"+'\n'.join(print_route(route, "map%d" % i, api)
                               for (i, route) in enumerate(routes))+"</table>"

def multitarget(keya, keyb, api, **params):
    res = u""
    max_results = 99

    # geocode source:
    coords[keya] = call_geocode(keya, api)[0]
    rev_coords[best_geocode_kkj(coords[keya])] = format_loc(
        best_geocode(coords[keya]))

    # geocode n closest targets:
    poi_group = poi_groups[keyb]
    poi_group.load_all()
    pois = poi_group.n_closest(5, best_geocode_kkj(coords[keya]))
    addresses = [poi.address for poi in pois]

    for keybpart in addresses:
        coords[keybpart] = call_geocode(keybpart, api)[0]
        rev_coords[best_geocode_kkj(coords[keybpart])] = format_loc(
            best_geocode(coords[keybpart]))

    res += print_utf8(u"<h3>Lähtöpisteenä %s</h3>"
                      % html_escapes(format_loc(best_geocode(coords[keya]))))

    # public transport:

    routes = []
    for poi in pois:
        route_res = call_route(a=best_geocode_kkj(coords[keya]),
                               b=best_geocode_kkj(coords[poi.address]),
                               api=api)
        route = sorted(route_res.findall('ROUTE'), key=route_duration)[0]
        routes += [(route_duration(route), poi, route)]

    routes.sort()

    res += u"<table><tr><th colspan=3>Joukkoliikenteellä lähimmät</th></tr>"
    for (_duration, poi, route) in routes[:max_results]:
        # print_route(route)
        source = rev_coords.get(route[1].get('x')[:-2]
                                + ","
                                + route[1].get('y')[:-2]
                                , "")
        target = rev_coords[route[-1].get('x')[:-2]+","+route[-1].get('y')[:-2]]
        info_url = ("http://www.reittiopas.fi/fi/?from=%s&to=%s"
                    % (source, target))
        lines = '-'.join([format_code(part.get('code'), api).strip()
                          for part in route.findall('LINE')]) or u"vain kävelyä"
        res += print_utf8("""<tr><td align=right>%s</td><td>%s</td><td align=right>(<a href="%s">%s</a>)</td></tr>"""
                          % html_escapes(format_length(route.find('LENGTH'))[0],
                                         poi.address, info_url, lines))
        res += "\n"
    res += u"""<tr><td colspan=3 align=right class='attribution'>(Tietolähde <a href="http://www.reittiopas.fi/">HSL Reittiopas</a>)</td></tr></table>"""

    # biking:

    if api != "Matka.fi":
        res += u"<table><tr><th colspan=3>Pyörällä lähimmät</th></tr>"
        for dist, keybpart in sorted([
            (call_kevytliikenne(best_geocode_kkj(coords[keya]),
                                best_geocode_kkj(coords[keybpart])),
             keybpart)
            for keybpart in addresses])[:max_results]:
            info_url = ("http://kevytliikenne.ytv.fi/fi/#from(point*%s)to(point*%s)"
                        % (best_geocode_kkj(coords[keya]).replace(",","*"),
                           best_geocode_kkj(coords[keybpart]).replace(",","*")))
            res += print_utf8("""<tr><td align=right>%s</td><td>%s</td><td align=right>(<a href="%s">%.1f km</a>)</td></tr>"""
                              % (format_duration(dist/1000.0/17.0*60),
                                 html_escape(rev_coords[best_geocode_kkj(coords[keybpart])]),
                                 info_url,
                                 dist/1000.0))
        res += u"""<tr><td colspan=3 align=right class='attribution'>(Tietolähde <a href="http://pk.hsl.fi/">Pyöräilyn ja kävelyn Reittiopas)</a></td></tr></table>"""

    # walking:

    routes = []
    for keybpart in addresses:
        route_res = call_route(a=best_geocode_kkj(coords[keya]), b=best_geocode_kkj(coords[keybpart]), use_bus=0, use_train=0, use_ferry=0, use_metro=0, use_tram=0, show=1, api=api)
        routes += route_res.findall('ROUTE')

    routes = sorted(routes, key=route_duration)

    res += u"<table><tr><th colspan=3>Kävellen lähimmät</th></tr>"
    for route in routes[:max_results]:
        # print_route(route)
        source = rev_coords.get(route[1].get('x')[:-2]+","+route[1].get('y')[:-2], "")
        target = rev_coords[route[-1].get('x')[:-2]+","+route[-1].get('y')[:-2]]
        info_url = "http://www.reittiopas.fi/fi/?from=%s&to=%s&mc1=1&mc2=1&mc3=1&mc4=1&mc5=1&mc6=1&mc0=1&nroutes=1&searchformtype=advanced#ResultDetails" % (source, target)

        res += print_utf8("""<tr><td align=right>%s</td><td>%s</td><td align=right>(<a href="%s">%s</a>)</td></tr>""" % html_escapes(format_length(route.find('LENGTH'))[0], target, info_url, format_length(route.find('LENGTH'))[1]))
        res += "\n"
    res += u"""<tr><td colspan=3 align=right class='attribution'>(Tietolähde <a href="http://www.reittiopas.fi/">HSL Reittiopas</a>)</td></tr></table>"""

    # as the crow flies:
    if False: # don't render this info:
        res += u"<table><tr><th colspan=3>Kartalla lähimmät</th></tr>"
        for dist, keybpart in sorted([
            (distance_map(best_geocode_kkj(coords[keya]),
                          best_geocode_kkj(coords[keybpart])),
             keybpart) for keybpart in addresses])[:max_results]:
            res += print_utf8("""<tr><td>%s</td><td align=right>(%.1f km)</td></tr>"""
                              % (html_escape(rev_coords[best_geocode_kkj(coords[keybpart])]),
                                 dist/1000.0))
        res += u"""<tr><td colspan=3 align=right class='attribution'>(Tietolähde <a href="http://www.reittiopas.fi/">HSL Reittiopas</a>)</td></tr></table>"""
    return res


def route(keya, keyb, api=None, **params):

    if keyb.lower() in poi_groups:
        keyb = keyb.lower()
    elif "|" in keyb:
        # create and store an ad-hoc PoiGroup
        poi_groups[keyb] = PoiGroup("kohde", "kohteet", keyb, u"Kohde-kenttä")

    if keyb in poi_groups:
        # multitarget:
        if keya:
            res = u"<h2>Lähimmät %s</h2>" % poi_groups[keyb].long_name
            if not "|" in keyb:
                res += (u"""<p class='attribution'>(Tietolähde %s)</p>"""
                        % html_escape(poi_groups[keyb].source))
            return res + multitarget(keya, keyb, api=api, **params)
        else:
            # source missing, display targets:
            poi_group = poi_groups[keyb]
            poi_group.load_all()

            res = ("<h2>%s</h2>"
                   % html_escape(poi_groups[keyb].long_name.capitalize()))
            res += u"<h3>Hakeaksesi reitit lähimpiin, anna lähtöpiste</h3>"
            res += ("<table><tr><th colspan=3>Kaikki %s</th></tr>"
                    % html_escape(poi_groups[keyb].long_name))
            for poi in sorted(poi_group.pois, key=lambda poi:poi.name):
                poi_str = html_escape(poi.name)
                if poi.address != poi.name:
                    poi_str += ", "+poi.address
                res += ("""<tr><td>%s</td></tr>""" % (html_escape(poi_str)))
            if not "|" in keyb:
                res += (u"""<tr><td colspan=3 align=right class='attribution'>(Tietolähde %s)</td></tr></table>"""
                        % html_escape(poi_groups[keyb].source))
            return res

    elif keya and keyb:
        # single target:
        return route_one(keya, keyb, api=api, **params)

def route_one(keya, keyb, api, **params):
        coords[keya] = call_geocode(keya, api)[0]
        rev_coords[best_geocode_kkj(coords[keya])] = format_loc(
            best_geocode(coords[keya]))
        coords[keyb] = call_geocode(keyb, api)[0]
        rev_coords[best_geocode_kkj(coords[keyb])] = format_loc(
            best_geocode(coords[keyb]))
        
        res = call_route(a=best_geocode_kkj(coords[keya]),
                         b=best_geocode_kkj(coords[keyb]),
                         detail="full", api=api, **params)

        return print_routes(res, api)

