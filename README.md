This set of containers and scripts that will check Kentik for interface usage and store it in a HarperDB database

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
  * '--config', YAML file with config settigs; defualts to config.yaml
  * '--url', The target url for the Kentik KDE Cluster API; Defualts to US Public
  * '--user', The KDE user name used to make api calls
  * '--token', The KDE token to used to make api calls
  * '--api_limit', The number of delay second for KDE non query api limit calls
  * '--api_query_limit', The number of delay second for KDE query api limit calls
  * '--items_per_query', The number of filter that will should produce one result each
  * '--queries_per_bucket', The number of queries to included in a request to Kentik
  * '--query_time_incorment', What query incremnt (minute | hour | day | month)  min is from now, hr is from the last hr, day and month are from midnite
  * '--query_time_amount', How many time incroments to query for
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