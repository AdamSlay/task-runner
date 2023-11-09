import argparse
import logging
import sys

from TaskRunner import TaskRunner

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)


def parse_args() -> argparse.Namespace:
    """
    Parse the command line arguments
    :return: argparse.Namespace object with the parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Run LongTermStats as an ECS task in Fargate with the provided arguments(start date, end date, warning level)')
    parser.add_argument('--sdate', type=str, default=None, help='The start date for the task in YYYY-MM-DD format')
    parser.add_argument('--edate', type=str, default=None, help='The end date for the task in YYYY-MM-DD format')
    parser.add_argument('--warn', type=str, default='WARN',
                        help='Default=WARN. The warning level to log (DEBUG, INFO, WARN, ERROR, CRITICAL)')
    parser.add_argument('--config', type=str, default='config.json', help='Path to the config file')
    parser.add_argument('--tags', type=str, default=None, help='Tags to apply to the task. Comma separated and no spaces "key1=value1,key2=value2"')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    runner = TaskRunner(args)
    runner.submit_task()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.exception(f'And unexpected error occurred: {e}')
