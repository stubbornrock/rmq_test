#!/usr/bin/env /usr/bin/python
'''Python module to query the RabbitMQ Management Plugin REST API and get
results that can then be used by Zabbix.

https://github.com/jasonmcintosh/rabbitmq-zabbix
'''
import json
import optparse
import socket
import urllib2
import subprocess
import tempfile
import os
import sys
import ConfigParser
from rmqlog import rmqlogger

class RabbitMQAPI(object):
    '''Class for RabbitMQ Management API'''

    def __init__(self, user_name='guest', password='guest', host_name='',
                 port=15672, conf='etc/zabbix/zabbix_agentd.conf'):
        self.user_name = user_name
        self.password = password
        self.host_name = host_name or socket.gethostname()
        self.port = port
        self.conf = conf or '/etc/zabbix/zabbix_agentd.conf'

    def call_api(self, path):
        '''Call the REST API and convert the results into JSON.'''
        url = 'http://{0}:{1}/api/{2}'.format(self.host_name, self.port, path)
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, url, self.user_name, self.password)
        handler = urllib2.HTTPBasicAuthHandler(password_mgr)
        return json.loads(urllib2.build_opener(handler).open(url).read())

    def check_aliveness(self):
        '''Declares a test queue, then publishes and consumes a message. 
           If everything is ok return {"status":"ok"}
           Note: the test queue will not be deleted (to to prevent queue churn if this is repeatedly pinged).
        '''
        return self.call_api('aliveness-test/%2f')['status']

    def list_whole_sys_items(self):
        ''' List the system items name for zabbix discovery to use!
        '''
        items = []
        for tup in conf.items("whole_sys_items"):
           for item in tup[1].split(','):
               element = {'{#ITEMNAME}':item}
               items.append(element)
        if DEBUG:
            rmqlogger.info(items)
        return items		

    def check_whole_sys(self):
        '''get item value to save in a file,
           use zabbix_sender to active send the key value
        ''' 
        return_code = 0       
        rdatafile = tempfile.NamedTemporaryFile(delete=False)	
        overview = self.call_api('overview')
        self._prepare_whole_sys_data(overview,rdatafile)
        if DEBUG:
            rdatafile.seek(0)
            rmqlogger.info(rdatafile.read())
        rdatafile.close()
        return_code |= self._send_data(rdatafile)
        os.unlink(rdatafile.name)
        return return_code				        

    def _prepare_whole_sys_data(self, overview, tmpfile):
        '''Prepare the whole sytem data for sending'''
        for item in conf.get('whole_sys_items','object_totals').split(','):
            key = '"rabbitmq.overview[{0}]"'
            key = key.format(item)
            value = overview.get('object_totals', {}).get(item,0)
            tmpfile.write("- %s %s\n" % (key, value))  
        for item in conf.get('whole_sys_items','queue_totals').split(','):
            key = '"rabbitmq.overview[{0}]"'
            key = key.format(item)
            value = overview.get('queue_totals', {}).get(item,0)
            tmpfile.write("- %s %s\n" % (key, value))              
        for item in conf.get('whole_sys_items','message_stats').split(','):   
            key = '"rabbitmq.overview[{0}]"'
            key = key.format(item)
            value = overview.get('message_stats', {}).get(item,{}).get('rate',0)
            tmpfile.write("- %s %s\n" % (key, value))    

    def list_nodes(self):
        '''Lists all rabbitMQ nodes in the cluster
        '''
        nodes = []
        for node in self.call_api('nodes'):
            # We need to return the node name, because Zabbix
            # does not support @ as an item paramater
            name = node['name'].split('@')[1]
            type = node['type']
            element = {'{#NODENAME}': name,
                       '{#NODETYPE}': type}
            nodes.append(element)
        if DEBUG:
            rmqlogger.info(nodes)
        return nodes
		
    def check_node(self):
        '''Return the value for a specific item in a node's details.
        '''		
        return_code = 0
        rdatafile = tempfile.NamedTemporaryFile(delete=False)	
        for node in self.call_api('nodes'):
            self._prepare_node_data(node,rdatafile)

        if DEBUG:
            rdatafile.seek(0)
            rmqlogger.info("\n"+rdatafile.read())
        rdatafile.close()
        return_code |= self._send_data(rdatafile)
        os.unlink(rdatafile.name)
        return return_code
       
    def _prepare_node_data(self,node,tmpfile):
        '''Prepare the queue data for sending
        '''
        try:
            check_items = conf.get('nodes','root').split(',')
        except Exception, e:
            rmqlogger.error("The monitor_items.conf file:%s" %str(e))
        else:
            for item in check_items:
                key = '"rabbitmq.node[{0},{1}]"'
                key = key.format(node['name'].split('@')[1],item)
                value =node.get(item, 0)
                tmpfile.write("- %s %s\n" % (key, value))

    def list_queues(self, filters=None):
        '''
        List all of the RabbitMQ queues, filtered against the filters provided
        in .rab.auth. See README.md for more information.
        '''
        queues = []
        if not filters:
            filters = [{}]
        for queue in self.call_api('queues'):
            for _filter in filters:
                check = [(x, y) for x, y in queue.items() if x in _filter]
                shared_items = set(_filter.items()).intersection(check)
                if len(shared_items) == len(_filter):
                    element = {'{#VHOSTNAME}': queue['vhost'],
                               '{#QUEUENAME}': queue['name']}
                    queues.append(element)
                    break
        if DEBUG: 
           rmqlogger.info(queues)
        return queues

    def check_queue(self, filters=None):
        '''Return the value for a specific item in a queue's details.
        '''
        return_code = 0
        if not filters:
            filters = [{}]

        rdatafile = tempfile.NamedTemporaryFile(delete=False)	
        for queue in self.call_api('queues'):
            success = False
            for _filter in filters:
                check = [(x, y) for x, y in queue.items() if x in _filter]
                shared_items = set(_filter.items()).intersection(check)
                if len(shared_items) == len(_filter):
                    success = True
                    break
            if success:
                self._prepare_queue_data(queue, rdatafile)
        if DEBUG:
            rdatafile.seek(0)
            rmqlogger.info("\n"+rdatafile.read())
        rdatafile.close()
        return_code |= self._send_data(rdatafile)
        os.unlink(rdatafile.name)
        return return_code

    def _prepare_queue_data(self, queue, tmpfile):
        '''Prepare the queue data for sending
        '''
        for item in conf.get('queues','root').split(','):
            key = '"rabbitmq.queue[{0},{1},{2}]"'
            key = key.format(queue['vhost'], queue['name'], item)
            value = queue.get(item, 0)
            tmpfile.write("- %s %s\n" % (key, value))

        for item in conf.get('queues','message_stats').split(','):
            key = '"rabbitmq.queue[{0},{1},{2}]"'
            key = key.format(queue['vhost'], queue['name'], item)
            value = queue.get('message_stats', {}).get(item, {}).get('rate',0)
            tmpfile.write("- %s %s\n" % (key, value))

    def _send_data(self, tmpfile):
        '''Send the key-value file data to Zabbix.
        '''
        args = 'zabbix_sender -c {0} -i {1}'
        return_code = 0
        if DEBUG:
            p = subprocess.Popen(args.format(self.conf, tmpfile.name),
                                       shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT)
            return_code = p.wait()
            rmqlogger.info("Return Code: %s\nMessage:%s"%(return_code,p.stdout.read()))
        else:
            return_code |= subprocess.call(args.format(self.conf, tmpfile.name),
                                       shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT)
        return return_code


def main():
    '''Command-line parameters and decoding for Zabbix use/consumption.
    '''
    choices = ['check_whole_sys', 'list_whole_sys_items',\
               'check_node', 'list_nodes', \
               'check_queue', 'list_queues', 'aliveness']
    parser = optparse.OptionParser()
    parser.add_option('--username', help='RabbitMQ API username',
                      default='guest')
    parser.add_option('--password', help='RabbitMQ API password',
                      default='guest')
    parser.add_option('--hostname', help='RabbitMQ API host',
                      default=socket.gethostname())
    parser.add_option('--port', help='RabbitMQ API port', type='int',
                      default=15672)
    parser.add_option('--conf', 
                      default='/etc/zabbix/zabbix_agentd.conf')
    parser.add_option('--check',help='Type of check',type='choice',
                      choices=choices)
    parser.add_option('--node', help='Which node to check (valid for --check=server)')
    parser.add_option('--metric', help='Which metric to evaluate (valid for --check=server)', default='')

    parser.add_option('--filters', help='Filter used queues (see README)FILTER')
    (options, args) = parser.parse_args()

    if not options.check:
        parser.error('You should specify one check type, Example: --check="xxx"!!')
    
    if options.check == 'list_queues' or options.check == 'check_queue':
        if not options.filters:
            filters = [{}]
            if DEBUG:
                rmqlogger.warning("Warn:%s List queues NO Filters!!" %options.check)
        else:
            try:
                filters = json.loads(options.filters)
            except Exception , e:
                rmqlogger.error("Error:%s is invalid filters object!" %(options.filters))
                parser.error("Error: Invalid filters object!!")
        if not isinstance(filters, (list, tuple)):
            filters = [filters]
    
    api = RabbitMQAPI(user_name=options.username, password=options.password,
                      host_name=options.hostname, port=options.port,
                      conf=options.conf)
    if options.check == 'aliveness':
        print api.check_aliveness()
    elif options.check == 'list_whole_sys_items':
        print json.dumps({'data': api.list_whole_sys_items()})
    elif options.check == 'check_whole_sys':
        print api.check_whole_sys()
    elif options.check == 'list_nodes':
        print json.dumps({'data': api.list_nodes()})
    elif options.check == 'check_node':
        print api.check_node()
    elif options.check == 'list_queues':
        print json.dumps({'data': api.list_queues(filters)})
    elif options.check == 'check_queue':
        print api.check_queue(filters)

if __name__ == '__main__':
    conf_file = "monitor_items.conf"
    #import pdb;pdb.set_trace()
    conf = ConfigParser.ConfigParser()
    if os.path.exists(conf_file):
        conf.read("monitor_items.conf")
        DEBUG = int(conf.get('debug','isLogDebug'))
        main()
    else:
        rmqlogger.error("The monitor_items.conf file does not exist!!")
