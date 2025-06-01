import argparse


parser = argparse.ArgumentParser(prog='pycpa', usage='TODO', description='python implementation of CPA')
parser.add_argument('program', help='the program to validate', nargs='+')

parser.add_argument('-o', '--output-directory', help='directory to write results to', type=str, default='out')

parser.add_argument('-c', '--config', action='append', required=True, help='which analysis configuration to use (use --list-configs to get a list of available ones)')
parser.add_argument('-p', '--property', action='append', default=['unreach-call'], help='which analysis configuration to use (use --list-configs to get a list of available ones)')
parser.add_argument('--list-configs', help='a list of available analyses')
parser.add_argument('--list-properties', help='a list of available properties')

parser.add_argument('--max-iterations', help='maximum number of CPA loop iterations', type=int)

parser.add_argument('--compact', help='print less output (only program and verdict)', action='store_true')
parser.add_argument('--verbose', help='print more output', action='store_true')
parser.add_argument('--log-level', help='level of debuggin output', type=int, default='0')

parser.add_argument('-v', '--version', help='show version', action='version', version='%(prog)s 0.2')

# TODO add parameters



