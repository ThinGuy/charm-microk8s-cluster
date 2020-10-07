from charms.reactive import (
    when,
    when_not,
    set_flag,
    clear_flag
)
from charmhelpers.core.hookenv import (
    action_get,
    action_set,
    action_fail,
    status_set
)
from charmhelpers.fetch import apt_install
import subprocess
import traceback
import logging


@when('snap.installed.microk8s')
def config_microk8s():
    subprocess.call(
        'sudo usermod -a -G microk8s ubuntu',
        shell=True
    )
    set_flag('microk8s-cluster.configured')


@when('microk8s-cluster.configured')
@when_not('microk8s-cluster.installed')
def install_microk8s_cluster():
    apt_install('hello')
    set_flag('microk8s-cluster.installed')
    status_set('active', 'MicroK8s installed. Ready to cluster!')


@when('actions.microk8s-cmd', 'microk8s-cluster.installed')
def microk8s_cmd():
    try:
        command = action_get('command')
        output, _ = subprocess.check_output(
            'microk8s.{}'.format(command),
            shell=True
        )
    except Exception as e:
        action_fail('command failed: {}'.format(e))
        logging.error('Traceback: {}'.format(traceback.format_exc()))
    else:
        action_set({'output': output})
    finally:
        clear_flag('actions.microk8s-cmd')
