#!/usr/bin/env python3

from os.path import expanduser
import os
import click
import logging 
import sys
import json
import fabric 

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%Y:%m:%d-%H:%M:%S')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class connMan():

    def __init__(self, log):
        self.log = log
        self.jump = None
        self.connection = None
        self.copy = None
        self.copyResult = None
        self.IdentityFile = None
        self.ec2user = None
        self.host = None

    def doCopy(self, from_file, to_file=None):
        """ copy files using the connections """
        self.copyResult = self.copy.put(from_file, to_file)

    def doDemo(self):
        if self.demo_port is None:
            self.log.error("'port' isn't set in the config file, cannot do demo")
            return 1

        if self.demo_host is None:
            self.log.error("'host' isn't set in the config file, cannot do demo")
            return 1

        if self.demo_remotePort is None:
            self.log.error("'host' isn't set in the config file, cannot do demo")
            return 1

        if self.demo_idFile is None:
            self.log.error("'idFile' isn't set in the config file, cannot do demo")
            return 1

        # get the port forward setup
        self.log.info("Setting up port forwarding connection from port {} to port {} and host {}".format(self.demo_remotePort, self.demo_port, self.demo_host))
        with self.connection.forward_remote(remote_port=self.demo_remotePort, 
                                            local_port=self.demo_port, 
                                            local_host=self.demo_host):

            # create the demo directory
            self.log.info("Creating the demo directory remotely")
            self.connection.run(r'mkdir -p ./demo;')
                         
            # copy up the id file
            self.log.info("Copying up demo_id file")
            self.doCopy(expanduser(self.demo_idFile), "demo/demo_idFile.pem")

            # create a sshfile 
            self.log.info("Creating a ssh config file")
            self.createTmpSshConfig("./demoSshConfig")

            # copy it up
            self.log.info("Copying it up")
            self.doCopy("./demoSshConfig", "demo/demoSshConfig")

            # remove the local copy
            self.log.info("Removing local copy ")
            os.remove("./demoSshConfig")

            # try and clone it
            self.log.info("Cloning ssmParameterManager remotely")
            self.connection.run( r'cd ./demo;'+
                                r'GIT_SSH_COMMAND="ssh -F ./demoSshConfig git clone git@gittun:martinfarrow/ssmParameterManager.git')


    def createTmpSshConfig(self, fpath):
        f = open(fpath, 'w')
        f.write("Host gittun\n")
        f.write("  hostname 127.0.0.1\n")
        f.write("  port {}\n".format(self.demo_remotePort))
        f.write("  IdentityFile ./demo_idFile.pem\n")
        f.write("  UserKnownHostsFile /dev/null\n")
        f.write("  StrictHostKeyChecking no\n")
        f.close()

    def confirmConnections(self):
        if (self.jumpCon is not None):
            self.log.info("Testing jump configuration, ps command, 5 lines")
            self.jumpCon.run("ps -ef | head -5")
        
        self.log.info("Confirming target configuration, ps command, 5 lines")
        self.connection.run("ps -ef | head -5")

    def commandWithTunnel(self):
        self.log.info("Executing sleep 60 with a tunnel, redirecting port 22022 to github.com on port 22")
        with self.connection.forward_remote(remote_port=22022, local_port=22, local_host="github.com"):
            self.connection.run("sleep 60")
        self.log.info("Times Up Finished")

    def buildConnections(self):
        """ build connections for use """
        self.jumpCon = None
        if self.jump is not None and 'jumphost' in self.jump and 'jumpuser' in self.jump and 'IdentityFile' in self.jump:
            self.jumpCon = fabric.Connection(host=self.jump['jumphost'],
                                        user=self.jump['jumpuser'],
                                        connect_kwargs={ "key_filename": expanduser(self.jump['IdentityFile']) })

        self.connection = fabric.Connection(host=self.host,
                                           user=self.ec2user,
                                           connect_kwargs={ "key_filename": expanduser(self.IdentityFile) },
                                           gateway=self.jumpCon)

        self.copy = fabric.transfer.Transfer(self.connection)

    def configTemplate(self):
        print("""{
  "_jump" : {
    "IdentityFile": "path-to-somefile",
    "jumpuser": "someuser",
    "jumphost": "hostname-or-IP"
  },
  "_global": {
    "ec2user": "global-value-here"
  },
  "target": {
    "IdentityFile": "path-to_somefile",
    "ec2user": "username",
    "host": "hostname-or-IP"
  },
  "demo": {
    "port": 22,
    "host": "github.com",
    "remotePort": 22022,
    "idFile": "path-to-your-github-idfile"
  }
}""")

    def loadConfig(self, filepath):
        """ load the external json config file """
        try:
            with open(filepath) as fp:
                self.config = json.load(fp)
        except IOError as e:
            errno, strerror = e.args
            self.log.error("Unable to open {}: errno({}): {}",format(errno, strerror))
        self.parseConfig()
        self.buildConnections()

    def parseConfig(self):
        """ Parse the config file and build internal data structures """

        if '_global' in self.config:
            self.log.info("Parsing Global section of config")
            gbl = self.config['_global']
        else:
            gbl = dict()

        if 'demo' in self.config:
            self.log.info("Parsing Demo section of config")
            self.demo = self.config['demo']

            config=self.config['demo']
            for feature in [ 'port', 'host', 'remotePort', 'idFile' ]:
                if feature in config:
                    value = config[feature]
                elif feature in gbl:
                    value = gbl[feature]
                else:
                    value = None

                self.__dict__['demo_'+feature] = value

        if '_jump' in self.config:
            self.log.info("Parsing _jump section of config")
            self.jump = self.config['_jump']
            self.log.info("Jump Host {}, jump user {}, jump idfile {}".format(self.jump['jumphost'], self.jump['jumpuser'], self.jump['IdentityFile']))
        else:
            self.jump = None


        if 'target' in self.config:
            self.log.info("Parsing target section of config")
            config=self.config['target']
            for feature in [ 'IdentityFile', 'ec2user', 'host' ]:
                if feature in config:
                    value = config[feature]
                elif feature in gbl:
                    value = gbl[feature]
                else:
                    value = None

                self.__dict__[feature] = value

            if (self.IdentityFile is None):
                self.log.error("IdentityFile is not set")

            if (self.ec2user is None):
                self.log.error("No defintion for ec2user has been found")
            self.log.info("Host {}, user {}, idfile {}".format(self.host, self.ec2user, self.IdentityFile))
            return
        self.log.error("No definition for 'target' was found in config file")


@click.command(name='demo', short_help='Do the cloning demo')
def demo():
    global cm
    cm.doDemo()


@click.command(name='tunnel', short_help='Setup a tunnel using the connection')
def tunnel():
    global cm
    cm.commandWithTunnel()


@click.command(name='confirm', short_help='Confirm the jump host and target are working by running ps -ef')
def confirm():
    global cm
    cm.confirmConnections()

@click.command(name='copy', short_help='Copy a file up the connection')
@click.argument('from_file', default=None)
@click.argument('to_file', nargs=-1) 
def copy(to_file, from_file):
    global cm
    to_file=list(to_file)
    if len(to_file) == 0:
        to_file.append(None)
    cm.doCopy(from_file, to_file[0])

@click.group()
@click.option('--config', required=False, default="./conf.json", type=click.Path(), help="config file")
@click.option('--template', is_flag=True, default=False, help="Output an example config file")
def cli(template, config):
    """Provides a framework for issuing comamnds with fabric to demo the use of copy,
       gateway(jump) hosts and port forwarding"""

    global cm 
    cm = connMan(logger)
    if template:
        cm.configTemplate()
        sys.exit(0)

    cm.loadConfig(config)

cli.add_command(copy)
cli.add_command(tunnel)
cli.add_command(confirm)
cli.add_command(demo)

if __name__ == '__main__':
    cli()

