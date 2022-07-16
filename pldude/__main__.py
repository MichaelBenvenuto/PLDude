from email.policy import default
import sys
import getopt

import argparse

from pldude.bconfigs import BuildConfig
from pldude.utils import PLDudeError

version_str = "v0.9.1"

splash = f"""
    ____  __    ____            __   
   / __ \/ /   / __ \__  ______/ /__ 
  / /_/ / /   / / / / / / / __  / _ \\
 / ____/ /___/ /_/ / /_/ / /_/ /  __/
/_/   /_____/_____/\__,_/\__,_/\___/

Programmable Logic Device Utility DEvtool
{version_str}
"""

def main():
    try:

        parser = argparse.ArgumentParser(prog='PLDude', description='Programmable Logic Device Utility DEvtool')

        parser.add_argument('-c', '--compile', action='store_true', help='synthesize specified design files')
        parser.add_argument('-l', '--platform', default='AUTO', type=str, help='specify a platform hint')
        parser.add_argument('-p', '--program', action='store_true', help='program a synthesized design')
        parser.add_argument('-s', '--simulate', default=None, type=str, nargs=1, help='simulate a given module')
        parser.add_argument('-v', '--verbosity', choices=['DEBUG','INFO','WARNING','ERROR','NONE'], default='INFO', help='set the output verbosity to a given level')
        parser.add_argument('-x', '--clean', action='store_true', help='clean the generated project files')
        parser.add_argument('--version', action='version', version=f'%(prog)s {version_str}')

        res = parser.parse_args()

        bconf = BuildConfig()

        bconf.SetCompile(res.compile)
        bconf.Clean(res.clean)
        bconf.SetProgram(res.program)
        
        if res.simulate != None:
            bconf.SetSimulate(True, res.simulate)

        bconf.SetVerbosity(res.verbosity)
        bconf.LoadConfig()

        bconf.GetSpecific(res.platform).run()
    except KeyboardInterrupt:
        bconf._logging.warning("User termination")
        bconf.Terminate()
        sys.exit(0)
    except PLDudeError as err:
            bconf._logging.log(err.level, err.reason)
            sys.exit(err.ecode)

if __name__ == '__main__':
    main()