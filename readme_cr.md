# Compte rendu – TP noté 2 Postagram

Ce fichier contient le compte rendu du travail réalisé pour le devoir noté 2 (Postagram). Le sujet officiel est dans `readme.md` (non modifié). Le plan détaillé étape par étape est dans `readme_cursor.md`.

---

## Démarrage

- **Objectif du TP** : Concevoir la partie backend de Postagram (API REST, EC2/ASG/LB, S3, DynamoDB, Lambda + Rekognition) en suivant le plan défini dans readme_cursor.md.
- **Réalisation** : Création des livrables de l’étape 0 : readme_cursor.md (plan détaillé des étapes 0 à 8), readme_cr.md (ce compte rendu), et mise à jour du .gitignore pour exclure readme_cursor.md des commits.
- **Commandes exécutées** : Aucune (création de fichiers uniquement).
- **Fichiers créés/modifiés** :
  - `readme_cursor.md` : créé, contient le plan complet avec objectifs, fichiers concernés et critères de fin pour chaque étape.
  - `readme_cr.md` : créé, contient ce compte rendu.
  - `.gitignore` : ajout de la ligne `readme_cursor.md`.

---

## Étape 1 – OpenTofu S3 + DynamoDB (terminée)

- **Réalisation** : Bucket S3 et table DynamoDB créés via OpenTofu (s3.tf, dynamodb.tf). Étape validée par l’utilisateur.
- **Commandes** : `cd "open tofu"` puis `tofu init` et `tofu apply` (à exécuter avec AWS configuré).

---

## Étape 2 – Webservice : création et récupération de posts (en local)

- **Réalisation** : Implémentation de POST /posts et GET /posts dans `webservice/app.py`.
- **Modifications dans `app.py`** :
  - **Import** : ajout de `from boto3.dynamodb.conditions import Key` pour les requêtes DynamoDB.
  - **POST /posts** : lecture du username dans le header `authorization`, génération d’un `id` avec `uuid.uuid4()`, préfixes USER# et POST# (sujet), construction de l’item (user, id, title, body), `table.put_item(Item=item)`, retour du résultat.
  - **GET /posts** : si le paramètre de requête `user` est présent → `table.query(KeyConditionExpression=Key("user").eq("USER#" + user))` ; sinon → `table.scan()`. Pour chaque item, formatage avec user, id, title, body, image (URL présignée S3 si le champ image existe), label (liste). Fonction helper `_post_to_response` pour générer l’URL présignée et le format attendu par l’IHM.
- **Environnement virtuel (Python 3.10)** : création du venv et installation des dépendances dans le dossier `webservice` :
  - Commandes exécutées :
    ```bash
    cd /Users/cartelgouabou/Perso/postagram_ensai/webservice
    python3.10 -m venv venv
    venv/bin/pip install -r requirements.txt
    ```
  - Pour activer le venv puis lancer le webservice : `source venv/bin/activate` puis `python3 app.py`. Ou directement : `venv/bin/python app.py`.
- Pour tester en local : s’assurer que le fichier `.env` contient `DYNAMO_TABLE` et `BUCKET` (noms de la table et du bucket créés par `tofu apply`).
- **Tests validés** : POST /posts (header `authorization: estelle`) et GET /posts ont retourné le post créé. Étape 2 terminée.

---

## Étape 3 – Lambda déclenchée par S3 + Rekognition (terminée)

- **lambda.tf** : Lambda postagram-rekognition, permission S3, notification bucket (events s3:ObjectCreated:*). Variable d’env TABLE = nom de la table DynamoDB.
- **Lambda (console puis repo)** : Code récupéré dans `open tofu/lambda/lambda_function.py` : lecture bucket/key depuis l’event S3, extraction user/post_id, appel Rekognition detect_labels, update_item DynamoDB (image + label). Variable d’env TABLE utilisée dans le code.
