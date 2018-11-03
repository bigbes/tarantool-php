#!/usr/bin/env python
# pylint: disable=missing-docstring
from __future__ import print_function

import os
import sys
import shutil
import subprocess

from lib.tarantool_server import TarantoolServer

PHPUNIT_PHAR = 'phpunit.phar'

def read_popen(cmd):
    path = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    path.wait()
    return path.stdout.read()

def read_popen_config(cmd):
    cmd = os.environ.get('PHP_CONFIG', 'php-config') + ' ' + cmd
    return read_popen(cmd)

def find_php_bin():
    path = read_popen('which php').strip().decode()
    if path.find('phpenv') != -1:
        version = read_popen('phpenv global')
        if version.find('system') != -1:
            return '/usr/bin/php'
        return '~/.phpenv/versions/{0}/bin/php'.format(version.strip())
    return path

def prepare_env(php_ini):
    if os.path.isdir('var'):
        shutil.rmtree('var')
    if not os.path.isdir('var') and not os.path.exists('var'):
        os.mkdir('var')
    shutil.copy('test/shared/phpunit.xml', 'var')
    # test_dir_path = os.path.abspath(os.path.join(os.getcwd(), 'test'))
    # test_lib_path = os.path.join(test_dir_path, PHPUNIT_PHAR)
    # shutil.copy('test/shared/tarantool.ini', 'var')
    shutil.copy(php_ini, 'var')
    shutil.copy('modules/tarantool.so', 'var')

def run_tests(vardir):
    test_dir_path = os.path.abspath(os.path.join(os.getcwd(), 'test'))
    test_cwd = os.path.dirname(vardir)
    test_lib_path = ""
    try:
        shutil.copy('test/shared/phpunit.xml', os.path.join(test_cwd, 'phpunit.xml'))
        shutil.copy('modules/tarantool.so', test_cwd)
        test_lib_path = os.path.join(test_dir_path, PHPUNIT_PHAR)

        version = read_popen_config('--version').decode().strip(' \n\t') + '.'
        version1 = read_popen_config('--extension-dir').decode().strip(' \n\t')
        version += '\n' + ('With' if version1.find('non-zts') == -1 else 'Without') + ' ZTS'
        version += '\n' + ('With' if version1.find('no-debug') == -1 else 'Without') + ' Debug'
        print('Running against ' + version)

        for php_ini in [
                'test/shared/tarantool-1.ini',
                'test/shared/tarantool-2.ini',
                'test/shared/tarantool-3.ini'
        ]:
            cmd = ''
            shutil.copy(php_ini, os.path.join(test_cwd, 'tarantool.ini'))
            if '--flags' in sys.argv:
                os.environ['ZEND_DONT_UNLOAD_MODULES'] = '1'
                os.environ['USE_ZEND_ALLOC'] = '0'
                os.environ['MALLOC_CHECK_'] = '3'
            if '--valgrind' in sys.argv:
                cmd = cmd + 'valgrind --leak-check=full --show-leak-kinds=all --log-file='
                cmd = cmd + os.path.basename(php_ini).split('.')[0] + '.out'
                cmd = cmd + ' --suppressions=test/shared/valgrind.sup'
                # cmd = cmd + ' --track-origins=yes'
                cmd = cmd + ' --keep-stacktraces=alloc-and-free'
                cmd = cmd + ' --freelist-vol=2000000000'
                cmd = cmd + ' --malloc-fill=0 --free-fill=0'
                cmd = cmd + ' --num-callers=50 ' + find_php_bin()
                cmd = cmd + ' -c tarantool.ini {0}'.format(test_lib_path)
            elif '--gdb' in sys.argv:
                cmd = cmd + 'gdb {0} --ex '.format(find_php_bin())
                cmd = cmd + '"set args -c tarantool.ini {0}"'.format(test_lib_path)
            elif '--lldb' in sys.argv:
                cmd = cmd + 'lldb -- {0} -c tarantool.ini {1}'.format(find_php_bin(), test_lib_path)
            elif '--strace' in sys.argv:
                cmd = cmd + 'strace ' + find_php_bin()
                cmd = cmd + ' -c tarantool.ini {0}'.format(test_lib_path)
            elif '--dtruss' in sys.argv:
                cmd = cmd + 'sudo dtruss ' + find_php_bin()
                cmd = cmd + ' -c tarantool.ini {0}'.format(test_lib_path)
            else:
                print(find_php_bin())
                cmd = '{0} -c tarantool.ini {1}'.format(find_php_bin(), test_lib_path)
                print(cmd)

            print('Running "%s" with "%s"' % (cmd, php_ini))
            proc = subprocess.Popen(cmd, shell=True, cwd=test_cwd)
            if proc.wait() != 0:
                print('Error')
                return
            if '--gdb' in sys.argv or '--lldb' in sys.argv:
                return

    finally:
        for elem in [
                os.path.join(test_cwd, 'tarantool.ini'),
                os.path.join(test_cwd, 'phpunit.xml'),
                os.path.join(test_cwd, 'tarantool.so'),
        ]:
            if os.path.exists(elem):
                os.remove(elem)

def test_tcp():
    # prepare, start Tarantool on TCP socket
    srv = TarantoolServer()
    srv.script = 'test/shared/box.lua'
    srv.start()

    run_tests(srv.vardir)

def test_unix():
    # prepare, start Tarantool on Unix socket
    srv = TarantoolServer()
    srv.script = 'test/shared/box.lua'
    srv.use_unix = True
    srv.start()

    run_tests(srv.vardir)

def main():
    # change dir
    path = os.path.dirname(sys.argv[0])
    if not path:
        path = '.'
    os.chdir(path)
    # if preparation mode is enabled - prepare directory and exit
    if '--prepare' in sys.argv:
        prepare_env('test/shared/tarantool-1.ini')
        exit(0)

    if '--tcp' in sys.argv or '--unix' not in sys.argv:
        test_tcp()

    if '--unix' in sys.argv:
        test_unix()

    return 0

exit(main())
