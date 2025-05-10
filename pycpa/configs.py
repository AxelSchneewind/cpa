import pycpa.config
import importlib

# TODO: get list of all files in config
configs = []


def get_config(name):
    return importlib.import_module('pycpa.config.' + name)
