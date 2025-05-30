

class LogPrinter:
    def __init__(self, args):
        self.compact = args.compact
        self.log_level = args.log_level

    def log_status(self, *msg):
        if not self.compact:
            print('\r',  *msg, end='')

    def log_task(self, program_name, configs, properties):
        if not self.compact:
            prop = str(properties[0]) if len(properties) == 1 else properties
            conf = str(configs[0]) if len(configs) == 1 else configs
            print('Verifying ', program_name, 'against', prop, 'using', conf)

    # 
    def log_debug(self, level, *msg):
        if not self.compact and self.log_level >= level:
            print(*msg)

    def log_result(self, programname, status, verdict, *msg):
        if not self.compact:
            print('\n', programname, ': ', status, ' ', verdict, *msg, sep='')
        else:
            print(programname, ': ', status, ' ', verdict, *msg, sep='')

    def log_intermediate_result(self, programname, status, verdict, *msg):
        if not self.compact and self.log_level >= 1:
            print('\n', programname, ': ', status, ' ', verdict, *msg, sep='')


# global object for printing messages
printer = None

def init_printer(args):
    """
    initialize global printer object from args
    """
    global printer
    printer = LogPrinter(args)