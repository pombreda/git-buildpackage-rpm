# vim: set fileencoding=utf-8 :
#
# (C) 2012 Intel Corporation <markus.lehtonen@linux.intel.com>
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
"""Test module for RPM command line tools of the git-buildpackage suite"""

import os

from tests.component import ComponentTestGitRepository

# Disable "Instance of 'Document' has no 'firstChild' member"
#   pylint: disable=E1103


RPM_TEST_DATA_SUBMODULE = os.path.join('tests', 'component', 'rpm', 'data')
RPM_TEST_DATA_DIR = os.path.abspath(RPM_TEST_DATA_SUBMODULE)

def setup():
    """Test Module setup"""
    ComponentTestGitRepository.check_testdata(RPM_TEST_DATA_SUBMODULE)

# vim:et:ts=4:sw=4:et:sts=4:ai:set list listchars=tab\:»·,trail\:·:
