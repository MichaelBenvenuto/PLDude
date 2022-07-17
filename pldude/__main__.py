import argparse

from pldude.utils.arguments import pldude_argcompile

version_str = "v0.9.1"

def main():
    args = pldude_argcompile()

    print(args)

if __name__ == '__main__':
    main()