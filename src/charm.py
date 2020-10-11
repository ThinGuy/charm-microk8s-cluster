#!/usr/bin/env python3
# Copyright 2020 craig.bender@canonical.com
# See LICENSE file for licensing details.

import logging
import json
import os
import subprocess
import random
import string
import socket
import yaml
from pathlib import Path
import apt

from ops.charm import CharmBase
from ops.main import main
from ops.framework import StoredState
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus, WaitingStatus, Network

logger = logging.getLogger(__name__)

class Microk8sClusterCharm(CharmBase):
	"""MicroK8s Cluster Charm."""
	stored = StoredState()

	def __init__(self, *args):
		"""Charm initialization for events observation."""
		super().__init__(*args)
		self.framework.observe(self.on.install, self)
		self.framework.observe(self.on.configure, self)
		if not self.unit.is_leader():
			 self.unit.status = WaitingStatus("Waiting for leadership")
			 return

	def on_install(self, event):
		"""Handle install state."""
		self.unit.status = MaintenanceStatus("Installing microk8s")
		self.state.installed = snap_install('microk8s')

	def check_tokens():
		if not self.unit.is_leader():
			return
		cmd = 'awk 2>/dev/null -F"|" '"'"'/\||^$/{if ($1=="") next;T=$1;NOW=(strftime(systime()));EXP=(strftime("%H:%M:%S",($2-NOW)));if ($2 -gt NOW) print T;next}'"'"' /var/snap/microk8s/current/credentials/cluster-tokens.txt'
		active_token = "'cluster_token': " + subprocess.check_output(cmd).decode('utf-8').strip() + "'"
		if isspace(active_token) == False:
			self.stored.cluster_token = active_token
		else:
			set_cluster_token()

	def create_token():
		if not self.unit.is_leader():
			return
		ttl = charm_config.get('token-ttl')
		length = (32 - (len(str(ttl))))
		x = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(length))
		new_token = ''.join(x + str(ttl))
		if isspace(active_token) == False:
			self.stored.cluster_token = new_token()

	def init_cluster():
		if not self.unit.is_leader():
			return
		if not self.state.installed:
			event.defer()
		if not self.state.configured:
			event.defer()
		cluster_token = create_token().strip()
		ttl = charm_config.get('token-ttl')
		join_str = 'sudo microk8s.add-node --token '+ cluster_token +' --token-ttl '+ ttl +'|awk '"'"'/^microk8s join/{printf $NF}'"'"''
		self.stored.leader_clustered = True
		self.stored.join_cmd = join_str

	def join_cluster():
		if self.unit.is_leader():
			return
		if not self.state.installed:
			event.defer()
		if not self.state.configured:
			event.defer()
		if not self.state.join_cmd:
			event.defer()
		cmd = self.state.join_cmd
		self.stored.leader_clustered = True
		self.stored.join_string = join_str

	def on_configure(self, event):
		if not self.state.installed:
			event.defer()
		cmd1 = 'sudo usermod -a -G microk8s $(id -un 1000)'
		cmd2 = 'sudo chown -f -R $(id -un 1000) /home/$(id -un 1000)/.kube'
		subprocess.call(cmd1, shell=True)
		subprocess.call(cmd2, shell=True)
		self.stored.configured = True
		if not self.unit.is_leader():
			self.unit.status = WaitingStatus("Waiting for cluster join string")
			return

	def _on_remove(self, event):
		"""Remove Node from Cluster"""
		self.unit.status = MaintenanceStatus("Leaving cluster")
		self.stored.started = False
		cmd = 'microk8s leave'
		subprocess.call(cmd, shell=True)

if __name__ == "__main__":
	main(Microk8sClusterCharm)

