#!/usr/bin/env python3

def qgis_list_to_list(qgis_str):
    '''
        This method converts list in string in format (element_count:element0,element1,...,elementn-1)
        to python list
    '''
    # comma delimited list
    elems_str = qgis_str.split(':')[1].rstrip(')')
    lst = [int(x) for x in elems_str.split(',')]
    return lst

