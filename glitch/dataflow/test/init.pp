# motd/manifests/init.pp

# This class manages the /etc/motd file.
# It inherits its configuration from the motd::params class.
class motd inherits motd::params {

  # Ensure the /etc/motd file exists and has the correct content.
  file { '/etc/motd':
    ensure  => file,
    content => $message, # <-- Using the variable from params.pp
    owner   => 'root',
    group   => 'root',
    mode    => '0644',
  }
}
