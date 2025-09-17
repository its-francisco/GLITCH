# recipes/default.rb
case node['environment']
when 'production'
  file '/var/www/html/index.html' do
    content '<h1>Welcome to Production!</h1>'
    mode '0644'
    owner 'www-data'
    group 'www-data'
  end
when 'development'
  file '/var/www/html/index.html' do
    content '<h1>This is the Development site.</h1>'
    mode '0644'
    owner 'www-data'
    group 'www-data'
  end
else
  file '/var/www/html/index.html' do
    content '<h1>Default Website Content.</h1>'
    mode '0644'
    owner 'www-data'
    group 'www-data'
  end
end
