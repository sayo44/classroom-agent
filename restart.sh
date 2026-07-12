#!/bin/bash
# 课堂智能体一键重启：停掉占用 8000 端口的旧进程，再后台启动服务
# 用法：bash restart.sh   （可在任意目录运行，脚本会自动切到自身所在目录）

cd "$(dirname "$0")" || exit 1

PORT=8000

echo "==> 停止占用 ${PORT} 端口的旧服务…"
PIDS=$(lsof -ti tcp:${PORT} 2>/dev/null || true)
if [ -n "$PIDS" ]; then
  kill -9 $PIDS 2>/dev/null || true
  echo "    已停止旧进程: $PIDS"
else
  echo "    当前没有旧进程在跑（端口空闲）"
fi

# 等端口释放
sleep 1

echo "==> 后台启动服务…"
nohup venv/bin/python run.py > server.log 2>&1 &
NEW_PID=$!
echo "    新进程 PID: $NEW_PID"

# 等几秒确认是否起来
sleep 3
if lsof -ti tcp:${PORT} >/dev/null 2>&1; then
  echo "==> 启动成功"
  echo "    访问: http://127.0.0.1:${PORT}/c/congcong"
  echo "    日志: server.log"
else
  echo "==> 启动失败，请查看 server.log"
  exit 1
fi
