require 'aws-sdk-secretsmanager'

client = Aws::SecretsManager::Client.new(region: 'us-east-1')
secret = client.get_secret_value(secret_id: 'my-app-db-password')
db_password = secret.secret_string