import pycpa.config
import importlib

# TODO: get list of all files in config and property
configs = []
properties = []

def get_config(name):
    return importlib.import_module('pycpa.config.' + name)

def get_property(name):
    return importlib.import_module('pycpa.property.' + name)
