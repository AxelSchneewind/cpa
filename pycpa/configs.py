import importlib

def load_cpa(name : str):
    modname = 'pycpa.config.' + name
    return importlib.import_module(modname)

def load_specification(name : str):
    modname = 'pycpa.property.' + name
    return importlib.import_module(modname)
