#!/usr/bin/env python
# encoding: utf-8

import sys
from math import sqrt

from urllib import urlencode
import urllib2

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET

from django.conf import settings

from django.contrib.gis.geos import Point # needed for transformations


REITTIOPAS_API_URI = "http://api.reittiopas.fi/public-ytv/fi/api/"
REITTIOPAS_ENCODING="iso-8859-1"

MATKAFI_API_URI = "http://api.matka.fi/public-lvm/fi/api/"
MATKAFI_ENCODING="iso-8859-1"

def call(**params):
    if params.get('api', None) == "Matka.fi":
        encoding = MATKAFI_ENCODING
    else:
        encoding = REITTIOPAS_ENCODING

    for key,val in params.items():
        if val is None:
            del params[key]
        if isinstance(val, str):
            params[key] = val.decode("utf-8").encode(encoding)
        if isinstance(val, unicode):
            params[key] = val.encode(encoding)


    cachefilename = "cache/body-"+urlencode(params)

    api = params.pop("api", None)
    if api == "Matka.fi":
        fetch_url = (MATKAFI_API_URI
                     + "?" + urlencode(params)
                     +  "&"
                     + "user=%s&pass=%s" % (settings.MATKAFI_USER,
                                            settings.MATKAFI_PASS))
    else:
        fetch_url = (REITTIOPAS_API_URI
                     + "?" + urlencode(params)
                     + "&"
                     + "user=%s&pass=%s" % (settings.REITTIOPAS_USER,
                                            settings.REITTIOPAS_PASS))
        
    try:
        if "time" in params:
            # caching is ok in this case
            f = file(cachefilename, "r")
            body = f.read()
            f.close()
            return body
    except IOError:
        pass
    
    try: 
        resp = None
        resp = urllib2.urlopen(urllib2.Request(fetch_url, headers={}))
        body = resp.read()
    finally:
        if resp:
            resp.close()

    try:
        f = file(cachefilename, "w")
        f.write(body)
        f.close()
    except IOError:
        pass
        
    return body

def call_for_xml(**params):
    body = call(format="xml", **params)

    # Parse XML
    
    mtrxml = ET.fromstring(body)

    assert mtrxml.tag == "MTRXML" or mtrxml.tag == "response"

    return mtrxml

def call_geocode(text, api=None):
    return call_for_xml(request="geocode", key=text, api=api)

def call_reverse_geocode(x, y, api=None):
    return call_for_xml(request="reverse_geocode", x=x, y=y, api=api)

def call_closest_stops_kkj2(x, y, radius, api=None):
    return call_for_xml(request="stops_area", closest_stops=1, x=x, y=y,
                        radius=radius, api=api)

def call_closest_stops_wgs84(lon, lat, radius, api=None):
    return call_for_xml(request="stops_area", closest_stops=1, lon=lon, lat=lat,
                        radius=radius, api=api)

def call_route(**params):
    return call_for_xml(request="route", **params)

def call_stop_timetable(stop_id, time=None, date=None, api=None):
    body = call(request="stop", stop=stop_id, time=time, date=date, api=api
                ).decode("iso-8859-1")
    
    lines = body.split("\n")[1:] # remove header and last empty line
    
    res = [line.split("|") for line in lines if line]

    if len(res) > 99:
        res.append([res[-1][0], "", "."*15, ""])
    
    return res


def merge_timetables(*data):
    return sorted(sum(data, []), key=lambda x:int(x[0]))


def best_geocode(geocode):
    """returns the best of the given geocoding results"""
    return geocode[0] # XXX best?

def best_geocode_kkj(geocode):
    """returns kkj coordinate string for the best of the given geocoding results"""
    best = geocode[0] # XXX best?
    return "%s,%s" % (best.get('x'), best.get('y'))


def wgs84_to_kkj(coords, api=None):
    if api == "Matka.fi":
        return wgs84_to_kkj3(coords)
    else:
        return wgs84_to_kkj2(coords)
    
def wgs84_to_kkj2(coords):
    x, y = coords.split(",")
    p = Point(x=float(x), y=float(y), srid=4326); # WGS84
    p.transform(2392); # KKJ2
    return "%d,%d" % (p.x,p.y)

def wgs84_to_kkj3(coords):
    x, y = coords.split(",")
    p = Point(x=float(x), y=float(y), srid=4326); # WGS84
    p.transform(2393); # KKJ3
    return "%d,%d" % (p.x,p.y)

def kkj_to_wgs84(coords, api=None):
    if api == "Matka.fi":
        return kkj3_to_wgs84(coords)
    else:
        return kkj2_to_wgs84(coords)

def kkj2_to_wgs84(coords):
    x, y = coords.split(",")
    p = Point(x=float(x), y=float(y), srid=2392); # KKJ2
    p.transform(4326); # WGS84
    return "%s,%s" % (p.x,p.y)

def kkj3_to_wgs84(coords):
    x, y = coords.split(",")
    p = Point(x=float(x), y=float(y), srid=2393); # KKJ3
    p.transform(4326); # WGS84
    return "%s,%s" % (p.x,p.y)

def wgs84_to_webmercator(coords):
    x, y = coords.split(",")
    p = Point(x=float(x), y=float(y), srid=4326); # WGS84
    p.transform(3857); # Web Mercator / Spherical Mercator
    return "%s,%s" % (p.x,p.y)


def route_duration(route):
    length = route.find('LENGTH')
    time = float(length.get('time'))
    return time

def distance_map(kkj1, kkj2):
    x1,y1=map(float, kkj1.split(","))
    x2,y2=map(float, kkj2.split(","))

    return sqrt((x1-x2)*(x1-x2)+(y1-y2)*(y1-y2))

def format_duration(time):
    if time >= 60:
        return "%d h %02d min" % (time / 60, time % 60)
    else:
        return "%d min" % (time % 60) 

def format_time(time):
    return "%02d:%s" % (int(time[:-2])%24, time[-2:])

def format_distance(dist):
    return "%.1f km" % (dist/1000)

def format_length(length):
    time = float(length.get('time'))
    dist = float(length.get('dist'))
    return (format_duration(time), format_distance(dist))

def format_code(code, api=None):
    if api == "Matka.fi":
        return code
    if code[:3] == "300": # local train
        return "  %s " % code[4]
    elif code[:4] == "1300": # metro
        return "  m "
    elif code[:3] == "110": # helsinki night bus
        return " %s" % code[2:5]
    elif code[:4] == "1019": # suomenlinna ferry
        return "  l "
    return code[1:-2].lstrip("0") # normal case

def format_code_and_type(code, type, api=None):
    types = u"Helsingin bussi,raitiovaunu,Espoon bussi,Vantaan bussi,seutubussi,metro,lautta,U-linja,muu paikallislinja,kaukolinja,pikalinja,paikallisjuna,kaukojuna,linja,,,,,,,Helsingin palvelulinja,Helsingin yöbussi,Espoon palvelulinja,Vantaan palvelulinja,seutuyöbussi".split(",")

    types_matkafi = {
         2: u"Tampereen paikallisbussi",
         7: u"Turun paikallisbussi",
        10: u"Jyväskylän paikallisbussi",
        12: u"Lahden paikallisbussi",
        15: u"erikoispikavuorobussi",
        16: u"pikavuorobussi",
        23: u"vakiovuorobussi",
        28: u"Helsingin paikallisbussi",
        29: u"raitiovaunu",
        33: u"metro",
        39: u"paikallisjuna",
        50: u"pikajuna",
        52: u"IC-juna",
        53: u"IC²-juna",
        54: u"Taajamajuna",
        58: u"lähiliikennejuna",
        59: u"Pendolino-juna",
    }
    
    try:
        if api != "Matka.fi":
            return types[int(type)-1] + " " + format_code(code, api).strip()
        else:
            return types_matkafi[int(type)] + " " + format_code(code, api
                                                                ).strip()
    except:
        pass
    return "kulkuneuvotyyppi=%s linja=%s" % (type, code) 

def format_loc(loc):
    res = loc.get('name1')
    if loc.get('number'):
        res += " " + loc.get('number')
    return res

def format_loc_complete(loc):
    res = loc.get('name1')
    if loc.get('number'):
        res += " " + loc.get('number')
    if loc.get('city'):
        res += ", " + loc.get('city')
    return res
