# vim: set fileencoding=utf-8 :
#
# (C) 2014 Guido Guenther <agx@sigxcpu.org>
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""Query and display config file values"""

from six.moves import configparser
import sys
import os, os.path
from gbp.config import GbpConfArgParser, GbpConfigDebian
from gbp.scripts.supercommand import import_command
import gbp.log


def build_parser(name):
    try:
        parser = GbpConfArgParser.create_parser(prog=name,
                                  description='display configuration settings')
    except configparser.ParsingError as err:
        gbp.log.err(err)
        return None

    parser.add_arg("-v", "--verbose", action="store_true",
                      help="verbose command execution")
    parser.add_conf_file_arg("--color", type='tristate')
    parser.add_conf_file_arg("--color-scheme")
    parser.add_argument("query", metavar="QUERY",
                        help="command[.optionname] to show")
    return parser


def parse_args(argv):
    parser = build_parser(argv[0])
    if not parser:
        return None
    return parser.parse_args(argv[1:])


def parse_cmd_config(command):
    """Make a command parse it's config files"""
    return GbpConfigDebian(command)


def print_cmd_single_value(query, printer):
    """Print a single configuration value of a command

    @param query: the cmd to print the value for
    @param printer: the printer to output the value
    """
    try:
        cmd, option = query.split('.')
    except ValueError:
        return 2

    config = parse_cmd_config(cmd)
    try:
        value = config.get_value(option)
    except KeyError:
        value = None
    printer("%s=%s" % (query, value))
    return 0 if value else 1


def print_cmd_all_values(cmd, printer):
    """
    Print all configuration values of a command

    @param cmd: the cmd to print the values for
    @param printer: the printer to output the values
    """
    if not cmd:
        return 2
    try:
        # Populae the parset to get a list of
        # valid options
        module = import_command(cmd)
        parser = module.build_parser(cmd)
    except (AttributeError, ImportError):
        return 2

    for option in parser.conf_file_args:
        value = parser.get_conf_file_value(option)
        if value != '':
            printer("%s.%s=%s" % (cmd, option, value))
    return 0


def value_printer(value):
    if (value):
        print(value)


def main(argv):
    retval = 1

    options = parse_args(argv)
    gbp.log.setup(options.color, options.verbose, options.color_scheme)

    if '.' in options.query:
        retval = print_cmd_single_value(options.query, value_printer)
    else:
        retval = print_cmd_all_values(options.query, value_printer)
    return retval

if __name__ == '__main__':
    sys.exit(main(sys.argv))

# vim:et:ts=4:sw=4:et:sts=4:ai:set list listchars=tab\:»·,trail\:·:
