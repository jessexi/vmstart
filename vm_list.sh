#!/bin/bash

# 获取所有运行中的 vmstart 进程
VMS=$(ps aux | grep "[v]mstart" | grep -v "grep")

if [ -z "$VMS" ]; then
    echo "没有正在运行的虚拟机。"
    exit 0
fi

echo -e "PID\tSTART_TIME\tCOMMAND"
echo "----------------------------------------------------------------"

# 格式化输出
ps -eo pid,lstart,command | grep "[v]mstart" | while read -r line; do
    pid=$(echo $line | awk '{print $1}')
    # 提取启动时间 (第2到第6列)
    start_time=$(echo $line | awk '{print $2,$3,$4,$5,$6}')
    # 提取命令路径
    cmd=$(echo $line | awk '{print $7}')
    
    echo -e "$pid\t$start_time\t$cmd"
done

echo "----------------------------------------------------------------"
echo "提示: 如需停止虚拟机，可以使用 'kill <PID>' 命令。"
