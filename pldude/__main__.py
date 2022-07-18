import sys
import argparse
from pldude.toolchain.builder import builder
from pldude.toolchain.tool import tool

from pldude.utils.arguments import pldude_argcompile
from pldude.utils.platforms import Platforms

def main():
    args = pldude_argcompile()

    if args.command == 'COMPILE':
        if args.environment == 'AUTO':
            for i in Platforms.builders:
                if i.tool.check_device('test'):
                    platform = i.tool
                    break
        else:
            platform = Platforms.builders_dict.get(args.environment, None)
        
        tool_build : builder = platform()
        if args.routine in ('FULL', 'SYNTH'):
            tool_build.synthesize()

        if args.routine in ('FULL', 'PAR'):
            tool_build.placer()

        if args.routine in ('FULL', 'IMPLEMENT'):
            tool_build.implementer()

        if args.routine == 'FULL':
            tool_build.bitstream()

    print(args)

if __name__ == '__main__':
    main()