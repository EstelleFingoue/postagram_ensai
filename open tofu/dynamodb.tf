# Aidez-vous du TP 4

resource "aws_dynamodb_table" "basic-dynamodb-table" {
  name           = "postagram-posts"
  billing_mode   = "PROVISIONED"
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "user"
  range_key      = "id"

  attribute {
    name = "user"
    type = "S"
  }

  attribute {
    name = "id"
    type = "S"
  }
}
# Notes: hash_key = user et range_key = id comme demandé par le sujet (partition = utilisateur, tri = id du post). name = postagram-posts pour identifier la table. Les préfixes USER# / POST# sont utilisés dans le code Python.

# A décommenter quand la table est définie !!
output "dynamotablename" {
  description = "The postagram bucket name"
  value       = aws_dynamodb_table.basic-dynamodb-table.name
}
# Notes: output utilisé par user_data (webservice) et Lambda pour connaître le nom de la table (variables d'environnement DYNAMO_TABLE / TASKS_TABLE).
