# jhbuild - a build script for GNOME 1.x and 2.x
# Copgyright (C) 2001-2003  James Henstridge
#
#   bootstrap.py: code to check whether prerequisite modules are installed
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from commands import getoutput
import os
import string
import urllib

term = os.environ.get('TERM', '')
_isxterm = term.find('xterm') >= 0 or term == 'rxvt'
del term
_boldcode = getoutput('tput bold')
_normal = getoutput('tput sgr0')

jhbuild_directory = os.path.split(os.path.abspath(__file__))[0]

class Bootstrap:
    def __init__(self, package, version, sourceurl, sourcesize, patches=[],
                 versioncheck=None):
        self.package = package
        self.version = version
        self.sourceurl = sourceurl
        self.sourcesize = sourcesize
        self.patches = patches
        self.versioncheck = versioncheck
        
    def _bold(self, msg):
        print '%s*** %s ***%s' % (_boldcode, msg, _normal)
        if _isxterm:
            print '\033]0;jhbuild: %s\007' % msg
            
    def _execute(self, command):
        print command
        ret = os.system(command)
        print
        return ret
    
    def wants_package(self):
        self._bold('checking for %s %s' % (self.package, self.version))
        if self.versioncheck:
            out = os.popen(self.versioncheck, 'r').read()
            if out == '':
                print 'package not found'
            elif string.find(out, string.replace(self.version, 'x', '')) >= 0:
                print 'package found'
                val = raw_input('do you want to install %s %s [y/N]? '
                                % (self.package, self.version))
                if val and string.lower(val)[0] == 'y':
                    return 1
                else:
                    return 0
            else:
                if out[-1] == '\n':
                    out = out[:-1]
                print 'might be okay:'
                print out
        val = raw_input('do you want to install %s %s [Y/n]? '
                        % (self.package, self.version))
        if val and string.lower(val)[0] == 'n':
            return 0
        return 1

    def build(self, config):
        if not self.wants_package():
            return

        # get the source package
        buildroot = config['checkoutroot']
        localfile = os.path.join(buildroot, os.path.basename(self.sourceurl))
        if not os.path.exists(localfile) or \
           os.stat(localfile)[6] != self.sourcesize:
            while 1:
                self._bold('downloading %s' % self.sourceurl)
                try:
                    urllib.urlretrieve(self.sourceurl, localfile)
                    if os.stat(localfile)[6] == self.sourcesize:
                        break # we got the file
                    print 'downloaded file does not match expected size'
                except IOError, e:
                    print 'Could not download file. Exception was: '
                    print e
                val = raw_input('try downloading again? ')
                if val and string.lower(val)[0] == 'n':
                    return
        
        # untar the source package
        os.chdir(buildroot)
        localfile = os.path.basename(self.sourceurl)
        self._bold('untaring %s' % localfile)
        if localfile.endswith('.bz2'):
            ret = self._execute('bzip2 -dc %s | tar xf -' % localfile)
        else:
            ret = self._execute('gzip -dc %s | tar xf -' % localfile)
        if ret != 0:
            print 'failed to untar', self.package
            return

        # change to package directory
        if localfile.endswith('.tar.gz'):
            os.chdir(localfile[:-7])
        elif localfile.endswith('.tgz'):
            os.chdir(localfile[:-4])
        elif localfile.endswith('.tar.bz2'):
            os.chdir(localfile[:-8])
        else:
            print 'unknown package extension: ', self.package
            return

        # is there a patch to apply?
        for patch_filename, patch_options in self.patches:
            patchfile = os.path.join(jhbuild_directory, patch_filename)
            self._bold('applying patch %s' % patch_filename)
            ret = self._execute('patch -p%d < %s' % (patch_options, patchfile))
            if ret != 0:
                print 'failed to patch', self.package
                return

        # configure ...
        self._bold('configuring %s' % self.package)
        ret = self._execute('./configure --prefix %s' % config['prefix'])
        if ret != 0:
            print 'failed to configure', self.package
            return

        # make
        self._bold('building %s' % self.package)
        ret = self._execute('make')
        if ret != 0:
            print 'failed to build', self.package
            return
        
        # install
        self._bold('installing %s' % self.package)
        ret = self._execute('make install')
        if ret != 0:
            print 'failed to install', self.package
            return

bootstraps = [
    Bootstrap('gettext', '0.11.5',
              'http://ftp.gnu.org/gnu/gettext/gettext-0.11.5.tar.gz',
              3724099,
              [('gettext-changelog.patch', 1)],  # patch to unbreak gettext ...
              'gettextize --version | head -1'),
    Bootstrap('autoconf', '2.57',
              'http://ftp.gnu.org/gnu/autoconf/autoconf-2.57.tar.gz',
              1074128,
              [],
	      'autoconf --version | head -1'),
    Bootstrap('libtool', '1.5',
              'http://ftp.gnu.org/gnu/libtool/libtool-1.5.tar.gz',
              2816075,
              [('libtool-1.3.5-mktemp.patch' , 1),
               ('libtool-1.4.3-ltmain-SED.patch', 1),
               ('libtool-1.4.2-expsym-linux.patch', 1)],
              'libtoolize --version | head -1'),
    Bootstrap('automake-1.4', '1.4-p6',
              'http://ftp.gnu.org/gnu/automake/automake-1.4-p6.tar.gz',
              375060,
              [],
              'automake-1.4 --version | head -1'),
    Bootstrap('automake-1.6', '1.6.3',
              'http://ftp.gnu.org/gnu/automake/automake-1.6.3.tar.gz',
              609618,
              [],
              'automake-1.6 --version | head -1'),
    Bootstrap('automake-1.7', '1.7.8',
              'http://ftp.gnu.org/gnu/automake/automake-1.7.8.tar.gz',
              736697,
              [],
              'automake-1.7 --version | head -1'),
    Bootstrap('pkg-config', '0.15.0',
              'http://www.freedesktop.org/software/pkgconfig/releases/pkgconfig-0.15.0.tar.gz',
              610697,
              [],
              'pkg-config --version'),
    Bootstrap('python', '2.x',
              'http://www.python.org/ftp/python/2.3.2/Python-2.3.2.tar.bz2',
              7161770,
              [],
              'echo "import sys, string; print string.split(sys.version)[0]" | python -'),
    Bootstrap('audiofile', '0.2.3',
              'http://www.68k.org/~michael/audiofile/audiofile-0.2.4.tar.gz',
              360358, 
              [],
              'audiofile-config --version'),
]

def build_bootstraps(config):
    for bootstrap in bootstraps:
        bootstrap.build(config)
