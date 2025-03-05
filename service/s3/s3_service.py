import boto3
from botocore.exceptions import ClientError
from service.logger.logger import get_logger
logger = get_logger("s3_service")
import json


def get_file_from_s3(path: str, file: str):
    """
    Retrieve a file from S3 bucket, supporting JSON and HTML files.
    
    Args:
        path (str): S3 bucket name
        file (str): File key/name in the bucket
    """
    s3_client = boto3.client('s3')
    
    try:
        response = s3_client.get_object(Bucket=path, Key=file)
        content = response['Body'].read().decode('utf-8')
        return content
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            logger.info(f"File {file} not found in bucket {path}")
        elif error_code == 'NoSuchBucket':
            logger.info(f"Bucket {path} does not exist")
        else:
            logger.info(f"Error accessing S3: {str(e)}")
        raise e
    
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise e
    
    
def upload_to_s3(s3_bucket, s3_path, file_name, data):
    try:
        logger.info(f"Uploading to S3 {s3_bucket}/{s3_path}/{file_name}")
        s3_client = boto3.client('s3')
        body=json.dumps(data, default=str,ensure_ascii=False)
        object_name =  s3_path + "/" + file_name
        s3_client.put_object(Body=body, Bucket=s3_bucket, Key=object_name)
        logger.info(f"Uploaded to S3 {s3_bucket}/{s3_path}/{file_name}")
        return object_name
    except Exception as e:
        logger.error(f"Error while uploading to S3: {str(e)}")
        raise e