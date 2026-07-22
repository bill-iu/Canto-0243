#!/usr/bin/env python3
"""
同步 README 中的版本號與 GitHub 最新 release 版本號

使用方法：
  python scripts/sync-version.py          # 自動同步
  python scripts/sync-version.py --dry    # 預覽不修改
  python scripts/sync-version.py --check  # 只檢查是否需要更新
"""

import re
import sys
import argparse
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError
import json


REPO = "bill-iu/Canto-0243"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"

# README 檔案及其對應的版本注釋標記
README_CONFIGS = [
    ("README.md", "version:zh-Hant"),
    ("docs/README.zh-Hans.md", "version:zh-Hans"),
    ("docs/README.en.md", "version:en"),
]


def fetch_latest_version() -> str:
    """從 GitHub API 獲取最新版本號"""
    try:
        with urlopen(API_URL, timeout=5) as response:
            data = json.loads(response.read().decode())
            tag_name = data.get("tag_name", "").lstrip("v")
            if not tag_name:
                raise ValueError("無法從 API 响應中獲取版本號")
            return f"v{tag_name}" if not tag_name.startswith("v") else tag_name
    except URLError as e:
        raise RuntimeError(f"無法連接 GitHub API: {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"無效的 JSON 响應: {e}")


def get_version_from_file(file_path: Path, marker: str) -> str:
    """從檔案中讀取現有的版本號"""
    content = file_path.read_text(encoding="utf-8")
    pattern = f"<!-- {marker} -->\n(.+?)\n<!-- /{marker} -->"
    match = re.search(pattern, content)
    if match:
        # 提取粗體內容中的版本號
        line = match.group(1)
        version_match = re.search(r"\*\*(.+?)\*\*", line)
        return version_match.group(1) if version_match else None
    return None


def update_version_in_file(file_path: Path, marker: str, new_version: str, dry_run: bool = False) -> bool:
    """更新檔案中的版本號，返回是否有修改"""
    content = file_path.read_text(encoding="utf-8")
    
    # 根據語言決定文本
    if marker.endswith("en"):
        text = f"Current version: **{new_version}**"
    else:
        text = f"目前版本：**{new_version}**"
    
    pattern = f"(<!-- {marker} -->)\n.+?\n(<!-- /{marker} -->)"
    replacement = f"\\1\n{text}\n\\2"
    
    new_content = re.sub(pattern, replacement, content)
    
    if new_content == content:
        return False  # 無修改
    
    if not dry_run:
        file_path.write_text(new_content, encoding="utf-8")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="同步 README 版本號與 GitHub 最新 release"
    )
    parser.add_argument(
        "--dry", action="store_true", help="預覽修改但不更新檔案"
    )
    parser.add_argument(
        "--check", action="store_true", help="只檢查是否需要更新"
    )
    args = parser.parse_args()

    # 取得專案根目錄
    root = Path(__file__).parent.parent

    print(f"📌 Repository: {REPO}")
    print(f"🔗 API: {API_URL}\n")

    # 獲取最新版本
    try:
        latest_version = fetch_latest_version()
        print(f"✓ 最新版本: {latest_version}")
    except RuntimeError as e:
        print(f"✗ 錯誤: {e}", file=sys.stderr)
        sys.exit(1)

    # 檢查和更新各 README
    needs_update = False
    print("\n📋 檢查 README 檔案:")

    for readme_path, marker in README_CONFIGS:
        full_path = root / readme_path
        current_version = get_version_from_file(full_path, marker)
        
        status = "✓" if current_version == latest_version else "✗"
        print(f"  {status} {readme_path}")
        print(f"     當前: {current_version or '(未找到)'},  最新: {latest_version}")

        if current_version != latest_version:
            needs_update = True
            if args.check:
                continue
            
            changed = update_version_in_file(
                full_path, marker, latest_version, dry_run=args.dry
            )
            if changed:
                action = "預覽更新" if args.dry else "已更新"
                print(f"     → {action}")

    # 輸出結果
    print("\n" + "=" * 50)
    if args.check:
        if needs_update:
            print("⚠️  需要更新版本號")
            sys.exit(1)
        else:
            print("✓ 所有 README 版本號已是最新")
            sys.exit(0)
    else:
        if needs_update:
            print("✓ 版本號已同步到最新" if not args.dry else "✓ 預覽完成（未修改）")
        else:
            print("✓ 所有 README 版本號已是最新")


if __name__ == "__main__":
    main()
