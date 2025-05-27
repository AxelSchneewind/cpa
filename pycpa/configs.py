import importlib

def load_cpa(name : str):
    name = name.split('/')[-1].split('.')[0]
    modname = 'pycpa.config.' + name
    return importlib.import_module(modname)

def load_specification(name : str):
    name = name.split('/')[-1].split('.')[0]
    modname = 'pycpa.property.' + name
    return importlib.import_module(modname)
