{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.ruby
  ];

  shellHook = ''
    if [ -f .venv/bin/activate ]; then
      source .venv/bin/activate
    fi
    
  '';
}
