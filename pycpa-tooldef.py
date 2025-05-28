# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.util as util
import benchexec.tools.template
import benchexec.model

from benchexec.tools.sv_benchmarks_util import (
    get_non_witness_input_files_or_identifier,
)

# class Tool(benchexec.tools.template.BaseTool):
class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for pycpa.
    """

    REQUIRED_PATHS = ["scripts"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("cpa.sh", subdir="scripts")

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def version(self, executable):
        return self._version_from_tool(executable, line_prefix='pycpa ')

    def name(self):
        return "pycpa"

    def project_url(self):
        return "https://https://github.com/AxelSchneewind/pycpa"


    def _get_additional_options(self, existing_options, task, rlimits):
        options = []

        if task.property_file:
            options += ["--property", task.property_file]

        return options

    def cmdline(self, executable, options, task, rlimits):
        additional_options = self._get_additional_options(options, task, rlimits)
        input_files = get_non_witness_input_files_or_identifier(task)
        return [executable] + options + additional_options + input_files + ['--compact']

    def determine_result(self, run):
        """
        Parse the output of the tool and extract the verification result.
        This method always needs to be overridden.
        If the tool gave a result, this method needs to return one of the
        benchexec.result.RESULT_* strings.
        Otherwise an arbitrary string can be returned that will be shown to the user
        and should give some indication of the failure reason
        (e.g., "CRASH", "OUT_OF_MEMORY", etc.).
        """
        for line in run.output:
            if "All test cases time out or crash, giving up!" in line:
                return "Couldn't run: all seeds time out or crash"
            if "ERROR:" in line:
                return "Couldn't run pycpa"
            if "FALSE" in line:
                return result.RESULT_FALSE_PROP
            if "TRUE" in line:
                return result.RESULT_TRUE_PROP
            if "UNKNOWN" in line:
                return result.RESULT_UNKNOWN
        return result.RESULT_UNKNOWN

