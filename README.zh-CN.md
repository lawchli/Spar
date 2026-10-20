# Spar

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform: Android](https://img.shields.io/badge/platform-Android-3DDC84?logo=android&logoColor=white)](#运行条件)
[![Status: prototype](https://img.shields.io/badge/status-prototype-orange.svg)](#待办)

[English](README.md) | **简体中文** | [日本語](README.ja.md)

Spar 是面向五极耳机孔安卓手机的立体声线路输入转接器。它通过手机内置的音频编解码器录制合成器、Eurorack 模块等立体声线路信号，不需要 USB 声卡；录音的同时，耳机输出仍可用于监听。

标准四极（CTIA/OMTP）耳机孔只有一路麦克风输入，因此现有的线路输入转接只能录单声道。五极耳机孔多出第二个麦克风触点，Spar 将左右声道分别接入这两路输入。

**开发与测试平台：** Sony Xperia XZ1 Compact，LineageOS 23.2（Android 16），已 root。

## 特点

- 经耳机孔录制立体声线路输入，无需 USB 声卡
- 低延迟监听：输入信号在手机音频编解码器芯片内部送回耳机，不经过安卓系统和应用
- 无源输入网络，仅四颗电阻，可做在 Spar 电路板上，也可搭在面包板上

## 性能

面包板原型配 Korg NTS-1 实测：

| 项目 | 数值 |
|---|---|
| 声道 | 双声道（立体声），可同时耳机监听 |
| 左右分离 | > 40 dB |
| 信噪比 | 约 65 dB |
| ADC 增益 | 12（范围 0–20，每档 1.5 dB） |
| NTS-1 音量开满时的峰值 | 约 −13 dBFS |
| 输入网络（每声道） | 10 kΩ 串联，2.2 kΩ 对地 |

成品板的测量结果（THD+N、动态范围、频率响应）将发布在 [`measurements`](../../tree/measurements) 分支。

## 运行条件

- 带五极耳机孔、且音频编解码器提供立体声（binaural）录音路径的安卓手机
- root 权限（用于 mixer 配置和录音工具）
- 自行制作电路板需要焊接工具

## 仓库结构

项目的每个部分在各自的分支上开发，`main` 只存放发布过的快照。

| 分支 | 内容 |
|---|---|
| [`software`](../../tree/software) | 手机端工具、脚本和配置说明 |
| [`pcb`](../../tree/pcb) | 电路板：原理图、布局、生产文件、BOM |
| [`enclosure`](../../tree/enclosure) | 3D 打印外壳 |
| [`measurements`](../../tree/measurements) | 成品的测量结果 |

## 待办

- [ ] PCB Rev D 打样与装配
- [ ] 适配 Rev D 的外壳
- [ ] 成品测量（THD+N、动态范围、频率响应）
- [ ] 在成品板上确定不啸叫的安全监听增益
- [ ] 手机端一键配置（Magisk 模块：开机服务、mixer 配置、录音控制）
- [ ] 在其他五极耳机孔手机上测试

## 许可

[MIT](LICENSE) © LawChli。第三方代码保留各自的许可（TinyALSA：BSD-3-Clause）。
