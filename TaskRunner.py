import argparse
import boto3
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)


class TaskRunner:
    """
    Run ECS tasks from the command line with overrides
    """

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.ecs = boto3.client('ecs')
        self.ssm = boto3.client('ssm')

        arn = boto3.client('sts').get_caller_identity()['Arn']
        self.aws_user = arn.split('/')[-1]

        with open(args.config, 'r') as f:
            self.config = json.load(f)

    def _build_command_arguments(self) -> list:
        """
        Build the command for the LongTermStats entrypoint from the command line arguments
        :return: command for the LongTermStats entrypoint as a list
        """
        command_args = []  # just the arguments, not the full command
        if self.args.sdate is not None:
            command_args.extend(["--sdate", self.args.sdate])
        if self.args.edate is not None:
            command_args.extend(["--edate", self.args.edate])
        if self.args.warn is not None:
            command_args.extend(["--warn", self.args.warn])

        logging.info(f'Command for LongTermStats entrypoint: {command_args}')
        return command_args

    def _build_network_configuration(self) -> dict:
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
            f'Network configuration for ECS task: [subnets: {subnet_id}, '
            f'security_groups: {security_group_id}, '
            f'assign_public_ip: {assign_public_ip}]')
        return network_configuration

    def _build_overrides(self) -> dict:
        """
        Build the overrides for the ECS task from SSM parameters and command line arguments
        :return: overrides for the ECS task as a dict
        """
        overrides = {
            'containerOverrides': [
                {
                    'name': self.config['overrides']['container_name'],
                    'command': self._build_command_arguments(),
                },
            ],
        }

        env_vars = self.config["task"]["env_vars"]
        if env_vars:
            environment = [{'name': v, 'value': env_vars[v]} for v in env_vars]
            logging.info(f'Environment variables provided for ECS task: {environment}')
            overrides['containerOverrides'][0]['environment'] = environment

        logging.info(f'Container_name: {self.config["overrides"]["container_name"]}')
        return overrides

    def _build_tags(self) -> list:
        """
        Build the tags for the ECS task
        :return: tags for the ECS task as a list of dicts
        """
        tags = []
        if self.args.tags:
            # convert tags string to list of dicts: [{'key': 'key1', 'value': 'value1'}]
            tags = self.args.tags
        tags.extend(self.config['task']['tags'])
        tags.append({'key': 'AwsUser', 'value': self.aws_user})
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
            networkConfiguration=self._build_network_configuration(),
            overrides=self._build_overrides(),
            tags=self._build_tags()
        )
        logging.info(f'Task submission response from AWS: {task_response["ResponseMetadata"]["HTTPStatusCode"]}')
        logging.info(f'Task ARN: {task_response["tasks"][0]["taskArn"]}')
        logging.info(f'Task Status: {task_response["tasks"][0]["lastStatus"]}')


def parse_args() -> argparse.Namespace:
    """
    Parse the command line arguments
    :return: argparse.Namespace object with the parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Run LTS as an ECS task in Fargate with the provided arguments(start date, end date, warning level)')
    parser.add_argument('--sdate', type=str, default=None, help='The start date for the task in YYYY-MM-DD format')
    parser.add_argument('--edate', type=str, default=None, help='The end date for the task in YYYY-MM-DD format')
    parser.add_argument('--warn', type=str, default='INFO',
                        help='Default=INFO. The warning level to log (DEBUG, INFO, WARN, ERROR, CRITICAL)')
    parser.add_argument('--config', type=str, default='run_config.json', help='Path to the config file')
    parser.add_argument('--tags', type=str, default=None,
                        help='Tags to apply to the task. Comma separated and no spaces "key1=value1,key2=value2"')
    args = parser.parse_args()

    if args.warn not in ['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL']:
        raise ValueError(f'Invalid warning level: {args.warn}')
    else:
        logging.getLogger().setLevel(args.warn)

    if args.tags is not None:
        args.tags = format_tags(str(args.tags))

    if args.warn is not None:
        args.warn = args.warn.upper()

    return args


def format_tags(tags: str) -> list:
    """
    Parse the tags argument into a list of dicts
    :param tags: tags argument from the command line
    :return: list of dicts with the tags formatted as required by the boto3 API
    """
    tags = tags.replace(' ', '')  # remove white spaces
    tags = tags.split(',')  # ['key1=value1', 'key2=value2']
    tags = [tag.split('=') for tag in tags]  # [['key1', 'value1'], ['key2', 'value2']]
    tags = [{'key': tag[0], 'value': tag[1]} for tag in
            tags]  # [{'key': 'key1', 'value': 'value1'}, {'key': 'key2', 'value': 'value2'}]
    return tags


def main():
    args = parse_args()
    runner = TaskRunner(args)
    runner.submit_task()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.exception(f'And unexpected error occurred: {e}')
