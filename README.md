# sovd-lab

纯软件的服务化车辆诊断（SOVD）实验室，提供一个可测试的内存诊断服务模型。它不连接车辆、不依赖硬件，用统一资源路径演示实体发现、故障读取、测量和配置写入。

## 痛点

ISO 17978-3:2026 面向 HPC、传统 ECU 和扩展车辆定义统一诊断 API，但工程团队仍需要在没有整车环境时验证资源路径、能力发现和错误语义。本项目提供确定性本地模型，方便先写客户端和回归测试。

## 使用

    python sovd.py list
    python sovd.py faults powertrain
    python sovd.py measure powertrain.engine_speed
    python sovd.py set powertrain mode sport

这是协议实验室，不是量产 SOVD 服务器或安全网关。

## 许可证

MIT
