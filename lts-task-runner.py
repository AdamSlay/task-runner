import argparse
import boto3
import logging
import toml

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
config = toml.load('config.toml')


def parse_args() -> argparse.Namespace:
    """
    Parse the command line arguments
    :return: argparse.Namespace object with the parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Run LongTermStats as an ECS task in Fargate with the provided arguments(start date, end date, warning level)')
    parser.add_argument('--sdate', type=str, default=None, help='The start date for the task in YYYY-MM-DD format')
    parser.add_argument('--edate', type=str, default=None, help='The end date for the task in YYYY-MM-DD format')
    parser.add_argument('--warn', type=str, default='INFO',
                        help='Default=INFO. The warning level to log (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
    args = parser.parse_args()
    logging.info(f'Parsed command line arguments: {args}')
    return args


def build_command(args: argparse.Namespace) -> list:
    """
    Build the command for the LongTermStats entrypoint from the command line arguments
    :param args: argparse.Namespace object with the parsed command line arguments
    :return: command for the LongTermStats entrypoint as a list
    """
    command = []  # arguments for the LongTermStats entrypoint, so you don't need to include 'LongTermStats'
    if args.sdate is not None:
        command.extend(["--sdate", args.sdate])
    if args.edate is not None:
        command.extend(["--edate", args.edate])
    if args.warn is not None:
        command.extend(["--warn", args.warn])

    logging.info(f'Command for LongTermStats entrypoint: {command}')
    return command


def build_network_configuration(ssm: boto3.client) -> dict:
    """
    Build the network configuration for the ECS task from SSM parameters
    :param ssm: boto3 client for SSM
    :return: network configuration for the ECS task as a dict
    """
    subnet_id = ssm.get_parameter(Name=f'{config["ssm"]["ssm_path"]}/subnet')['Parameter']['Value']
    security_group_id = ssm.get_parameter(Name=f'{config["ssm"]["ssm_path"]}/security_group')['Parameter']['Value']
    assign_public_ip = ssm.get_parameter(Name=f'{config["ssm"]["ssm_path"]}/assign_public_ip')['Parameter']['Value']

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


def build_overrides(ssm: boto3.client, command: list) -> dict:
    """
    Build the overrides for the ECS task from SSM parameters and command line arguments
    :param ssm: boto3 client for SSM
    :param command: command for the LongTermStats entrypoint as a list
    :return: overrides for the ECS task as a dict
    """
    ssm_env_vars = ssm.get_parameters_by_path(Path=f'{config["ssm"]["ssm_path"]}/env', Recursive=True)
    environment = [{'name': parm['Name'].split('/')[-1], 'value': parm['Value']} for parm in ssm_env_vars['Parameters']]

    overrides = {
        'containerOverrides': [
            {
                'name': config['overrides']['container_name'],
                'command': command,
                'environment': environment
            },
        ],
    }
    logging.info(f'Container_name: {config["overrides"]["container_name"]}')
    logging.info(f'Environment: {environment}')
    return overrides


def build_tags() -> list:
    """
    Build the tags for the ECS task
    :return: tags for the ECS task as a list of dicts
    """
    sts = boto3.client('sts')
    arn = sts.get_caller_identity()['Arn']
    username = arn.split('/')[-1]
    tags = [
        {
            'key': 'ManualRun',
            'value': 'True'
        },
        {
            'key': 'User',
            'value': username
        }
    ]
    return tags


def submit_task(ecs: boto3.client, network_configuration: dict, overrides: dict) -> None:
    """
    Submit the ECS task to AWS and return the response
    :param ecs: boto3 client for ECS
    :param network_configuration: Network configuration for the ECS task as a dict
    :param overrides: Overrides for the ECS task as a dict
    :return: Response from AWS as a dict
    """
    task_response = ecs.run_task(
        cluster=config['task']['cluster'],
        taskDefinition=config['task']['task_def'],
        count=config['task']['count'],
        launchType=config['task']['launch_type'],
        networkConfiguration=network_configuration,
        overrides=overrides,
        tags=build_tags()
    )
    logging.info(f'Task submission response from AWS: {task_response["ResponseMetadata"]["HTTPStatusCode"]}')
    logging.info(f'Task ARN: {task_response["tasks"][0]["taskArn"]}')
    logging.info(f'Task Status: {task_response["tasks"][0]["lastStatus"]}')


def main():
    args = parse_args()
    ecs = boto3.client('ecs')
    ssm = boto3.client('ssm')

    command = build_command(args)
    overrides = build_overrides(ssm, command)
    network_configuration = build_network_configuration(ssm)

    submit_task(ecs, network_configuration, overrides)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.exception(f'And unexpected error occurred: {e}')
