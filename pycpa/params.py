import argparse


parser = argparse.ArgumentParser(prog='pycpa', usage='TODO', description='python implementation of CPA')
parser.add_argument('program', help='the program to validate', nargs='+')

parser.add_argument('-c', '--config', help='which analysis configuration to use (use --list-configs to get a list of available ones)')
parser.add_argument('-p', '--property', help='which analysis configuration to use (use --list-configs to get a list of available ones)')
parser.add_argument('--list-configs', help='a list of available analyses')
parser.add_argument('--list-properties', help='a list of available properties')

# TODO add parameters



