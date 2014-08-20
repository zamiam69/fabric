from __future__ import with_statement

from datetime import datetime
import copy
import getpass
import sys

from nose.tools import with_setup, ok_, raises
from fudge import (Fake, clear_calls, clear_expectations, patch_object, verify,
    with_patched_object, patched_context, with_fakes)

from fabric.context_managers import settings, hide, show
from fabric.network import (HostConnectionCache, join_host_strings, normalize,
    denormalize, key_filenames, ssh)
from fabric.io import output_loop
import fabric.network  # So I can call patch_object correctly. Sigh.
from fabric.state import env, output, _get_system_username
from fabric.operations import run, sudo, prompt
from fabric.exceptions import NetworkError
from fabric.tasks import execute
from fabric.api import parallel
from fabric import utils # for patching

from utils import *
from server import (server, PORT, RESPONSES, PASSWORDS, CLIENT_PRIVKEY, USER,
    CLIENT_PRIVKEY_PASSPHRASE)


#
# Subroutines, e.g. host string normalization
#

class TestSSHConfig(FabricTest):
    def env_setup(self):
        super(TestSSHConfig, self).env_setup()
        env.use_ssh_config = True
        env.ssh_config_path = support("ssh_config_2")
        # Undo the changes FabricTest makes to env for server support
        env.user = env.local_user
        env.port = env.default_port

    def test_global_user_with_default_env(self):
        """
        Global User should override default env.user
        """
        eq_(normalize("localhost")[0], "satan")

    def test_global_user_with_nondefault_env(self):
        """
        Global User should NOT override nondefault env.user
        """
        with settings(user="foo"):
            eq_(normalize("localhost")[0], "foo")

    def test_specific_user_with_default_env(self):
        """
        Host-specific User should override default env.user
        """
        eq_(normalize("myhost")[0], "neighbor")

    def test_user_vs_host_string_value(self):
        """
        SSH-config derived user should NOT override host-string user value
        """
        eq_(normalize("myuser@localhost")[0], "myuser")
        eq_(normalize("myuser@myhost")[0], "myuser")

    def test_global_port_with_default_env(self):
        """
        Global Port should override default env.port
        """
        eq_(normalize("localhost")[2], "666")

    def test_global_port_with_nondefault_env(self):
        """
        Global Port should NOT override nondefault env.port
        """
        with settings(port="777"):
            eq_(normalize("localhost")[2], "777")

    def test_specific_port_with_default_env(self):
        """
        Host-specific Port should override default env.port
        """
        eq_(normalize("myhost")[2], "664")

    def test_port_vs_host_string_value(self):
        """
        SSH-config derived port should NOT override host-string port value
        """
        eq_(normalize("localhost:123")[2], "123")
        eq_(normalize("myhost:123")[2], "123")

    def test_hostname_alias(self):
        """
        Hostname setting overrides host string's host value
        """
        eq_(normalize("localhost")[1], "localhost")
        eq_(normalize("myalias")[1], "otherhost")

    def test_host_with_leading_wildcard(self):
        """
        Check leading wildcard handling
        """
        eq_(normalize("blubb.bla")[0], "lucifer")
        eq_(normalize("blubb.bla")[1], "127.6.6.6")

    def test_host_with_trailing_wildcard(self):
        """
        Check trailing wildcard handling
        """
        eq_(normalize("blubb.baz")[0], "favourite")
        eq_(normalize("blubb.baz")[1], "127.7.7.7")

    @with_patched_object(utils, 'warn', Fake('warn', callable=True,
        expect_call=True))
    def test_warns_with_bad_config_file_path(self):
        # use_ssh_config is already set in our env_setup()
        with settings(hide('everything'), ssh_config_path="nope_bad_lol"):
            normalize('foo')

    @server()
    def test_real_connection(self):
        """
        Test-server connection using ssh_config values
        """
        with settings(
            hide('everything'),
            ssh_config_path=support("testserver_ssh_config"),
            host_string='testserver',
        ):
            ok_(run("ls /simple").succeeded)

