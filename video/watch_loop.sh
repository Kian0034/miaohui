#!/bin/bash
# 自维持监控：monitor退出后若未通过则重启，最多24小时
cd /Users/ff/miaohui/video
for i in $(seq 1 6); do
  if grep -q '"passed": true' gh_state.json 2>/dev/null && grep -q '"dyn": true' gh_state.json 2>/dev/null; then
    echo "PASSED - actions done, exit" >> gh.log
    break
  fi
  if grep -q '"passed": true' gh_state.json 2>/dev/null && [ $i -ge 4 ]; then
    echo "PASSED but dyn unfinished - exit anyway" >> gh.log
    break
  fi
  echo "wrapper: 启动第${i}轮监控 $(date +%H:%M:%S)" >> gh.log
  python3 bili_monitor.py
done
