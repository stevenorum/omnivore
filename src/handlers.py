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

S3 = boto3.resource("s3").Bucket(os.environ["DATA_BUCKET"])
DDB = boto3.resource("dynamodb").Table(os.environ["DATA_TABLE"])

def make_response(body, code=200, headers={}, base64=False):
    _headers = {"Content-Type": "text/html"}
    _headers.update(headers)
    return {
        "body": body,
        "statusCode": code,
        "headers": _headers,
        "isBase64Encoded": base64
    }

def apigateway_handler(event, context):
    print(json.dumps(event))
    if event["httpMethod"] == "POST" and event.get("body") and event["path"] == "/store":
        body = event.get("body")
        if body.startswith("{"):
            try:
                data = json.loads(body)
            except:
                traceback.print_exc()
                raise
        else:
            try:
                data = urllib.parse.parse_qs(body)
                data = {k:data[k][0] for k in data if len(data[k]) > 0}
            except:
                traceback.print_exc()
                raise
        if "data" in data and "source" in data:
            data_record = store_data(data["data"], data["source"], data.get("content-type"))
            return make_response(body=json.dumps(data_record), code=200, headers={"Content-Type": "text/json"})
        else:
            logging.warn("Missing either/both of data and source")
    else:
        logging.warn("Method, body, or path are incorrect.")
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

def store_data(data, source, content_type=None):
    content_type = content_type if content_type else "application/octet-stream"
    identifier = secrets.token_urlsafe(64)
    item = {
        "identifier":identifier,
        "source":source,
        "received":now()
    }
    CE = Attr("identifier").not_exists()
    ATTEMPTS = 10
    for i in range(1, ATTEMPTS+1):
        try:
            response = DDB.put_item(Item=item, ConditionExpression=CE)
            logging.debug(response)
            break
        except:
            traceback.print_exc()
            if i >= ATTEMPTS:
                raise
            identifier = secrets.token_urlsafe(64)
            item["identifier"] = identifier
    response = S3.put_object(Key=identifier,
                             Body=bytify(data),
                             Metadata={"source":source,"received":item["received"]},
                             ContentType=content_type)
    logging.debug(response)
    return item
