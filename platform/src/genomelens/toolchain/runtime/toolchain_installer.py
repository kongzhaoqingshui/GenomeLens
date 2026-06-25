"""把缺失 runtime toolchains(运行时工具链) 下载并安装到项目缓存"""

# region import
from __future__ import annotations

import hashlib
import json
import re
import shutil
import tarfile
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from genomelens.toolchain.runtime.resource_locator import project_root

# endregion


BLAST_LATEST_URL = "https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/LATEST/"
IMAGEMAGICK_WINDOWS_ZIP_URL = "https://imagemagick.org/archive/windows/ImageMagick-windows.zip"
KNOWN_ARCHIVE_SHA256: dict[str, str] = {}


@dataclass(frozen=True)
class ToolchainInstallResult:
    """toolchain(工具链) 安装尝试的结果"""

    # fmt: off
    name: str          # 工具链名称
    status: str        # 安装状态（ok/error/unsupported）
    path: str = ""     # 安装路径
    message: str = ""  # 状态说明或错误信息

    @property
    # fmt: on

    def ok(self) -> bool:
        """安装是否成功"""

        return self.status == "ok"


def downloads_root() -> Path:
    """返回工具链下载缓存根目录"""

    # 下载缓存和安装目录分离，便于重复安装时复用归档包
    return project_root() / "references" / "downloads" / "toolchains"


def toolchains_root() -> Path:
    """返回工具链安装根目录"""

    return project_root() / "toolchains"


def _sha256(path: Path) -> str:
    """计算文件 SHA256 摘要"""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_path(target: Path) -> Path:
    """返回下载归档对应的 manifest 路径"""

    return target.with_suffix(target.suffix + ".sha256.json")


def _read_download_manifest(target: Path) -> dict[str, object]:
    """读取下载 manifest，失败时返回空 dict"""

    path = _manifest_path(target)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_download_manifest(name: str, url: str, target: Path, digest: str) -> None:
    """写入下载 manifest 记录"""

    payload = {
        "name": name,
        "url": url,
        "archive": str(target),
        "sha256": digest,
    }
    _manifest_path(target).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _verify_archive(name: str, url: str, target: Path) -> bool:
    """验证归档完整性，通过 SHA256 与 manifest 比对"""

    if not target.is_file() or target.stat().st_size <= 0:
        return False
    digest = _sha256(target)
    expected = KNOWN_ARCHIVE_SHA256.get(url, "")
    if expected and digest.lower() != expected.lower():
        raise RuntimeError(f"{name} archive SHA256 mismatch: expected {expected}, got {digest}")
    manifest = _read_download_manifest(target)
    recorded = str(manifest.get("sha256") or "")
    recorded_url = str(manifest.get("url") or "")
    if recorded and recorded != digest:
        return False
    if recorded_url and recorded_url != url:
        return False
    # 本地包一旦验证通过，就刷新 manifest，后续可直接信任缓存
    _write_download_manifest(name, url, target, digest)
    return True


def _download(name: str, url: str, target: Path) -> Path:
    """下载 URL 到目标路径，并验证完整性"""

    target.parent.mkdir(parents=True, exist_ok=True)
    if _verify_archive(name, url, target):
        return target
    if target.exists():
        target.unlink()
    tmp = target.with_suffix(target.suffix + ".part")
    # 先落到 .part，再替换目标文件，避免半截下载伪装成可用缓存
    with urllib.request.urlopen(url, timeout=120) as response, tmp.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    tmp.replace(target)
    if not _verify_archive(name, url, target):
        raise RuntimeError(f"{name} archive verification failed: {target}")
    return target


def _ensure_within(root: Path, child: Path) -> None:
    """确保子路径不逃出根目录，防止 zip slip"""

    root_resolved = root.resolve(strict=False)
    child_resolved = child.resolve(strict=False)
    if root_resolved == child_resolved:
        return
    if root_resolved not in child_resolved.parents:
        raise RuntimeError(f"Refusing to extract path outside target directory: {child}")


def _safe_extract_tar(archive: Path, target: Path) -> None:
    """安全解压 tar.gz，拒绝符号链接与越界路径"""

    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            if member.issym() or member.islnk():
                raise RuntimeError(f"Refusing to extract archive link: {member.name}")
            # 在真正 extractall 前先检查每个成员是否越界
            _ensure_within(target, target / member.name)
        tar.extractall(target)


def _safe_extract_zip(archive: Path, target: Path) -> None:
    """安全解压 zip，拒绝越界路径"""

    with zipfile.ZipFile(archive) as zip_handle:
        for info in zip_handle.infolist():
            _ensure_within(target, target / info.filename)
        zip_handle.extractall(target)


def _safe_replace_dir(source: Path, target: Path) -> None:
    """安全替换目录，限制在 toolchains_root 内"""

    root = toolchains_root().resolve(strict=False)
    resolved = target.resolve(strict=False)
    if not str(resolved).lower().startswith(str(root).lower()):
        raise RuntimeError(f"Refusing to replace path outside toolchains: {target}")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def _find_child_with_files(root: Path, required: list[str]) -> Path:
    """在解压目录中查找包含必需文件的子目录"""

    required_lower = {item.lower() for item in required}
    for candidate in [root, *[item for item in root.rglob("*") if item.is_dir()]]:
        names = {item.name.lower() for item in candidate.iterdir() if item.is_file()}
        bin_dir = candidate / "bin"
        bin_names = {item.name.lower() for item in bin_dir.iterdir() if item.is_file()} if bin_dir.is_dir() else set()
        # 兼容“可执行文件在根目录”和“可执行文件在 bin/”两种归档布局
        if required_lower.issubset(names) or required_lower.issubset(bin_names):
            return candidate
    raise FileNotFoundError(f"Downloaded archive did not contain required files: {required}")


def _latest_blast_windows_archive() -> str:
    """从 NCBI LATEST 页面解析最新 Windows BLAST+ 归档 URL"""

    with urllib.request.urlopen(BLAST_LATEST_URL, timeout=60) as response:
        listing = response.read().decode("utf-8", errors="replace")
    matches = re.findall(r'href="([^"]*ncbi-blast-[^"]+-x64-win64\.tar\.gz)"', listing)
    if not matches:
        raise RuntimeError("Could not find an x64 Windows BLAST+ tar.gz archive in NCBI LATEST")
    # 目录页里可能同时保留多个版本，按文件名排序后取最新值
    return BLAST_LATEST_URL + sorted(matches)[-1]


def install_blast() -> ToolchainInstallResult:
    """下载并安装 BLAST+ 到 `toolchains/blast/current`"""

    try:
        url = _latest_blast_windows_archive()
        archive = downloads_root() / "blast" / Path(url).name
        _download("blast", url, archive)
        with tempfile.TemporaryDirectory(prefix="genomelens-blast-") as tmpdir:
            extract_root = Path(tmpdir)
            _safe_extract_tar(archive, extract_root)
            source = _find_child_with_files(extract_root, ["blastn.exe", "makeblastdb.exe"])
            target = toolchains_root() / "blast" / "current"
            _safe_replace_dir(source, target)
        return ToolchainInstallResult("blast", "ok", str(target), f"Installed BLAST+ from {url}")
    except Exception as exc:  # noqa: BLE001 - install command reports any download/extract failure
        return ToolchainInstallResult("blast", "error", message=str(exc))


def install_imagemagick() -> ToolchainInstallResult:
    """下载并安装 ImageMagick 到 `toolchains/imagemagick/current`"""

    try:
        archive = downloads_root() / "imagemagick" / "ImageMagick-windows.zip"
        _download("imagemagick", IMAGEMAGICK_WINDOWS_ZIP_URL, archive)
        with tempfile.TemporaryDirectory(prefix="genomelens-imagemagick-") as tmpdir:
            extract_root = Path(tmpdir)
            _safe_extract_zip(archive, extract_root)
            source = _find_child_with_files(extract_root, ["magick.exe"])
            target = toolchains_root() / "imagemagick" / "current"
            _safe_replace_dir(source, target)
        return ToolchainInstallResult(
            "imagemagick",
            "ok",
            str(target),
            f"Installed ImageMagick from {IMAGEMAGICK_WINDOWS_ZIP_URL}",
        )
    except Exception as exc:  # noqa: BLE001 - install command reports any download/extract failure
        return ToolchainInstallResult("imagemagick", "error", message=str(exc))


def install_toolchain(name: str) -> ToolchainInstallResult:
    """按公开名称安装受支持的 toolchain(工具链)"""

    # 统一的名称分发表同时服务于 CLI、配置和诊断模块
    if name == "blast":
        return install_blast()
    if name == "imagemagick":
        return install_imagemagick()
    return ToolchainInstallResult(name, "unsupported", message=f"Unsupported toolchain: {name}")
