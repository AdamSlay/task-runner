import argparse
import boto3
import json
import logging


class TaskRunner:
    """
    Run ECS tasks from the command line with overrides from a config file
    """

    def __init__(self, args: argparse.Namespace):

        with open(args.config, 'r') as f:
            self.config = json.load(f)

        self.args = args
        self.ecs = boto3.client('ecs')
        self.ssm = boto3.client('ssm')
        arn = boto3.client('sts').get_caller_identity()['Arn']
        self.aws_user = arn.split('/')[-1]

    def build_command_arguments(self) -> list:
        """
        Build the command for the LongTermStats entrypoint from the command line arguments
        :return: command for the LongTermStats entrypoint as a list
        """
        command_args = []  # arguments for the LongTermStats entrypoint, so you don't need to include 'LongTermStats'
        if self.args.sdate is not None:
            command_args.extend(["--sdate", self.args.sdate])
        if self.args.edate is not None:
            command_args.extend(["--edate", self.args.edate])
        if self.args.warn is not None:
            command_args.extend(["--warn", self.args.warn])

        logging.info(f'Command for LongTermStats entrypoint: {command_args}')
        return command_args

    def build_network_configuration(self) -> dict:
        """
        Build the network configuration for the ECS task from SSM parameters
        :return: network configuration for the ECS task as a dict
        """
        subnet_path = self.config["ssm"]["ssm_path"] + "/subnet"
        sg_path = self.config["ssm"]["ssm_path"] + "/security_group"
        ip_path = self.config["ssm"]["ssm_path"] + "/assign_public_ip"

        subnet_id = self.ssm.get_parameter(Name=subnet_path)['Parameter']['Value']
        security_group_id = self.ssm.get_parameter(Name=sg_path)['Parameter']['Value']
        assign_public_ip = self.ssm.get_parameter(Name=ip_path)['Parameter']['Value']

        network_configuration = {
            'awsvpcConfiguration': {
                'subnets': [subnet_id],
                'securityGroups': [security_group_id],
                'assignPublicIp': assign_public_ip
            }
        }
        logging.info(
            f'Network configuration for ECS task: [subnets: {subnet_id}, security_groups: {security_group_id}, assign_public_ip: {assign_public_ip}]')
        return network_configuration

    def build_overrides(self) -> dict:
        """
        Build the overrides for the ECS task from SSM parameters and command line arguments
        :return: overrides for the ECS task as a dict
        """
        overrides = {
            'containerOverrides': [
                {
                    'name': self.config['overrides']['container_name'],
                    'command': self.build_command_arguments(),
                },
            ],
        }

        env_vars = self.config["task"]["env_vars"]
        if env_vars:
            environment = [{e: env_vars[e]} for e in env_vars]
            logging.info(f'Environment variables provided for ECS task: {environment}')
            overrides['containerOverrides'][0]['environment'] = environment

        logging.info(f'Container_name: {self.config["overrides"]["container_name"]}')
        return overrides

    def build_tags(self) -> list:
        """
        Build the tags for the ECS task
        :return: tags for the ECS task as a list of dicts
        """
        tags = []
        if self.args.tags:
            # convert tags string to list of dicts: [{'key': 'key1', 'value': 'value1'}, {'key': 'key2', 'value': 'value2'}]
            tags = [{'key': t.split('=')[0], 'value': t.split('=')[1]} for t in self.args.tags.split(',')]
        tags.extend(self.config['task']['tags'])
        tags.append({'key': 'aws_user', 'value': self.aws_user})
        return tags

    def submit_task(self) -> None:
        """
        Submit the ECS task to AWS
        :return: Response from AWS as a dict
        """
        task_response = self.ecs.run_task(
            cluster=self.config['task']['cluster'],
            taskDefinition=self.config['task']['task_def'],
            count=self.config['task']['count'],
            launchType=self.config['task']['launch_type'],
            networkConfiguration=self.build_network_configuration(),
            overrides=self.build_overrides(),
            tags=self.build_tags()
        )
        logging.info(f'Task submission response from AWS: {task_response["ResponseMetadata"]["HTTPStatusCode"]}')
        logging.info(f'Task ARN: {task_response["tasks"][0]["taskArn"]}')
        logging.info(f'Task Status: {task_response["tasks"][0]["lastStatus"]}')
