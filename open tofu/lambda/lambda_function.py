import json
from urllib.parse import unquote_plus
import boto3
import os
import logging
print('Loading function')
logger = logging.getLogger()
logger.setLevel("INFO")
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
rekognition = boto3.client('rekognition')

table = dynamodb.Table(os.getenv("TABLE"))

def lambda_handler(event, context):
    logger.info(json.dumps(event, indent=2))
    # Récupération du bucket et de la clé depuis l'event S3
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = unquote_plus(event["Records"][0]["s3"]["object"]["key"])
    # Récupération de l'utilisateur et de l'id du post (format: user/id_publication/image_name)
    user_part, post_id_part = key.split('/')[:2]
    # Préfixes USER# / POST# pour correspondre aux clés DynamoDB stockées par le webservice
    user_key = user_part if user_part.startswith("USER#") else f"USER#{user_part}"
    post_id_key = post_id_part if post_id_part.startswith("POST#") else f"POST#{post_id_part}"
    # Appel à Rekognition
    label_data = rekognition.detect_labels(
        Image={
            "S3Object": {
                "Bucket": bucket,
                "Name": key
            }
        },
        MaxLabels=5,
        MinConfidence=0.75
    )
    logger.info(f"Labels data : {label_data}")
    # Récupération des noms des labels
    labels = [label["Name"] for label in label_data["Labels"]]
    # Mise à jour de la table DynamoDB (image = chemin S3, label = liste des labels)
    table.update_item(
        Key={
            "user": user_key,
            "id": post_id_key
        },
        UpdateExpression="SET image = :img, #lbl = :labels",
        ExpressionAttributeNames={"#lbl": "label"},
        ExpressionAttributeValues={
            ":img": key,
            ":labels": labels
        }
    )
    return {"statusCode": 200, "body": json.dumps({"labels": labels})}