import argparse
import pldude.platforms

from pldude.utils.platforms import get_platforms
from pldude.utils.metadata import VERSION_STR

def pldude_argcompile() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog='pldude', description='Programmable Logic Device Utility DEvtool')

    tools = get_platforms(pldude.platforms)

    builder_classes = tools['builders'].copy()
    simulator_classes = tools['simulators'].copy()
    tool_classes = builder_classes.copy()
    tool_classes.extend(simulator_classes)

    builder_names = [i.name for i in builder_classes]
    simulator_names = [i.name for i in simulator_classes]
    tool_names = builder_names.copy()
    tool_names.extend(simulator_names)

    subcommand_subparser = parser.add_subparsers(required=True, dest='command')
    compile_parser = subcommand_subparser.add_parser('COMPILE', description='compiles a design')
    compile_parser.add_argument('-r', '--routine', default='FULL', choices=['FULL','SYNTH','PAR','IMPLEMENT'], help='select a compilation routine')
    compile_enviro = compile_parser.add_argument_group(title='environment')
    compile_choices = ['AUTO']
    compile_choices.extend(builder_names)
    compile_enviro.add_argument('-e', '--environment', default='AUTO', choices=compile_choices, help='select and environment to compile with')

    simulator_parser = subcommand_subparser.add_parser('SIMULATE', description='simulates a design')
    simulator_parser.add_argument('MODULE', help='module to simulate')
    simulator_parser.add_argument('-t', '--type', default='BEHAVIORAL', choices=['BEHAVIORAL','SYNTH','PAR','IMPLEMENT'], help='select a simulation type')
    simulator_enviro = simulator_parser.add_argument_group(title='environment')
    simulator_choices = ['AUTO']
    simulator_choices.extend(simulator_names)
    simulator_enviro.add_argument('-e', '--environment', default='AUTO', choices=simulator_choices, help='select and environment to simulate with')

    clean_parser = subcommand_subparser.add_parser('CLEAN', description='cleans generated project files')

    platform_parser = subcommand_subparser.add_parser('PLAT', description='run commands for a specific platform')
    platform_subparser = platform_parser.add_subparsers(required=True, dest='platform')

    for i in tool_classes:
        plat_parse = platform_subparser.add_parser(i.name)
        i.tool.configure_args(plat_parse)

    other_args = parser.add_argument_group(title='other options')
    other_args.add_argument('--version', action='version', version=f'%(prog)s {VERSION_STR}')

    return parser.parse_args()