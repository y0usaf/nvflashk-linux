use sha2::{Digest, Sha256};
use std::env;
use std::ffi::OsString;
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};

const INPUT_SHA256: &str = "bc36918546a749650a1a28cfd990a506a531b77529b57a7f119ad214563bc7e7";
const OUTPUT_SHA256: &str = "06508cc681069d295f9006bdd1179f207fcf94f890a7927eb437af918850e221";
const PATCH_OFFSET: usize = 0x1a_5af3;
const ORIGINAL: [u8; 6] = [0x0f, 0x84, 0x12, 0x01, 0x00, 0x00];
const PATCHED: [u8; 6] = [0x90; 6];

fn usage() {
    println!(
        "nvflashk-linux — guarded NVFlash patcher\n\n\
         Usage: nvflashk-linux <input> <output>\n\n\
         Supported input:\n\
           Linux x86-64 NVFlash 5.792.0\n\
           SHA-256: {INPUT_SHA256}\n\n\
         This creates a new experimental binary. It does not invoke NVFlash or access hardware.\n\
         The output path must not already exist."
    );
}

fn sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn apply_patch(bytes: &mut [u8]) -> Result<(), String> {
    let target = bytes
        .get_mut(PATCH_OFFSET..PATCH_OFFSET + ORIGINAL.len())
        .ok_or_else(|| "input is too short for the verified patch offset".to_owned())?;
    if target != ORIGINAL {
        return Err(format!(
            "patch precondition failed at 0x{PATCH_OFFSET:x}: expected {}, found {}",
            hex(&ORIGINAL),
            hex(target)
        ));
    }
    target.copy_from_slice(&PATCHED);
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
    let result = (|| {
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temp)
            .map_err(|error| {
                format!("cannot create temporary output {}: {error}", temp.display())
            })?;
        file.set_permissions(fs::Permissions::from_mode(mode))
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
    let _ = fs::remove_file(&temp);
    result
}

fn run(input: &Path, output: &Path) -> Result<(), String> {
    if input == output {
        return Err("input and output paths must differ".to_owned());
    }

    let (mut bytes, mode) = read_input(input)?;
    let actual_input = sha256(&bytes);
    if actual_input != INPUT_SHA256 {
        return Err(format!(
            "unsupported input SHA-256: {actual_input}\nexpected: {INPUT_SHA256}"
        ));
    }

    apply_patch(&mut bytes)?;
    let actual_output = sha256(&bytes);
    if actual_output != OUTPUT_SHA256 {
        return Err(format!(
            "internal verification failed: output SHA-256 {actual_output}"
        ));
    }
    write_new_atomic(output, &bytes, mode)?;

    println!("created: {}", output.display());
    println!("SHA-256: {actual_output}");
    println!("status: experimental; hardware flashing has not been validated");
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
    fn patch_replaces_only_verified_branch() {
        let mut bytes = vec![0_u8; PATCH_OFFSET + ORIGINAL.len()];
        bytes[PATCH_OFFSET..].copy_from_slice(&ORIGINAL);
        apply_patch(&mut bytes).unwrap();
        assert_eq!(&bytes[PATCH_OFFSET..], PATCHED);
        assert!(bytes[..PATCH_OFFSET].iter().all(|byte| *byte == 0));
    }

    #[test]
    fn patch_rejects_unexpected_instruction() {
        let mut bytes = vec![0_u8; PATCH_OFFSET + ORIGINAL.len()];
        assert!(apply_patch(&mut bytes).is_err());
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
}
