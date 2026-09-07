use std::process::Command;

fn binary() -> Command {
    Command::new(env!("CARGO_BIN_EXE_nvflashk-linux"))
}

#[test]
fn version_reports_package_version() {
    let output = binary().arg("--version").output().unwrap();

    assert!(output.status.success());
    assert_eq!(
        String::from_utf8_lossy(&output.stdout).trim(),
        concat!("nvflashk-linux ", env!("CARGO_PKG_VERSION"))
    );
}

#[test]
fn version_rejects_unexpected_extra_arguments() {
    let output = binary().args(["--version", "extra"]).output().unwrap();

    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("unexpected arguments"));
}

#[test]
fn help_does_not_print_stale_status() {
    let output = binary().arg("--help").output().unwrap();

    assert!(output.status.success());
    assert!(!String::from_utf8_lossy(&output.stdout).contains("status:"));
}
