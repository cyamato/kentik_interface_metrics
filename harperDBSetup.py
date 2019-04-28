#!/usr/bin/env python3

__author__ = "Craig Yamato <craig.yamato2@gmail.com>"
__copyright__ = "Copyright 2019"
__credits__ = ["Craig Yamato"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Craig Yamato <craig.yamato2@gmail.com>"
__email__ = "craig.yamato2@gmail.com"
__status__ = "Devlopment"

import yaml # Used to load config yaml file
import json # Used to work with JSON objects sent and recived from Kentik
import requests # Used to make HTTPS RESTFull API Calls to Kentik
import argparse # Used to work with Command line arguments
import sys # Used to send meesages to STDERR
import base64 # To basic encoding

harper = {
  'url': 'http://localhost:9925',
  'auth': {
    'user': 'My_User_Name',
    'password': 'My_Password'
  },
  'create_schema': {
    'operation': 'create_schema',
    'schema': 'Kentik_Local'
  },
  'create_table': {
    "operation":"create_table",
    "schema":"Kentik_Local",
    "table":"Interface_Utlization",
    "hash_attribute": "id"
  }
}

# Get Command Line Argguments
cliArgs = None
msg = "This script will download the p50%, p95%, p99%, p100% utlization "
msg = msg + "for every interface monitored by a Kentik KDE cluster"
parser = argparse.ArgumentParser(description=msg)

# Add command line arguments
parser.add_argument('-v', '--version', action='version', 
  version='%(prog)s 1.0')
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

cliArgs = parser.parse_args(sys.argv[1:])

error = False # Set if there is a major error in the config

dockerSecrets = {}
try:
  with open('/run/secrets/harperdb.yml', 'r') as yamlConfig:
    try:
      dockerSecrets = yaml.safe_load(yamlConfig)
    except yaml.YAMLError as exc:
      print(exc)
except FileNotFoundError as e:
  print('No secrets found')

if cliArgs.harperdb_url is not None:
  harper['url'] = cliArgs.harperdb_url
else:
  print("Harper harperdb_url not set", file=sys.stderr)
  error = True

if cliArgs.harperdb_user is not None:
  harper['auth']['user'] = cliArgs.harperdb_user
elif hasattr(dockerSecrets, 'user'):
  harper['auth']['user'] = dockerSecrets.user
else:
  print("Harper harperdb_user not set", file=sys.stderr)
  error = True

if cliArgs.harperdb_password is not None:
  harper['auth']['password'] = cliArgs.harperdb_password
elif hasattr(dockerSecrets, 'password'):
  harper['auth']['password'] = dockerSecrets.password
else:
  print("Harper harperdb_password not set", file=sys.stderr)
  error = True

if cliArgs.harperdb_schema is not None:
  harper['create_schema']['schema'] = cliArgs.harperdb_schema
  harper['create_table']['schema'] = cliArgs.harperdb_schema

if cliArgs.harperdb_table is not None:
  harper['create_table']['table'] = cliArgs.harperdb_table

# Exit if there was an error
if error:
    sys.exit(1)

print(harper)
print(harper['auth'])
print(harper['auth']['user'])

# Make header
authStr = harper['auth']['user'] + ':' + harper['auth']['password']
authStr = bytes(authStr, 'utf-8')
authStr = base64.b64encode(authStr)
authStr = authStr.decode('ascii')
authStr = 'Basic ' + authStr
headers={
  'Content-Type': 'application/json',
  'Authorization': authStr
} 

# function to make harperDB Calls
def harperDBAPICall(payload):
  req = requests.request(
      'POST', 
      harper['url'],
      headers=headers, 
      data=payload
  )
  
  # Check if data was returned; 204 is OK but no data
  if req.status_code == 200 or req.status_code == 201:
      try:
          response = req.json()
          print(response['message'])
      except ValueError:
          print("Harper Error", file=sys.stderr)
          
  else:
      print("Harper Error: HTTP Response Code", req.status_code, file=sys.stderr)
      print(req.text, file=sys.stderr)

print('Setting Up HarperDB @', harper['url'])

harperDBAPICall(harper['create_schema'])
harperDBAPICall(harper['create_table'])
