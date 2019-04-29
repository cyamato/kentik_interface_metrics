This is a set of containers and scripts that will check Kentik for interface usage and store it in a HarperDB database

---

kentikQueryInterfaceMetrics.py is the main Python 3 script for gathering interface metrics
The defualt output pre DB processing is:
```
  [{
    'ifIndex': ,
    'alias': ,
    'disc': ,
    'capacity': ,
    'network_boundary': ,
    'connectivity_type': ,
    'provider': ,
    'vrf': ,
    'interface_ip': ,
    'deviceName': ,
    'deviceSampleRate': ,
    'siteName': ,
    'top_nexthop_asns': ,
    'fromTime': ,
    'toTime': ,
    'avg_bits_per_sec': ,
    'p95th_bits_per_sec': ,
    'p99th_bits_per_sec': ,
    'max_bits_per_sec': ,
    'avg_avg_sample_rate': ,
    'avg_flows_per_sec': 
  }]
```

It will also output this to a json text file at --logLoc + --output_file which defualts to ./data.json

The last Kentik request and resposne will be logged to --logLoc as lastRequest.json and lastResponse.json

Script loggs are sent to stdout/sdterr and the file logs.log in --logLoc

To change the database used write a new DB handler function and change the pointer in the ```addResultsToLocalDB``` function.  The dbArray var holds the array described above.

---

kentikBaseQuery.json file is the base query that is used for requests to Kentik.  Change this file to change the request including deminsions, filters, and metrics 

---

harperDBSetup.py file is a Python 3 script to setup a HarperDB for use with the kentikQueryInterfaceMetrics.py

---

### Docker

Please set the information in the .env

Please update the scripts for the right security

to setup run 
```docker-compose up -d``` to setup

Run as a cron job
```docker-compose up -d getKentikInterfaces```

### CLI 

to setup run 
```
pip install --no-cache-dir -r requirements.txt
python3 harperDBSetup.py \
  --harperdb_url=$KENTIK_HARPERDB_URL \
  --harperdb_user=$KENTIK_HARPERDB_USER \
  --harperdb_password+$KENTIK_HARPERDB_PASSWORD
``` 


run 
```
python3 kentikQueryInterfaceMetrics.py \
  --user=$KENTIK_API_USER \
  --token=$KENTIK_API_TOKEN \
  --harperdb_url=$KENTIK_HARPERDB_URL \
  --harperdb_user=$KENTIK_HARPERDB_USER \
  --harperdb_password+$KENTIK_HARPERDB_PASSWORD
```

#### kentikQueryInterfaceMetrics.py switch commands
  * '--config', YAML file with config settings; defaults to config.yaml
  * '--url', The target url for the Kentik KDE Cluster API; Defaults to US Public
  * '--user', The KDE user name used to make api calls
  * '--token', The KDE token to used to make api calls
  * '--api_limit', The number of delays second for KDE non-query api limit calls
  * '--api_query_limit', The number of delays second for KDE query api limit calls
  * '--items_per_query', The number of filters that will produce one result each
  * '--queries_per_bucket', The number of queries to include in a request to Kentik
  * '--query_time_incorment', What query increment (minute | hour | day | month)  min is from now, hr is from the last hr, day and month are from midnite
  * '--query_time_amount', How many time increments to query for
  * '--dbFormat', The format that record that will be sent to the local database [column | json]
  * '--output_file', The name of the JSON file used for the output - This will match the last sent information to the local DB
  * '--base_query', The name of the json file with the base Kentik query to be used
  * '--logLoc', The directory where local log files should be saved
  * '--loglevel', The logging level
  * '--harperdb_url', The url of the HarperDB server
  * '--harperdb_user', The user name with write access to HarperDB
  * '--harperdb_password', The HarperDB Password
  * '--harperdb_schema', The name of the Kentik Schema
  * '--harperdb_table', The name of the interfaces table

#### kentikQueryInterfaceMetrics.py Enviroment Varabules:
  * KENTIK_URL
  * KENTIK_API_USER
  * KENTIK_API_TOKEN
  * KENTIK_QUERY_TIME_INCROMENT
  * KENTIK_QUERY_TIME_AMOUNT
  * LOGLEVEL
  * KENTIK_HARPERDB_URL
  * KENTIK_HARPERDB_USER
  * KENTIK_HARPERDB_PASSWORD
  * KENTIK_HARPERDB_SCHEMA
  * KENTIK_HARPERDB_TABLE
  
#### kentikQueryInterfaceMetrics.py switch commands
  * '--harperdb_url', The url of the HarperDB server
  * '--harperdb_user', The user name with write access to HarperDB
  * '--harperdb_password', The HarperDB Password
  * '--harperdb_schema', The name of the Kentik Schema
  * '--harperdb_table', The name of the interfaces table