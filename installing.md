Step by step guide: Deploying kubernetes cluster for Labmon usage

Minimum deployment

For testing/development purposes, a mini-cluster can be deployed with a single node. This model is NOT recommended for production.
On this model there's a single control-plane node and 0 ir more worker nodes. If no worker nodes are deployed, the control plane node can also act as a worker node.

Step by step guide
•	Deploy a Ubuntu 18.04 VM with at least following resources:

4CPUs
16 Gb RAM
32 Gb disk
2 NICs

NIC 1 should be connected to the routable network (where it has reachability from outside) (ens160 on Linux)
NIC 2 should be connected to a trunk interface (ens192 on Linux)

•	Setup PROXY environment 
o	Add to /etc/environment
o	Make sure that the IP address of the node goes through no_proxy

http_proxy="http://proxy.esl.cisco.com:80/"
https_proxy="http://proxy.esl.cisco.com:80/"
no_proxy=".cisco.com,127.0.0.1,localhost,10.0.0.0/8"
HTTP_PROXY="http://proxy.esl.cisco.com:80/"
HTTPS_PROXY="http://proxy.esl.cisco.com:80/"
NO_PROXY=".cisco.com,127.0.0.1,localhost,10.0.0.0/8"


•	Install packages

sudo apt-get update && sudo apt-get -y upgrade
sudo apt install docker.io apt-transport-https curl python3 python3-pip -y
sudo systemctl start docker
sudo systemctl enable docker
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add
sudo apt-add-repository "deb http://apt.kubernetes.io/ kubernetes-xenial main"
sudo apt-get install kubeadm -y
pip3 install kubernetes


•	Edit /etc/fstab to remove any swap entry
•	reboot
•	Enable proxy for docker


sudo mkdir /etc/systemd/system/docker.service.d

sudo bash

echo "[Service]" > /etc/systemd/system/docker.service.d/http-proxy.conf

echo 'Environment="HTTP_PROXY=http://proxy.esl.cisco.com:80/" "HTTPS_PROXY=http://proxy.esl.cisco.com:80/" NO_PROXY="*.cisco.com; 10.224.0.0; 10.96.0.0"' >> /etc/systemd/system/docker.service.d/http-proxy.conf
exit

sudo systemctl daemon-reload
sudo systemctl restart docker
•	Docker should work now:
sudo docker run hello-world

At this point, you can clone the VM into a template to install further nodes afterwards 

•	Lock kubernetes upgrades: 

sudo apt-mark hold kubelet kubeadm kubectl

•	Clone repository:


mkdir ~/kubeinstall

cd ~/kubeinstall

git clone https://wwwin-github.cisco.com/EPFL/labmon_kubernetes.git .


•	Edit kubeadm-config.yaml to reflect the routable IP address of the ubuntu VM on controlPlaneEndpoint

sudo kubeadm init --config=kubeadm-config.yaml --upload-certs
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config


•	Check kubernetes is up and running
kubectl get nodes -o wide

NAME               STATUS     ROLES    AGE    VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION      CONTAINER-RUNTIME
kube-labmon-demo   NotReady   master   118s   v1.15.0   10.51.66.97   <none>        Ubuntu 18.04.2 LTS   4.15.0-45-generic   docker://18.9.7

Status NotReady is expected, since we still need to install network plugins 

Untaint master node


kubectl taint nodes --all node-role.kubernetes.io/master-



Install network plugins

kubectl apply -f flannel.yaml

kubectl apply -f multus.yaml

kubectl apply -f labmon-plugin.yaml


sudo mkdir -p /root/.kube
sudo cp ~/.kube/config /root/.kube


At this point, node should change to 'Ready'



lab@kube-labmon-demo:~/kubeinstall$ kubectl get nodes -o wide
NAME               STATUS   ROLES    AGE   VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION      CONTAINER-RUNTIME
kube-labmon-demo   Ready    master   11m   v1.15.0   10.51.66.97   <none>        Ubuntu 18.04.2 LTS   4.15.0-45-generic   docker://18.9.7


Test pods can be scheduled

kubectl run hello-kubernetes --replicas=2 --image=paulbouwer/hello-kubernetes:1.5 --port=8080

kubectl expose deployment hello-kubernetes --type=NodePort  --target-port=8080 --name=hello-kubernetes

kubectl get svc
NAME               TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE
hello-kubernetes   NodePort    10.110.34.173   <none>        8080:32640/TCP   5s



Note the port on the 'hello-kubernetes' service. In this case 32640.
From a browser on your laptop, connect to the IP of the node, using the port listed there, for example:


kubectl get nodes -o wide
NAME               STATUS   ROLES    AGE   VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION      CONTAINER-RUNTIME
kube-labmon-demo   Ready    master   30m   v1.15.0   10.51.66.97   <none>        Ubuntu 18.04.2 LTS   4.15.0-45-generic   docker://18.9.7


kubectl get svc
NAME               TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE
hello-kubernetes   NodePort    10.110.34.173   <none>        8080:32640/TCP   5s

On this example, browse to  http://10.51.66.97:32640 (internal IP of the node + the port displayed on the 'kubectl  get svc' CLI. You should get a webpage with the hello world screen 

 

You can delete the test deployment and service now


kubectl delete deployment/hello-kubernetes

kubectl delete svc/hello-kubernetes



Create token for Labmon


kubectl apply -f labmon-role.yaml

kubectl -n kube-system describe secret $(kubectl -n kube-system get secret | grep labmon | awk '{print $1}')

This will print the token to be provisioned to labmon, for example:


Data
====
ca.crt: 1025 bytes
namespace: 11 bytes
token: eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJrdWJlLXN5c3RlbSIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VjcmV0Lm5hbWUiOiJsYWJtb24tdG9rZW4tdDJ2czYiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoibGFibW9uIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQudWlkIjoiNTgwZmIxNjMtOGZiNy00MGUzLWIxYzctNjhlMTI4OThmOGZhIiwic3ViIjoic3lzdGVtOnNlcnZpY2VhY2NvdW50Omt1YmUtc3lzdGVtOmxhYm1vbiJ9.VOwBRnE5OxcmX0fNOopUrPKyvtRsYD_o2hagqNyGgHd7yR-NZrrPfJqN_oNHcWTxau18JdZXg9lv6OHXYc8gdhRdTwt0Ul7XC4nDbATNuns4FR2oNOCbu_Adeq7XxCaNzLl4_jjMkF-jVMA7DrdxuyZl8o6z9qpSzpXflO8BLP3p1TmA4SzEP-k2XN4lCt37C1agpfadTS3DngHB7U0z-POssqG-r0EKzeZT1iZGCvUuilZEBzsC6uwyfNNVSlY8OQJbXld2INAT7cykYS0-Ts2dW0KFJ0veyd4pY-1fjfz9hHslUomO6nCRWzCKBcgWbQ4NF39m8lw1UA3qF58UzQ






On labmon k8s_parameters.env add token and node IP address:


k8s_token=eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJrdWJlLXN5c3RlbSIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VjcmV0Lm5hbWUiOiJhZG1pbi11c2VyLXRva2VuLXp0OWxrIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQubmFtZSI6ImFkbWluLXVzZXIiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiI1MDI0MDdiYS05NzY2LTExZTktOTg5YS0wMDUwNTY4YTQxNGMiLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6a3ViZS1zeXN0ZW06YWRtaW4tdXNlciJ9.guoENNzaX5lMNXS4DhXgO2EGGK4Dj8UeUVRNpQrQXDqM8w6U-oT97qFqmeXe2E4NNR8ev-wANlpjQntRYZWLdfDw16OHaG4VE_vnqgutE_vQxxJ-VQYCyxpbB6bS_8dciPRQ7JCVELwiTTrB_O00wKlbItI--rcQq_Ippf7kjZ3te_E_bf0ySSPEyNh1G87UgBHVmdMs38JGrkg77fZxoeiI1-DAGW8HappBjM4TwDw-zkGcsXbd-XIvlYXDLhexPv66R8xHfK8SWju9gNv0bJthO0IZBwqmSskicPfZOnjrZjQ20C7jOqdBeRavHqxwaJGLsFMQulMHF39GWO57OQ
k8s_host=https://10.51.66.97:6443


Adding additional nodes
•	Clone the VM using the template described above
•	Change hostname as required
•	Lock kubernetes upgrades: apt-mark hold kubelet kubeadm kubectl
•	Execute in kube master
kubeadm token create --print-join-command
//example of the output
//kubeadm join 10.51.66.40:6443 --token uh9s52.8i4tw9b8llsqbdqj     --discovery-token-ca-cert-hash sha256:688881ef43bdc9b62706997f40a1d22fbac09cdbe03c523b2382d1d352ce5cdc

•	On the new node
•	Clear any previous configuration
kubeadm reset
•	pass this output on the new host you want to add
ex. kubeadm join .....


For control plane nodes:
kubeadm init phase upload-certs --experimental-upload-certs
kubeadm token create --print-join-command
Add this
--experimental-control-plane --certificate-key <key from kubeadm init phase upload-certs>


HA customizations

•	Bump replica count of CoreDNS to 3
kubectl scale  deployment/coredns -n kube-system --replicas=3

