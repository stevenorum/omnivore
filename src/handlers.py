import boto3
from boto3.dynamodb.conditions import Attr
from datetime import datetime
import json
import logging
import os
import secrets
import sys
import traceback
import urllib.parse

root = logging.getLogger()
root.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

for noisy in ('botocore', 'boto3', 'requests'):
    logging.getLogger(noisy).level = logging.WARN

try:
    with open("/var/task/static_config.json") as f:
        data = json.load(f)
        for k in data:
            os.environ[k] = data[k].strip()
except:
    logging.exception("Unable to add static info to the path.  Falling back to the bundled defaults.")

def make_response(body, code=200, headers={}, base64=False):
    _headers = {"Content-Type": "text/html"}
    _headers.update(headers)
    return {
        "body": body,
        "statusCode": code,
        "headers": _headers,
        "isBase64Encoded": base64
    }

BUCKET_NAME = os.environ["DATA_BUCKET"]
TABLE_NAME = os.environ["DATA_TABLE"]

S3 = boto3.client("s3")
DDB = boto3.client("dynamodb")

def apigateway_handler(event, context):
    print(json.dumps(event))
    if event["httpMethod"] == "POST" and event.get("body") and event["path"] == "/store":
        data = urllib.parse.parse_qs(event["body"])
        if "data" in data and "source" in data:
            if "content-type" in data:
                store_data(data["data"][0], data["source"][0], data["content-type"][0])
            else:
                store_data(data["data"][0], data["source"][0])
            return make_response(body='{"success":true}', code=200, headers={"Content-Type": "text/json"})
    return make_response(body="Required arguments are missing.", code=400)

def now():
    return datetime.now().strftime("%Y/%m/%d %H:%M:%S%z")

def bytify(data):
    if isinstance(data,str):
        return data.encode("utf-8")
    elif isinstance(data, (list, dict)):
        return bytify(json.dumps(data, separators=(',',':'), sort_keys=True))
    else:
        return data

def store_data(data, source, content_type="application/octet-stream"):
    identifier = secrets.token_urlsafe(64)
    item = {
        "identifier":{"S":identifier},
        "source":{"S":source},
        "received":{"S":now()}
    }
    CE = Attr("identifier").not_exists()
    for i in range(10):
        try:
            response = DDB.put_item(TableName=TABLE_NAME, Item=item, ConditionExpression=CE)
            print(response)
            break
        except:
            traceback.print_exc()
            identifier = secrets.token_urlsafe(64)
            item["identifier"]["S"] = identifier
    response = S3.put_object(Bucket=BUCKET_NAME,
                             Key=identifier,
                             Body=bytify(data),
                             Metadata={"source":source,"received":item["received"]["S"]},
                             ContentType=content_type)
    print(response)
