poetry run glitch repr --tech ansible ../oracles/data/repos/clones/2015-Middleware-Keynote/demo-ansible/playbooks/projects_setup.yml

dependencies: 
    {
      "ir_type": "Dependency",
      "line": 4,
      "column": -33550336,
      "end_line": -33550336,
      "end_column": -33550336,
      "code": "- include: cloudformation_setup.yml\n",
      "names": "cloudformation_setup.yml"
    },
    {
      "ir_type": "Dependency",
      "line": 5,
      "column": -33550336,
      "end_line": -33550336,
      "end_column": -33550336,
      "code": "- include: group_setup.yml\n",
      "names": "group_setup.yml"
    }

need to resolve them first to find variable declarations and add them to the cfg

keep a list of attributes that will include other files (ex.var_files)

vmware/deploy.yml includes vars.yml, and has the secret pw: "{{ new_vm_passwd }}"


python -m glitch lint --tech ansible --dataflow glitch/dataflow/dependencyResolution/vmware/deploy.yml 
python -m glitch cfg --tech ansible --dump --dataflow glitch/dataflow/dependencyResolution/vmware/deploy.yml # outputs the repr, for debugging