#!/usr/bin/env python2.5
# encoding: utf-8

class Poi(object):
    def __init__(self, name, address, kkj):
        self.name = name
        self.address = address
        self.kkj = kkj

# circular reference
import servicemap

class PoiGroup(object):
    def __init__(self, name, long_name, addresses, source):
        self.name = name
        self.long_name = long_name
        self.addresses = addresses
        self.source = source

        self.pois = [Poi(addr, addr, None) for addr in self.addresses.split("|")]

    def load_all(self):
        pass

    def n_closest(self, number, center_xy):
        # XXX return all for now
        return self.pois

poi_groups = {
    'alko': PoiGroup("Alko", u"Alkon myymälät", "Ala-Malmin tori 5|Panuntie 11|Viikintori 3", "Alko"),
    'kela': PoiGroup("Kela", "Kelan toimistot", u"Soidintie 4|Koskelantie 5|Tallinnanaukio 4|Kahvikuja 3|Hämeentie 15|Salomonkatu 17", "Kela"),
    u'päärata': PoiGroup(u"Päärata", u"pääradan kaukojuna-asemat", "Helsinki/VR|Pasila/VR|Tikkurila/VR", "VR"),
    'rantarata': PoiGroup("Rantarata", "rantaradan kaukojuna-asemat", "Helsinki/VR|Pasila/VR|Espoo/VR|Kirkkonummi/VR", "VR"),
}

poi_groups.update(servicemap.poi_groups)
