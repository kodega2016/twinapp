import os
import shutil
import zipfile
import subprocess
from pathlib import Path


def resolve_target() -> tuple[str, str, str, str]:
    """Resolve Lambda runtime and architecture build targets from env vars."""
    python_version = os.getenv("LAMBDA_PYTHON_VERSION", "3.12")
    architecture = os.getenv("LAMBDA_ARCH", "x86_64").lower()

    if architecture not in {"x86_64", "arm64"}:
        raise ValueError("LAMBDA_ARCH must be either 'x86_64' or 'arm64'.")

    docker_platform = "linux/amd64" if architecture == "x86_64" else "linux/arm64"
    wheel_platform = (
        "manylinux2014_x86_64" if architecture == "x86_64" else "manylinux2014_aarch64"
    )
    return python_version, architecture, docker_platform, wheel_platform


def verify_pydantic_core_binary(package_dir: str, python_version: str, architecture: str) -> None:
    """Fail fast if pydantic_core native extension doesn't match target ABI."""
    major, minor = python_version.split(".", 1)
    abi_tag = f"cpython-{major}{minor}"
    arch_tag = "x86_64" if architecture == "x86_64" else "aarch64"

    pydantic_dir = Path(package_dir) / "pydantic_core"
    if not pydantic_dir.exists():
        raise RuntimeError("pydantic_core package not found in lambda-package.")

    native_modules = list(pydantic_dir.glob("_pydantic_core*.so"))
    if not native_modules:
        raise RuntimeError("No pydantic_core native extension (.so) found in lambda-package.")

    has_compatible_module = any(
        abi_tag in mod.name and arch_tag in mod.name for mod in native_modules
    )
    if not has_compatible_module:
        found = ", ".join(mod.name for mod in native_modules)
        raise RuntimeError(
            "Incompatible pydantic_core binary found. "
            f"Expected ABI containing '{abi_tag}' and '{arch_tag}', found: {found}"
        )


def main():
    python_version, architecture, docker_platform, wheel_platform = resolve_target()

    print("Creating Lambda deployment package...")
    print(f"Target runtime: python{python_version}")
    print(f"Target architecture: {architecture}")

    # Clean up
    if os.path.exists("lambda-package"):
        shutil.rmtree("lambda-package")
    if os.path.exists("lambda-deployment.zip"):
        os.remove("lambda-deployment.zip")

    # Create package directory
    os.makedirs("lambda-package")

    # Install dependencies using Docker with Lambda runtime image
    print("Installing dependencies for Lambda runtime...")

    # Use the official AWS Lambda image matching the target runtime.
    # This ensures compatibility with Lambda's runtime environment
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{os.getcwd()}:/var/task",
            "--platform",
            docker_platform,
            "--entrypoint",
            "",  # Override the default entrypoint
            f"public.ecr.aws/lambda/python:{python_version}",
            "/bin/sh",
            "-c",
            (
                "pip install "
                "--target /var/task/lambda-package "
                "-r /var/task/requirements.txt "
                f"--platform {wheel_platform} "
                "--only-binary=:all: "
                "--upgrade"
            ),
        ],
        check=True,
    )

    verify_pydantic_core_binary("lambda-package", python_version, architecture)

    # Copy application files
    print("Copying application files...")
    for file in ["server.py", "lambda_handler.py", "context.py", "resources.py"]:
        if os.path.exists(file):
            shutil.copy2(file, "lambda-package/")
    
    # Copy data directory
    if os.path.exists("data"):
        shutil.copytree("data", "lambda-package/data")

    # Create zip
    print("Creating zip file...")
    with zipfile.ZipFile("lambda-deployment.zip", "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk("lambda-package"):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, "lambda-package")
                zipf.write(file_path, arcname)

    # Show package size
    size_mb = os.path.getsize("lambda-deployment.zip") / (1024 * 1024)
    print(f"✓ Created lambda-deployment.zip ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()