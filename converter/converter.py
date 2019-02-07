#!/usr/bin/env python3
import geojson

def convert_to_geojson(data, filename='processed_valid.geojson'):
    '''
        This converts processed.geojson to valid geojson file.

        Outline of the output file:
        featurecollection
            feature
                id
                geometry
                    Point
                    coordinates
            feature
                properties
                   lenght, priority, maintenance_method, source (id), target (id) 
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


if __name__=="__main__":
    import json
    convert_to_geojson(json.loads('processed.geojson'))










