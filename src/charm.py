#!/usr/bin/env python3
# Copyright 2020 craig.bender@canonical.com
# See LICENSE file for licensing details.

import logging
import json
import os
import subprocess
import random
import string
import yaml
from pathlib import Path
from ops.charm import CharmBase, CharmEvents
from ops.framework import StoredState
from ops.main import main
from ops.model import (
    ActiveStatus,
    BlockedStatus,
    MaintenanceStatus,
    WaitingStatus,
	Network,
)

logger = logging.getLogger(__name__)

class Microk8sClusterCharm(CharmBase):
	"""MicroK8s Cluster Charm."""
	_stored = StoredState()
	
	def __init__(self, *args):
		super().__init__(*args)
		self.framework.observe(self.on.install, self._on_install)
		self.framework.observe(self.on.start, self._on_start)
		self.framework.observe(self.on.remove, self._on_remove)
		# -- initialize states --
		self._stored.set_default(installed=False)
		self._stored.set_default(started=False)
		self._stored.set_default(clustered=False)
		self._stored.set_default(remove=False)
		self._stored.set_default(unitname=os.environ["JUJU_UNIT_NAME"])

	def _on_install(self, event):
		if self.state.installed:
			return
		self.unit.status = MaintenanceStatus("Installing microk8s")
		cmd = 'sudo snap install microk8s --classic'
		subprocess.call(cmd, shell=True)
		self._stored.installed = True

	def _on_start(self, event):
		if not self.state.installed:
			event.defer()
		if self.state.started:
			return		
		self.unit.status = MaintenanceStatus("Configuring microk8s")
		cmd1 = 'sudo usermod -a -G microk8s $(id -un 1000)'
		cmd2 = 'sudo chown -f -R $(id -un 1000) /home/$(id -un 1000)/.kube'
		subprocess.call(cmd1, shell=True)
		subprocess.call(cmd2, shell=True)
		self._stored.started = True
		init_cluster()

	def init_cluster():
		if not self.state.started:
			event.defer()
		if not self.unit.is_leader():
			self.unit.status = WaitingStatus("Waiting for leadership")
			return
		token = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(length))
		cmd = 'sudo microk8s.add-node --token '+ token +' --token-ttl=900'
		subprocess.call(cmd, shell=True)
		self._stored.cluster_token = token

	def _on_remove(self, event):
		self.unit.status = MaintenanceStatus("Leaving cluster")
		cmd = 'microk8s leave'
		subprocess.call(cmd, shell=True)
		self._stored.remove = True

if __name__ == "__main__":
	main(Microk8sClusterCharm)

