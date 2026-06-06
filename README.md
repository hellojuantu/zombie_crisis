# 僵尸危机

一个轻量的多人联机恐怖撤离射击原型。服务端权威模拟玩家、僵尸、子弹、任务物、撤离点和关卡；前端负责输入预测、插值、HUD 和 Canvas 渲染。

## 运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 server_asgi.py
```

打开：

```text
http://localhost:8080/
```

局域网联机时，让朋友访问你的局域网 IP：

```text
http://你的局域网IP:8080/
```

## 操作

- WASD：移动
- 鼠标：瞄准
- 左键：开火
- 空格 / Shift：冲刺

## 玩法循环

- 关卡推进：每一关生成不同迷宫，只有完成撤离条件并读条成功才进入下一关
- 收集任务：保险丝主要在迷宫里找，病毒样本和门禁卡需要击杀特定感染体掉落
- 多撤离点：每关有多个撤离点，不同撤离点要求不同任务物组合
- 恐怖探索：撤离点需要靠近后才显形，HUD 会显示缺什么和哪个出口可撤
- 游戏导演：低频检查战场热度，把远离玩家的僵尸重新拉回压力圈，减少空场断档
- 僵尸避障：僵尸遇到迷宫墙体会选边绕行，不再只会直线撞墙
- 连杀奖励：连杀 10 获得短速射，连杀 20 获得短三连发，连杀 30 获得短护盾
- 精英压力：波次会逐步解锁爬行者、重型、毒性、装甲、跳扑、尖啸、爆裂体
- 特殊行为：跳扑怪会短距离爆发，尖啸怪会鼓舞附近尸群，爆裂体死亡后会范围爆炸
- Boss 节点：每 5 关出现巨型感染体，形成阶段高潮和高价值掉落来源
- 全服榜：服务端下发 top 8，前端不再用视野内玩家冒充全服排行

## 架构

- `server_game/`：服务端权威模拟，不包含浏览器或渲染逻辑
- `server_asgi.py`：ASGI + Socket.IO 生产入口
- `static/js/game/`：前端游戏主循环、渲染、HUD、特效
- `static/js/protocol.js`：紧凑快照协议解码
- `tools/load_test.py`：Socket.IO 压测脚本

## 测试

```bash
python3 -m unittest discover -s tests -v
node tests/test_protocol.js
node tests/test_prediction.js
node tests/test_interpolation.js
node tests/test_camera.js
node tests/test_timing.js
node tests/test_netcode.js
```

## 压测

```bash
python3 tools/load_test.py --clients 100 --duration 10 --ramp 0.01 --input-interval 0.066 --shoot-duty 0.85
```

当前优化重点：

- WebSocket only，避免轮询退化
- 服务端权威，客户端预测与插值
- AOI 视野裁剪，减少 100 人同步包大小
- 网络快照 16Hz，服务端模拟 30Hz，兼顾局域网多人压力和移动平滑度
- 高频事件按附近玩家定向发送
- HUD 显示 Ping、FPS、服务端 tick/sync 指标
