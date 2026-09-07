use std::ffi::OsString;
use std::path::{Path, PathBuf};

pub(crate) fn legacy_root() -> Result<PathBuf, String> {
    dirs::home_dir()
        .map(|home| home.join(".unsloth").join("studio"))
        .ok_or_else(|| "Could not determine home directory".to_string())
}

pub(crate) fn selected_root() -> Result<PathBuf, String> {
    match explicit_environment_root()? {
        Some(root) => Ok(root),
        None => legacy_root(),
    }
}

/// Ordinary desktop installs retain their legacy-root policy. An explicitly
/// selected interpreter instead shares the CLI's data-root selection.
pub(crate) fn explicit_environment_root() -> Result<Option<PathBuf>, String> {
    let Some(environment) =
        crate::process::managed_env_override(std::env::var_os("UNSLOTH_ENV_DIR"))?
    else {
        return Ok(None);
    };
    root_for_environment(&environment, |name| std::env::var_os(name)).map(Some)
}

fn root_for_environment(
    environment: &Path,
    lookup: impl Fn(&str) -> Option<OsString>,
) -> Result<PathBuf, String> {
    for name in ["UNSLOTH_STUDIO_HOME", "STUDIO_HOME"] {
        if let Some(raw) = lookup(name) {
            let value = raw
                .to_str()
                .ok_or_else(|| format!("{name} is not valid Unicode"))?
                .trim();
            if !value.is_empty() {
                return resolve_data_path(value);
            }
        }
    }
    let environment = resolve_path(environment)?;
    if environment.join(".unsloth-studio-owned").is_file() {
        if let Ok(recorded) = std::fs::read_to_string(environment.join(".unsloth-studio-home")) {
            let path = Path::new(recorded.trim());
            if path.is_absolute() {
                return resolve_path(path);
            }
        }
    }
    if environment
        .file_name()
        .is_some_and(|name| name == "unsloth_studio")
    {
        if let Some(root) = environment.parent() {
            if root.join("share").join("studio.conf").is_file()
                || root
                    .join("bin")
                    .join(if cfg!(windows) {
                        "unsloth.exe"
                    } else {
                        "unsloth"
                    })
                    .is_file()
                || managed_cmd_shim(&root.join("bin").join("unsloth.cmd"))
            {
                return Ok(root.to_path_buf());
            }
        }
    }
    legacy_root()
}

fn managed_cmd_shim(path: &Path) -> bool {
    if !cfg!(windows) || !path.metadata().is_ok_and(|metadata| metadata.len() <= 8192) {
        return false;
    }
    std::fs::read(path).is_ok_and(|body| {
        [
            b"unsloth-studio-managed-launcher".as_slice(),
            b"from unsloth_cli import app".as_slice(),
        ]
        .iter()
        .all(|marker| body.windows(marker.len()).any(|bytes| bytes == *marker))
    })
}

fn resolve_data_path(value: &str) -> Result<PathBuf, String> {
    #[cfg(windows)]
    let value = {
        let home = std::env::var_os("USERPROFILE")
            .map(PathBuf::from)
            .or_else(dirs::home_dir)
            .ok_or_else(|| "Could not expand the Studio data root".to_string())?;
        crate::process::expand_windows_user(value, &home, std::env::var("USERNAME").ok().as_deref())
    };
    #[cfg(not(windows))]
    let value = if value == "~" || value.starts_with("~/") {
        let home =
            dirs::home_dir().ok_or_else(|| "Could not expand the Studio data root".to_string())?;
        home.join(value.strip_prefix("~/").unwrap_or(""))
            .to_string_lossy()
            .into_owned()
    } else if value.starts_with('~') {
        return Err("Use an absolute Studio data root instead of ~username".to_string());
    } else {
        value.to_string()
    };
    resolve_path(Path::new(&value))
}

/// Like Path.resolve(strict=False): canonicalize the existing ancestor, without
/// creating the data directory just to select it.
pub(crate) fn resolve_path(path: &Path) -> Result<PathBuf, String> {
    let absolute = std::path::absolute(path)
        .map_err(|error| format!("Could not resolve {}: {error}", path.display()))?;
    let mut ancestor = absolute.as_path();
    let mut missing = Vec::new();
    loop {
        match ancestor.canonicalize() {
            Ok(mut resolved) => {
                for component in missing.iter().rev() {
                    resolved.push(component);
                }
                return Ok(simplified_windows_path(&resolved));
            }
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                let Some(name) = ancestor.file_name() else {
                    return Err(format!("Could not resolve {}: {error}", path.display()));
                };
                missing.push(name);
                ancestor = ancestor.parent().ok_or_else(|| error.to_string())?;
            }
            Err(error) => return Err(format!("Could not resolve {}: {error}", path.display())),
        }
    }
}

pub(crate) fn simplified_windows_path(path: &Path) -> PathBuf {
    let text = path.to_string_lossy();
    if let Some(rest) = text.strip_prefix(r"\\?\UNC\") {
        PathBuf::from(format!(r"\\{rest}"))
    } else if let Some(rest) = text.strip_prefix(r"\\?\") {
        PathBuf::from(rest)
    } else {
        path.to_path_buf()
    }
}

pub(crate) fn apply_child_root(cmd: &mut std::process::Command) -> Result<(), String> {
    if let Some(root) = explicit_environment_root()? {
        cmd.env("UNSLOTH_STUDIO_HOME", &root);
        cmd.env("STUDIO_HOME", &root);
        let environment =
            crate::process::managed_env_override(std::env::var_os("UNSLOTH_ENV_DIR"))?
                .ok_or_else(|| "UNSLOTH_ENV_DIR changed during launch".to_string())?;
        cmd.env("UNSLOTH_ENV_DIR", environment);
    } else {
        cmd.env_remove("UNSLOTH_STUDIO_HOME");
        cmd.env_remove("STUDIO_HOME");
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn explicit_environment_keeps_data_root_alias_precedence() {
        let root = tempfile::tempdir().unwrap();
        let environment = root.path().join("external-python");
        let data = root.path().join("custom-data");
        let lower_priority = root.path().join("other-data");
        for specific in [false, true] {
            let selected = root_for_environment(&environment, |name| match name {
                "UNSLOTH_STUDIO_HOME" if specific => Some(data.clone().into_os_string()),
                "STUDIO_HOME" => Some(
                    if specific { &lower_priority } else { &data }
                        .clone()
                        .into_os_string(),
                ),
                _ => None,
            })
            .unwrap();
            assert_eq!(selected, resolve_path(&data).unwrap());
            assert!(!selected.exists());
        }
    }

    #[test]
    fn relative_data_root_is_resolved_before_the_child_changes_directory() {
        let selected = resolve_data_path("relative-data-root").unwrap();
        assert!(selected.is_absolute());
        assert_eq!(
            selected,
            resolve_path(&std::env::current_dir().unwrap().join("relative-data-root")).unwrap()
        );
    }

    #[test]
    fn explicit_environment_recovers_its_recorded_data_root() {
        let root = tempfile::tempdir().unwrap();
        let environment = root.path().join("external-python");
        let data = root.path().join("custom-data");
        std::fs::create_dir_all(&environment).unwrap();
        std::fs::write(environment.join(".unsloth-studio-owned"), "").unwrap();
        std::fs::write(
            environment.join(".unsloth-studio-home"),
            data.to_str().unwrap(),
        )
        .unwrap();
        assert_eq!(
            root_for_environment(&environment, |_| None).unwrap(),
            resolve_path(&data).unwrap()
        );
        std::fs::remove_file(environment.join(".unsloth-studio-owned")).unwrap();
        assert_eq!(
            root_for_environment(&environment, |_| None).unwrap(),
            legacy_root().unwrap()
        );
    }

    #[test]
    fn explicit_environment_data_root_is_shared_by_child_and_native_services() {
        with_explicit_test_environment(|environment, data| {
            let _ownership = crate::desktop_backend_owner::use_disk_root_id_for_test();
            let bin_dir = environment.join(if cfg!(windows) { "Scripts" } else { "bin" });
            std::fs::create_dir_all(&bin_dir).unwrap();
            let bin = bin_dir.join(if cfg!(windows) {
                "unsloth.exe"
            } else {
                "unsloth"
            });
            let python = bin_dir.join(if cfg!(windows) {
                "python.exe"
            } else {
                "python"
            });
            std::fs::write(&bin, "").unwrap();
            std::fs::write(&python, "").unwrap();
            assert_eq!(crate::process::resolve_backend_binary().unwrap(), bin);
            assert_eq!(crate::diagnostics::studio_dir(), data);
            assert_eq!(
                crate::desktop_auth::desktop_secret_path().unwrap(),
                data.join("auth").join(".desktop_secret")
            );

            let pending = crate::desktop_backend_owner::new_pending_owner().unwrap();
            assert_eq!(
                std::fs::read_to_string(data.join("share").join("studio_install_id"))
                    .unwrap()
                    .trim(),
                pending.studio_root_id
            );
            let owner =
                crate::desktop_backend_owner::activate_owner(pending, 8888, 1, 12345).unwrap();
            assert!(data.join("run").join("desktop_backend.json").is_file());
            owner.remove();

            let mut command = crate::process::build_managed_cli_command(&bin, &["studio"]).unwrap();
            crate::process::apply_managed_cli_context_at(&mut command, data).unwrap();
            let mut async_command = crate::process::build_managed_cli_command_tokio(
                &bin,
                &["studio", "provision-desktop-auth"],
            )
            .unwrap();
            crate::process::apply_managed_cli_context_tokio(&mut async_command).unwrap();
            for command in [&command, async_command.as_std()] {
                for name in ["UNSLOTH_STUDIO_HOME", "STUDIO_HOME"] {
                    assert!(command
                        .get_envs()
                        .any(|(key, value)| key == name && value == Some(data.as_os_str())));
                }
                assert!(command
                    .get_envs()
                    .any(|(key, value)| key == "UNSLOTH_ENV_DIR"
                        && value == Some(environment.as_os_str())));
            }
            assert!(crate::native_path_policy::reject_sensitive_document_folder(data).is_err());
            assert!(
                crate::native_path_policy::reject_sensitive_document_folder(environment).is_err()
            );
            let output = data.join("outputs").join("metrics.json");
            std::fs::create_dir_all(output.parent().unwrap()).unwrap();
            std::fs::write(&output, "{}").unwrap();
            assert!(crate::native_path_policy::classify_artifact_path(
                crate::native_path_policy::NativeArtifactKind::TrainingOutput,
                &output
            )
            .is_ok());

            let stage = data.join(crate::staged_update::STAGE_DIR);
            std::fs::create_dir_all(&stage).unwrap();
            std::fs::write(stage.join("keep"), "untouched").unwrap();
            assert_eq!(crate::staged_update::status(data).state, "none");
            assert!(crate::staged_update::pending_versions(data).is_none());
            crate::staged_update::discard(data);
            crate::staged_update::reconcile_at_launch(data, "1.0.0");
            assert!(!crate::staged_update::confirm_activated(data, "1.0.0"));
            assert_eq!(
                std::fs::read_to_string(stage.join("keep")).unwrap(),
                "untouched"
            );
        });
    }

    #[test]
    fn invalid_or_missing_explicit_environment_never_uses_legacy_runtime() {
        with_explicit_test_environment(|environment, _data| {
            let missing = crate::process::resolve_backend_binary().unwrap_err();
            assert!(missing.contains("refusing to use another environment"));
            for value in ["relative-env", "C:drive-relative"] {
                std::env::set_var("UNSLOTH_ENV_DIR", value);
                assert!(selected_root().is_err());
                assert!(crate::process::resolve_backend_binary().is_err());
                assert!(crate::desktop_auth::desktop_secret_path().is_err());
                assert!(crate::desktop_backend_owner::ensure_installed_studio_root_id().is_err());
                assert!(crate::process::managed_cli_context_error().is_some());
                assert!(!crate::staged_update::uses_default_environment());
            }
            std::env::set_var("UNSLOTH_ENV_DIR", environment);
        });
    }
}

#[cfg(test)]
pub(crate) fn with_explicit_test_environment(test: impl FnOnce(&Path, &Path)) {
    let _lock = crate::native_path_policy::PROCESS_ENV_LOCK
        .lock()
        .unwrap_or_else(|error| error.into_inner());
    struct Restore(Vec<(&'static str, Option<OsString>)>);
    impl Drop for Restore {
        fn drop(&mut self) {
            for (name, value) in &self.0 {
                match value {
                    Some(value) => std::env::set_var(name, value),
                    None => std::env::remove_var(name),
                }
            }
        }
    }
    let _restore = Restore(
        ["UNSLOTH_ENV_DIR", "UNSLOTH_STUDIO_HOME", "STUDIO_HOME"]
            .into_iter()
            .map(|name| (name, std::env::var_os(name)))
            .collect(),
    );
    let scratch = tempfile::tempdir().unwrap();
    let environment = resolve_path(&scratch.path().join("external-python")).unwrap();
    let data = resolve_path(&scratch.path().join("custom-data")).unwrap();
    std::fs::create_dir_all(&data).unwrap();
    std::env::set_var("UNSLOTH_ENV_DIR", &environment);
    std::env::remove_var("UNSLOTH_STUDIO_HOME");
    std::env::set_var("STUDIO_HOME", &data);
    test(&environment, &data);
}
