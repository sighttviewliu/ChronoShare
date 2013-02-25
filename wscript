# -*- Mode: python; py-indent-offset: 4; indent-tabs-mode: nil; coding: utf-8; -*-
import os

VERSION='0.1'
APPNAME='chronoshare'

from waflib import Build, Logs, Utils

def options(opt):
    opt.add_option('--debug',action='store_true',default=False,dest='debug',help='''debugging mode''')
    opt.add_option('--test', action='store_true',default=False,dest='_test',help='''build unit tests''')
    opt.add_option('--yes',action='store_true',default=False) # for autoconf/automake/make compatibility
    opt.add_option('--log4cxx', action='store_true',default=False,dest='log4cxx',help='''Compile with log4cxx logging support''')

    if Utils.unversioned_sys_platform () == "darwin":
        opt.add_option('--autoupdate', action='store_true',default=False,dest='autoupdate',help='''(OSX) Download sparkle framework and enable autoupdate feature''')

    opt.load('compiler_c compiler_cxx boost ccnx protoc qt4')

def check_framework(conf, name, **kwargs):
  frameworkLocations = (os.environ.get('HOME') + '/Library/Frameworks'
                        , '/opt/local/Library/Frameworks'
                        , '/Library/Frameworks'
                        , '/Network/Library/Frameworks'
                        , '/System/Library/Frameworks'
                        )
  uselib = name.upper()
  frameworkName = name + ".framework"
  found = False
  for frameworkLocation in frameworkLocations:
    dynamicLib = os.path.join(frameworkLocation, frameworkName, name)
    if os.path.exists(dynamicLib):
      conf.env.append_unique('FRAMEWORK_' + uselib, name)
      conf.msg('Checking for %s' % name, dynamicLib, 'GREEN')
      conf.env.append_unique('INCLUDES_' + uselib, os.path.join(frameworkLocation, frameworkName, 'Headers'))
      found = True
      define_name = kwargs.get('define_name', None)
      if define_name is not None:
        conf.define(define_name, 1)
      break

  if not found:
    mandatory = kwargs.get('mandatory', True)
    if mandatory:
      conf.fatal('Cannot find ' + frameworkName)
    else:
      conf.msg('Checking for %s' % name, False, 'YELLOW')

def configure(conf):
    conf.load("compiler_c compiler_cxx")

    conf.define ("CHRONOSHARE_VERSION", VERSION)

    conf.check_cfg(package='sqlite3', args=['--cflags', '--libs'], uselib_store='SQLITE3', mandatory=True)
    conf.check_cfg(package='libevent', args=['--cflags', '--libs'], uselib_store='LIBEVENT', mandatory=True)
    conf.check_cfg(package='libevent_pthreads', args=['--cflags', '--libs'], uselib_store='LIBEVENT_PTHREADS', mandatory=True)

    if Utils.unversioned_sys_platform () == "darwin":
        conf.check_cxx(framework_name='Foundation', uselib_store='OSX_FOUNDATION', mandatory=False, compile_filename='test.mm')
        conf.check_cxx(framework_name='CoreWLAN',   uselib_store='OSX_COREWLAN',   define_name='HAVE_COREWLAN', mandatory=False, compile_filename='test.mm')

        if conf.options.autoupdate:
            try:
                # Try standard paths first
                conf.check_cxx (framework_name='Sparkle', header_name="Foundation/Foundation.h",
                                uselib_store='OSX_SPARKLE', define_name='HAVE_SPARKLE', mandatory=True, compile_filename='test.mm')
            except:
                try:
                    # Try local path
                    Logs.info ("Check local version of Sparkle framework")
                    conf.check_cxx (framework_name='Sparkle', header_name="Foundation/Foundation.h",
                                    uselib_store='OSX_SPARKLE', define_name='HAVE_SPARKLE', mandatory=True,
                                    cxxflags="-F%s/build/Sparkle" % conf.path.abspath(),
                                    linkflags="-F%s/build/Sparkle" % conf.path.abspath(), compile_filename='test.mm')
                except:
                    # Download to local path and retry
                    Logs.info ("Sparkle framework not found, trying to download it to 'build/'")

                    import urllib, subprocess, os
                    urllib.urlretrieve ("http://sparkle.andymatuschak.org/files/Sparkle%201.5b6.zip", "build/Sparkle.zip")
                    subprocess.call ("unzip build/Sparkle.zip -d build/Sparkle", shell=True)
                    os.remove ("build/Sparkle.zip")

                    conf.check_cxx (framework_name='Sparkle', header_name="Foundation/Foundation.h",
                                    uselib_store='OSX_SPARKLE', define_name='HAVE_SPARKLE', mandatory=True,
                                    cxxflags="-F%s/build/Sparkle" % conf.path.abspath(),
                                    linkflags="-F%s/build/Sparkle" % conf.path.abspath(), compile_filename='test.mm')
            if conf.is_defined('HAVE_SPARKLE'):
                conf.env.HAVE_SPARKLE = 1 # small cheat for wscript

    if not conf.check_cfg(package='openssl', args=['--cflags', '--libs'], uselib_store='SSL', mandatory=False):
        libcrypto = conf.check_cc(lib='crypto',
                                  header_name='openssl/crypto.h',
                                  define_name='HAVE_SSL',
                                  uselib_store='SSL')
    else:
        conf.define ("HAVE_SSL", 1)
    if not conf.get_define ("HAVE_SSL"):
        conf.fatal ("Cannot find SSL libraries")

    if conf.options.log4cxx:
        conf.check_cfg(package='liblog4cxx', args=['--cflags', '--libs'], uselib_store='LOG4CXX', mandatory=True)
        conf.define ("HAVE_LOG4CXX", 1)

    conf.load ('ccnx')

    conf.load('protoc')

    conf.load('qt4')

    conf.load('boost')

    conf.check_boost(lib='system test iostreams filesystem regex thread')

    boost_version = conf.env.BOOST_VERSION.split('_')
    if int(boost_version[0]) < 1 or int(boost_version[1]) < 46:
        Logs.error ("Minumum required boost version is 1.46")
        return

    conf.check_ccnx (path=conf.options.ccnx_dir)
    conf.define ('CCNX_PATH', conf.env.CCNX_ROOT)

    if conf.options.debug:
        conf.define ('_DEBUG', 1)
        conf.env.append_value('CXXFLAGS', ['-O0', '-Wall', '-Wno-unused-variable', '-g3'])
    else:
        conf.env.append_value('CXXFLAGS', ['-O3', '-g'])

    if conf.env["CXX"] == ["clang++"]:
        conf.env.append_value('CXXFLAGS', ['-fcolor-diagnostics', '-Qunused-arguments'])

    if conf.options._test:
        conf.define ('_TESTS', 1)
        conf.env.TEST = 1

    conf.write_config_header('src/config.h')

def build (bld):
    executor = bld.objects (
        target = "executor",
        features = ["cxx"],
        source = bld.path.ant_glob(['executor/**/*.cc']),
        use = 'BOOST BOOST_THREAD LIBEVENT LIBEVENT_PTHREADS LOG4CXX',
        includes = "executor src",
        )

    scheduler = bld.objects (
        target = "scheduler",
        features = ["cxx"],
        source = bld.path.ant_glob(['scheduler/**/*.cc']),
        use = 'BOOST BOOST_THREAD LIBEVENT LIBEVENT_PTHREADS LOG4CXX executor',
        includes = "scheduler executor src",
        )

    libccnx = bld (
        target="ccnx",
        features=['cxx'],
        source = bld.path.ant_glob(['ccnx/**/*.cc', 'ccnx/**/*.cpp']),
        use = 'BOOST BOOST_THREAD SSL CCNX LOG4CXX scheduler executor',
        includes = "ccnx src scheduler executor",
        )

    adhoc = bld (
        target = "adhoc",
        features=['cxx'],
        includes = "ccnx src",
    )
    if Utils.unversioned_sys_platform () == "darwin":
        adhoc.mac_app = True
        adhoc.source = 'adhoc/adhoc-osx.mm'
        adhoc.use = "OSX_FOUNDATION OSX_COREWLAN"

    chornoshare = bld (
        target="chronoshare",
        features=['cxx'],
        source = bld.path.ant_glob(['src/**/*.cc', 'src/**/*.cpp', 'src/**/*.proto']),
        use = "BOOST BOOST_FILESYSTEM SQLITE3 LOG4CXX scheduler ccnx",
        includes = "ccnx scheduler src executor",
        )

    fs_watcher = bld (
        target = "fs_watcher",
        features = "qt4 cxx",
        defines = "WAF",
        source = bld.path.ant_glob(['fs-watcher/*.cc']),
        use = "SQLITE3 LOG4CXX scheduler executor QTCORE",
        includes = "fs-watcher scheduler executor src",
        )

    # Unit tests
    if bld.env['TEST']:
      unittests = bld.program (
          target="unit-tests",
          features = "qt4 cxx cxxprogram",
          defines = "WAF",
          source = bld.path.ant_glob(['test/*.cc']),
          use = 'BOOST_TEST BOOST_FILESYSTEM LOG4CXX SQLITE3 QTCORE QTGUI ccnx database fs_watcher chronoshare',
          includes = "ccnx scheduler src executor gui fs-watcher",
          install_prefix = None,
          )

    qt = bld (
        target = "ChronoShare",
        features = "qt4 cxx cxxprogram",
        defines = "WAF",
        source = bld.path.ant_glob(['gui/*.cpp', 'gui/*.cc', 'gui/*.qrc']),
        includes = "ccnx scheduler executor fs-watcher gui src adhoc . ",
        use = "BOOST BOOST_FILESYSTEM SQLITE3 QTCORE QTGUI LOG4CXX fs_watcher ccnx database chronoshare"
        )

    if Utils.unversioned_sys_platform () == "darwin":
        app_plist = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist SYSTEM "file://localhost/System/Library/DTDs/PropertyList.dtd">
<plist version="0.9">
<dict>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleGetInfoString</key>
    <string>Created by Waf</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>NOTE</key>
    <string>THIS IS A GENERATED FILE, DO NOT MODIFY</string>
    <key>CFBundleExecutable</key>
    <string>%s</string>
    <key>LSUIElement</key>
    <string>1</string>
</dict>
</plist>'''
        qt.mac_app = "ChronoShare.app"
        qt.mac_plist = app_plist % "ChronoShare"
        qt.use += " OSX_FOUNDATION OSX_COREWLAN adhoc"

        if bld.env['HAVE_SPARKLE']:
            qt.use += " OSX_SPARKLE"
            qt.source += ["osx/auto-update/sparkle-auto-update.mm"]
            qt.includes += " osx/auto-update"

    cmdline = bld (
        target = "csd",
	features = "qt4 cxx cxxprogram",
	defines = "WAF",
	source = "cmd/csd.cc",
	includes = "ccnx scheduler executor gui fs-watcher src . ",
	use = "BOOST BOOST_FILESYSTEM SQLITE3 QTCORE QTGUI LOG4CXX fs_watcher ccnx database chronoshare"
	)

    dump_db = bld (
        target = "dump-db",
        features = "cxx cxxprogram",
	source = "cmd/dump-db.cc",
	includes = "ccnx scheduler executor gui fs-watcher src . ",
	use = "BOOST BOOST_FILESYSTEM SQLITE3 QTCORE LOG4CXX fs_watcher ccnx database chronoshare"
        )

from waflib import TaskGen
@TaskGen.extension('.mm')
def m_hook(self, node):
    """Alias .mm files to be compiled the same as .cc files, gcc/clang will do the right thing."""
    return self.create_compiled_task('cxx', node)
