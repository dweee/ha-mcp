{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  outputs = { self, nixpkgs }: let
    pkgs = nixpkgs.legacyPackages.x86_64-linux;
  in {
    packages.x86_64-linux.sync-source = pkgs.stdenvNoCC.mkDerivation {
      name = "ha-mcp-sync-source";
      src = self;
      nativeBuildInputs = [ pkgs.python314 ];
      buildPhase = "python -m compileall -q src custom_components";
      installPhase = "mkdir -p $out/share/ha-mcp && cp -r src custom_components $out/share/ha-mcp/";
    };
  };
}
