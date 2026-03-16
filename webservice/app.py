#################################################################################################
##                                                                                             ##
##                                 NE PAS TOUCHER CETTE PARTIE                                 ##
##                                                                                             ##
## 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 ##
import boto3
from botocore.config import Config
import os
import uuid
from dotenv import load_dotenv
from typing import Union
import logging
from boto3.dynamodb.conditions import Key
from fastapi import FastAPI, Request, status, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

load_dotenv()
from getSignedUrl import getSignedUrl

app = FastAPI()
logger = logging.getLogger("uvicorn")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://web-alb-823642335.us-east-1.elb.amazonaws.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
	logger.error(f"{request}: {exc_str}")
	content = {'status_code': 10422, 'message': exc_str, 'data': None}
	return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class Post(BaseModel):
    title: str
    body: str

my_config = Config(
    region_name='us-east-1',
    signature_version='v4',
)

dynamodb = boto3.resource('dynamodb', config=my_config)
table = dynamodb.Table(os.getenv("DYNAMO_TABLE"))
s3_client = boto3.client('s3', config=boto3.session.Config(signature_version='s3v4'))
bucket = os.getenv("BUCKET")

## ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ##
##                                                                                                ##
####################################################################################################


@app.post("/posts")
async def post_a_post(post: Post, authorization: str | None = Header(default=None)):
    """
    Poste un post ! Les informations du poste sont dans post.title, post.body et le user dans authorization
    """
    logger.info(f"title : {post.title}")
    logger.info(f"body : {post.body}")
    logger.info(f"user : {authorization}")

    # Préfixes USER# / POST# comme recommandé par le sujet (éviter chevauchements)
    user_key = f"USER#{authorization}"
    post_id = f"POST#{uuid.uuid4()}"
    item = {
        "user": user_key,
        "id": post_id,
        "title": post.title,
        "body": post.body,
    }
    res = table.put_item(Item=item)
    return res

def _post_to_response(item: dict) -> dict:
    """Formate un item DynamoDB en post pour l'API (sujet : user, id, title, body, image, label)."""
    post = {
        "user": item["user"],
        "id": item["id"],
        "title": item["title"],
        "body": item["body"],
        "image": "",
        "label": item.get("label", []),
    }
    if item.get("image"):
        post["image"] = s3_client.generate_presigned_url(
            Params={"Bucket": bucket, "Key": item["image"]},
            ClientMethod="get_object",
            ExpiresIn=3600,
        )
    return post


@app.get("/posts")
async def get_all_posts(user: Union[str, None] = None):
    """
    Récupère tout les postes.
    - Si un user est présent dans le requête, récupère uniquement les siens
    - Si aucun user n'est présent, récupère TOUS les postes de la table !!
    """
    if user:
        logger.info(f"Récupération des postes de : {user}")
        response = table.query(KeyConditionExpression=Key("user").eq(f"USER#{user}"))
    else:
        logger.info("Récupération de tous les postes")
        response = table.scan()
    items = response.get("Items", [])
    return [_post_to_response(it) for it in items]

    
@app.delete("/posts/{post_id}")
async def delete_post(post_id: str, authorization: str | None = Header(default=None)):
    logger.info(f"post id : {post_id}")
    logger.info(f"user: {authorization}")

    user_key = f"USER#{authorization}" if authorization else None
    post_id_key = post_id if post_id.startswith("POST#") else f"POST#{post_id}"

    if not user_key:
        raise HTTPException(status_code=401, detail="authorization header required")

    # Récupération du post pour savoir s'il a une image
    try:
        item = table.get_item(Key={"user": user_key, "id": post_id_key}).get("Item")
    except Exception:
        item = None
    if item and item.get("image"):
        s3_client.delete_object(Bucket=bucket, Key=item["image"])

    res = table.delete_item(Key={"user": user_key, "id": post_id_key})
    return res



# Alias pour conformité au sujet (readme : GET /getSignedUrlPut) ; la webapp appelle /signedUrlPut.
@app.get("/getSignedUrlPut")
async def get_signed_url_put_alias(filename: str, filetype: str, postId: str, authorization: str | None = Header(default=None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Header Authorization requis")
    if not filename or not filetype or not postId:
        raise HTTPException(
            status_code=400,
            detail="Paramètres requis : filename, filetype, postId (tous non vides)",
        )
    bucket = os.getenv("BUCKET")
    if not bucket:
        return JSONResponse(
            status_code=503,
            content={"detail": "Configuration serveur : BUCKET manquant"},
        )
    try:
        return getSignedUrl(filename, filetype, postId, authorization)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

#################################################################################################
##                                                                                             ##
##                                 NE PAS TOUCHER CETTE PARTIE                                 ##
##                                                                                             ##
## 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 ##
@app.get("/signedUrlPut")
async def get_signed_url_put(filename: str, filetype: str, postId: str, authorization: str | None = Header(default=None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Header Authorization requis")
    if not filename or not filetype or not postId:
        raise HTTPException(
            status_code=400,
            detail="Paramètres requis : filename, filetype, postId (tous non vides)",
        )
    bucket = os.getenv("BUCKET")
    if not bucket:
        return JSONResponse(
            status_code=503,
            content={"detail": "Configuration serveur : BUCKET manquant"},
        )
    try:
        return getSignedUrl(filename, filetype, postId, authorization)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="debug")

## ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ##
##                                                                                                ##
####################################################################################################