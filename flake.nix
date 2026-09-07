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
          path: type:
          let
            relative = pkgs.lib.removePrefix "${toString ./.}/" (toString path);
            base = builtins.baseNameOf path;
          in
          pkgs.lib.cleanSourceFilter path type
          && !(pkgs.lib.hasPrefix "research/samples/" relative)
          && relative != "result"
          && !(pkgs.lib.hasPrefix "result-" relative)
          && relative != "dist"
          && base != "__pycache__"
          && base != ".pytest_cache"
          && relative != "target"
          && !(pkgs.lib.hasPrefix "target/" relative);
      };
      package = pkgs.rustPlatform.buildRustPackage {
        pname = "nvflashk-linux";
        version = (builtins.fromTOML (builtins.readFile ./Cargo.toml)).package.version;
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
      checks.${system} = {
        default = package;
        release-tests =
          pkgs.runCommand "release-tests"
            {
              nativeBuildInputs = [
                pkgs.python3Packages.pytest
                pkgs.git
              ];
            }
            ''
              cp -r ${projectSource}/. source
              chmod -R u+w source
              mkdir -p source/scripts
              cp ${./scripts/validate-release} source/scripts/validate-release
              cd source
              export HOME="$TMPDIR/home"
              mkdir -p "$HOME"
              VALIDATOR=${./scripts/validate-release} pytest -q tests/test_*.py research/test_no_write.py
              touch $out
            '';
      };
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
