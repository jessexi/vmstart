# 开发环境操作系统文件目录结构

## 环境概述

| 项目 | 值 |
|------|-----|
| **操作系统** | Ubuntu 24.04.3 LTS (Noble Numbat) |
| **内核** | gVisor (runsc) 4.4.0 |
| **架构** | x86_64 |
| **容器类型** | Docker + gVisor 沙箱 |
| **总内存** | 21GB |
| **磁盘空间** | 30GB |

---

## 根目录结构 `/`

```
/
├── bin -> usr/bin          # 用户命令 (符号链接)
├── boot/                   # 启动文件 (空)
├── container_info.json     # 容器信息 (只读)
├── dev/                    # 设备文件
├── etc/                    # 系统配置文件
├── home/                   # 用户主目录
├── lib -> usr/lib          # 共享库 (符号链接)
├── lib64 -> usr/lib64      # 64位库 (符号链接)
├── media/                  # 可移动媒体挂载点
├── mnt/                    # 临时挂载点
├── opt/                    # 可选软件包
├── proc/                   # 进程信息虚拟文件系统
├── process_api             # 容器进程API
├── root/                   # root用户主目录
├── run/                    # 运行时数据
├── sbin -> usr/sbin        # 系统命令 (符号链接)
├── srv/                    # 服务数据
├── sys/                    # 系统信息虚拟文件系统
├── tmp/                    # 临时文件
├── usr/                    # 用户程序和数据
└── var/                    # 可变数据
```

---

## `/dev` 设备目录

gVisor 沙箱环境只暴露最小必需设备:

```
/dev/
├── fd -> /proc/self/fd     # 文件描述符
├── full                    # 满设备
├── fuse                    # FUSE 设备
├── net/                    # 网络设备
├── null                    # 空设备
├── ptmx -> pts/ptmx        # 伪终端主设备
├── pts/                    # 伪终端
├── random                  # 随机数生成器
├── shm/                    # 共享内存
├── stderr -> /proc/self/fd/2
├── stdin -> /proc/self/fd/0
├── stdout -> /proc/self/fd/1
├── tty                     # 终端设备
├── urandom                 # 非阻塞随机数
└── zero                    # 零设备
```

**注意**: 无 `/dev/kvm`，不支持硬件虚拟化

---

## `/etc` 配置目录

```
/etc/
├── apt/                    # APT 包管理配置
├── bash.bashrc             # Bash 全局配置
├── ca-certificates/        # CA 证书
├── ca-certificates.conf    # CA 证书配置
├── dbus-1/                 # D-Bus 配置
├── default/                # 服务默认配置
├── dpkg/                   # dpkg 包管理配置
├── environment             # 环境变量
├── fonts/                  # 字体配置
├── group                   # 用户组信息
├── gshadow                 # 组密码信息
├── hostname                # 主机名
├── hosts                   # 主机解析
├── init.d/                 # 启动脚本
├── os-release              # 系统版本信息
├── passwd                  # 用户账户信息
├── shadow                  # 用户密码信息
├── ssh/                    # SSH 配置
├── ssl/                    # SSL/TLS 配置
└── systemd/                # systemd 配置
```

---

## `/usr` 用户程序目录

```
/usr/
├── bin/                    # 用户命令 (~700+ 程序)
│   ├── apt, apt-get        # 包管理
│   ├── bash, sh, zsh       # Shell
│   ├── curl, wget          # 网络工具
│   ├── git, gh             # 版本控制
│   ├── python3, pip        # Python
│   ├── node, npm, bun      # Node.js
│   ├── gcc, g++, clang     # 编译器
│   ├── vim, nano           # 编辑器
│   └── ...
├── include/                # C/C++ 头文件
├── lib/                    # 共享库
├── lib64/                  # 64位共享库
├── libexec/                # 内部可执行文件
├── local/                  # 本地安装的软件
├── sbin/                   # 系统管理命令
├── share/                  # 架构无关数据
└── src/                    # 源代码
```

---

## `/var` 可变数据目录

```
/var/
├── backups/                # 备份文件
├── cache/                  # 缓存数据
│   └── apt/                # APT 缓存
├── lib/                    # 状态信息
│   ├── apt/                # APT 状态
│   ├── dpkg/               # dpkg 数据库
│   └── postgresql/         # PostgreSQL 数据
├── lock -> /run/lock       # 锁文件
├── log/                    # 日志文件
├── mail/                   # 邮件
├── run -> /run             # 运行时数据
├── spool/                  # 队列数据
└── tmp/                    # 临时文件
```

---

## `/proc` 进程信息目录

gVisor 模拟的进程文件系统:

```
/proc/
├── [PID]/                  # 进程目录
│   ├── cgroup              # cgroup 信息
│   ├── cmdline             # 命令行参数
│   ├── environ             # 环境变量
│   ├── fd/                 # 文件描述符
│   ├── mountinfo           # 挂载信息
│   ├── ns/                 # 命名空间
│   └── status              # 进程状态
├── cgroups                 # cgroup 控制器
├── cpuinfo                 # CPU 信息
├── filesystems             # 文件系统类型
├── loadavg                 # 系统负载
├── meminfo                 # 内存信息
├── self -> [current PID]   # 当前进程
├── stat                    # 系统统计
└── sentry-meminfo          # gVisor 内存信息
```

---

## `/sys` 系统信息目录

```
/sys/
├── block/                  # 块设备
├── bus/                    # 总线类型
├── class/                  # 设备类
├── dev/                    # 设备
├── devices/                # 设备树
├── firmware/               # 固件
├── fs/                     # 文件系统
│   └── cgroup/             # cgroup 挂载点
├── kernel/                 # 内核参数
├── module/                 # 内核模块
└── power/                  # 电源管理
```

---

## `/home` 用户目录

```
/home/
└── user/                   # 开发用户目录
    └── vmstart/            # 当前项目目录
```

---

## 文件系统挂载信息

| 挂载点 | 文件系统 | 大小 | 说明 |
|--------|----------|------|------|
| `/` | 9p | 30G | 根文件系统 (通过 9P 协议挂载) |
| `/dev` | tmpfs | 315G | 设备文件系统 |
| `/dev/shm` | tmpfs | 315G | 共享内存 |
| `/proc` | proc | - | 进程信息 |
| `/sys` | sysfs | - | 系统信息 (只读) |
| `/sys/fs/cgroup` | tmpfs | - | cgroup 控制组 |

---

## Cgroup 资源限制

```
/sys/fs/cgroup/
├── cpu/                    # CPU 时间限制
├── cpuacct/                # CPU 使用统计
├── cpuset/                 # CPU 核心绑定
├── devices/                # 设备访问控制
├── job/                    # 作业控制
├── memory/                 # 内存限制
└── pids/                   # 进程数限制
```

---

## 命名空间隔离

| Namespace | 说明 |
|-----------|------|
| `pid` | 进程ID隔离 |
| `mnt` | 挂载点隔离 |
| `net` | 网络栈隔离 |
| `ipc` | 进程间通信隔离 |
| `uts` | 主机名隔离 |
| `user` | 用户/组ID映射 |

---

## 安全特性

- **gVisor Sentry**: 用户空间内核，拦截所有系统调用
- **9P 文件系统**: 通过 Gofer 代理进行文件访问
- **Capabilities 限制**: 移除敏感内核能力
- **设备隔离**: 只暴露最小必需设备
- **只读挂载**: `/sys` 以只读方式挂载
