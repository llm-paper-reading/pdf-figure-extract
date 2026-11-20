"""联网冒烟测试：逐条执行 README「使用」节的命令（--net 开启，默认跳过）。

README 示例页码写错（FA Figure 2 实际在 p6），
只有原样执行 README 命令才能发现。运行方式：
    pytest tests/test_readme_commands.py --net
"""
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
FA_PDF = "https://arxiv.org/pdf/2205.14135"
VLLM_PDF = "https://arxiv.org/pdf/2309.06180"


def pytest_collection_modifyitems(config, items):
    if config.getoption("--net"):
        return
    skip = pytest.mark.skip(reason="network test, run with --net")
    for item in items:
        if "net" in item.keywords:
            item.add_marker(skip)


def run(*args, cwd):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / args[0]), *map(str, args[1:])],
        capture_output=True, text=True, cwd=cwd)


@pytest.fixture(scope="module")
def workdir(tmp_path_factory):
    import urllib.request
    d = tmp_path_factory.mktemp("readme")
    for name, url in [("paper.pdf", FA_PDF), ("vllm.pdf", VLLM_PDF)]:
        urllib.request.urlretrieve(url, d / name)
    return d


@pytest.mark.net
def test_readme_extract_svg(workdir):
    r = run("extract_svg.py", "paper.pdf", "2", "1", "fig1.svg", cwd=workdir)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.net
def test_readme_extract_fig(workdir):
    r = run("extract_fig.py", "paper.pdf", "6", "2", "fig2.png", cwd=workdir)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OK" in r.stdout  # 四边墨迹自检通过


@pytest.mark.net
def test_readme_clip_mode(workdir):
    r = run("extract_svg.py", "vllm.pdf", "5", "5", "fig5.svg",
            "--clip", "318,40,560,168", cwd=workdir)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.net
def test_readme_check_border(workdir):
    r = run("check_border.py", "fig1.svg", "fig2.png", "fig5.svg", cwd=workdir)
    assert r.returncode == 0, r.stdout + r.stderr
