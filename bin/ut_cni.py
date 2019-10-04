#!/usr/bin/python3

import unittest
from unittest import mock
import labmon_cni
import logging

MOCKED_K8S_PARAMS = {
    'CNI_COMMAND' : 'ADD',
    'CNI_CONTAINERID' : "1234cntid4321",
    'CNI_NETNS' : "33efdij",
    'CNI_IFNAME' : 'net1',
    'CNI_ARGS' : 'K8S_POD_NAMESPACE=123455;K8S_POD_NAME=MY_POD_NAME',
    'CNI_PATH' : '/bin'
}

MOCKED_INTERFACE_MAPS = [
    {"interface":"net1","vlan":519,"ip":"1.1.1.1","netmask":""},
    {"interface":"net2","vlan":520,"ip":"2.2.2.2","netmask":""}
]

def log_exec(arg):
    logging.info(f"-> {arg} <-\n")

def log_exec_with_rc(arg):
    logging.info(f"-> {arg} <-\n")
    return "de:ad:be:ee:ef"

class lmUnitTest(unittest.TestCase):        
    @mock.patch('labmon_cni.K8s_Params.get_k8s_params')
    @mock.patch('labmon_cni.K8s_Params.get_interface_maps')
    @mock.patch('labmon_cni.OSexec.exec', log_exec)
    @mock.patch('labmon_cni.OSexec.exec_get_output', log_exec_with_rc)
    def test_one(self,
        labmon_cni_K8s_Params_get_interface_maps,
        labmon_cni_K8s_Params_get_k8s_params):
        labmon_cni_K8s_Params_get_k8s_params.return_value = MOCKED_K8S_PARAMS
        labmon_cni_K8s_Params_get_interface_maps.return_value = MOCKED_INTERFACE_MAPS
        K8 = labmon_cni.K8s_CNI()
        K8.entrypoint()
        

logging.basicConfig(filename='/tmp/app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
unittest.main()