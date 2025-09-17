$enable_ssl = true
$protocol = 'http'

if $enable_ssl {
  $protocol = 'https'

} else {
  notify { 'SSL is disabled, using HTTP': }
}
$use_strict_security = true
$protocol = 'X'

notify { "Using protocol: $protocol": }
