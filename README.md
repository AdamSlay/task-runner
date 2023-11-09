# LTS Task Runner

This script is intended to be used as a task runner for the LongTermStats image in AWS Fargate.
Most environment variables and network related variables are stored in the _***SSM Parameter Store***_ and accessed via the ```ssm_path``` 
variable in the ```config.toml``` file. Note that the ```boto3``` library from AWS will use the AWS account that is logged in on the local ```aws-cli```.

## Installation
To install the script, clone the repository and install the dependencies:
```bash
pip3 install -r requirements.txt
```

## Usage
You must be logged into the ```aws-cli``` with an account that has the appropriate permissions to run the script.

To run the script and launch a new task, run the following command:
```bash
python3 lts-task-runner.py --sdate [YYYY-MM-DD] --edate [YYYY-MM-DD] --warn [DEBUG, INFO, WARNING, ERROR, CRITICAL]
```

If any parameter is not specified, the container will use its default value.

## Configuration
The following parameters should be stored in the _***SSM Parameter Store***_:
- ```subnet_id```: the subnet ID in which the Fargate cluster is intended to run stored as a comma separated list of Strings
- ```security_group_id```: the security group ID in which the Fargate cluster is intended to run stored as a comma separated list of Strings
- ```assign_public_ip```: whether to assign a public IP to the Fargate cluster, either "ENABLED" or "DISABLED"
- ```/env```: a subdirectory containing the environment variables for the LongTermStats application. As of now, DATASERVER_HOST and MESONET_MAILHOST

The configuration file is stored in the ```config.json``` file. This file is ignored by git, so you can edit the ```config.json.example``` file then rename it to ```config.json```.
The following parameters can be configured:
- ```cluster```: the name of the ECS cluster
- ```task_def```: the name of the task definition
- ```launch_type```: the launch type of the task, either "FARGATE" or "EC2"
- ```count```: the number of tasks to run
- ```ssm_path```: the path to the SSM Parameter Store
- ```container_name```: the name of the container to run