use sha2::{Digest, Sha256};
use std::env;
use std::ffi::OsString;
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::os::unix::fs::{MetadataExt, PermissionsExt};
use std::path::{Path, PathBuf};

const INPUT_SHA256: &str = "bc36918546a749650a1a28cfd990a506a531b77529b57a7f119ad214563bc7e7";
const OUTPUT_SHA256: &str = "082f84b1c80b14c2c0eccb3c41c4bec7f8f5886fa03e533abb87d64ce0f36cfa";

#[derive(Clone, Copy)]
struct Patch {
    offset: usize,
    original: &'static [u8],
    patched: &'static [u8],
}

const PATCHES: [Patch; 2] = [
    // The early Board ID gate must accept the explicitly supplied overridesub
    // option too. Its Board ID label and separate YES confirmation stay intact.
    Patch {
        offset: 0x1a_abc6,
        original: &[0xbe, 0x7d, 0xd5, 0x99, 0x00],
        patched: &[0xbe, 0x13, 0x80, 0x95, 0x00],
    },
    Patch {
        offset: 0x1a_5af3,
        original: &[0x0f, 0x84, 0x12, 0x01, 0x00, 0x00],
        patched: &[0x90; 6],
    },
];

const VERSION: &str = env!("CARGO_PKG_VERSION");

fn usage() {
    println!(
        "nvflashk-linux {VERSION} — guarded NVFlash patcher\n\n\
         Usage: nvflashk-linux <input> <output>\n\n\
         Supported input:\n\
           Linux x86-64 NVFlash 5.792.0\n\
           SHA-256: {INPUT_SHA256}\n\n\
         This creates a new experimental binary. It does not invoke NVFlash or access hardware.\n\
         Validation: one RTX 4090 original-VBIOS restoration; other cards/firmware and sustained stability unverified.\n\
         Bypassing a mismatch does not establish firmware compatibility; flashing can leave hardware unusable.\n\
         The output path must not already exist."
    );
}

fn sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn apply_patches(bytes: &mut [u8]) -> Result<(), String> {
    for patch in PATCHES {
        let target = bytes
            .get(patch.offset..patch.offset + patch.original.len())
            .ok_or_else(|| {
                format!(
                    "input is too short for verified patch offset 0x{:x}",
                    patch.offset
                )
            })?;
        if target != patch.original {
            return Err(format!(
                "patch precondition failed at 0x{:x}: expected {}, found {}",
                patch.offset,
                hex(patch.original),
                hex(target)
            ));
        }
    }

    for patch in PATCHES {
        bytes[patch.offset..patch.offset + patch.patched.len()].copy_from_slice(patch.patched);
    }
    Ok(())
}

fn hex(bytes: &[u8]) -> String {
    bytes
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<Vec<_>>()
        .join(" ")
}

fn read_input(path: &Path) -> Result<(Vec<u8>, u32), String> {
    let mut file =
        File::open(path).map_err(|error| format!("cannot open {}: {error}", path.display()))?;
    let metadata = file
        .metadata()
        .map_err(|error| format!("cannot inspect {}: {error}", path.display()))?;
    if !metadata.is_file() {
        return Err(format!("input is not a regular file: {}", path.display()));
    }

    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)
        .map_err(|error| format!("cannot read {}: {error}", path.display()))?;
    Ok((bytes, metadata.permissions().mode()))
}

fn temp_path(output: &Path) -> Result<PathBuf, String> {
    let name = output
        .file_name()
        .ok_or_else(|| format!("output has no file name: {}", output.display()))?;
    let mut temp_name = OsString::from(".");
    temp_name.push(name);
    temp_name.push(format!(".tmp.{}", std::process::id()));
    Ok(output.with_file_name(temp_name))
}

fn write_new_atomic(output: &Path, bytes: &[u8], mode: u32) -> Result<(), String> {
    if output.exists() {
        return Err(format!(
            "refusing to replace existing output: {}",
            output.display()
        ));
    }

    let temp = temp_path(output)?;
    let mut created = false;
    let result = (|| {
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temp)
            .map_err(|error| {
                format!("cannot create temporary output {}: {error}", temp.display())
            })?;
        created = true;
        file.set_permissions(fs::Permissions::from_mode(mode & !0o7022))
            .map_err(|error| format!("cannot set output permissions: {error}"))?;
        file.write_all(bytes)
            .map_err(|error| format!("cannot write temporary output: {error}"))?;
        file.sync_all()
            .map_err(|error| format!("cannot sync temporary output: {error}"))?;

        // A hard link publishes the completed inode atomically and fails if output exists.
        fs::hard_link(&temp, output)
            .map_err(|error| format!("cannot publish {}: {error}", output.display()))?;
        Ok(())
    })();
    if created {
        let _ = fs::remove_file(&temp);
    }
    result
}

fn same_file(input: &Path, output: &Path) -> Result<bool, String> {
    let input_metadata = fs::metadata(input)
        .map_err(|error| format!("cannot inspect {}: {error}", input.display()))?;
    match fs::metadata(output) {
        Ok(output_metadata) => Ok(input_metadata.dev() == output_metadata.dev()
            && input_metadata.ino() == output_metadata.ino()),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(error) => Err(format!("cannot inspect {}: {error}", output.display())),
    }
}

fn run(input: &Path, output: &Path) -> Result<(), String> {
    if input == output || same_file(input, output)? {
        return Err("input and output paths must differ".to_owned());
    }

    let (mut bytes, mode) = read_input(input)?;
    let actual_input = sha256(&bytes);
    if actual_input != INPUT_SHA256 {
        return Err(format!(
            "unsupported input SHA-256: {actual_input}\nexpected: {INPUT_SHA256}"
        ));
    }

    apply_patches(&mut bytes)?;
    let actual_output = sha256(&bytes);
    if actual_output != OUTPUT_SHA256 {
        return Err(format!(
            "internal verification failed: output SHA-256 {actual_output}"
        ));
    }
    write_new_atomic(output, &bytes, mode)?;

    println!("created: {}", output.display());
    println!("SHA-256: {actual_output}");
    Ok(())
}

fn main() {
    let args: Vec<_> = env::args_os().collect();
    if args.len() == 1
        || args
            .get(1)
            .is_some_and(|arg| arg == "-h" || arg == "--help")
    {
        usage();
        return;
    }
    if args
        .get(1)
        .is_some_and(|arg| arg == "--version" || arg == "-V")
    {
        if args.len() == 2 {
            println!("nvflashk-linux {VERSION}");
            return;
        }
        eprintln!("error: unexpected arguments after --version\n");
        usage();
        std::process::exit(2);
    }
    if args.len() != 3 {
        eprintln!("error: expected <input> <output>\n");
        usage();
        std::process::exit(2);
    }

    if let Err(error) = run(Path::new(&args[1]), Path::new(&args[2])) {
        eprintln!("error: {error}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn patch_applies_two_edits_and_changes_exactly_nine_bytes() {
        let len = PATCHES
            .iter()
            .map(|patch| patch.offset + patch.original.len())
            .max()
            .unwrap();
        let mut bytes = vec![0_u8; len];
        for patch in PATCHES {
            bytes[patch.offset..patch.offset + patch.original.len()]
                .copy_from_slice(patch.original);
        }
        let original = bytes.clone();

        apply_patches(&mut bytes).unwrap();

        for patch in PATCHES {
            assert_eq!(
                &bytes[patch.offset..patch.offset + patch.patched.len()],
                patch.patched
            );
        }
        assert_eq!(
            original
                .iter()
                .zip(&bytes)
                .filter(|(before, after)| before != after)
                .count(),
            9
        );
    }

    #[test]
    fn patch_rejects_either_unexpected_instruction_without_mutation() {
        for broken in 0..PATCHES.len() {
            let len = PATCHES
                .iter()
                .map(|patch| patch.offset + patch.original.len())
                .max()
                .unwrap();
            let mut bytes = vec![0_u8; len];
            for patch in PATCHES {
                bytes[patch.offset..patch.offset + patch.original.len()]
                    .copy_from_slice(patch.original);
            }
            bytes[PATCHES[broken].offset] ^= 0xff;
            let original = bytes.clone();

            assert!(apply_patches(&mut bytes).is_err());
            assert_eq!(bytes, original);
        }
    }

    #[test]
    fn run_rejects_unknown_hash_without_output() {
        let base = env::temp_dir().join(format!("nvflashk-linux-test-{}-hash", std::process::id()));
        let input = base.with_extension("input");
        let output = base.with_extension("output");
        let _ = fs::remove_file(&input);
        let _ = fs::remove_file(&output);
        fs::write(&input, b"not nvflash").unwrap();

        assert!(run(&input, &output).is_err());
        assert!(!output.exists());
        fs::remove_file(input).unwrap();
    }

    #[test]
    fn run_rejects_output_aliasing_input() {
        let base =
            env::temp_dir().join(format!("nvflashk-linux-test-{}-alias", std::process::id()));
        let input = base.with_extension("input");
        let output = base.with_extension("output");
        let _ = fs::remove_file(&input);
        let _ = fs::remove_file(&output);
        fs::write(&input, b"not nvflash").unwrap();
        std::os::unix::fs::symlink(&input, &output).unwrap();

        assert_eq!(
            run(&input, &output),
            Err("input and output paths must differ".to_owned())
        );
        fs::remove_file(&output).unwrap();
        fs::remove_file(input).unwrap();
    }

    #[test]
    fn atomic_writer_refuses_existing_output() {
        let output = env::temp_dir().join(format!(
            "nvflashk-linux-test-{}-existing",
            std::process::id()
        ));
        let _ = fs::remove_file(&output);
        fs::write(&output, b"keep").unwrap();

        assert!(write_new_atomic(&output, b"replace", 0o600).is_err());
        assert_eq!(fs::read(&output).unwrap(), b"keep");
        fs::remove_file(output).unwrap();
    }

    #[test]
    fn atomic_writer_preserves_preexisting_temporary_file() {
        let output = env::temp_dir().join(format!(
            "nvflashk-linux-test-{}-collision",
            std::process::id()
        ));
        let temp = temp_path(&output).unwrap();
        let _ = fs::remove_file(&output);
        let _ = fs::remove_file(&temp);
        fs::write(&temp, b"keep").unwrap();

        assert!(write_new_atomic(&output, b"replace", 0o600).is_err());
        assert_eq!(fs::read(&temp).unwrap(), b"keep");
        fs::remove_file(temp).unwrap();
    }

    #[test]
    fn atomic_writer_strips_special_and_group_world_write_bits() {
        let output = env::temp_dir().join(format!(
            "nvflashk-linux-test-{}-permissions",
            std::process::id()
        ));
        let _ = fs::remove_file(&output);

        write_new_atomic(&output, b"output", 0o6777).unwrap();

        assert_eq!(
            fs::metadata(&output).unwrap().permissions().mode() & 0o7777,
            0o755
        );
        fs::remove_file(output).unwrap();
    }
}
