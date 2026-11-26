#!/bin/bash
# 双击运行：读取 ~/Music/网易云音乐 里最新的 8 首歌（支持 .ncm），给视频配乐。
# 也可以在终端里运行：bash 一键配乐.command --folder "/某个/文件夹" --count 8
cd "$(dirname "$0")" || exit 1
echo "== GTA 编年史 · 一键配乐 =="

if ! command -v python3 >/dev/null 2>&1 || ! python3 -c "import sys" >/dev/null 2>&1; then
  echo "需要先安装 Python 3：在「终端」里运行  xcode-select --install  ，装好后再双击本文件。"
  read -r -p "按回车键关闭..." _; exit 1
fi

if [ ! -x .venv/bin/python ]; then
  echo "第一次运行：正在准备环境（只需要一次，约 1~3 分钟）……"
  python3 -m venv .venv || { echo "创建虚拟环境失败"; read -r -p "按回车键关闭..." _; exit 1; }
fi
PY=.venv/bin/python
PKGS="numpy scipy soundfile pycryptodome imageio-ffmpeg mutagen"
if ! $PY -c "import numpy, scipy, soundfile, Crypto, imageio_ffmpeg, mutagen" >/dev/null 2>&1; then
  $PY -m pip install -q --upgrade pip >/dev/null 2>&1
  $PY -m pip install -q --timeout 30 $PKGS \
    || $PY -m pip install -q -i https://pypi.tuna.tsinghua.edu.cn/simple $PKGS \
    || { echo "安装依赖失败，请检查网络后重试。"; read -r -p "按回车键关闭..." _; exit 1; }
fi

$PY src/add_music.py "$@"
status=$?
echo
read -r -p "按回车键关闭窗口..." _
exit $status
