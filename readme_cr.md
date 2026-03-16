# Compte rendu – TP noté 2 Postagram

**Membres du groupe :**

- Estelle Danielle FINGOUE
- Rosine SORO

Ce document décrit le travail réalisé pour le devoir noté 2 (Postagram). Le sujet officiel est dans `readme.md`.

## Architecture cible

L’architecture ci-dessous rappelle le flux de l’application : l’utilisateur utilise l’application React dans le navigateur ; les requêtes API (GET/POST/DELETE /posts, GET signedUrlPut) passent par le Load Balancer vers les instances EC2 qui exécutent le webservice FastAPI. Le backend génère des URL présignées S3 pour que le client uploade les images directement dans le bucket S3. À chaque dépôt d’image dans S3, une Lambda est déclenchée, appelle Amazon Rekognition pour détecter les labels, puis met à jour la table DynamoDB. Le webservice lit et écrit les posts dans DynamoDB et renvoie les URLs présignées et les labels à l’IHM.

![Architecture cible TP noté](img/architecture%20cible%20TP%20noté.png)

**Comment utiliser ce compte rendu :** les sections suivent l’ordre chronologique des étapes du TP. Pour chaque étape sont listés les fichiers modifiés ; pour chaque fichier sont indiqués les blocs ou lignes modifiés, les valeurs mises et la raison du choix. En suivant cet ordre, on peut reproduire le TP de zéro et comprendre chaque modification.

---

## Étape 0 – Livrables et configuration du projet

**Objectif :** avoir un compte rendu et un `.gitignore` adapté au projet.

**Fichiers créés/modifiés :**

| Fichier        | Lignes / bloc | Valeurs                                                                                                                                 | Raison                                                                                          |
| -------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `readme_cr.md` | (création)    | Ce compte rendu                                                                                                                         | Livrable demandé par le sujet.                                                                  |
| `.gitignore`   | (ajouts)      | `readme_cursor.md`, `open tofu/.terraform`, `open tofu/output/`, `open tofu/*.tfstate`, `open tofu/*.tfstate.backup`, `webservice/.env`, `webservice/venv/`, `webservice/__pycache__/`, `.DS_Store` | Ne pas versionner fichiers temporaires, états OpenTofu, secrets, environnements virtuels et caches. |

**Commandes exécutées :** aucune (création et édition de fichiers uniquement).

**Critères de fin :** existence de `readme_cr.md`, `.gitignore` à jour.

---

## Étape 1 – OpenTofu : S3 et DynamoDB

**Objectif :** créer le bucket S3 et la table DynamoDB pour le stockage des images et des posts (sujet).

**Prérequis :** AWS configuré (credentials), OpenTofu installé.

**Fichiers modifiés :** `open tofu/s3.tf`, `open tofu/dynamodb.tf`.

### open tofu/s3.tf

| Bloc / lignes                                                | Modification   | Valeurs                                                                                          | Raison                                                                                                                                                          |
| ------------------------------------------------------------ | -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `resource "aws_s3_bucket" "bucket"`                          | Ajout (l.3–6)  | `bucket_prefix = "postagram-"`, `force_destroy = true`                                           | **bucket_prefix** : génère un nom unique (ex. postagram-xxx) et évite les conflits de noms globaux S3. **force_destroy** : permet de vider et supprimer le bucket avec `tofu destroy` (utile en TP / dev). |
| `output "bucketname"`                                         | Ajout (l.10–13) | `value = aws_s3_bucket.bucket.bucket`                                                            | Expose le nom du bucket pour user_data (webservice) et Lambda (variables d’environnement).                                                                      |
| `resource "aws_s3_bucket_cors_configuration" "cors_bucket"`    | Ajout (l.17–25) | `allowed_headers = ["*"]`, `allowed_methods = ["GET", "HEAD", "PUT"]`, `allowed_origins = ["*"]` | CORS obligatoire pour que la webapp (navigateur) envoie des requêtes PUT vers S3 (upload direct depuis le front).                                                |

### open tofu/dynamodb.tf

| Bloc / lignes                                          | Modification   | Valeurs                                                                                                                                                                           | Raison                                                                                             |
| ------------------------------------------------------ | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `resource "aws_dynamodb_table" "basic-dynamodb-table"` | Ajout (l.3–20) | `name = "postagram-posts"`, `hash_key = "user"`, `range_key = "id"`, `billing_mode = "PROVISIONED"`, `read_capacity = 5`, `write_capacity = 5`, attributs `user` et `id` (type S) | Sujet : partition par utilisateur (user), tri par id du post. Préfixes USER# / POST# utilisés dans le code Python. |
| `output "dynamotablename"`                             | Ajout (l.24–27) | `value = aws_dynamodb_table.basic-dynamodb-table.name`                                                                                                                            | Nom de la table pour .env (webservice) et Lambda (variable TABLE).                                |

**Commandes exécutées :** `cd "open tofu"`, `tofu init`, `tofu apply`.

**Critères de fin :** `tofu apply` réussi ; outputs `bucketname` et `dynamotablename` affichés. Noter ces noms pour l’étape 2 (fichier `.env`).

---

## Étape 2 – Webservice : création et récupération de posts (local)

**Objectif :** implémenter POST /posts et GET /posts en local (sujet).

**Prérequis :** Étape 1 faite, noms du bucket et de la table connus.

**Fichiers modifiés :** `webservice/app.py`, création de `webservice/.env`.

### webservice/app.py

| Lignes / bloc        | Modification                                      | Valeurs / code                                                                                                                                                                 | Raison                                                                                                                      |
| -------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| Import               | Ajout                                             | `from boto3.dynamodb.conditions import Key`                                                                                                                                    | Requêtes DynamoDB (query avec KeyConditionExpression).                                                                      |
| Ordre chargement env | `load_dotenv()` avant `from getSignedUrl import getSignedUrl` | —                                                                                                                                                                              | getSignedUrl utilise `os.getenv("BUCKET")` à l’import ; sans load_dotenv avant, BUCKET est None → erreur sur presigned URL. |
| POST /posts          | Bloc route (l.68–88)                              | user_key = USER# + authorization, post_id = POST# + uuid4(), item (user, id, title, body), `table.put_item(Item=item)`                                                          | Sujet : format user/id avec préfixes ; retour attendu par l’IHM.                                                            |
| GET /posts           | Bloc route (l.109–124)                            | Paramètre optionnel `user` ; si présent `table.query(Key("user").eq("USER#" + user))`, sinon `table.scan()` ; formatage avec _post_to_response (URL présignée si image, label)   | Sujet : filtre par user ou liste globale ; format réponse avec image et label pour l’IHM.                                   |
| Helper               | `_post_to_response` (l.90–106)                     | Génère URL présignée S3 et format (user, id, title, body, image, label)                                                                                                        | Éviter duplication et garder format IHM cohérent.                                                                            |

### webservice/.env (création)

| Ligne     | Valeurs                                                 | Raison                                                      |
| --------- | ------------------------------------------------------- | ----------------------------------------------------------- |
| (fichier) | `DYNAMO_TABLE=<dynamotablename>`, `BUCKET=<bucketname>` | Valeurs issues des outputs de l’étape 1 ; ne pas committer. |

**Environnement :** création du venv dans `webservice` (`python3 -m venv venv` ou `python3.10 -m venv venv`), puis `pip install -r requirements.txt`. Lancer le webservice avec `venv/bin/python app.py` (ou `source venv/bin/activate` puis `python app.py`).

**Critères de fin :** POST /posts et GET /posts fonctionnent en local ; `.env` présent avec DYNAMO_TABLE et BUCKET.

---

## Étape 3 – Lambda déclenchée par S3 + Rekognition

**Objectif :** à chaque dépôt d’objet dans le bucket, déclencher une Lambda qui appelle Rekognition et met à jour DynamoDB (sujet).

**Fichiers modifiés :** `open tofu/lambda.tf`, `open tofu/lambda/lambda_function.py`.

### open tofu/lambda.tf

| Bloc / lignes                                                 | Modification | Valeurs                                                                                                                                                             | Raison                                                                    |
| ------------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `data "archive_file" "lambda_dir"`                            | l.5–9        | source_dir = lambda, output_path = output/function.zip                                                                                                              | Empaqueter le code Python pour la Lambda.                                 |
| `resource "aws_lambda_function" "lambda_function"`            | l.12–35      | function_name = "postagram-rekognition", role = LabRole, handler = "lambda_function.lambda_handler", runtime = "python3.13", environment TABLE = nom table DynamoDB | Déclencher sur S3 ; variable TABLE pour que la Lambda connaisse la table.  |
| `resource "aws_lambda_permission" "allow_from_S3"`            | l.39–46      | action Lambda Invoke, principal s3.amazonaws.com, source_arn = bucket                                                                                               | Autoriser S3 à appeler la Lambda.                                          |
| `resource "aws_s3_bucket_notification" "bucket_notification"` | l.50–57      | events = ["s3:ObjectCreated:*"], lambda_function_arn                                                                                                                | Déclencher la Lambda à chaque dépôt d’objet dans le bucket.                |

### open tofu/lambda/lambda_function.py

| Lignes / bloc | Modification | Valeurs                                                        | Raison                                                           |
| ------------- | ------------ | -------------------------------------------------------------- | ---------------------------------------------------------------- |
| Lecture event | l.17–18      | bucket/key depuis event["Records"][0]["s3"], unquote_plus(key) | Format event S3 ; unquote_plus pour les clés avec espaces.        |
| Clés DynamoDB | l.20–24      | user_key, post_id_key avec préfixes USER# / POST# si besoin    | Aligner avec les clés stockées par le webservice.                |
| Rekognition   | l.25–36      | detect_labels, MaxLabels=5, MinConfidence=0.75                 | Sujet : détection de labels sur l’image.                         |
| DynamoDB      | l.38–50      | update_item SET image = :img, label = :labels                  | Stocker le chemin S3 et la liste des labels dans l’item du post. |

**Commandes exécutées :** `tofu apply` depuis `open tofu`. Test : déposer un fichier dans le bucket (console AWS ou CLI) et vérifier que les labels apparaissent dans l’item DynamoDB.

**Critères de fin :** Lambda invoquée à chaque upload ; labels écrits en DynamoDB.

---

## Étape 4 – Webservice : DELETE /posts/{post_id}

**Objectif :** implémenter DELETE /posts/{post_id} avec suppression en DynamoDB et suppression de l’image dans S3 si présente (sujet).

**Fichiers modifiés :** `webservice/app.py`.

| Lignes / bloc           | Modification   | Valeurs                                                                                                                                                                      | Raison                                                                     |
| ----------------------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| DELETE /posts/{post_id}  | Route (l.127–147) | authorization → user_key (USER#), normalisation post_id (POST# si absent), get_item pour récupérer le post ; si champ image alors s3_client.delete_object ; puis table.delete_item ; si pas authorization → 401 | Sujet : suppression du post en DynamoDB et de l’image dans S3 si présente. |

**Critères de fin :** suppression du post en base et de l’objet S3 si une image était associée ; 401 si header authorization absent.

---

## Étape 5 – OpenTofu : EC2, ASG, Load Balancer

**Objectif :** déployer le webservice sur une flotte EC2 (1 à 4 instances) derrière un ALB (sujet).

**Fichiers modifiés :** `open tofu/config_base.tf`, `open tofu/infra ec2.tf`, `open tofu/user_data.sh`.

### open tofu/config_base.tf

| Lignes | Modification | Valeurs                                             | Raison                                                                                |
| ------ | ------------ | --------------------------------------------------- | ------------------------------------------------------------------------------------- |
| 52–58  | Bloc ingress | from_port 8080, to_port 8080, cidr_blocks 0.0.0.0/0 | Webservice et health-check ALB sur port 8080 ; sans cela le Target Group reste unhealthy (502). |

### open tofu/infra ec2.tf

| Bloc / lignes                                 | Modification | Valeurs                                                                                                           | Raison                                                              |
| --------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| variable git_repo / iam_instance_profile_name | l.4–13       | git_repo = URL du dépôt, iam_instance_profile_name = "LabInstanceProfile"                                         | Adapter le repo ; LabInstanceProfile pour AWS Academy.               |
| aws_launch_template                           | l.19–54      | AMI ami-0ecb62995f68bb549, t3.micro, key_name vockey, user_data avec templatefile(bucket, dynamo_table, git_repo) | Sujet : instances avec user_data pour clone, .env et lancement app.   |
| aws_autoscaling_group                         | l.59–78      | desired 1, min 1, max 4, health_check_type ELB, target_group_arns                                                 | Sujet : 1 à 4 instances ; health-check via ALB sur 8080.           |
| aws_lb, aws_lb_target_group                   | l.83–117     | ALB application, TG port 8080, health_check path = "/posts"                                                       | Webservice sur 8080 ; /posts évite 404 (pas de GET /).               |
| aws_lb_listener                               | l.122–132    | port 80, forward vers TG                                                                                          | Accès HTTP standard.                                                |
| output load_balancer_dns_name                 | l.137–141    | value = aws_lb.web_alb.dns_name                                                                                   | URL pour tests et baseURL webapp.                                   |

### open tofu/user_data.sh

| Lignes | Modification | Valeurs                                                                                                 | Raison                                                                                      |
| ------ | ------------ | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| 6–14   | Script       | clone ${git_repo}, cd webservice, .env avec BUCKET et DYNAMO_TABLE, pip install, venv/bin/python app.py | Bootstrap des instances : même code et config que le sujet ; guillemets corrects pour .env. |

**Commandes exécutées :** `tofu apply` depuis `open tofu` ; récupérer l’URL du Load Balancer (output `load_balancer_dns_name`).

**Critères de fin :** Instances en état healthy derrière l’ALB ; `curl http://<ALB_DNS>/posts` retourne du JSON.

---

## Étape 6 – groupe.md et URL webapp

**Objectif :** renseigner les membres du groupe et configurer la webapp pour les tests sur AWS (sujet).

**Fichiers modifiés :** `groupe.md`, `webapp/src/index.js`.

| Fichier             | Lignes     | Valeurs                                                   | Raison                                                          |
| ------------------- | ---------- | --------------------------------------------------------- | --------------------------------------------------------------- |
| groupe.md           | (création) | Liste des membres (Estelle Danielle FINGOUE, Rosine SORO) | Sujet : identification du groupe.                               |
| webapp/src/index.js | 12         | axios.defaults.baseURL = "http://<ALB_DNS>" (sans slash final) | Pointer la webapp vers le Load Balancer pour les tests sur AWS. |

**Commandes exécutées :** aucune (édition des fichiers). Pour tester : `npm install` puis `npm start` dans `webapp`, et utiliser l’URL du Load Balancer.

**Critères de fin :** groupe.md présent ; baseURL pointant vers l’ALB.

---

## Étape 7/8 – Vérification et rendu

**Objectif :** vérifier tous les endpoints, upload d’images, affichage et labels ; finaliser le CR et préparer l’archive pour le rendu.

**Résumé des tests :** POST /posts, GET /posts (avec et sans filtre user), DELETE /posts/{post_id}, GET signedUrlPut puis upload S3, affichage des images et des labels Rekognition dans l’IHM.

**Rappel rendu :** archive (ex. .zip) avec le code OpenTofu et le webservice, selon les consignes du sujet. Aucune modification de code supplémentaire à décrire ici si tout est déjà couvert dans les étapes précédentes.

---

## Correctifs et améliorations (post-TP)

Modifications effectuées après les étapes principales pour faire fonctionner ou stabiliser l’application. Même format : fichier → lignes/bloc modifiés → valeurs → raison.

### webservice/app.py

| Lignes / bloc | Modification | Valeurs | Raison |
| -------------- | ------------- | ------- | ------ |
| Ordre chargement | load_dotenv() puis import getSignedUrl | — | Déjà documenté en Étape 2 : BUCKET doit être chargé avant l’import de getSignedUrl. |
| Routes signedUrlPut (GET /getSignedUrlPut, GET /signedUrlPut) | Validation et gestion d’erreurs | Vérification authorization (sinon 401), filename/filetype/postId non vides (sinon 400), BUCKET défini (sinon 503) ; try/except autour de getSignedUrl avec retour 500 et détail | Éviter erreurs "expected string or bytes-like object, got NoneType" et renvoyer des réponses HTTP claires. |

### webapp – Post.js

| Lignes / bloc | Modification | Valeurs | Raison |
| -------------- | ------------- | ------- | ------ |
| Appel getSignedUrlPut | Passage de filetype | filetype passé en paramètre et utilisé pour le Content-Type du PUT S3 | Signature S3 et Content-Type doivent correspondre. |
| PUT S3 | URL en chaîne | putUrl = uploadUrl.href (string) pour instance.put(putUrl, ...) | Éviter problèmes cross-origin avec l’objet URL dans axios. |
| Vérification | uploadURL | Si response.data?.uploadURL absent, lever une erreur explicite | Éviter crash cryptique si la réponse backend est incomplète. |
| Gestion d’erreurs | try/catch | try/catch séparé pour le PUT S3 avec message explicite (backend OK / échec S3) | Distinguer erreur backend et erreur upload S3. |
| Nettoyage | Ponctuation | Correction de `});;` en `});` | Erreur de syntaxe. |

### webapp – PostList.js

| Lignes / bloc | Modification | Valeurs | Raison |
| -------------- | ------------- | ------- | ------ |
| key React | key={post.id} | Au lieu de key={posts.id} | Clé unique par élément pour React (éviter warning et bugs de rendu). |

### open tofu/s3.tf

| Bloc | Modification | Valeurs | Raison |
| ---- | ------------- | ------- | ------ |
| aws_s3_bucket_cors_configuration | Déjà documenté en Étape 1 | allowed_origins = ["*"], allowed_methods incluant PUT | CORS nécessaire pour l’upload direct depuis le navigateur vers S3. |

### Nettoyage des logs

| Fichier | Modification | Valeurs | Raison |
| ------- | ------------- | ------- | ------ |
| Post.js, SubmitPost.js, HomePage.js | Suppression | Tous les console.log retirés | Repo propre pour le rendu. |
| webservice/app.py | Suppression | logger.error / logger.exception superflus dans les routes signedUrlPut (si ajoutés en debug) | Idem. |

---

## Annexes (optionnel)

- **Récapitulatif des commandes :** `tofu init`, `tofu apply` (dans `open tofu`) ; lancement webservice : `venv/bin/python app.py` dans `webservice` ; lancement webapp : `npm install` puis `npm start` dans `webapp`. Exemples curl : POST /posts avec header authorization, GET /posts, GET /posts?user=..., DELETE /posts/{post_id}.
- **Contenu type du .env :** DYNAMO_TABLE=postagram-posts, BUCKET=postagram-xxxx (sans committer le fichier).
- **Format de réponse GET /posts :** liste d’objets avec user, id, title, body, image (URL présignée ou ""), label (liste), pour alignement avec l’IHM.
