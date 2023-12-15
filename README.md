# LTS Task Runner

This script is intended to be used as a task runner for the LongTermStats image in AWS Fargate.
Most environment variables and network related variables are stored in the _***SSM Parameter Store***_ and accessed via the ```ssm_path``` 
variable in the ```run_config.json``` file. Edit the ```run_config.json``` file to change the task configuration.
Note that the ```boto3``` library from AWS will use the AWS account that is logged in on the local ```aws-cli```.

## Installation
To install the script, clone the repository and install the dependencies:
```bash
pip3 install -r requirements.txt
```

## Usage
You must be logged into the ```aws-cli``` with an account that has the appropriate AWS permissions to run the task in ECS.

To run the script and launch a new task, run the following command:
```shell
python3 TaskRunner.py --sdate [YYYY-MM-DD] --edate [YYYY-MM-DD] --warn [DEBUG, INFO, WARNING, ERROR, CRITICAL]
```
Tags should be specified as a comma separated list of key-value pairs, e.g. 
```shell
python3 TaskRunner.py --sdate [YYYY-MM-DD] --edate [YYYY-MM-DD] --tags key1=value1,key2=value2
python3 TaskRunner.py --sdate 2023-12-03 --edate 2023-12-07 --tags version=<image-version>,commit=<git-hash>
```
Specify a config file with the ```--config``` flag:
```shell
python3 TaskRunner.py --config <path/to/config.json>
```



If any parameter is not specified, the container will use its default value.

## Configuration
The following parameters should be stored in the _***SSM Parameter Store***_ at the ```ssm_path``` location:
- ```subnet_id```: AWS VPC Subnet ID
- ```security_group_id```: AWS VPC Security Group ID
- ```assign_public_ip```: "ENABLED" or "DISABLED"
- ```DATASERVER_HOST```: Route53 DNS name
- ```MESONET_MAILHOST```: email

To alter the run configuration, edit the ```run_config.json``` file. This file is ignored by git, so you can edit the ```run_config.json.example``` file then rename it to ```run_config.json```.
The following parameters can be configured:
- ```cluster```: ECS Cluster
- ```task_def```: Task Definition
- ```launch_type```: "FARGATE" or "EC2"
- ```count```: number of tasks to run
- ```ssm_path```: SSM Parameter Store path
- ```container_name```: Container Image to Run