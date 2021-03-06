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
"""Basic tests for the git-import-srpm tool"""

import os
import shutil
import urllib2
from nose.plugins.skip import SkipTest
from nose.tools import assert_raises, eq_, ok_  # pylint: disable=E0611
from mock import Mock

from gbp.scripts.import_srpm import main as import_srpm
from gbp.git import GitRepository
from gbp.rpm import SrcRpmFile

from tests.component import ComponentTestBase
from tests.component.rpm import RPM_TEST_DATA_DIR as DATA_DIR

# Disable "Method could be a function warning"
# pylint: disable=R0201

def mock_import(args):
    """Wrapper for import-srpm"""
    # Call import-orig-rpm with added arg0
    return import_srpm(['arg0'] + args)


class TestImportPacked(ComponentTestBase):
    """Test importing of src.rpm files"""

    def test_invalid_args(self):
        """See that import-srpm fails gracefully if called with invalid args"""
        eq_(mock_import([]), 1)
        with assert_raises(SystemExit):
            mock_import(['--invalid-arg=123'])

    def test_basic_import(self):
        """Test importing of non-native src.rpm"""
        srpm = os.path.join(DATA_DIR, 'gbp-test-1.0-1.src.rpm')
        eq_(mock_import(['--no-pristine-tar', srpm]), 0)
        # Check repository state
        repo = GitRepository('gbp-test')
        files =  set(['Makefile', 'README', 'bar.tar.gz', 'dummy.sh', 'foo.txt',
                  'gbp-test.spec', 'my.patch', 'mydir/myfile.txt'])
        self._check_repo_state(repo, 'master', ['master', 'upstream'], files)
        # Four commits: upstream, packaging files, one patch and the removal
        # of imported patches
        eq_(len(repo.get_commits()), 4)

    def test_basic_import2(self):
        """Import package with multiple spec files and full url patch"""
        srpm = os.path.join(DATA_DIR, 'gbp-test2-2.0-0.src.rpm')
        eq_(mock_import(['--no-pristine-tar', srpm]), 0)
        # Check repository state
        repo = GitRepository('gbp-test2')
        files = set(['Makefile', 'README', 'bar.tar.gz', 'dummy.sh', 'foo.txt',
                 'gbp-test2.spec', 'gbp-test2-alt.spec', 'my.patch',
                 'mydir/myfile.txt'])
        self._check_repo_state(repo, 'master', ['master', 'upstream'], files)

        # Four commits: upstream, packaging files, one patch and the removal
        # of imported patches
        eq_(len(repo.get_commits()), 4)

    def test_basic_import_orphan(self):
        """
        Test importing of non-native src.rpm to separate packaging and
        development branches
        """
        srpm = os.path.join(DATA_DIR, 'gbp-test2-2.0-0.src.rpm')
        eq_(mock_import(['--no-pristine-tar', '--orphan-packaging', srpm]), 0)
        # Check repository state
        repo = GitRepository('gbp-test2')
        files = set(['bar.tar.gz', 'foo.txt', 'gbp-test2.spec',
                 'gbp-test2-alt.spec', 'my.patch', 'my2.patch', 'my3.patch'])
        self._check_repo_state(repo, 'master', ['master', 'upstream'], files)
        # Only one commit: the packaging files
        eq_(len(repo.get_commits()), 1)

    def test_basic_native_import(self):
        """Test importing of native src.rpm"""
        srpm = os.path.join(DATA_DIR, 'gbp-test-native-1.0-1.src.rpm')
        eq_(mock_import(['--native', srpm]), 0)
        # Check repository state
        files = set(['.gbp.conf', 'Makefile', 'README', 'dummy.sh',
                 'packaging/gbp-test-native.spec'])
        repo = GitRepository('gbp-test-native')
        self._check_repo_state(repo, 'master', ['master'], files)
        # Only one commit: the imported source tarball
        eq_(len(repo.get_commits()), 1)

    def test_import_no_orig_src(self):
        """Test importing of (native) srpm without orig tarball"""
        srpm = os.path.join(DATA_DIR, 'gbp-test-native2-2.0-0.src.rpm')
        eq_(mock_import([srpm]), 0)
        # Check repository state
        repo = GitRepository('gbp-test-native2')
        self._check_repo_state(repo, 'master', ['master'])
        # Only one commit: packaging files
        eq_(len(repo.get_commits()), 1)

    def test_import_compressed_patches(self):
        """Test importing of non-native src.rpm with compressed patches"""
        srpm = os.path.join(DATA_DIR, 'gbp-test-1.1-2.src.rpm')
        eq_(import_srpm(['arg0', srpm]), 0)
        # Check repository state
        repo = GitRepository('gbp-test')
        files =  set(['Makefile', 'README', 'AUTHORS', 'NEWS', 'bar.tar.gz',
                    'dummy.sh', 'foo.txt', 'gbp-test.spec', 'my.patch',
                    'mydir/myfile.txt'])
        self._check_repo_state(repo, 'master', ['master', 'upstream'], files)
        # Four commits: upstream, packaging files, three patches and the removal
        # of imported patches
        eq_(len(repo.get_commits()), 6)

    def test_multiple_versions(self):
        """Test importing of multiple versions"""
        srpms = [ os.path.join(DATA_DIR, 'gbp-test-1.0-1.src.rpm'),
                  os.path.join(DATA_DIR, 'gbp-test-1.0-1.other.src.rpm'),
                  os.path.join(DATA_DIR, 'gbp-test-1.1-1.src.rpm') ]
        eq_(mock_import(['--no-pristine-tar', srpms[0]]), 0)
        repo = GitRepository('gbp-test')
        self._check_repo_state(repo, 'master', ['master', 'upstream'])
        eq_(len(repo.get_commits()), 4)
        # Try to import same version again
        eq_(mock_import([srpms[1]]), 0)
        eq_(len(repo.get_commits()), 4)
        eq_(len(repo.get_commits(until='upstream')), 1)
        eq_(mock_import(['--no-pristine-tar', '--allow-same-version',
                         srpms[1]]), 0)
        # Added new versio packaging plus one patch
        eq_(len(repo.get_commits()), 7)
        eq_(len(repo.get_commits(until='upstream')), 1)
        # Import new version
        eq_(mock_import(['--no-pristine-tar', srpms[2]]), 0)
        files = set(['Makefile', 'README', 'bar.tar.gz', 'dummy.sh', 'foo.txt',
                 'gbp-test.spec', 'my.patch', 'mydir/myfile.txt'])
        self._check_repo_state(repo, 'master', ['master', 'upstream'], files)
        eq_(len(repo.get_commits()), 11)
        eq_(len(repo.get_commits(until='upstream')), 2)
        # Check number of tags
        eq_(len(repo.get_tags('upstream/*')), 2)
        eq_(len(repo.get_tags('packaging/*')), 3)

    def test_import_to_existing(self):
        """Test importing to an existing repo"""
        srpm = os.path.join(DATA_DIR, 'gbp-test-1.0-1.src.rpm')

        # Create new repo
        repo = GitRepository.create('myrepo')
        os.chdir('myrepo')
        shutil.copy2('.git/HEAD', 'foobar')
        repo.add_files('.')
        repo.commit_all('First commit')

        # Test importing to non-clean repo
        shutil.copy2('.git/HEAD', 'foobaz')
        eq_(mock_import(['--create-missing', srpm]), 1)
        self._check_log(0, 'gbp:error: Repository has uncommitted changes')
        self._clear_log()
        os.unlink('foobaz')

        # The first import should fail because upstream branch is missing
        eq_(mock_import([srpm]), 1)
        self._check_log(-1, 'Also check the --create-missing-branches')
        eq_(mock_import(['--no-pristine-tar', '--create-missing', srpm]), 0)
        self._check_repo_state(repo, 'master', ['master', 'upstream'])
        # Four commits: our initial, upstream, packaging files, one patch,
        # and the removal of imported patches
        eq_(len(repo.get_commits()), 5)

        # The import should fail because missing packaging-branch
        srpm = os.path.join(DATA_DIR, 'gbp-test-1.1-1.src.rpm')
        eq_(mock_import(['--packaging-branch=foo', srpm]), 1)
        self._check_log(-1, 'Also check the --create-missing-branches')


    def test_filter(self):
        """Test filter option"""
        srpm = os.path.join(DATA_DIR, 'gbp-test-1.0-1.src.rpm')
        eq_(mock_import(['--no-pristine-tar', '--filter=README', '--filter=mydir', srpm]), 0)
        # Check repository state
        repo = GitRepository('gbp-test')
        files = set(['Makefile', 'dummy.sh', 'bar.tar.gz', 'foo.txt',
                 'gbp-test.spec', 'my.patch', 'mydir/myfile.txt'])
        self._check_repo_state(repo, 'master', ['master', 'upstream'], files)

    def test_tagging(self):
        """Test tag options of import-srpm"""
        srpm = os.path.join(DATA_DIR, 'gbp-test-1.0-1.src.rpm')

        # Invalid packaging tag keywords
        eq_(mock_import(['--no-pristine-tar', '--packaging-tag=%(foo)s', srpm]),
            1)
        self._check_log(-1, ".*Missing value 'foo' in {'release': '1', "
                            "'upstreamversion': '1.0', 'version': '1.0-1', "
                            "'vendor': 'downstream'}")
        # Remove upstream tag
        repo = GitRepository('gbp-test')
        repo.delete_tag('upstream/1.0')

        # Invalid upstream tag keywords
        eq_(mock_import(['--no-pristine-tar', '--upstream-tag=%(foo)s', srpm]),
            1)
        self._check_log(-1, ".*Missing value 'foo' in "
                            "{'upstreamversion': '1.0', 'version': '1.0'}")

        # Try with good keywords, with --skip-packaging-tag
        eq_(mock_import(['--no-pristine-tar', '--vendor=foo',
                         '--skip-packaging-tag',
                         '--packaging-tag=%(vendor)s/%(version)s',
                         '--upstream-tag=upst/%(version)s', srpm]), 0)
        eq_(repo.describe('upstream'), 'upst/1.0')
        eq_(len(repo.get_tags()), 1)

        # Re-import, creating packaging tag
        eq_(mock_import(['--no-pristine-tar', '--vendor=foo',
                         '--packaging-tag=%(vendor)s/%(version)s',
                         '--upstream-tag=upst/%(version)s', srpm]), 0)
        eq_(repo.describe('HEAD'), 'foo/1.0-1')
        eq_(len(repo.get_tags()), 2)

    def test_tagging_native(self):
        """Test tagging of native packages with import-srpm"""
        srpm = os.path.join(DATA_DIR, 'gbp-test-native-1.0-1.src.rpm')

        # Invalid packaging tag keywords
        eq_(mock_import(['--no-pristine-tar', '--packaging-tag=%(foo)s',
                         srpm, '--native']), 1)
        self._check_log(-1, ".*Missing value 'foo' in {'release': '1', "
                            "'upstreamversion': '1.0', 'version': '1.0-1', "
                            "'vendor': 'downstream'}")

        # Try with good keywords, with --skip-packaging-tag.
        # Upstream tag format should not matter
        eq_(mock_import(['--no-pristine-tar', '--vendor=foo', '--native',
                         '--skip-packaging-tag',
                         '--packaging-tag=%(vendor)s/%(version)s',
                         '--upstream-tag=%(foo)s', srpm]), 0)
        repo = GitRepository('gbp-test-native')
        eq_(len(repo.get_tags()), 0)

        # Run again, now creating packaging tag
        eq_(mock_import(['--no-pristine-tar', '--vendor=foo', '--native',
                         '--packaging-tag=%(vendor)s/%(version)s',
                         '--upstream-tag=%(foo)s', srpm]), 0)
        eq_(repo.describe('HEAD'), 'foo/1.0-1')


    def test_misc_options(self):
        """Test various options of git-import-srpm"""
        srpm = os.path.join(DATA_DIR, 'gbp-test2-2.0-0.src.rpm')

        eq_(mock_import(['--no-pristine-tar',
                    '--no-patch-import',
                    '--packaging-branch=pack',
                    '--upstream-branch=orig',
                    '--packaging-dir=packaging',
                    '--packaging-tag=ver_%(upstreamversion)s-rel_%(release)s',
                    '--upstream-tag=orig/%(upstreamversion)s',
                    '--author-is-committer',
                    srpm]), 0)
        # Check repository state
        repo = GitRepository('gbp-test2')
        files = set(['Makefile', 'README', 'dummy.sh', 'packaging/bar.tar.gz',
                 'packaging/foo.txt', 'packaging/gbp-test2.spec',
                 'packaging/gbp-test2-alt.spec', 'packaging/my.patch',
                 'packaging/my2.patch', 'packaging/my3.patch'])
        self._check_repo_state(repo, 'pack', ['pack', 'orig'], files)
        eq_(len(repo.get_commits()), 2)
        # Check packaging dir
        eq_(len(repo.get_commits(paths='packaging')), 1)
        # Check tags
        tags = repo.get_tags()
        eq_(set(tags), set(['orig/2.0', 'ver_2.0-rel_0']))
        # Check git committer/author
        info = repo.get_commit_info('pack')
        eq_(info['author'].name, 'Markus Lehtonen')
        eq_(info['author'].email, 'markus.lehtonen@linux.intel.com')
        eq_(info['author'].name, info['committer'].name)
        eq_(info['author'].email, info['committer'].email)


class TestImportUnPacked(ComponentTestBase):
    """Test importing of unpacked source rpms"""

    def setup(self):
        super(TestImportUnPacked, self).setup()
        # Unpack some source rpms
        os.mkdir('multi-unpack')
        for pkg in ['gbp-test-1.0-1.src.rpm', 'gbp-test2-2.0-0.src.rpm']:
            unpack_dir = pkg.replace('.src.rpm', '-unpack')
            os.mkdir(unpack_dir)
            pkg_path = os.path.join(DATA_DIR, pkg)
            SrcRpmFile(pkg_path).unpack(unpack_dir)
            SrcRpmFile(pkg_path).unpack('multi-unpack')

    def test_import_dir(self):
        """Test importing of directories"""
        eq_(mock_import(['--no-pristine-tar', 'gbp-test-1.0-1-unpack']), 0)
        # Check repository state
        repo = GitRepository('gbp-test')
        self._check_repo_state(repo, 'master', ['master', 'upstream'])

        # Check that importing dir with multiple spec files fails
        eq_(mock_import(['multi-unpack']), 1)
        self._check_log(-1, 'gbp:error: Failed determine spec file: '
                               'Multiple spec files found')

    def test_import_spec(self):
        """Test importing of spec file"""
        specfile = 'gbp-test2-2.0-0-unpack/gbp-test2.spec'
        eq_(mock_import([specfile]), 0)
        # Check repository state
        ok_(GitRepository('gbp-test2').is_clean())

    def test_missing_files(self):
        """Test importing of directory with missing packaging files"""
        specfile = 'gbp-test2-2.0-0-unpack/gbp-test2.spec'
        os.unlink('gbp-test2-2.0-0-unpack/my.patch')
        eq_(mock_import([specfile]), 1)
        self._check_log(-1, "gbp:error: File 'my.patch' listed in spec "
                            "not found")


class TestDownloadImport(ComponentTestBase):
    """Test download functionality"""

    def test_urldownload(self):
        """Test downloading and importing src.rpm from remote url"""
        srpm = 'http://raw.github.com/marquiz/git-buildpackage-rpm-testdata/'\
               'master/gbp-test-1.0-1.src.rpm'
        # Mock to use local files instead of really downloading
        local_fn = os.path.join(DATA_DIR, os.path.basename(srpm))
        urllib2.urlopen = Mock()
        urllib2.urlopen.return_value = open(local_fn, 'r')

        eq_(mock_import(['--no-pristine-tar', '--download', srpm]), 0)
        # Check repository state
        repo = GitRepository('gbp-test')
        self._check_repo_state(repo, 'master', ['master', 'upstream'])

    def test_nonexistent_url(self):
        """Test graceful failure when trying download from nonexistent url"""
        srpm = 'http://url.does.not.exist.com/foo.src.rpm'
        # Do not connect to remote, mock failure
        urllib2.urlopen = Mock()
        urllib2.urlopen.side_effect = urllib2.HTTPError(srpm, 404, "Not found",
                                                        None, None)

        eq_(mock_import(['--download', srpm]), 1)
        self._check_log(-1, "gbp:error: Download failed: HTTP Error 404")
        self._clear_log()

    def test_invalid_url(self):
        """Test graceful failure when trying download from invalid url"""
        srpm = 'foob://url.does.not.exist.com/foo.src.rpm'
        eq_(mock_import(['--download', srpm]), 1)
        self._check_log(-1, "gbp:error: Download failed: unknown url type:")
        self._clear_log()


class TestPristineTar(ComponentTestBase):
    """Test importing with pristine-tar"""

    @classmethod
    def setup_class(cls):
        if not os.path.exists('/usr/bin/pristine-tar'):
            raise SkipTest('Skipping %s:%s as pristine-tar tool is not '
                           'available' % (__name__, cls.__name__))
        super(TestPristineTar, cls).setup_class()

    def test_basic_import_pristine_tar(self):
        """Test importing of non-native src.rpm, with pristine-tar"""
        srpm = os.path.join(DATA_DIR, 'gbp-test-1.0-1.src.rpm')
        eq_(mock_import(['--pristine-tar', srpm]), 0)
        # Check repository state
        repo = GitRepository('gbp-test')
        self._check_repo_state(repo, 'master', ['master', 'upstream',
                               'pristine-tar'])
        # Four commits: upstream, packaging files, one patch and the removal
        # of imported patches
        eq_(len(repo.get_commits()), 4)

    def test_unsupported_archive(self):
        """Test importing of src.rpm with a zip source archive"""
        srpm = os.path.join(DATA_DIR, 'gbp-test-native-1.0-1.src.rpm')
        eq_(mock_import(['--pristine-tar', srpm]), 0)
        # Check repository state
        repo = GitRepository('gbp-test-native')
        self._check_repo_state(repo, 'master', ['master', 'upstream'])
        # Check that a warning is printed
        self._check_log(-1, "gbp:warning: Ignoring pristine-tar")


class TestBareRepo(ComponentTestBase):
    """Test importing to a bare repository"""

    def test_basic_import_to_bare_repo(self):
        """Test importing of srpm to a bare git repository"""
        srpm = os.path.join(DATA_DIR, 'gbp-test-1.0-1.src.rpm')
        # Create new repo
        repo = GitRepository.create('myrepo', bare=True)
        os.chdir('myrepo')
        eq_(mock_import([srpm]), 0)
        self._check_repo_state(repo, 'master', ['master', 'upstream'])
        # Patch import to bare repos not supported -> only 2 commits
        eq_(len(repo.get_commits(until='master')), 2)

# vim:et:ts=4:sw=4:et:sts=4:ai:set list listchars=tab\:»·,trail\:·:
