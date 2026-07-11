{
  description = "Auditable Linux nvflashk binary patcher";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
      python = pkgs.python3.withPackages (ps: [
        ps.capstone
        ps.pefile
        ps.pyelftools
      ]);
      projectSource = pkgs.lib.cleanSourceWith {
        src = ./.;
        filter =
          path: _type:
          let
            relative = pkgs.lib.removePrefix "${toString ./.}/" (toString path);
          in
          !(pkgs.lib.hasPrefix "research/samples/" relative)
          && relative != "result"
          && relative != "target"
          && !(pkgs.lib.hasPrefix "target/" relative);
      };
      package = pkgs.rustPlatform.buildRustPackage {
        pname = "nvflashk-linux";
        version = "0.1.0";
        src = projectSource;
        cargoLock.lockFile = ./Cargo.lock;
        doCheck = true;
        meta = {
          description = "Guarded patcher for user-supplied NVIDIA NVFlash Linux binaries";
          license = pkgs.lib.licenses.mit;
          platforms = [ system ];
          mainProgram = "nvflashk-linux";
        };
      };
    in
    {
      packages.${system} = {
        default = package;
        nvflashk-linux = package;
      };
      checks.${system}.default = package;
      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          binutils
          cargo
          clippy
          ghidra
          nixfmt
          radare2
          rustc
          rustfmt
          python
          unzip
          file
        ];
      };
      formatter.${system} = pkgs.nixfmt;
    };
}
