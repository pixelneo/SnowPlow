#!/usr/bin/env python3
import geojson
from best_solution import *

def convert_to_geojson(data, filename='processed_valid.geojson'):
    ''' This converts processed.geojson to valid geojson file.
        Outline of the output file:
        featurecollection
            feature
                id
                geometry
                    Point
                    coordinates
            feature
                properties
                   length, priority, maintenance_method, source (id), target (id)
                geometry
                    LineString
                    coordinates
    '''

    points = {}
    for p in data['nodes']:
        points[p['id']] = geojson.Feature(id=p['id'], geometry=geojson.Point(p['gps']))

    links = []
    for l in data['links']:
        coord = (points[l['source']]['geometry']['coordinates'], points[l['target']]['geometry']['coordinates'])
        links.append(geojson.Feature(geometry=geojson.LineString(coord), properties=l))

    features = links
    features.extend(points.values())

    feat_coll = geojson.FeatureCollection(features)

    with open(filename, 'w') as f:
        f.write(geojson.dumps(feat_coll, indent=2))

def convert_from_best_solution(graph, cars, filename='circuits.geojson'):
    ''' This converts processed.geojson to valid geojson file.
        Outline of the output file:
        featurecollection
            feature                 # stores
                id
                geometry
                    Point
                    coordinates
            feature
                properties
                   length,
                   priority,
                   maintenance_method,
                   source (id),
                   target (id),
                   car_id = []      # a list of cars MAINTAINING this road
                geometry
                    LineString
                    coordinates


            # feature                 # circuit of a car - or A car and its roads
                # properties
                    # roads = [(..,..)]
                    # store
                    # id
                    # method
                    # min_priority
                # geometry
                    # LineString
                    # coordinates

    '''
    def get_uniq_link(source, target):
        first = min((source, target))
        second = max((target, source))
        return (first, second)



    # results
    features = []

    # helping structures
    node_coordinates = {x['id']:(x['gps'][1], x['gps'][0]) for x in graph['nodes']}

    links = {}
    for l in graph['links']:
        coord = (node_coordinates[l['source']], node_coordinates[l['target']])
        props = l
        props['car_id'] = list()
        tpl = get_uniq_link(l['source'], l['target'])

        assert tpl not in links # link already exists

        links[tpl] = {'geometry':geojson.LineString(coord), 'properties':props}

    for c in cars:
        for r in c['roads']:
            tpl = get_uniq_link(r[0],r[1])
            links[tpl]['properties']['car_id'].append(c['id'])

    features = [geojson.Feature(geometry=x['geometry'], properties=x['properties']) for x in links.values()]
    feat_coll = geojson.FeatureCollection(features)

    with open(filename, 'w') as f:
        f.write(geojson.dumps(feat_coll, indent=2))

    return feat_coll




if __name__=="__main__":
    import json
    convert_from_best_solution(graph, cars)











