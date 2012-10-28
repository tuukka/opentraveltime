#!/usr/bin/env python
# encoding: utf-8

import sys

from urllib import urlencode
import urllib2

import json

from apirequest import distance_map, wgs84_to_kkj2

from poi import Poi

PALVELUKARTTA_API_URI = 'http://www.hel.fi/palvelukarttaws/rest/v2/unit/'

def poi_from_servicemap(poidata):
    if False: # don't use ETRS-GK25 coordinates
        coords = "%s,%s" % (poidata['easting_etrs_gk25'],
                            poidata['northing_etrs_gk25'])
    elif False: # don't geocode the street address to KKJ2 coordinates
        from apirequest import call_geocode, best_geocode_kkj
        coords = best_geocode_kkj(call_geocode(poidata['street_address_fi'])[0])
    else: # do convert from WGS84 to KKJ2 coordinates
        coords = wgs84_to_kkj2("%s,%s" % (poidata['longitude'],
                                          poidata['latitude']))

    return Poi(poidata['name_fi'], poidata['street_address_fi'], coords)

class PoiGroup(object):

    def __init__(self, id_number, name, long_name):
        self.name = name
        self.long_name = long_name
        self.addresses = None
        self.source = u"Pääkaupunkiseudun Palvelukartta"

        self.coords = None
        self.pois = None

        self.id_number = id_number

    def load_all(self):
        if self.addresses is not None:
            return

        pois = call_for_json(service=self.id_number)
        self.addresses = '|'.join(poi['street_address_fi'] for poi in pois)
        self.names = '|'.join(poi['name_fi'] for poi in pois)
        self.pois = [poi_from_servicemap(poi) for poi in pois]

    def n_closest(self, number, center_xy):
        pois = sorted(self.pois, key=lambda p:distance_map(center_xy, p.kkj))
        return pois[:number]

poi_groups = {'uimahalli': PoiGroup(28148, "Uimahalli", "uimahallit")}

def call(**params):
    for key,val in params.items():
        if val is None:
            del params[key]
        if isinstance(val, str):
            params[key] = val.decode("utf-8").encode("iso-8859-1")
        if isinstance(val, unicode):
            params[key] = val.encode("iso-8859-1")

    cachefilename = "cache/servicemap-"+urlencode(params)

    fetch_url = PALVELUKARTTA_API_URI + "?" + urlencode(params) 
        
    # XXX get results from cache?
    
    try: 
        # print fetch_url
        resp = urllib2.urlopen(urllib2.Request(fetch_url, headers={}))
        body = resp.read()
    finally:
        resp.close()

    try:
        f = file(cachefilename, "w")
        f.write(body)
        f.close()
    except IOError:
        pass
        
    return body

def call_for_json(**params):
    body = call(**params)

    # Parse JSON
    
    document = json.loads(body)

    return document


if __name__ == '__main__':
    json = call_for_json(service=poi_groups['uimahalli'].id_number)

    for x in json: print x['name_fi'], x['street_address_fi']
