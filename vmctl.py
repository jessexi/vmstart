#!/usr/bin/env python3
"""
vmctl - VM管理命令行工具

支持功能:
- 启动VM (支持挂载指定系统盘)
- 停止VM
- 列出运行中的VM
- 查看VM状态
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# 配置文件和运行时数据目录
VMCTL_HOME = Path.home() / ".vmctl"
VMCTL_RUN = VMCTL_HOME / "run"
VMCTL_CONFIG = VMCTL_HOME / "config.json"

# 默认配置
DEFAULT_CONFIG = {
    "default_cpu": 2,
    "default_memory": "2G",
    "default_disk": "ubuntu.raw",
    "vmstart_binary": "./vmstart",
    "seed_iso": "seed.iso",
    "efi_var_store": "efi_vars.store",
}


def ensure_dirs():
    """确保必要的目录存在"""
    VMCTL_HOME.mkdir(exist_ok=True)
    VMCTL_RUN.mkdir(exist_ok=True)


def load_config():
    """加载配置文件"""
    if VMCTL_CONFIG.exists():
        with open(VMCTL_CONFIG) as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return DEFAULT_CONFIG


def save_vm_info(name: str, pid: int, disk: str, config: dict):
    """保存VM运行信息"""
    ensure_dirs()
    info = {
        "name": name,
        "pid": pid,
        "disk": disk,
        "started_at": datetime.now().isoformat(),
        "config": config,
    }
    info_file = VMCTL_RUN / f"{name}.json"
    with open(info_file, "w") as f:
        json.dump(info, f, indent=2)


def remove_vm_info(name: str):
    """移除VM运行信息"""
    info_file = VMCTL_RUN / f"{name}.json"
    if info_file.exists():
        info_file.unlink()


def get_running_vms():
    """获取所有运行中的VM信息"""
    ensure_dirs()
    vms = []
    for info_file in VMCTL_RUN.glob("*.json"):
        try:
            with open(info_file) as f:
                info = json.load(f)
            # 检查进程是否还存在
            pid = info.get("pid")
            if pid and is_process_running(pid):
                vms.append(info)
            else:
                # 进程已结束，清理信息文件
                info_file.unlink()
        except (json.JSONDecodeError, KeyError):
            continue
    return vms


def is_process_running(pid: int) -> bool:
    """检查进程是否运行中"""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def parse_memory(mem_str: str) -> int:
    """解析内存大小字符串 (例如: 2G, 512M, 1024)"""
    mem_str = mem_str.strip().upper()
    if mem_str.endswith("G"):
        return int(mem_str[:-1]) * 1024 * 1024 * 1024
    elif mem_str.endswith("M"):
        return int(mem_str[:-1]) * 1024 * 1024
    elif mem_str.endswith("K"):
        return int(mem_str[:-1]) * 1024
    else:
        return int(mem_str)


def format_memory(bytes_val: int) -> str:
    """格式化内存大小为可读字符串"""
    if bytes_val >= 1024 * 1024 * 1024:
        return f"{bytes_val // (1024 * 1024 * 1024)}G"
    elif bytes_val >= 1024 * 1024:
        return f"{bytes_val // (1024 * 1024)}M"
    else:
        return f"{bytes_val // 1024}K"


# ============== 命令实现 ==============


def cmd_start(args):
    """启动VM"""
    config = load_config()

    # 确定VM名称
    name = args.name or f"vm-{int(time.time())}"

    # 检查是否已有同名VM在运行
    running_vms = get_running_vms()
    for vm in running_vms:
        if vm["name"] == name:
            print(f"错误: VM '{name}' 已在运行中 (PID: {vm['pid']})")
            return 1

    # 确定系统盘路径
    disk = args.disk or config["default_disk"]
    if not os.path.exists(disk):
        print(f"错误: 系统盘 '{disk}' 不存在")
        print("提示: 使用 --disk 参数指定系统盘路径，或先下载/创建系统盘镜像")
        return 1

    # 检查seed.iso
    seed_iso = args.seed or config["seed_iso"]
    if not os.path.exists(seed_iso):
        print(f"警告: seed.iso '{seed_iso}' 不存在，cloud-init可能无法工作")

    # 构建VM配置
    cpu = args.cpu or config["default_cpu"]
    memory = args.memory or config["default_memory"]
    memory_bytes = parse_memory(memory)

    vm_config = {
        "cpu": cpu,
        "memory": memory,
        "memory_bytes": memory_bytes,
        "disk": os.path.abspath(disk),
        "seed": os.path.abspath(seed_iso) if os.path.exists(seed_iso) else None,
    }

    print(f"正在启动VM '{name}'...")
    print(f"  系统盘: {disk}")
    print(f"  CPU: {cpu} 核")
    print(f"  内存: {memory}")

    # 生成临时配置文件供vmstart使用
    vm_config_file = VMCTL_RUN / f"{name}_config.json"
    ensure_dirs()
    with open(vm_config_file, "w") as f:
        json.dump(vm_config, f)

    # 设置环境变量传递配置
    env = os.environ.copy()
    env["VMCTL_DISK"] = os.path.abspath(disk)
    env["VMCTL_CPU"] = str(cpu)
    env["VMCTL_MEMORY"] = str(memory_bytes)
    env["VMCTL_NAME"] = name
    if os.path.exists(seed_iso):
        env["VMCTL_SEED"] = os.path.abspath(seed_iso)

    # 获取vmstart二进制路径
    vmstart_bin = args.binary or config["vmstart_binary"]
    if not os.path.exists(vmstart_bin):
        print(f"错误: vmstart二进制文件 '{vmstart_bin}' 不存在")
        return 1

    # 先进行代码签名（如果需要）
    entitlements = "vmstart.entitlements"
    if os.path.exists(entitlements):
        subprocess.run(
            ["codesign", "--sign", "-", "--entitlements", entitlements, "--force", vmstart_bin],
            capture_output=True,
        )

    if args.foreground:
        # 前台运行
        print("以前台模式启动，按Ctrl+C停止...")
        try:
            process = subprocess.Popen([vmstart_bin], env=env)
            save_vm_info(name, process.pid, disk, vm_config)
            process.wait()
        except KeyboardInterrupt:
            print("\n正在停止VM...")
            process.terminate()
        finally:
            remove_vm_info(name)
    else:
        # 后台运行
        log_file = VMCTL_RUN / f"{name}.log"
        with open(log_file, "w") as log:
            process = subprocess.Popen(
                [vmstart_bin],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )

        save_vm_info(name, process.pid, disk, vm_config)
        print(f"VM '{name}' 已在后台启动")
        print(f"  PID: {process.pid}")
        print(f"  日志: {log_file}")
        print(f"\n使用 'vmctl stop {name}' 停止VM")
        print(f"使用 'vmctl logs {name}' 查看日志")

    return 0


def cmd_stop(args):
    """停止VM"""
    running_vms = get_running_vms()

    if args.all:
        # 停止所有VM
        if not running_vms:
            print("没有正在运行的VM")
            return 0

        for vm in running_vms:
            stop_vm(vm["name"], vm["pid"], force=args.force)
        return 0

    if not args.name:
        print("错误: 请指定VM名称或使用 --all 停止所有VM")
        return 1

    # 查找指定的VM
    target_vm = None
    for vm in running_vms:
        if vm["name"] == args.name:
            target_vm = vm
            break

    if not target_vm:
        # 尝试按PID查找
        try:
            pid = int(args.name)
            for vm in running_vms:
                if vm["pid"] == pid:
                    target_vm = vm
                    break
        except ValueError:
            pass

    if not target_vm:
        print(f"错误: 未找到VM '{args.name}'")
        print("使用 'vmctl list' 查看运行中的VM")
        return 1

    return stop_vm(target_vm["name"], target_vm["pid"], force=args.force)


def stop_vm(name: str, pid: int, force: bool = False):
    """停止指定的VM"""
    print(f"正在停止VM '{name}' (PID: {pid})...")

    try:
        if force:
            os.kill(pid, signal.SIGKILL)
        else:
            os.kill(pid, signal.SIGTERM)
            # 等待进程结束
            for _ in range(10):
                time.sleep(0.5)
                if not is_process_running(pid):
                    break
            else:
                # 超时，强制终止
                print("进程未响应，强制终止...")
                os.kill(pid, signal.SIGKILL)

        remove_vm_info(name)
        print(f"VM '{name}' 已停止")
        return 0
    except ProcessLookupError:
        remove_vm_info(name)
        print(f"VM '{name}' 进程已不存在")
        return 0
    except PermissionError:
        print(f"错误: 没有权限停止进程 {pid}")
        return 1


def cmd_list(args):
    """列出运行中的VM"""
    running_vms = get_running_vms()

    if not running_vms:
        print("没有正在运行的VM")
        return 0

    if args.json:
        print(json.dumps(running_vms, indent=2))
        return 0

    # 表格输出
    print(f"{'NAME':<20} {'PID':<10} {'DISK':<30} {'STARTED':<20}")
    print("-" * 80)

    for vm in running_vms:
        name = vm.get("name", "unknown")
        pid = vm.get("pid", "?")
        disk = vm.get("disk", "?")
        # 截断过长的磁盘路径
        if len(disk) > 28:
            disk = "..." + disk[-25:]
        started = vm.get("started_at", "?")
        if started != "?":
            # 格式化时间
            try:
                dt = datetime.fromisoformat(started)
                started = dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass

        print(f"{name:<20} {pid:<10} {disk:<30} {started:<20}")

    print("-" * 80)
    print(f"共 {len(running_vms)} 个VM正在运行")
    return 0


def cmd_status(args):
    """查看VM状态"""
    running_vms = get_running_vms()

    if not args.name:
        # 显示概览
        print(f"运行中的VM数量: {len(running_vms)}")
        return cmd_list(args)

    # 查找指定VM
    target_vm = None
    for vm in running_vms:
        if vm["name"] == args.name:
            target_vm = vm
            break

    if not target_vm:
        print(f"VM '{args.name}' 未在运行")
        return 1

    # 显示详细信息
    print(f"VM: {target_vm['name']}")
    print(f"  状态: 运行中")
    print(f"  PID: {target_vm['pid']}")
    print(f"  系统盘: {target_vm['disk']}")
    print(f"  启动时间: {target_vm['started_at']}")

    if "config" in target_vm:
        cfg = target_vm["config"]
        print(f"  CPU: {cfg.get('cpu', '?')} 核")
        print(f"  内存: {cfg.get('memory', '?')}")

    return 0


def cmd_logs(args):
    """查看VM日志"""
    log_file = VMCTL_RUN / f"{args.name}.log"

    if not log_file.exists():
        print(f"错误: 未找到VM '{args.name}' 的日志文件")
        return 1

    if args.follow:
        # 实时跟踪日志
        subprocess.run(["tail", "-f", str(log_file)])
    else:
        # 显示最后n行
        lines = args.lines or 50
        subprocess.run(["tail", "-n", str(lines), str(log_file)])

    return 0


def cmd_config(args):
    """管理配置"""
    ensure_dirs()

    if args.show:
        config = load_config()
        print(json.dumps(config, indent=2))
        return 0

    if args.set:
        key, value = args.set.split("=", 1)
        config = load_config()

        # 尝试解析数值
        try:
            value = int(value)
        except ValueError:
            pass

        config[key] = value
        with open(VMCTL_CONFIG, "w") as f:
            json.dump(config, f, indent=2)
        print(f"配置已更新: {key} = {value}")
        return 0

    if args.reset:
        if VMCTL_CONFIG.exists():
            VMCTL_CONFIG.unlink()
        print("配置已重置为默认值")
        return 0

    # 默认显示配置
    config = load_config()
    print(json.dumps(config, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="vmctl",
        description="VM管理命令行工具 - 支持动态启动、停止虚拟机",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  vmctl start --disk /path/to/system.raw --name myvm    启动VM并挂载指定系统盘
  vmctl start --disk ubuntu.raw --cpu 4 --memory 4G    指定CPU和内存启动
  vmctl stop myvm                                       停止指定VM
  vmctl stop --all                                      停止所有VM
  vmctl list                                            列出运行中的VM
  vmctl logs myvm -f                                    实时查看日志
        """,
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version="vmctl 1.0.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # start 命令
    start_parser = subparsers.add_parser("start", help="启动VM")
    start_parser.add_argument(
        "-d", "--disk",
        metavar="PATH",
        help="系统盘镜像路径 (必须是RAW格式)",
    )
    start_parser.add_argument(
        "-n", "--name",
        metavar="NAME",
        help="VM名称 (默认自动生成)",
    )
    start_parser.add_argument(
        "-c", "--cpu",
        type=int,
        metavar="N",
        help="CPU核心数 (默认: 2)",
    )
    start_parser.add_argument(
        "-m", "--memory",
        metavar="SIZE",
        help="内存大小，如 2G, 512M (默认: 2G)",
    )
    start_parser.add_argument(
        "-s", "--seed",
        metavar="PATH",
        help="seed.iso路径 (用于cloud-init)",
    )
    start_parser.add_argument(
        "-b", "--binary",
        metavar="PATH",
        help="vmstart二进制文件路径",
    )
    start_parser.add_argument(
        "-f", "--foreground",
        action="store_true",
        help="前台运行（不放入后台）",
    )
    start_parser.set_defaults(func=cmd_start)

    # stop 命令
    stop_parser = subparsers.add_parser("stop", help="停止VM")
    stop_parser.add_argument(
        "name",
        nargs="?",
        help="VM名称或PID",
    )
    stop_parser.add_argument(
        "-a", "--all",
        action="store_true",
        help="停止所有VM",
    )
    stop_parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="强制停止 (SIGKILL)",
    )
    stop_parser.set_defaults(func=cmd_stop)

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出运行中的VM")
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="以JSON格式输出",
    )
    list_parser.set_defaults(func=cmd_list)

    # status 命令
    status_parser = subparsers.add_parser("status", help="查看VM状态")
    status_parser.add_argument(
        "name",
        nargs="?",
        help="VM名称",
    )
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="以JSON格式输出",
    )
    status_parser.set_defaults(func=cmd_status)

    # logs 命令
    logs_parser = subparsers.add_parser("logs", help="查看VM日志")
    logs_parser.add_argument(
        "name",
        help="VM名称",
    )
    logs_parser.add_argument(
        "-f", "--follow",
        action="store_true",
        help="实时跟踪日志",
    )
    logs_parser.add_argument(
        "-n", "--lines",
        type=int,
        metavar="N",
        help="显示最后N行 (默认: 50)",
    )
    logs_parser.set_defaults(func=cmd_logs)

    # config 命令
    config_parser = subparsers.add_parser("config", help="管理配置")
    config_parser.add_argument(
        "--show",
        action="store_true",
        help="显示当前配置",
    )
    config_parser.add_argument(
        "--set",
        metavar="KEY=VALUE",
        help="设置配置项",
    )
    config_parser.add_argument(
        "--reset",
        action="store_true",
        help="重置为默认配置",
    )
    config_parser.set_defaults(func=cmd_config)

    # 解析参数
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # 执行对应命令
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
