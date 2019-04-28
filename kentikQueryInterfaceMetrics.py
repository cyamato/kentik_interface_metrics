#!/usr/bin/env python3

__author__ = "Craig Yamato <craig.yamato2@gmail.com>"
__copyright__ = "Copyright 2019"
__credits__ = ["Craig Yamato"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Craig Yamato <craig.yamato2@gmail.com>"
__email__ = "craig.yamato2@gmail.com"
__status__ = "Devlopment"

# Input arguments
# url | KENTIK_URL
# user | KENTIK_API_USER
# token | KENTIK_API_TOKEN
# api_limit
# api_query_limit
# items_per_query
# queries_per_bucket
# config
# filters
# metrics
# dimensions
# dbFormat
# output_file
# base_query
# logLoc
# loglevel | LOGLEVEL
# harperdb_url | KENTIK_HARPERDB_URL
# harperdb_user | KENTIK_HARPERDB_USER
# harperdb_password | KENTIK_HARPERDB_PASSWORD
# harperdb_schema | KENTIK_HARPERDB_SCHEMA
# harperdb_table | KENTIK_HARPERDB_TABLE
# query_time_incorment | KENTIK_QUERY_TIME_INCROMENT
# query_time_amount | KENTIK_QUERY_TIME_AMOUNT

# Import external libaries
import os # Used to get ENV vars
import sys # Used to send meesages to STDERR
import argparse # Used to work with Command line arguments
import yaml # Used to load config yaml file
import json # Used to work with JSON objects sent and recived from Kentik
from urllib.parse import urlparse # Make sure the Kentik API Request is HTTPS
import requests # Used to make HTTPS RESTFull API Calls to Kentik
from time import sleep # Used to space API Request to meet Kentik rate limiting
import base64 # To basic encoding
import datetime # Date settings for the query
import logging # Create Logs

# A class to hold settings information
class GlobalArgs:
    url = 'api.kentik.com/api/v5' # The Kentik Cluster's API Base URL
    user = None # The Kentik API User name
    token = None # The Kentik API Token
    filters = []
    metrics = []
    dimensions = []
    api_limit = 1 # Number of delay seconcds between Non Query API calls
    api_query_limit = 3 # Number of delay seconcds between Query API calls
    items_per_query = 350 # Number of expected returns based on one result per filter
    queries_per_bucket = 5 # Number of quieres to send at one time
    dbFormat = 'column' # Local DB Format (Column | JSON)
    output_file = 'data.json' # The name of the local copy of the resposes
    base_query = 'kentikBaseQuery.json' # A Kentik Query Template to use
    logLoc = './' # Where the log of last request and last response should be stored
    loglevel = 'info' # What level of logging should be used
    harperdb_url = 'http://localhost:9925'
    harperdb_user = '' 
    harperdb_password = ''
    harperdb_schema = 'Kentik_Local'
    harperdb_table = 'Interface_Utlization'
    query_time_incorment = 'day' # What query incremnt (minute | hour | day | month)
    query_time_amount = 1 # How many time incroments to query for

# A class to hold Kentik's interface information
class Interface:
    id = 0
    alias = None
    disc = None
    capacity = 0
    network_boundary = None
    connectivity_type = None
    top_nexthop_asns = []
    provider = None
    vrf = None
    interface_ip = None
    deviceName = None
    deviceSampleRate = 0
    siteName = None
    results = []
    
    def toDict(self, dbFormat='column'):
        d = {
            'ifIndex': self.id,
            'alias': self.alias,
            'disc': self.disc,
            'capacity': self.capacity,
            'network_boundary': self.network_boundary,
            'connectivity_type': self.connectivity_type,
            'provider': self.provider,
            'vrf': self.vrf,
            'interface_ip': self.interface_ip,
            'deviceName': self.deviceName,
            'deviceSampleRate': self.deviceSampleRate,
            'siteName': self.siteName
        }
        
        # Only add Next Hops if JSON
        if type(self.top_nexthop_asns) == 'list' and len(self.top_nexthop_asns) > 0:
            if dbFormat == 'column':
                d['top_nexthop_asns'] = ','.join(self.top_nexthop_asns)
            else:
                d['top_nexthop_asns'] = self.top_nexthop_asns
        else:
            d['top_nexthop_asns'] = []
        
        # Add in all Kentik results except the Key field
        for returned in self.results:
            for key, value in returned.items():
                if key != 'key' and key != 'timeSeries':
                    d[key] = value
        
        return d
    
    def __init__(self, 
        id, 
        alias, 
        disc, 
        capacity, 
        network_boundary, 
        connectivity_type, 
        top_nexthop_asns, 
        provider, 
        vrf, 
        interface_ip, 
        deviceName,
        deviceSampleRate,
        siteName
    ):
        self.id = id
        self.alias = alias
        self.disc = disc
        self.capacity = capacity
        self.network_boundary = network_boundary
        self.connectivity_type = connectivity_type
        self.top_nexthop_asns = top_nexthop_asns
        self.provider = provider
        self.vrf = vrf
        self.interface_ip = interface_ip
        self.deviceName = deviceName
        self.deviceSampleRate = deviceSampleRate
        self.siteName = siteName
    
# A class to hold Kentik's device information
class Device:
    id = 0
    name = None
    siteName = None
    sampleRate = 1
    def __init__(self, id, name, siteName, sampleRate=1):
        self.id = id
        self.name = name
        self.siteName = siteName
        self.sampleRate = sampleRate
        
# A functional class for the Interface discovery and data collection
class KentikInterfaceInfo:
    gArgs = GlobalArgs()
    
    logger = None # Future logging
    
    # Function to setup logging
    def loggingSetup(self):
        logLevel = logging.INFO
        if self.gArgs.loglevel == 'debug':
            logLevel = logging.DEBUG
        elif self.gArgs.loglevel == 'warning':
            logLevel = logging.WARN
        elif self.gArgs.loglevel == 'error':
            logLevel = logging.ERROR
        elif self.gArgs.loglevel == 'critical':
            logLevel = logging.CRITICAL
        
        self.logger = logging.getLogger('Kentik_Interface_Metrics')
        self.logger.setLevel(logLevel)
        formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(processName)s:%(process)d:%(filename)s:%(lineno)d:%(message)s")
        fh = logging.FileHandler(self.gArgs.logLoc + "logs.log")
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        return self
    
    # Setup all working vars
    def setup(self):
        error = False # Set if there is a major error in the config
        
        # Get Command Line Argguments
        cliArgs = None
        msg = "This script will download the p50%, p95%, p99%, p100% utlization "
        msg = msg + "for every interface monitored by a Kentik KDE cluster"
        parser = argparse.ArgumentParser(description=msg)
        
        # Add command line arguments
        parser.add_argument('-v', '--version', action='version', 
            version='%(prog)s 1.0')
        parser.add_argument('-c', '--config', default='./config.yaml',
            help='YAML file with config settigs; defualts to config.yaml')
        parser.add_argument('-l', '--url',
            help='The target url for the Kentik KDE Cluster API; Defualts to US Public')
        parser.add_argument('-u', '--user', 
            help='The KDE user name used to make api calls')
        parser.add_argument('-t', '--token',
            help='The KDE token to used to make api calls')
        parser.add_argument('--api_limit',
            help='The number of delay second for KDE non query api limit calls')
        parser.add_argument('--api_query_limit',
            help='The number of delay second for KDE query api limit calls')
        parser.add_argument('--items_per_query',
            help='The number of filter that will should produce one result each')
        parser.add_argument('--queries_per_bucket',
            help='The number of queries to included in a request to Kentik')
        parser.add_argument('--dbFormat',
            help='The format that record that will be sent to the local database [column | json]')
        parser.add_argument('--output_file',
            help='The name of the JSON file used for the output - This will match the last sent information to the local DB')
        parser.add_argument('--base_query',
            help='The name of the json file with the base Kentik query to be used')
        parser.add_argument('--logLoc',
            help='The directory where local log files should be saved')
        parser.add_argument('--loglevel',
            help='The logging level')
        parser.add_argument('--harperdb_url',
            help='The url of the HarperDB server')
        parser.add_argument('--harperdb_user',
            help='The user name with write access to HarperDB')
        parser.add_argument('--harperdb_password',
            help='The HarperDB Password')
        parser.add_argument('--harperdb_schema',
            help='The name of the Kentik Schema')
        parser.add_argument('--harperdb_table',
            help='The name of the interfaces table')
        parser.add_argument('--query_time_incorment',
            help='What query incremnt (minute | hour | day | month)  min is from now, hr is from the last hr, day and month are from midnite')
        parser.add_argument('--query_time_amount',
            help= 'How many time incroments to query for')

        cliArgs = parser.parse_args(sys.argv[1:])
    
        # Get Enviroment Vars
        localEnvArgs = GlobalArgs ()
        localEnvArgs.url = os.environ.get('KENTIK_URL')
        localEnvArgs.user = os.environ.get('KENTIK_API_USER')
        localEnvArgs.token = os.environ.get('KENTIK_API_TOKEN')
        localEnvArgs.loglevel = os.environ.get('LOGLEVEL')
        localEnvArgs.harperdb_url = os.environ.get('KENTIK_HARPERDB_URL')
        localEnvArgs.harperdb_user = os.environ.get('KENTIK_HARPERDB_USER')
        localEnvArgs.harperdb_password = os.environ.get('KENTIK_HARPERDB_PASSWORD')
        localEnvArgs.harperdb_schema = os.environ.get('KENTIK_HARPERDB_SCHEMA')
        localEnvArgs.harperdb_table = os.environ.get('KENTIK_HARPERDB_TABLE')
        localEnvArgs.query_time_incorment = os.environ.get('KENTIK_QUERY_TIME_INCROMENT')
        localEnvArgs.query_time_amount = os.environ.get('KENTIK_QUERY_TIME_AMOUNT')
        
        # Get Config File Arguments
        fileArgs = GlobalArgs()
        try:
            with open(cliArgs.config, 'r') as yamlConfig:
                try:
                    fileArgs = yaml.safe_load(yamlConfig)
                except yaml.YAMLError as exc:
                    print(exc)
        except FileNotFoundError as e:
            print('No local config file found')

        # Get Docker Secrets
        kentikDockerSecrets = None
        try:
            with open('/run/secrets/kentik_api.yml', 'r') as yamlConfig:
                try:
                    kentikDockerSecrets = yaml.safe_load(yamlConfig)
                except yaml.YAMLError as exc:
                    print(exc)
        except FileNotFoundError as e:
            print('No Kentik secrets found')
        harperDockerSecrets = None
        try:
            with open('/run/secrets/harperdb.yml', 'r') as yamlConfig:
                try:
                    harperDockerSecrets = yaml.safe_load(yamlConfig)
                except yaml.YAMLError as exc:
                    print(exc)
        except FileNotFoundError as e:
            print('No HarperDB secrets found')
            
        # Mix them into one object with the priority of CLI, ENV, File
        if cliArgs.url is not None:
            self.gArgs.url = cliArgs.url
        elif localEnvArgs.url is not None:
            self.gArgs.url = localEnvArgs.url
        elif hasattr(fileArgs,'url'):
            self.gArgs.url = fileArgs.url
            
        if cliArgs.user is not None:
            self.gArgs.user = cliArgs.user
        elif localEnvArgs.user is not None:
            self.gArgs.user = localEnvArgs.user
        elif hasattr(fileArgs,'user'):
            self.gArgs.user = fileArgs.user
        elif hasattr(kentikDockerSecrets, 'user'):
            self.gArgs.user = kentikDockerSecrets.user
        else:
            self.logger.critical("Kentik API user is not set")
            error = True
            
        if cliArgs.token is not None:
            self.gArgs.token = cliArgs.token
        elif localEnvArgs.token is not None:
            self.gArgs.token = localEnvArgs.token
        elif hasattr(fileArgs, 'token'):
            self.gArgs.token = fileArgs.token
        elif hasattr(kentikDockerSecrets,'token'):
            self.gArgs.token = kentikDockerSecrets.token
        else:
            self.logger.critical("Kentik API token is not set")
            error = True
            
        if cliArgs.api_limit is not None:
            self.gArgs.api_limit = cliArgs.api_limit
        elif localEnvArgs.api_limit is not None:
            self.gArgs.api_limit = localEnvArgs.api_limit
        elif hasattr(fileArgs, 'api_limit'):
            self.gArgs.api_limit = fileArgs.api_limit

        if cliArgs.api_query_limit is not None:
            self.gArgs.api_query_limit = cliArgs.api_query_limit
        elif localEnvArgs.api_query_limit is not None:
            self.gArgs.api_query_limit = localEnvArgs.api_query_limit
        elif hasattr(fileArgs,'api_query_limit'):
            self.gArgs.api_query_limit = fileArgs.api_query_limit
        
        if cliArgs.loglevel is not None:
            self.gArgs.loglevel = cliArgs.loglevel
        elif localEnvArgs.loglevel is not None:
            self.gArgs.loglevel = localEnvArgs.loglevel
        elif hasattr(fileArgs,'loglevel'):
            self.gArgs.loglevel = fileArgs.loglevel
        
        if cliArgs.harperdb_url is not None:
            self.gArgs.harperdb_url = cliArgs.harperdb_url
        elif localEnvArgs.harperdb_url is not None:
            self.gArgs.harperdb_url = localEnvArgs.harperdb_url
        elif hasattr(fileArgs, 'harperdb_url'):
            self.gArgs.harperdb_url = fileArgs.harperdb_url
        
        if cliArgs.harperdb_user is not None:
            self.gArgs.harperdb_user = cliArgs.harperdb_user
        elif localEnvArgs.harperdb_user is not None:
            self.gArgs.harperdb_user = localEnvArgs.harperdb_user
        elif hasattr(fileArgs,'harperdb_user'):
            self.gArgs.harperdb_user = fileArgs.harperdb_user
        elif hasattr(harperDockerSecrets,'user'):
            self.gArgs.harperdb_user = harperDockerSecrets.user
        
        if cliArgs.harperdb_password is not None:
            self.gArgs.harperdb_password = cliArgs.harperdb_password
        elif localEnvArgs.harperdb_password is not None:
            self.gArgs.harperdb_password = localEnvArgs.harperdb_password
        elif hasattr(fileArgs,'harperdb_password'):
            self.gArgs.harperdb_password = fileArgs.harperdb_password
        elif hasattr(harperDockerSecrets,'password'):
            self.gArgs.harperdb_password = harperDockerSecrets.password
        
        if cliArgs.harperdb_schema is not None:
            self.gArgs.harperdb_schema = cliArgs.harperdb_schema
        elif localEnvArgs.harperdb_schema is not None:
            self.gArgs.harperdb_schema = localEnvArgs.harperdb_schema
        elif hasattr(fileArgs,'harperdb_schema'):
            self.gArgs.harperdb_schema = fileArgs.harperdb_schema
        
        if cliArgs.harperdb_table is not None:
            self.gArgs.harperdb_table = cliArgs.harperdb_table
        elif localEnvArgs.harperdb_table is not None:
            self.gArgs.harperdb_table = localEnvArgs.harperdb_table
        elif hasattr(fileArgs,'harperdb_table'):
            self.gArgs.harperdb_table = fileArgs.harperdb_table
        
        if cliArgs.query_time_incorment is not None:
            self.gArgs.query_time_incorment = cliArgs.query_time_incorment
        elif localEnvArgs.query_time_incorment is not None:
            self.gArgs.query_time_incorment = localEnvArgs.query_time_incorment
        elif hasattr(fileArgs,'query_time_incorment'):
            self.gArgs.query_time_incorment = fileArgs.query_time_incorment
        
        if cliArgs.query_time_amount is not None:
            self.gArgs.query_time_amount = cliArgs.query_time_amount
        elif localEnvArgs.query_time_amount is not None:
            self.gArgs.query_time_amount = localEnvArgs.query_time_amount
        elif hasattr(fileArgs,'query_time_amount'):
            self.gArgs.query_time_amount = fileArgs.query_time_amount

        if cliArgs.items_per_query is not None:
            self.gArgs.items_per_query = cliArgs.items_per_query
        elif hasattr(fileArgs,'items_per_query'):
            self.gArgs.items_per_query = fileArgs.items_per_query
        
        if cliArgs.queries_per_bucket is not None:
            self.gArgs.queries_per_bucket = cliArgs.queries_per_bucket
        elif hasattr(fileArgs,'queries_per_bucket'):
            self.gArgs.queries_per_bucket = fileArgs.queries_per_bucket
        
        if cliArgs.dbFormat is not None:
            self.gArgs.dbFormat = cliArgs.dbFormat
        elif hasattr(fileArgs,'dbFormat'):
            self.gArgs.dbFormat = fileArgs.dbFormat
        
        if cliArgs.output_file is not None:
            self.gArgs.output_file = cliArgs.output_file
        elif hasattr(fileArgs,'output_file'):
            self.gArgs.output_file = fileArgs.output_file
        
        if cliArgs.base_query is not None:
            self.gArgs.base_query = cliArgs.base_query
        elif hasattr(fileArgs,'base_query'):
            self.gArgs.base_query = fileArgs.base_query
        
        if cliArgs.logLoc is not None:
            self.gArgs.logLoc = cliArgs.logLoc
        elif hasattr(fileArgs,'logLoc'):
            self.gArgs.logLoc = fileArgs.logLoc
            
        if hasattr(fileArgs, 'filters'):
            self.gArgs.filters = fileArgs.filters
            
        if hasattr(fileArgs, 'metrics'):
            self.gArgs.metrics = fileArgs.metrics
            
        if hasattr(fileArgs, 'dimensions'):
            self.gArgs.dimensions = fileArgs.dimensions
        
        # Garbeg Cleanup; Don't use del as it only removes the memory refrance 
        # and GC will miss it.
        parser = None
        cliArgs = None
        localEnvArgs = None
        fileArgs = None
        
        # Exit if there was an error
        if error:
            sys.exit(1)
    
        return self
    
    # Function to make API calls to Kentik
    # This function will setup all need authintacation from system envirement vars
    def kentik_api(self, endpoint, method, payload={}):
        """Make an API call to Kenitk"""
        
        # Setup needed Kentik auth headers in request
        headers = {
            'X-CH-Auth-API-Token': self.gArgs.token,
            'X-CH-Auth-Email': self.gArgs.user,
            'Content-Type': 'application/json'
        }
        
        # Make sure request is https and make the API Endpoint URL
        urlParts = urlparse(self.gArgs.url)
        endpoint = 'https://' + urlParts.netloc + urlParts.path + endpoint
        urlParts = None
        
        # Convert payload to JSON if not already a string
        if type(payload) is not 'str':
            try:
                payload = json.dumps(payload)
            except ValueError as exc:
                self.logger.warning(exc)
                payload = "{}"
        
        # Make the API Call
        req = requests.request(method, endpoint, headers=headers, data=payload)
        
        # Check the response
        response = {}
        # Check if data was returned; 204 is OK but no data
        if req.status_code == 200 or req.status_code == 201:
            try:
                response = req.json()
            except ValueError:
                self.logger.warning("Kentik API Error decoding JSON Response")
                
        elif req.status_code != 204:
            self.logger.warning("Kentik API Error: HTTP Response Code" + req.status_code)
            self.logger.warning(req.text)
        
        # Garbeg Cleanup; Don't use del as it only removes the memory refrance 
        # and GC will miss it.
        headers = None
        endpoint = None
        method = None
        payload = None
        req = None
        
        return response
    
    # Function to get all devices in Kentik
    def getKentikDevices(self):
        self.logger.info('Getting all Devices configured in Kentik')
        self.devices = [] # Array of devices
        
        # Call API for inventory
        kentikDevices = self.kentik_api('/devices', 'GET', {})
        # If you don't need string formating concatantion is faster
        self.logger.info('Recived information for ' + str(len(kentikDevices['devices'])) + ' devices')
        
        # Loop throgh each return to build a device class for each result
        for device in kentikDevices['devices']:
            d = Device(
                device['id'],
                device['device_name'],
                device['site']['site_name'],
                device['device_sample_rate']
            )
            if device['all_interfaces']:
                self.devices.append(d) # Save devices with interfaces to our array
            d = None
            device = None
            
        self.deviceCount = len(self.devices)
        self.logger.info(str(self.deviceCount) + ' devices had interfaces')
    
        return self
    
    # Function to get all device interfaces (Using this call to get ifindex)
    def getInterfaces(self):
        self.interfaces = []
        # Loop through each device and get its interfaces from Kentik
        ir = 0
        self.logger.info('Getting device interfaces')
        if hasattr(self, 'devices'):
            for device in self.devices:
                # Get interfaces for this device from Kentik API
                endpoint = '/device/'+ device.id +'/interfaces' # Make the API Endpoint
                kentikInterfaces = self.kentik_api(endpoint, 'GET', {})
                
                self.logger.info('Recived ' 
                    + str(len(kentikInterfaces)) 
                    + ' interface for Device '
                    + device.name 
                    + ' (' + str(device.id) + ') ' 
                    + str(ir+1) + " of " + str(self.deviceCount))
                
                if len(kentikInterfaces) > 0:
                    # Control loop to limit each interface group to the maxmium per query
                    devices = {
                        'interfaceGroups': [],
                        'name': device.name
                    }
                    interfaces = []
                    counterInterfaces = 2 # We are using a base 2 count to avoid a complex >= if statment bellow
                    for interface in kentikInterfaces:
                        i = Interface(
                            interface['snmp_id'],
                            interface['snmp_alias'],
                            interface['interface_description'],
                            interface['snmp_speed'],
                            interface['network_boundary'],
                            interface['connectivity_type'],
                            interface['top_nexthop_asns'],
                            interface['provider'],
                            None,
                            interface['interface_ip'],
                            device.name,
                            device.sampleRate,
                            device.siteName
                        )
                        # Add VRF info if provided
                        if 'vrf' in interface.keys():
                            if 'name' in interface['vrf'].keys():
                                i.vrf = interface['vrf']['name']
                            else:
                                i.vrf = interface['vrf_id']
                        interfaces.append(i)
                        i = None
                        
                        # Check if we have maxed out; if so add the curent interfaces to the group
                        if counterInterfaces > self.gArgs.items_per_query:
                            devices["interfaceGroups"].append(interfaces)
                            interfaces = []
                    
                    # If there are any interfaces left add them to the group for this device 
                    if interfaces:
                        devices["interfaceGroups"].append(interfaces)
                    
                    # Add Device and Interfaces to self.interfaces for later use
                    self.interfaces.append(devices)
                    
                    # Pause if not the last device
                    if ir < self.deviceCount:
                        sleep(self.gArgs.api_limit)
                    
                    # GC Cleanup
                    kentikInterfaces = None
                ir = ir + 1
        # GC Cleanup
        self.devices = None
        
        return self
    
    # Function to do month date math
    def monthdelta(self, date, delta):
        m, y = (date.month+delta) % 12, date.year + ((date.month)+delta-1) // 12
        if not m: m = 12
        d = min(date.day, [31,
            29 if y%4==0 and not y%400==0 else 28,31,30,31,30,31,31,30,31,30,31][m-1])
        return date.replace(day=d,month=m, year=y)
        
    # Function to load the base Kentik query
    def loadBaseQuery(self):
        self.kQuery = {}
        try:
            with open(self.gArgs.base_query, 'r') as baseQuery:
                # Convert the JSON file to a Dict
                try:
                    self.kQuery = json.load(baseQuery)
                except ValueError as exc:
                    self.logger.critical(exc)
                    sys.exit(1)
        except FileNotFoundError as e:
            self.logger.critical('Base Query Not Found:' + self.gArgs.base_query)
            sys.exit(1)
            
        # Setup base time for query (End time is nearer to now)
        endTime = datetime.datetime.now()
        if self.gArgs.query_time_incorment == 'minute':
            endTime = endTime.replace(microsecond=0,second=0)
            startTime = endTime - datetime.timedelta(minutes=self.gArgs.query_time_amount)
            
        elif self.gArgs.query_time_incorment == 'hour':
            endTime = endTime.replace(microsecond=0,second=0,minute=0)
            startTime = endTime - datetime.timedelta(hours=self.gArgs.query_time_amount)
        
        elif self.gArgs.query_time_incorment == 'day':
            endTime = endTime.replace(microsecond=0,second=0,minute=0,hour=0)
            startTime = endTime - datetime.timedelta(days=self.gArgs.query_time_amount)
        
        elif self.gArgs.query_time_incorment == 'month':
            endTime = endTime.replace(microsecond=0,second=0,minute=0,hour=0)
            startTime = self.monthdelta(endTime, -1*self.gArgs.query_time_amount)
        
        self.fromTime = startTime.strftime("%Y%m%dT%H:%M:00%z")
        self.toTime = endTime.strftime("%Y%m%dT%H:%M:00%z")
        
        self.kQuery['queries'][0]['query']['starting_time'] = startTime.strftime("%Y-%m-%d %H:%M")
        self.kQuery['queries'][0]['query']['ending_time'] = endTime.strftime("%Y-%m-%d %H:%M")
        
        return self
    
    # Function to make sure that we have a list
    def listCheck(self, test, name):
        if type(test) is str:
            # Try JSON
            try:
                test = json.load(test)
            except ValueError as jexc:
                # Nope try YAML
                try:
                    test = yaml.safe_load(test)
                except yaml.YAMLError as yexc:
                    self.logger.warning(yexc)
        if type(test) is dict:
            test = [test]
        if type(test) is not list:
            self.logger.warning('User defined ' + name + ' are not of type string, object, or array')
            test = None
        name = None
        return test
    
    # function to add any addational filters
    def addQueryFilters(self):
        if self.gArgs.filters:
            # Make sure we have list
            addons = self.listCheck(self.gArgs.filters, 'Filters')
            # Add any addons
            if addons:
                self.kQuery["queries"][0]["query"]["filters_obj"]["filterGroups"].extend(addons)
        else:
            self.logger.info('No addational filters')
            
        return self
    
    # function to add any addational metrics
    def addQueryMetrics(self):
        if self.gArgs.metrics:
            # Make sure we have list
            addons = self.listCheck(self.gArgs.metrics, 'Metrics')
            # Add any addons
            if addons:
                self.kQuery["queries"][0]["query"]["aggregates"].extend(addons)
                
            # Check if we need to add an units to the query
            for metric in self.kQuery["queries"][0]["query"]["aggregates"]:
                if metric["unit"] not in self.kQuery["queries"]["query"]["metric"]:
                    self.kQuery["queries"][0]["query"]["metric"].append(metric["unit"])
        else:
            self.logger.info('No addational metrics')
            
        return self
    
    # function to add any addational dimensions
    def addQueryDimensions(self):
        try: 
            check = self.kQuery["queries"][0]["query"]["dimension"].index('InterfaceID_dst')
        except ValueError:
            self.kQuery["queries"][0]["query"]["dimension"].append('InterfaceID_dst')
        if self.gArgs.dimensions:
            # Make sure we have list
            addons = self.listCheck(self.gArgs.dimensions, 'Dimensions')
            # Add any addons
            if addons:
                self.kQuery["queries"][0]["query"]["dimension"].extend(addons)
        else:
            self.logger.info('No addational dimensions')
        
        return self
    
    # function to bulk load interface data to HarperDB
    def sendToHarperDB(self, data):
        # Define our new line
        newLine = '\n'
        keys = data[0].keys()
        keysLen = len(keys) - 1
        
        # Make Headers
        bulkData = ','.join(keys)
        bulkData = bulkData + newLine
        
        # Add lines to bulkData
        for record in data:
            keyIndex = 0
            for key in keys:
                bulkData = bulkData + str(record[key])
                if keyIndex < keysLen:
                    bulkData = bulkData + ","
                else:
                    bulkData = bulkData + newLine
                keyIndex += 1
        
        # Build HarperDB bulk insert object
        hdbObject = {
            'operation': 'csv_data_load',
            'action': 'insert',
            'schema': self.gArgs.harperdb_schema,
            'table': self.gArgs.harperdb_table,
            'data': bulkData
        }
        
        # Make header
        authStr = self.gArgs.harperdb_user + ':' + self.gArgs.harperdb_password
        authStr = bytes(authStr, 'utf-8')
        authStr = base64.b64encode(authStr)
        authStr = authStr.decode('ascii')
        authStr = 'Basic ' + authStr
        headers={
            'Content-Type': 'application/json',
            'Authorization': authStr
        } 
        
        # Make a request
        try:
            req = requests.request(
                'POST', 
                self.gArgs.harperdb_url,
                headers=headers, 
                data=hdbObject
            )
        except requests.exceptions.ConnectionError as e:
            self.logger.critical(e)
            sys.exit(1)
        # Check if data was returned; 204 is OK but no data
        if req.status_code == 200 or req.status_code == 201:
            try:
                response = req.json()
                self.logger.info(response['message'])
            except ValueError:
                self.logger.warning("Harper Error")
                
        else:
            self.logger.critical("Harper Error: HTTP Response Code " + req.status_code)
            self.logger.critical(req.text)
            sys.exit(1)
    
    # function to update our local DB
    def addResultsToLocalDB(self):
        # Designed for HarperDB
        dbArray = []
        # Turn each interface class into a dict and add to dbArray
        for device in self.interfaces:
            for ig in device['interfaceGroups']:
                for i in ig:
                    interfaceX = i.toDict()
                    interfaceX['fromTime'] = self.fromTime
                    interfaceX['toTime'] = self.toTime
                    dbArray.append(interfaceX)
                    
        with open(self.gArgs.logLoc + self.gArgs.output_file, 'w') as outfile:  
            outfile.write(json.dumps(dbArray, indent=4))
            
        self.sendToHarperDB(dbArray)
        
        return self
    
    # function to process kentik top x query results
    def processKentikTopX(self, results):
        # build a refrance index so we don't have to O1 loop every time
        bucketNameIndexs = []
        for b in self.interfaces:
            bucketNameIndexs.append(b['name'])
        
        # Loop through results
        for bucketResult in results['results']:
            # Turn Bucket Name back into device
            bucketResultName = bucketResult['bucket'][:bucketResult['bucket'].rfind('_')]
            
            # Find device in self.interface[]
            bucketIndex = bucketNameIndexs.index(bucketResultName)
            
            # Loop through each result
            for interface in bucketResult['data']:
                # Extract Interface SNMP ID
                ifIndex = interface['output_port'][interface['output_port'].rfind('(')+1:]
                ifIndex = ifIndex[:-1]
            
                # Find Inferface SNMP ID in self.interface[device][]
                for g in self.interfaces[bucketIndex]['interfaceGroups']:
                    gIndexFound = False
                    for ifInfo in g:
                        if ifIndex == ifInfo.id:
                            ifInfo.results.append(interface)
                            gIndexFound = True # Get out of the ifGroup Loop
                            break
                    if gIndexFound:
                        break # Get out of the ifGroup Loop
                    
            # Update with Metrics
            
        # GC
        del bucketNameIndexs[:]
        bucketResultName = None
        bucketIndex = None
        ifIndex = None
        
        return self
    
    # Submit Kentik top x query
    def submitTopXQuery(self, bucket):
        self.logger.info('Running Kentik API Top X Query')
        endpoint = '/query/topXdata'
        interfaceMetrics = self.kentik_api(endpoint, 'POST', bucket)
        
        # Process recived data
        self.processKentikTopX(interfaceMetrics)
        
        # Pause for API Limit
        sleep(self.gArgs.api_query_limit)
        
        # Save a local copy of request and response from Kentik
        with open(self.gArgs.logLoc + 'lastRequest.json', 'w') as outfile:  
            outfile.write(json.dumps(bucket, indent=4))
        with open(self.gArgs.logLoc + 'lastResponse.json', 'w') as outfile:  
            outfile.write(json.dumps(interfaceMetrics, indent=4))
            
        return self
    
    # function to count queries in a bucket and submit when needed
    def queryBucketCount(self, countQueries, bucket, deviceCheck, force):
        if force:
            if len(bucket['queries']) > 1:
                self.submitTopXQuery(bucket)
            countQueries = None
            bucket = None
        else:
            if not deviceCheck:
                countQueries += 1
            # if <: None as >= causes two checks when ran
            if countQueries < self.gArgs.queries_per_bucket:
                None
            else:
                self.submitTopXQuery(bucket)
                countQueries = 0
                bucket = {
                   "queries": [] 
                }
        return countQueries, bucket;
    
    # Function to build and run Buckets of Queries
    def makeQueryBuckets(self):
        #Check that we have interface to check for data on
        if hasattr(self, 'interfaces'):
            if self.interfaces:
                # Query for traffic on all interfaces
                # Outter loop is for each device
                # Next inner loop is for each interface group
                # Next inner loop is to build each interfaces filter
                # One device per query
                
                # Set up our query
                baseQuery = self.kQuery['queries'][0]
                bucket = {
                    "queries": []
                }
                
                # Track how many queries we have; fater then LENing every time
                countQueries = 0
                # Outter device loop
                for device in self.interfaces:
                    # Inner interfaceGroup loop
                    qCount = 0
                    for ig in device['interfaceGroups']:
                        query = baseQuery # New interfaceGroup, new query
                        query['bucket'] = device['name'] + "_" + str(qCount)
                        qCount += 1
                        query['query']['device_name'] = [device['name']]
                        
                        # Inner interface filter loop
                        fs = [] # Array of Filters
                        for interface in ig:
                            # Make filter
                            fs.append({
                                'filterField': 'output_port',
                                'operator': '=',
                                'filterValue': interface.id
                            })
                            
                        # Make filter group
                        fg = {
                            'name': '',
                            'named': False,
                            'connector': 'Any',
                            'not': False,
                            'autoAdded': "",
                            'filters': fs.copy(),
                            'saved_filters': [],
                            'filterGroups': []
                        }
                        
                        # Add filter group to query
                        query['query']['filters_obj']['filterGroups'] = [{
                            'name': '',
                            'named': False,
                            'connector': 'Any',
                            'not': False,
                            'autoAdded': "",
                            'filters': fs.copy(),
                            'saved_filters': [],
                            'filterGroups': []
                        }]
                        
                        del fs[:]
                        
                        # Add Query to bucket; new query object set at top of loop
                        bucket['queries'].append(query.copy())
                            
                        # Check if bucket needs to be procesed
                        countQueries, bucket = self.queryBucketCount(countQueries, bucket, False, False)
                    # Check if bucket needs to be procesed
                    countQueries, bucket = self.queryBucketCount(countQueries, bucket, True, False)
                # force bucket submit
                countQueries, bucket = self.queryBucketCount(countQueries, bucket, False, True)
        return self

    # Start Message
    def startMessage(self):
        self.logger.info('started')
        return self
        
    # End Message
    def completedMessage(self):
        self.logger.info('completed')
        return self

interfaceInfo = (KentikInterfaceInfo()
    .setup()
    .loggingSetup()
    .startMessage()
    .loadBaseQuery()
    .addQueryFilters()
    .addQueryMetrics()
    .addQueryDimensions()
    .getKentikDevices()
    .getInterfaces()
    .makeQueryBuckets()
    .addResultsToLocalDB()
    .completedMessage()
)

interfaceInfo = None
