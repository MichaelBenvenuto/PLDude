from pldude.bconfigs import BuildConfig
from pldude.utils import PLDudeError
import sys
import getopt

splash = """
    ____  __    ____            __   
   / __ \/ /   / __ \__  ______/ /__ 
  / /_/ / /   / / / / / / / __  / _ \\
 / ____/ /___/ /_/ / /_/ / /_/ /  __/
/_/   /_____/_____/\__,_/\__,_/\___/

Programmable Logic Device Utility DEvtool
v0.9.0
"""

usage = """
Usage:
    pldude [-c|--compile] [-p|--program] [-v|--verbosity <DEBUG|INFO|WARNING|ERROR|NONE>] [-s|--simulate <module>] [-h|--help] [-x|--clean]

Options:
    -c | --compile              Synthesize all hdl files
    -p | --program              Upload synthesized hdl files to PLD, will synthesize if files are not already
    -v | --verbosity            Set verbosity level (INFO|WARNING|ERROR|NONE)
    -s | --simulate             Simulate the specified module
    -h | --help                 Display this message
    -x | --clean                Clean all tool-generated files

"""

def main():
    try:
        print(splash)

        if len(sys.argv[1:]) == 0:
            print(usage)
            sys.exit(0)

        try:
            arg, opt = getopt.getopt(sys.argv[1:], "cpv:s:hx", ['compile', 'program', 'verbosity=', 'simulate=', 'help', 'clean'])
        except getopt.GetoptError as err:
            print(err)
            print(usage)
            sys.exit(2)

        bconf = BuildConfig()
        for o, a in arg:
            if o in ('-c', '--compile'):
                bconf.SetCompile(True)
            elif o in ('-p', '--program'):
                bconf.SetProgram(True)
            elif o in ('-v', '--verbosity'):
                bconf.SetVerbosity(a)
            elif o in ('-s', '--simulate'):
                bconf.SetSimulate(True, a)
            elif o in ('-x', '--clean'):
                bconf.Clean(True)
            elif o in ('-h', '--help'):
                print(usage)
                sys.exit(0)

        bconf.LoadConfig()

        bconf.GetSpecific().run()
    except KeyboardInterrupt:
        bconf._logging.warning("User termination")
        bconf.Terminate()
        sys.exit(0)
    except PLDudeError as err:
            bconf._logging.log(err.level, err.reason)
            sys.exit(err.ecode)

if __name__ == '__main__':
    main()