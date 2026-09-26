'''pipeline/aws/delete_all_from_bucket.py'''
import os
import boto3
from dotenv import load_dotenv

load_dotenv()  # reads .env in the current working directory (or pass a path)

s3 = boto3.client(
    's3',
    aws_access_key_id=os.environ['AWS_ACCESS_ID'],
    aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
    region_name='ap-southeast-7',
    endpoint_url='https://s3.ap-southeast-7.amazonaws.com',
)

bucket = 'cow-bucket-613211402323-ap-southeast-7-an'
prefix = 'gdrive-backup/'

paginator = s3.get_paginator('list_object_versions')
total_deleted = 0

for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
    to_delete = []
    to_delete += [{'Key': v['Key'], 'VersionId': v['VersionId']} for v in page.get('Versions', [])]
    to_delete += [{'Key': m['Key'], 'VersionId': m['VersionId']} for m in page.get('DeleteMarkers', [])]

    if not to_delete:
        continue

    resp = s3.delete_objects(Bucket=bucket, Delete={'Objects': to_delete, 'Quiet': True})
    total_deleted += len(to_delete)
    if resp.get('Errors'):
        print(f"Errors: {resp['Errors']}")

print(f"Deleted {total_deleted} object versions/markers under '{prefix}'")