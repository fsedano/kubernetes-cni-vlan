#!/usr/bin/python3

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
import json
import ipaddress

"""

Tasks for labmon:
Create namespace
Create networkattachment req

apiVersion: k8s.cni.cncf.io/v1
kind: NetworkAttachmentDefinition
metadata:
  name: qinq-conf
  namespace: test
spec:
  config: '{ "cniVersion": "0.3.1", "name": "mynet", "type": "fran-cni", "network":
    "9.71.0.0/16", "subnet": "9.71.50.0/24" }'

"""
def get_interface_data_mock(pod_name, pod_namespace, the_file):
    the_file.write("MOCK!!")
    return {'cisco.epfl/interface_maps': '[{"interface":"net1","vlan":519,"ip":"1.1.1.1","netmask":""},{"interface":"net2","vlan":520,"ip":"2.2.2.2","netmask":""}]', 'k8s.v1.cni.cncf.io/networks': 'qinq-conf'}

def get_interface_data(pod_name, pod_namespace, the_file):
    the_file.write("Compute interface data for name={} ns={}\n".format(pod_name, pod_namespace))
    config.load_kube_config()
    v1=client.CoreV1Api()
    req_ip = ""
    vlan_id = 0
    req_prefixlen = 24
    the_file.write("Start 1\n")
    try:
        data = v1.read_namespaced_pod(pod_name, pod_namespace)
        vlan_id = int(data.metadata.annotations['cisco.epfl/vlan_id'])
    except:
        the_file.write("Got exception!\n")
        pass
    try:
        the_file.write("Req IP!\n")
        req_ip = data.metadata.annotations['cisco.epfl/ip_address']
    except:
        the_file.write("Got exception!\n")
        pass
    try:
        the_file.write("Req mask\n")
        req_prefixlen = data.metadata.annotations['cisco.epfl/ip_prefix_length']
    except:
        the_file.write("Got exception\n")
        pass

    the_file.write("Requested ip={}".format(req_ip))
    return vlan_id, req_ip, req_prefixlen

def try_cmd(cmd, the_file):
    try:
        rc = subprocess.check_output(cmd, shell=True).decode()
        the_file.write("CMD={} Out={}\n".format(cmd, rc))
    except:
        the_file.write("EXCEPT cmd={}\n".format(cmd))

def try_cmd_mock(cmd, the_file):
    print(f"Mocking call to {cmd}")
    the_file.write(f"Mock call to {cmd}")


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

def process_interface(interface_data, namespace, interface_data_array, ip_data_array):
    ouput_ip_data= {"version" :"4", "interface" : len(interface_data_array)}
    ouput_interface_data = {"name":interface_data['interface'], "sandbox" : namespace}
    if interface_data['netmask'] == "":
        interface_data['netmask'] = "255.255.255.0"


    #IP = IPAddress(f"interface_data['ip']"/{interface_data['netmask']}").netmask_bits()
    IP = ipaddress.ip_interface(f"{interface_data['ip']}/{interface_data['netmask']}")

    interface_data_array.append(ouput_interface_data)
    ip_data_array.append(ouput_ip_data)
    ouput_ip_data['address'] = str(IP.with_prefixlen)
    host_if_name="veth{}".format(random.randint(100,10000))
    interface_mac = "aa:bb:cc:dd:ee:ff"
    br_name = "phy_{}".format(interface_data['vlan'])
    try_cmd("modprobe --first-time 8021q", the_file)

    cmd = "ip link set ens192 up"
    try_cmd(cmd, the_file)

    try_cmd("ip link set ens192 up", the_file)
    try_cmd("ip link add link ens192 name ens192.{} type vlan id {}".format(interface_data['vlan'], interface_data['vlan']),the_file)
    try_cmd("ip link set ens192.{} up".format(interface_data['vlan']), the_file)

    try_cmd("brctl addbr {}".format(br_name), the_file)
    try_cmd("brctl addif {} ens192.{}".format(br_name, interface_data['vlan']), the_file)
    try_cmd("ip link set {} up".format(br_name), the_file)
    try_cmd("iptables -A FORWARD -i {}  -j ACCEPT".format(br_name), the_file)
    cmd = "ln -sfT %s /var/run/netns/%s"
    cmd = cmd % (netns, containerid)
    r = subprocess.check_output(cmd, shell=True).decode()
    the_file.write(" Cmd={} ret={}\n".format(cmd, r))

    cmd = "ip link add %s type veth peer name %s"
    cmd = cmd % (ifname, host_if_name)
    #r = subprocess.check_output(cmd, shell=True).decode()
    the_file.write(" Cmd={} ret={}\n".format(cmd, r))

    cmd = "ip link set %s up"
    cmd = cmd % host_if_name
    #r = subprocess.check_output(cmd, shell=True).decode()
    the_file.write(" Cmd={} ret={}\n".format(cmd, r))

    cmd = "ip link set %s master %s"
    phy_name = "phy_{}".format(interface_data['vlan'])
    cmd = cmd % (host_if_name, phy_name)
    #r = subprocess.check_output(cmd, shell=True).decode()
    the_file.write(" Cmd={} ret={}\n".format(cmd, r))

    cmd = "ip link set %s netns %s"
    cmd = cmd % (ifname, containerid)
    #r = subprocess.check_output(cmd, shell=True).decode()
    the_file.write(" Cmd={} ret={}\n".format(cmd, r))

    cmd = "ip netns exec %s ip link set %s up"
    cmd = cmd % (containerid, ifname)
    #r = subprocess.check_output(cmd, shell=True).decode()
    the_file.write(" Cmd={} ret={}\n".format(cmd, r))

    if interface_data['ip'] != "":
        cmd = "ip netns exec %s ip addr add %s/%s dev %s"
        cmd = cmd % (containerid, interface_data['ip'], interface_data['netmask'], ifname)
        #r = subprocess.check_output(cmd, shell=True).decode()
        the_file.write(" Cmd={} ret={}\n".format(cmd, r))

    cmd = "ip netns exec %s ip link show %s | awk '/ether/ {print $2}'"
    cmd = cmd % (containerid, ifname)
    #mi_mac = subprocess.check_output(cmd, shell=True).decode().rstrip()
    interface_mac = "aa:bb:cc:dd:ee:ff"
    the_file.write(" Cmd={} ret={}\n".format(cmd, interface_mac))
    #container_ip_string = "{}/{}".format(interface_data['ip'], interface_data['netmask'])
    #ip_ret_section = ip_ret % (container_ip_string)
    ouput_interface_data['mac'] = interface_mac

def extract_k8s_data():
    k8s_data =  {}
    k8s_data['CNI_COMMAND'] = os.environ['CNI_COMMAND']
    k8s_data['CNI_CONTAINERID'] = os.environ['CNI_CONTAINERID']
    k8s_data['CNI_NETNS'] = os.environ['CNI_NETNS']
    k8s_data['CNI_IFNAME'] = os.environ['CNI_IFNAME']
    k8s_data['CNI_ARGS'] = os.environ['CNI_ARGS']
    k8s_data['CNI_PATH'] = os.environ['CNI_PATH']
    return k8s_data

### Entrypoint ###
#k8s_env = os.environ._data
k8s_env =  extract_k8s_data()
# for testing
#k8s_env = {'CNI_COMMAND': 'ADD', 'CNI_CONTAINERID': 'e5b733f3a276ea748053003ebd00943ec115ab06c9ad6240eb0a09c638412254', 'CNI_NETNS': '/proc/13882/ns/net', 'CNI_ARGS': 'IgnoreUnknown=1;K8S_POD_NAMESPACE=ns-gtopo-51-topo-309;K8S_POD_NAME=fe3e97b2-6c848ff4d5-rgd4s;K8S_POD_INFRA_CONTAINER_ID=e5b733f3a276ea748053003ebd00943ec115ab06c9ad6240eb0a09c638412254', 'CNI_IFNAME': 'net1', 'CNI_PATH': '/opt/cni/bin'}
#k8s_env2 = {}
#k8s_env2['PATH'] = k8s_env[b'PATH'].decode('utf-8')
#print(f"ENV1 is {k8s_env} ENV2 is {k8s_env2}")

with open('/var/log/labmon-cni.log', 'a') as the_file:
    the_file.write("LABMON CNI called! \n  oper={}\n  CONT_ID={}\n  ".format( k8s_env['CNI_COMMAND'], k8s_env['CNI_CONTAINERID'] ))
    the_file.write("Netns={}\n  Ifname={}\n  Args={}\n  Path={} \n".format( k8s_env['CNI_NETNS'], k8s_env['CNI_IFNAME'], k8s_env['CNI_ARGS'], k8s_env['CNI_PATH']))

    cni_args = k8s_env['CNI_ARGS']
    input_data = dict(s.split('=') for s in cni_args.split(';'))

    for line in iter(sys.stdin.readline, ''):
        the_file.write(' stdin={}\n'.format(line))

    the_file.write("\n")

    if k8s_env['CNI_COMMAND'] == 'ADD':
        the_file.write("1\n")
        cmd = "mkdir -p /var/run/netns/"
        r = subprocess.check_output(cmd, shell=True).decode()

        ifname = k8s_env['CNI_IFNAME']
        containerid = k8s_env['CNI_CONTAINERID']
        netns = k8s_env['CNI_NETNS']
        #vlan, containerip, containerpfxlen = get_interface_data(input_data['K8S_POD_NAME'], input_data['K8S_POD_NAMESPACE'], the_file)
        #interface_data = get_interface_data_mock(input_data['K8S_POD_NAME'], input_data['K8S_POD_NAMESPACE'], the_file)
        interface_data = get_interface_data(input_data['K8S_POD_NAME'], input_data['K8S_POD_NAMESPACE'], the_file)
        the_file.write("GOT vlan={}".format(interface_data))

        interfaces_data_json = json.loads(interface_data['cisco.epfl/interface_maps'])

        interface_data_array = []
        ip_data_array = []
        for interface_data in interfaces_data_json:
            print(f"Interface is {interface_data}")
            print(f"IF name is {interface_data['interface']}")
            process_interface(interface_data, netns, interface_data_array, ip_data_array)


        final_data = {"cniVersion" : "0.3.1", "interfaces" : interface_data_array, "ips" : ip_data_array}

        print(json.dumps(final_data, sort_keys=True, indent=4))
        the_file.write(json.dumps(final_data, sort_keys=True, indent=4))

sys.exit(0)