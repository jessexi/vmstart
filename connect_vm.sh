#!/bin/bash
KEY="./vm_key"
echo "正在等待虚拟机 SSH 服务就绪..."
echo "请确保虚拟机已启动 (运行 ./start_vm.sh)"

# 循环尝试连接，直到成功
while true; do
    # 获取虚拟机 IP (假设只有一个 vmstart 实例)
    # 注意：这里我们使用 arp -a 扫描本地网段，或者盲试常见 IP，
    # 但最简单的方法是让用户手动查 IP，或者我们尝试连接该网段的活跃 IP。
    # 由于 macOS Virtualization framework 的 NAT IP 不固定，
    # 我们先尝试直接连接控制台显示的 IP，或者让脚本只作为登录器。
    
    echo "---------------------------------------------------"
    echo "提示: 请在另一个终端运行 ./start_vm.sh 启动虚拟机。"
    echo "启动后，请查看控制台输出的 IP 地址 (通常是 192.168.64.x)"
    echo "然后运行: ssh -i $KEY ubuntu@<IP地址>"
    echo "---------------------------------------------------"
    echo "或者，我可以尝试为您自动扫描并连接..."
    
    # 简单的 ARP 扫描尝试找到虚拟机 (MAC地址我们在 swift 代码里固定了: 02:00:00:00:00:01)
    VM_IP=$(arp -a | grep "2:0:0:0:0:1" | awk -F'[()]' '{print $2}')
    
    if [ -n "$VM_IP" ]; then
        echo "发现虚拟机 IP: $VM_IP"
        echo "正在尝试连接..."
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=2 -i $KEY ubuntu@$VM_IP
        if [ $? -eq 0 ]; then
            exit 0
        fi
    else
        echo "尚未检测到虚拟机网络 (请等待几秒)..."
    fi
    sleep 3
done
