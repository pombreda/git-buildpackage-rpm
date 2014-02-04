# vim: set fileencoding=utf-8 :
#
# (C) 2014 Intel Corporation <markus.lehtonen@linux.intel.com>
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
"""An RPM Changelog"""

import datetime
import re

import gbp.log


class ChangelogError(Exception):
    """Problem parsing changelog"""
    pass


class _ChangelogHeader(object):
    """The header part of one changelog section"""

    def __init__(self, pkgpolicy, time=None, **kwargs):
        self._pkgpolicy = pkgpolicy
        self._data = {'time': time}
        self._data.update(kwargs)

    def __contains__(self, key):
        return key in self._data

    def __getitem__(self, key):
        if key in self._data:
            return self._data[key]
        return None

    def __str__(self):
        keys = dict(self._data)
        keys['time'] = self._data['time'].strftime(
                            self._pkgpolicy.Changelog.header_time_format)
        try:
            return self._pkgpolicy.Changelog.header_format % keys + '\n'
        except KeyError as err:
            raise ChangelogError("Unable to format changelog header, missing "
                                 "property %s" % err)


class _ChangelogEntry(object):
    """An entry (one 'change') in an RPM changelog"""

    def __init__(self, pkgpolicy, author, text):
        """
        @param pkgpolicy: RPM packaging policy
        @type pkgpolicy: L{RpmPkgPolicy}
        @param author: author of the change
        @type author: C{str}
        @param text: message of the changelog entry
        @type text: C{str} or C{list} of C{str}
        """
        self._pkgpolicy = pkgpolicy
        self.author = author
        if isinstance(text, str):
            self._text = text.splitlines()
        else:
            self._text = text
        # Strip trailing empty lines
        while text and not text[-1].strip():
            text.pop()

    def __str__(self):
        # Currently no (re-)formatting, just raw text
        string = ""
        for line in self._text:
            string += line + '\n'
        return string


class _ChangelogSection(object):
    """One section (set of changes) in an RPM changelog"""

    def __init__(self, pkgpolicy, *args, **kwargs):
        self._pkgpolicy = pkgpolicy
        self.header = _ChangelogHeader(pkgpolicy, *args, **kwargs)
        self.entries = []
        self._trailer = '\n'


    def __str__(self):
        text = str(self.header)
        for entry in self.entries:
            text += str(entry)
        # Add "section separator"
        text += self._trailer
        return text

    def set_header(self, *args, **kwargs):
        """Change the section header"""
        self.header = _ChangelogHeader(self._pkgpolicy, *args, **kwargs)

    def add_entry(self, *args, **kwargs):
        """Add new entry"""
        entry = _ChangelogEntry(self._pkgpolicy, *args, **kwargs)
        self.entries.append(entry)
        return entry


class Changelog(object):
    """An RPM changelog"""

    def __init__(self, pkgpolicy):
        self._pkgpolicy = pkgpolicy
        self.sections = []

    def __str__(self):
        string = ""
        for section in self.sections:
            string += str(section)
        return string

    def add_section(self, *args, **kwargs):
        """Add new empty section"""
        section = _ChangelogSection(self._pkgpolicy, *args, **kwargs)
        self.sections.insert(0, section)
        return section


class ChangelogParser(object):
    """Parser for RPM changelogs"""

    def __init__(self, pkgpolicy):
        self._pkgpolicy = pkgpolicy
        self.section_match_re = pkgpolicy.Changelog.section_match_re
        self.section_split_re = pkgpolicy.Changelog.section_split_re
        self.header_split_re = pkgpolicy.Changelog.header_split_re
        self.header_name_split_re = pkgpolicy.Changelog.header_name_split_re
        self.body_name_re = pkgpolicy.Changelog.body_name_re

    def raw_parse_string(self, string):
        """Parse changelog - only splits out raw changelog sections."""
        changelog = Changelog(self._pkgpolicy)
        ch_section = ""
        for line in string.splitlines():
            if re.match(self.section_match_re, line, re.M | re.S):
                if ch_section:
                    changelog.sections.append(ch_section)
                ch_section = line + '\n'
            elif ch_section:
                ch_section += line + '\n'
            else:
                raise ChangelogError("First line in changelog is invalid")
        if ch_section:
            changelog.sections.append(ch_section)
        return changelog

    def raw_parse_file(self, changelog):
        """Parse changelog file - only splits out raw changelog sections."""
        try:
            with open(changelog) as ch_file:
                return self.raw_parse_string(ch_file.read())
        except IOError as err:
            raise ChangelogError("Unable to read changelog file: %s" % err)

    def _parse_section_header(self, text):
        """Parse one changelog section header"""
        # Try to split out time stamp and "changelog name"
        match = re.match(self.header_split_re, text, re.M)
        if not match:
            raise ChangelogError("Unable to parse changelog header: %s" % text)
        try:
            time = datetime.datetime.strptime(match.group('ch_time'),
                                             "%a %b %d %Y")
        except ValueError:
            raise ChangelogError("Unable to parse changelog header: invalid "
                                 "timestamp '%s'" % match.group('ch_time'))
        # Parse "name" part which consists of name and/or email and an optional
        # revision
        name_text = match.group('ch_name')
        match = re.match(self.header_name_split_re, name_text)
        if not match:
            raise ChangelogError("Unable to parse changelog header: invalid "
                                 "name / revision '%s'" % name_text)
        kwargs = match.groupdict()
        return _ChangelogSection(self._pkgpolicy, time=time, **kwargs)

    def _parse_section_entries(self, section, text):
        """Parse entries from a string and add them to a section"""
        header = section.header
        author = header['name'] if 'name' in header else header['email']
        entry_text = []
        for line in text.splitlines():
            match = re.match(self.body_name_re, line)
            if match:
                if entry_text:
                    section.add_entry(author=author, text=entry_text)
                author = match.group('name')
            else:
                if line.startswith("-"):
                    if entry_text:
                        section.add_entry(author=author, text=entry_text)
                    entry_text = [line]
                else:
                    if not entry_text:
                        gbp.log.info("First changelog entry (%s) is garbled, "
                                     "entries should start with a dash ('-')" %
                                     line)
                    entry_text.append(line)
        if entry_text:
            section.add_entry(author=author, text=entry_text)

    def parse_section(self, text):
        """Parse one section"""
        # Check that the first line(s) look like a changelog header
        match = re.match(self.section_split_re, text, re.M | re.S)
        if not match:
            raise ChangelogError("Doesn't look like changelog header: %s..." %
                                 text.splitlines()[0])
        # Parse header and entries
        section = self._parse_section_header(match.group('ch_header'))
        self._parse_section_entries(section, match.group('ch_body'))

        return section

