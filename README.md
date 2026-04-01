# 🛩️ Airplane Shooter - 打飞机游戏

> 一个使用 Pygame 开发的竖版飞行射击游戏

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Pygame](https://img.shields.io/badge/Pygame-2.0+-green.svg)
![MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 🎮 游戏说明

- **方向键 / WASD**：控制飞机移动
- **空格键**：发射子弹
- **P 键**：暂停游戏
- **ESC**：退出游戏

## 🚀 运行方法

### 方式一：直接运行（推荐）

```bash
# 安装依赖
pip install pygame

# 运行游戏
python airplane_shooter.py
```

### 方式二：双击运行（Windows）

直接双击 `start.bat` 文件即可启动游戏。

## 📁 文件说明

```
airplane-shooter/
├── airplane_shooter.py   # 游戏主程序
├── requirements.txt      # Python 依赖
├── README.md             # 说明文档
└── start.bat             # Windows 一键启动脚本
```

## 🎯 游戏特性

- ✅ 流畅的飞机操控
- ✅ 连续发射子弹系统
- ✅ 多种敌机类型
- ✅ 爆炸特效动画
- ✅ 分数实时统计
- ✅ 难度递增机制
- ✅ 飞机血量系统
- ✅ 音效支持

## 🏆 游戏规则

- 躲避或击毁迎面而来的敌机
- 每击毁一架敌机得 **10 分**
- 难度随分数增加而提升（敌机速度加快）
- 被敌机或敌机子弹击中会掉血
- 血量耗尽，游戏结束
- 挑战最高分！
