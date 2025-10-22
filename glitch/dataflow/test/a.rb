# Chef Recipe with scope shadowing

# Outer scope - NOT hardcoded (safe)
db_pass = node['database']['password']

# Inner scope block
ruby_block 'configure_temp_user' do
  block do
    # Inner scope - HARDCODED secret (dangerous)
    db_pass = "HardcodedSecret999!"
    
    Chef::Log.info("Temp password: #{db_pass}")
  end
end

# Back in outer scope - uses which db_pass?
postgresql_user 'admin' do
  password db_pass
  action :create
end

# Another resource using the same variable
file '/etc/db.conf' do
  content "password=#{db_pass}"
  mode '0600'
end