a = Aws::SecretsManager.get_secret_value(secret_id: 'my-db-pass').secret_string

user 'osmdata' do
  a = 'hardcoded'
end

user 'osmdata' do
  supports manage_home: true
  comment 'osm data'
  uid '1201'
  gid 'osmdata'
  shell '/bin/bash'
  home '/home/osmdata'
  password a
  system false
  action :create
  not_if "getent passwd osmdata"
end
