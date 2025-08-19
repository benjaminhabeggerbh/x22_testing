import os
import glob
import time
import boto3
import json
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
import argparse
from x22_fleet.Library.BaseLogger import BaseLogger


class AwsTransfer():
    def __init__(self,aws_secrets_path = "aws-secrets.json",log_to_file = True,log_to_console=False):
        self.logger = BaseLogger(log_file_path="AwsTransfer.log", log_to_file=log_to_file, log_to_console=log_to_console).get_logger()
        self._load_aws_config(aws_secrets_path)
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id = self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name =self.region

        )

    def _load_aws_config(self,file_path):
        with open(file_path, "r") as file:
            config = json.load(file)
            self.aws_access_key_id = config["aws_access_key_id"]
            self.aws_secret_access_key = config["aws_secret_access_key"]
            self.bucket_name = config["bucket_name"]
            self.region = config["region"]

    def upload_file_to_s3(self, source_filename, target_filename):
        try:
            self.s3_client.upload_file(source_filename, self.bucket_name, target_filename)
            self.logger.info(f"Uploaded to AWS: {source_filename} | {self.bucket_name} | {target_filename}")
            return True
        except Exception as ex:
            self.logger.info(f"Exception in uploading to AWS bucket: {ex}")
            return False

    def process_directory_upload_aws(self, directory_path):
        # Replace colons in the directory path with underscores
        sanitized_path = directory_path.replace(":", "_")
        
        # Ensure the directory exists
        if not os.path.exists(directory_path):
            self.logger.info(f"Directory does not exist: {directory_path}")
            return

        # Loop through all files and directories
        for root, dirs, files in os.walk(directory_path):
            # Skip the "archive" directory
            if "archive" in root:
                continue

            for local_filename in files:
                local_filepath = os.path.join(root, local_filename)

                if ".elf" in local_filename:
                    coredump_filename = local_filepath.replace("transfers", "coredumps")
                    os.rename(local_filepath, f"{coredump_filename}")
                    self.logger.info(f"Moved {local_filepath} to {coredump_filename}")

                if local_filename and not ".tmp" in local_filename and not ".elf" in local_filename and not ".uploaded" in local_filename:
                    if os.path.isfile(local_filepath):
                        # Use only the file name as the target filename
                        sanitized_filename = os.path.basename(local_filepath).replace(":", "_")
                        target_filename = sanitized_filename

                        self.logger.info(f"Local filename: {local_filepath}, Target filename: {target_filename}")

                        if self.upload_file_to_s3(local_filepath, target_filename):
                            # Mark the file as uploaded
                            os.rename(local_filepath, local_filepath + ".uploaded")
                            self.logger.info(f"Marked file as uploaded: {local_filepath}")
                        else:
                            self.logger.error(f"Failed to upload file: {local_filepath}")

    def recycle_old_files(self, directory_path):
        """Delete .uploaded files older than 5 days."""
        now = datetime.now()
        cutoff_time = now - timedelta(days=5)

        for root, dirs, files in os.walk(directory_path):
            for local_filename in files:
                if local_filename.endswith(".uploaded"):
                    local_filepath = os.path.join(root, local_filename)
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(local_filepath))

                    if file_mtime < cutoff_time:
                        try:
                            os.remove(local_filepath)
                            self.logger.info(f"Deleted old file: {local_filepath}")
                        except Exception as ex:
                            self.logger.error(f"Error deleting file {local_filepath}: {ex}")

def main():
    parser = argparse.ArgumentParser(description="X22 Status Listener Service")
    parser.add_argument(
        "--credentials",
        type=str,
        default="credentials.json",
        help="Path to the credentials JSON file"
    )
    parser.add_argument(
        "--aws_secrets",
        type=str,
        default="aws-secrets.json",
        help="Path to the aws-secrets JSON file"
    )
    args = parser.parse_args()
    trans = AwsTransfer(args.aws_secrets,log_to_console=True)

    current_path = os.getcwd()

    topics = ["#"]

    with open(args.credentials, "r") as f:
        credentials = json.load(f)
        basepath = credentials.get("basepath")

    transferpath  = f"{basepath}/ftp/transfers"

    trans.logger.info(f"X22 aws transfer service, the current working directory is: {current_path}, transferpath: {transferpath}")
    
    while(True):
        now = datetime.now()
        formatted_date = now.strftime("%A, %B %d, %Y %H:%M:%S")
        trans.logger.info(f"Transfer service up and running {formatted_date}")
        trans.process_directory_upload_aws(transferpath)
        trans.recycle_old_files(transferpath)
        time.sleep(10)

if __name__ == "__main__":
    main()
