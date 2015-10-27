﻿"""Runs Scala, PySpark and SQL statement through Spark using a REST endpoint in remote cluster.
Provides the %spark magic."""

# Copyright (c) 2015  aggftw@gmail.com
# Distributed under the terms of the Modified BSD License.

from __future__ import print_function

from IPython.core.magic import (Magics, magics_class, line_cell_magic)
from IPython.core.magic_arguments import (argument, magic_arguments, parse_argstring)
import altair.api as alt

from .livyclientlib.sparkcontroller import SparkController
from .livyclientlib.rawviewer import RawViewer
from .livyclientlib.altairviewer import AltairViewer
from .livyclientlib.log import Log
from .livyclientlib.utils import get_magics_home_path, join_paths


@magics_class
class RemoteSparkMagics(Magics):

    def __init__(self, shell, data=None, mode="debug", use_altair=True, interactive=False):
        # You must call the parent constructor
        super(RemoteSparkMagics, self).__init__(shell)

        self.logger = Log()
        self.interactive = interactive

        try:
            self.magics_home_path = get_magics_home_path()
            path_to_serialize = join_paths(self.magics_home_path, "state.json")

            self.logger.debug("Will serialize to {}.".format(path_to_serialize))

            self.spark_controller = SparkController(serialize_path=path_to_serialize)
        except KeyError:
            self.spark_controller = SparkController()

        self.spark_controller.set_log_mode(mode)

        if use_altair:
            alt.use_renderer('lightning')
            self.viewer = AltairViewer()
        else:
            self.viewer = RawViewer()

        self.logger.debug("Initialized spark magics.")

    @magic_arguments()
    @argument("-s", "--sql", type=bool, default=False, help='Whether to use SQL.')
    @argument("-c", "--client", help="The name of the Livy client to use. "
                                     "If only one client has been created, there's no need to specify a client.")
    @argument("-t", "--chart", type=str, default="area", help='Chart type to use: table, area, line, bar.')
    @argument("command", type=str, default=[""], nargs="*", help="Commands to execute.")
    @line_cell_magic
    def spark(self, line, cell=""):
        """Magic to execute spark remotely.           
           If invoked with no subcommand, the code will be executed against the specified endpoint.
           Subcommands
           -----------
           info
               Display the mode and available Livy endpoints.
           viewer
               Change how to display sql results: "auto" or "df"
               "auto" will use Altair to create an automatic visualization.
               "df" will display the results as pandas dataframes.
               e.g. `%spark viewer auto`
           mode
               Set the mode to be used. Possible arguments are: "normal" or "debug".
               e.g. `%%spark mode debug`
           add
               Add a Livy endpoint. First argument is the friendly name of the endpoint, second argument
               is the language, and third argument is the connection string.
               e.g. `%%spark add test python url=https://sparkcluster.example.net/livy;username=admin;password=MyPassword`
           delete
               Delete a Livy endpoint. Argument is the friendly name of the endpoint to be deleted.
               e.g. `%%spark delete defaultlivy`
           cleanup
               Delete all Livy endpoints. No arguments required.
               e.g. `%%spark cleanup`
        """
        usage = "Please look at usage of %spark by executing `%spark?`."
        user_input = line
        args = parse_argstring(self.spark, user_input)

        subcommand = args.command[0].lower()

        # info
        if subcommand == "info":
            # Info is printed by default
            pass
        # viewer
        elif subcommand == "viewer":
            if len(args.command) != 2:
                raise ValueError("Subcommand 'viewer' requires an argument. {}".format(usage))
            v = args.command[1].lower()
            if v == "auto":
                self.viewer = AltairViewer()
            else:
                self.viewer = RawViewer()
        # mode
        elif subcommand == "mode":
            if len(args.command) != 2:
                raise ValueError("Subcommand 'mode' requires an argument. {}".format(usage))
            self.spark_controller.set_log_mode(args.command[1])
        # add
        elif subcommand == "add":
            if len(args.command) != 4:
                raise ValueError("Subcommand 'add' requires three arguments. {}".format(usage))
            name = args.command[1].lower()
            language = args.command[2]
            connection_string = args.command[3]
            self.spark_controller.add_endpoint(name, language, connection_string)
        # delete
        elif subcommand == "delete":
            if len(args.command) != 2:
                raise ValueError("Subcommand 'delete' requires an argument. {}".format(usage))
            name = args.command[1].lower()
            self.spark_controller.delete_endpoint(name)
        # cleanup 
        elif subcommand == "cleanup":
            self.spark_controller.cleanup()
        # run
        elif len(subcommand) == 0:
            self.logger.debug("line: " + line)
            self.logger.debug("cell: " + cell)
            self.logger.debug("args: " + str(args))
            result = self.spark_controller.run_cell(args.client, args.sql, cell)
            return self.viewer.visualize(result, args.chart)
        # error
        else:
            raise ValueError("Subcommand '{}' not found. {}".format(subcommand, usage))

        # Print info after any valid subcommand
        if len(subcommand) > 0:
            if len(cell) > 0:
                print("Warning: Cell body not executed because subcommmand found.")
                print(usage)
            self._print_info()

    def _print_info(self):
        if self.interactive:
            print("Info for running Spark:\n    mode={}\n    {}\n"
                  .format(self.spark_controller.get_log_mode(), self.spark_controller.get_client_keys()))

        
def load_ipython_extension(ip):
    ip.register_magics(RemoteSparkMagics)
