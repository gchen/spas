#!/usr/bin/env python
# encoding: utf-8

from fabric.api import *
from fabric.api import settings
from datetime import *
import os

#env.hosts=['openstack-03','openstack-04','openstack-05'] 
env.hosts=['openstack-04','openstack-05'] 
env.roledefs={'master':['openstack-03'],'slaves':['openstack-04','openstack-05']}
env.user = 'spark'
env.password = 'spark'

def setting_ci():
    local('echo "add and commit settings in local"')

def update_setting_remote():
    print "remote update"
    with cd('/tmp'): 
        run('ls -l | wc -l') 

def create_user(name):
    run('useradd %s' %(name))
    run('passwd %s'%(name))

@roles('master','slaves')
def acmd(cmd):
    res = run('%s' %(cmd))

@roles('slaves')
def cmd(cmd):
    res = run('%s' %(cmd))

def ssh_key():
    res = run ('cat ~/.ssh/id_rsa.pub')
    os.system('echo ' + res + '>> ~/.ssh/authorized_keys')     
    #run('echo ' + res + ' >> ~/.ssh/authorized_keys')
    #run('chmod 600 ~/.ssh/authorized_keys')

def deploy_cass():
    put('/home/spark/cassandra/apache-cassandra-2.0.14/', '/home/spark/cassandra/',mirror_local_mode=True)

def suscp(local,remote):
    put(local,remote,use_sudo=True,mirror_local_mode=True)

@roles('slaves')
def scp(local,remote):
    put(local,remote,mirror_local_mode=True)

@roles('master','slaves')
def startCass_old():
    with settings(warn_only=True):
        run('sh /home/spark/cassandra/apache-cassandra-2.0.14/bin/cassandra &',pty=False)
        run('user=`whoami`;pgrep -u $user -f cassandra')

@roles('master','slaves')
def killCass_old():
    with settings(warn_only=True):
        run("user=`whoami`;pgrep -u $user -f cassandra | xargs kill -9")

@roles('master','slaves')
def syCaConf_old():
    put('/home/spark/cassandra/conf_template/*','/home/spark/cassandra/apache-cassandra-2.0.14/conf/')
    updateIpInCassConf_old()

@roles('master','slaves')
def updateIpInCassConf_old():
    ip = run("ifconfig | grep \"inet addr\" | grep -v \"127.0.0.1\" | awk '{print $2}' | awk -F ':' '{print $2}' | grep 9.186")
    run("sed -i s/__HOSTIP__/" + ip + "/ /home/spark/cassandra/apache-cassandra-2.0.14/conf/cassandra.yaml")

@roles('master','slaves')
def startC():
    with settings(warn_only=True):
        run("sudo service cassandra stop")
        run("sudo service cassandra start")
        run("sudo service datastax-agent stop")
        run("sudo service datastax-agent start")

@roles('master','slaves')
def stopC():
    run("sudo service cassandra stop")

@roles('master','slaves')
def syCaConf():
    put('/home/spark/cassandra/conf_template_2.1/*','/etc/cassandra/conf/',use_sudo=True)
    updateIpInCassConf()

@roles('master','slaves')
def updateIpInCassConf():
    ip = run("ifconfig | grep \"inet addr\" | grep -v \"127.0.0.1\" | awk '{print $2}' | awk -F ':' '{print $2}' | grep 9.186")
    run("sudo sed -i s/listen_address\:/listen_address:\ " + ip + "/ /etc/cassandra/conf/cassandra.yaml")
    run("sudo sed -i s/rpc_address\:/rpc_address:\ " + ip + "/ /etc/cassandra/conf/cassandra.yaml")

@roles('master','slaves')
def startOpsAgent():
    run("sudo service datastax-agent stop")
    run("sudo service datastax-agent start")

@roles('master')
def WtCass():
    # write test three nodes
    run('/usr/bin/cassandra-stress \
         -d openstack-03,openstack-04,openstack-05 \
         --columns=10 \
         -n 10000000 \
         -o INSERT \
         -R SimpleStrategy \
         -l 3 \
         -f ' + 'CassWRITE-'+datetime.now().strftime("%Y%m%d-%H%M%S")+'.out')

@roles('master')
def RdCass():
    # read test three nodes
    run('/usr/bin/cassandra-stress \
         -d openstack-03,openstack-04,openstack-05 \
         --columns=10 \
         -n 10000000 \
         -o READ \
         -f ' + 'CassREAD-'+datetime.now().strftime("%Y%m%d-%H%M%S")+'.out')

@roles('master','slaves')
def Stress():
    #run('cassandra-stress user profile=/home/spark/cqlstress-counter-example.yaml ops\(insert=2,simple1=1\) -node openstack-04,openstack-05')

    # Running below test in three nodes in parallel, hence we will end up with 20M * 3 = 60M messages.
    run('cassandra-stress user profile=/home/spark/cqlgrowingio.yaml ops\(insert=1\) n=20000000 -node openstack-03,openstack-04,openstack-05 -rate threads\>=16 threads\<=32 auto -log file=' + 'CassStress-'+datetime.now().strftime("%Y%m%d-%H%M%S")+'.out')

@roles('master')
def WtCass_old():
    # Use stress deamon has bug: https://issues.apache.org/jira/browse/CASSANDRA-5978
    #run('/home/spark/cassandra/apache-cassandra-2.0.14/tools/bin/cassandra-stressd start')   
    #run('/home/spark/cassandra/apache-cassandra-2.0.14/tools/bin/cassandra-stress -d 9.186.100.95,9.186.95.94 -n 10000000 --send-to localhost')

    # Write data
    # use two hosts for stress test has bugs http://stackoverflow.com/search?q=[cassandra]+Frame+size+larger+than+max+length
    #run('/home/spark/cassandra/apache-cassandra-2.0.14/tools/bin/cassandra-stress -d 9.186.100.95,9.186.95.94 --columns=10 -n 1000')
  
    #TODO seems if run this test for first time, fabric can't successfully create new keyspace "Keyspace1"?
    # running single node should be OK
    #run('/home/spark/cassandra/apache-cassandra-2.0.14/tools/bin/cassandra-stress -d 9.186.100.95 --columns=10 -n 100000000')

    # write test three nodes
    run('/home/spark/cassandra/apache-cassandra-2.0.14/tools/bin/cassandra-stress \
         -d openstack-03,openstack-04,openstack-05 \
         --columns=10 \
         -n 100000000 \
         -o INSERT \
         -R SimpleStrategy \
         -l 3 \
         -f ' + 'CassWRITE-'+datetime.now().strftime("%Y%m%d-%H%M%S")+'.out')

@roles('master')
def RdCass_old():
    # read test three nodes
    run('/home/spark/cassandra/apache-cassandra-2.0.14/tools/bin/cassandra-stress \
         -d openstack-03,openstack-04,openstack-05 \
         --columns=10 \
         -n 10000000 \
         -o READ \
         -f ' + 'CassREAD-'+datetime.now().strftime("%Y%m%d-%H%M%S")+'.out')

@roles('master','slaves')
def install_oracel_jdk():
    run('mkdir -p /usr/lib/jvm/;\
         sudo tar zxvf ~/jdk-8u45-linux-x64.tar.gz -C /usr/lib/jvm/;\
         sudo update-alternatives --install "/usr/bin/java" "java" "/usr/lib/jvm/jdk1.8.0_45/bin/java" 1;\
         sudo update-alternatives --set java /usr/lib/jvm/jdk1.8.0_45/bin/java;')

@roles('master','slaves')
def install_dsc21():
    run('touch /tmp/datastax.repo')
    run('sudo echo \'[datastax]\' >> /tmp/datastax.repo')
    run('sudo echo \'name = DataStax Repo for Apache Cassandra\' >> /tmp/datastax.repo')
    run('sudo echo \'baseurl = http://rpm.datastax.com/community\' >> /tmp/datastax.repo')
    run('sudo echo \'enabled = 1\' >> /tmp/datastax.repo')
    run('sudo echo \'gpgcheck = 0\' >> /tmp/datastax.repo')
    run('sudo mv /tmp/datastax.repo /etc/yum.repos.d/datastax.repo')
    run('sudo chmod 644 /etc/yum.repos.d/datastax.repo')
    run('sudo yum install dsc21; sudo yum install cassandra21-tools')

@roles('master','slaves')
def mkdir_dsc21():
    run("    sudo mkdir -p /local_tmp_disk/cassandra/commit2/; sudo chown -R cassandra:cassandra /local_tmp_disk/cassandra/commit2/")
    run(" sudo mkdir -p /hdfs_disk0/cassandra/data2;sudo chown -R cassandra:cassandra /hdfs_disk0/cassandra/data2")



