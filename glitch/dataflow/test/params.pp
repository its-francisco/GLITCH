# motd/manifests/params.pp

# This class holds the default parameters for the motd module.
class motd::params {
  # The content that will be written to the motd file.
  $message = 'Hello! This server is managed by Puppet. 🤖'
}
