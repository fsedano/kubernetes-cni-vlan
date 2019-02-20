#!/usr/bin/python

"""

-- save as /opt/cni/bin/fran-cni

{
  "cniVersion": "0.3.1",
  "interfaces": [
      {
          "name": "eth0",
          "mac": "a2:a6:39:94:24:ef",
          "sandbox": "/proc/4941/ns/net"
      }
  ],
  "ips": [
      {
          "version": "4",
          "address": "10.244.1.2/24",
          "gateway": "10.244.1.1",
          "interface": 0
      }
  ]
}
"""
import sys
import os
import time
import subprocess
import random
from kubernetes import client, config


def get_vlan_ip(pod_name, pod_namespace, the_file):
	the_file.write("Compute vlan for name={} ns={}\n".format(pod_name, pod_namespace))
	config.load_kube_config()
	v1=client.CoreV1Api()
	req_ip = ""
	vlan_id = 0
	try:
		data = v1.read_namespaced_pod(pod_name, pod_namespace)
		vlan_id = int(data.metadata.annotations['cisco.epfl/vlan_id'])
	except:
		pass
	try:
		req_ip = data.metadata.annotations['cisco.epfl/ip_address']
	except:
		pass
	the_file.write("Requested ip={}".format(req_ip))
	return vlan_id, req_ip

def try_cmd(cmd, the_file):
	try:
		rc = subprocess.check_output(cmd, shell=True)
		the_file.write("CMD={} Out={}\n".format(cmd, rc))
	except:
		the_file.write("EXCEPT cmd={}\n".format(cmd))

def common_setup(vlan_id, the_file):
	br_name = "phy_{}".format(vlan_id)

	try_cmd("modprobe --first-time 8021q", the_file)

	cmd = "ip link set ens192 up"
	try_cmd(cmd, the_file)

	try_cmd("ip link set ens192 up", the_file)
	try_cmd("ip link add link ens192 name ens192.{} type vlan id {}".format(vlan_id, vlan_id),the_file)
	try_cmd("ip link set ens192.{} up".format(vlan_id), the_file)
	try_cmd("brctl addbr {}".format(br_name), the_file)
	try_cmd("brctl addif {} ens192.{}".format(br_name, vlan_id), the_file)
	try_cmd("ip link set {} up".format(br_name), the_file)
	try_cmd("iptables -A FORWARD -i {}  -j ACCEPT".format(br_name), the_file)


with open('/var/log/fran.log', 'a') as the_file:
	the_file.write("FRAN called! \n  oper={}\n  CONT_ID={}\n  ".format( os.environ['CNI_COMMAND'], os.environ['CNI_CONTAINERID'] ))
	the_file.write("Netns={}\n  Ifname={}\n  Args={}\n  Path={} \n".format( os.environ['CNI_NETNS'], os.environ['CNI_IFNAME'], os.environ['CNI_ARGS'], os.environ['CNI_PATH']))

	cni_args = os.environ['CNI_ARGS']
	input_data = dict(s.split('=') for s in cni_args.split(';'))

	for line in iter(sys.stdin.readline, ''):
		the_file.write(' stdin={}\n'.format(line))

	the_file.write("\n")

	ret = """
{
  "cniVersion": "0.3.1",
  "interfaces": [
      {
          "name": "%s",
          "mac": "%s",
          "sandbox": "%s"
      }
  ],
  "ips": [
      {
          "version": "4",
          "address": "%s/24",
          "gateway": "%s",
          "interface": 0
      }
  ]
}
	"""
	
	if os.environ['CNI_COMMAND'] == 'ADD':
		the_file.write("1\n")
		os.system("mkdir -p /var/run/netns/")

		ifname = os.environ['CNI_IFNAME']
		containerid = os.environ['CNI_CONTAINERID']
		netns = os.environ['CNI_NETNS']
		vlan, containerip = get_vlan_ip(input_data['K8S_POD_NAME'], input_data['K8S_POD_NAMESPACE'], the_file)
		the_file.write("GOT vlan={}".format(vlan))

		host_if_name="veth{}".format(random.randint(100,10000))
		if containerip == "":
			containerip = "9.9.71.{}".format(random.randint(2,254))
		gw_ip = "9.9.71.1"

		if vlan > 0:
			common_setup(vlan, the_file)

			cmd = "ln -sfT %s /var/run/netns/%s"
			cmd = cmd % (netns, containerid)
			r = os.system(cmd)
			the_file.write(" Cmd={} ret={}\n".format(cmd, r))

			cmd = "ip link add %s type veth peer name %s"
			cmd = cmd % (ifname, host_if_name)
			r = os.system(cmd)
			the_file.write(" Cmd={} ret={}\n".format(cmd, r))

			cmd = "ip link set %s up"
			cmd = cmd % host_if_name
			r = os.system(cmd)
			the_file.write(" Cmd={} ret={}\n".format(cmd, r))

			cmd = "ip link set %s master phy_638"
			cmd = cmd % host_if_name
			r = os.system(cmd)
			the_file.write(" Cmd={} ret={}\n".format(cmd, r))

			cmd = "ip link set %s netns %s"
			cmd = cmd % (ifname, containerid)
			r = os.system(cmd)
			the_file.write(" Cmd={} ret={}\n".format(cmd, r))

			cmd = "ip netns exec %s ip link set %s up"
			cmd = cmd % (containerid, ifname)
			r = os.system(cmd)
			the_file.write(" Cmd={} ret={}\n".format(cmd, r))

			cmd = "ip netns exec %s ip addr add %s/24 dev %s"
			cmd = cmd % (containerid, containerip, ifname)
			r = os.system(cmd)
			the_file.write(" Cmd={} ret={}\n".format(cmd, r))

			# Send GARP
			cmd = "nohup echo 'sleep 5; ip netns exec %s /usr/sbin/arping -U -c 1 %s' | at now" 
			cmd = cmd % (containerid, containerip)
			try:
				out = subprocess.check_output(cmd, shell=True)
				the_file.write(" Cmd={} ret={}\n".format(cmd, out))
			except subprocess.CalledProcessError as e:
				the_file.write("Except on cmd={}. E={}\n".format(cmd, e))
				
			

			#cmd = "ip netns exec %s ip route add default via %s dev %s"
			#cmd = cmd % (containerid, gw_ip, ifname)
			#r = os.system(cmd)
			#the_file.write(" Cmd={} ret={}\n".format(cmd, r))
		
			cmd = "ip netns exec %s ip link show %s | awk '/ether/ {print $2}'"
			cmd = cmd % (containerid, ifname)
			mi_mac = subprocess.check_output(cmd, shell=True).rstrip()
			the_file.write(" Cmd={} ret={}\n".format(cmd, mi_mac))
		
		ret = ret % (host_if_name, mi_mac,netns, containerip, gw_ip)
		the_file.write(" mi_mac={} Out={}".format(mi_mac,ret))
		print(ret)

sys.exit(0)

