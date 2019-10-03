#!/usr/bin/python3
import sys
import os
import time
import subprocess
import random
from kubernetes import client, config
import json
import ipaddress

class K8s_Params:
    def __init__(self):
        self.k8s_data = self.get_k8s_params()
        self.pod_data = self.get_pod_data()

    def get_pod_data(self):
        input_data = dict(s.split('=') for s in self.k8s_data['CNI_ARGS'].split(';'))
        data = {}
        data['K8S_POD_NAME'] = input_data['K8S_POD_NAME']
        data['K8S_POD_NAMESPACE'] = input_data['K8S_POD_NAMESPACE']
        return data

    def get_k8s_params(self):
        k8s_data =  {}
        k8s_data['CNI_COMMAND'] = os.environ['CNI_COMMAND']
        k8s_data['CNI_CONTAINERID'] = os.environ['CNI_CONTAINERID']
        k8s_data['CNI_NETNS'] = os.environ['CNI_NETNS']
        k8s_data['CNI_IFNAME'] = os.environ['CNI_IFNAME']
        k8s_data['CNI_ARGS'] = os.environ['CNI_ARGS']
        k8s_data['CNI_PATH'] = os.environ['CNI_PATH']
        input_data = dict(s.split('=') for s in k8s_data['CNI_ARGS'].split(';'))
        k8s_data['K8S_POD_NAME'] = input_data['K8S_POD_NAME']
        k8s_data['K8S_POD_NAMESPACE'] = input_data['K8S_POD_NAMESPACE']
        return k8s_data

    #fixme getters
    def command(self):
        return self.k8s_data['CNI_COMMAND']

    def is_command_add(self):
        return self.command() == "ADD"

    def is_command_del(self):
        return self.command() == "DEL"

    def container_id(self):
        return self.k8s_data['CNI_CONTAINERID']

    def netns(self):
        return self.k8s_data['CNI_NETNS']

    def pod_name(self):
        return ""
    
    def get_interface_maps(self, pod_name, netns):
        return {}

class OSexec:
    def exec(self, cmd):
        rc = subprocess.check_output(cmd, shell=True).decode()
        return rc

class K8s_CNI:
    def __init__(self):
        self.k = K8s_Params()
        self.OS = OSexec()

    def oper_add(self):
        print("In oper add!")
        #rc = self.OS.exec("ls")
        #print(f"RC is {rc}")
        k = self.k
        container_id = k.container_id()
        print(f"pod name={k.pod_name()}")
        print(f"pod namespace={k.netns()}")
        interface_data = k.get_interface_maps(k.pod_name(), k.netns())
        print(f"Add: interface_data is {interface_data}\n")


    def oper_del(self):
        print("In oper DEL!")

    def entrypoint(self):
        if self.k.is_command_add():
            self.oper_add()
        if self.k.is_command_del():
            self.oper_del()