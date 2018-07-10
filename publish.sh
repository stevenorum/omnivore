#!/bin/bash

source private_vars.sh

rm -rf build/
mkdir -p build
#bash upload_static_assets.sh build/static_config.json
cp -r src/* build/
#cp -r static build/
#cp -r jinja_templates build/
cp SamTemplate.json build/
touch requirements.txt
pip3 install -t build/ -r requirements.txt
cp SamTemplate.json ProcessedSamTemplate.json
#python3 generate_lambda_template.py SamTemplate.json ProcessedSamTemplate.json
#python3 process_static_functions.py ProcessedSamTemplate.json ProcessedSamTemplate.json

aws --region $AWS_REGION --profile $AWS_PROFILE \
    cloudformation package \
    --template-file ProcessedSamTemplate.json \
    --s3-bucket $S3_BUCKET \
    --output-template-file NewSamTemplate.json \
    --use-json && \
aws --region $AWS_REGION --profile $AWS_PROFILE \
    cloudformation deploy \
    --template-file NewSamTemplate.json \
    --capabilities CAPABILITY_IAM \
    --stack-name $STACK_NAME && \
rm NewSamTemplate.json
