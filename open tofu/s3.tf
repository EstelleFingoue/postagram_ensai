# Aidez-vous du TP 4

resource "aws_s3_bucket" "bucket" {
  bucket_prefix = "postagram-"
  force_destroy  = true
}
# Notes: bucket_prefix donne un nom unique au bucket (évite les conflits). force_destroy permet de vider et supprimer le bucket avec tofu destroy (sujet : stocker les images).

# A décommenter seulement quand le bucket est défini
output "bucketname" {
  description = "The postagram bucket name"
  value       = aws_s3_bucket.bucket.bucket
}
# Notes: output utilisé par user_data et Lambda pour connaître le nom du bucket (variables d'environnement).

# A décommenter seulement quand le bucket est défini
resource "aws_s3_bucket_cors_configuration" "cors_bucket" {
  bucket = aws_s3_bucket.bucket.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD", "PUT"]
    allowed_origins = ["*"]
  }
}
# Notes: CORS obligatoire pour que la webapp (navigateur) puisse envoyer des requêtes PUT pour uploader les images vers S3.
