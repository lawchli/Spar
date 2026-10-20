# Spar

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform: Android](https://img.shields.io/badge/platform-Android-3DDC84?logo=android&logoColor=white)](#requirements)
[![Status: prototype](https://img.shields.io/badge/status-prototype-orange.svg)](#to-do)

**English** | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

Spar is a stereo line-in adapter for Android phones with a 5-pole headphone jack. It records a stereo line-level source, such as a synthesizer or a Eurorack module, through the phone's built-in audio codec, with no USB audio interface, while the headphone output remains available for monitoring.

A standard 4-pole (CTIA/OMTP) jack provides a single microphone input, so line-in adapters for it are limited to mono. A 5-pole jack adds a second microphone contact; Spar feeds the left and right channels into these two inputs.

**Development and test platform:** Sony Xperia XZ1 Compact, LineageOS 23.2 (Android 16), rooted.

## Features

- Stereo line input through the headphone jack, without a USB audio interface
- Low-latency monitoring: the input is looped back to the headphones inside the phone's audio codec, bypassing Android and apps
- Passive input network of four resistors, which can be built on the Spar board or on a breadboard

## Performance

Measured on the breadboard prototype with a Korg NTS-1:

| Item | Value |
|---|---|
| Channels | 2 (stereo), headphone monitoring at the same time |
| Left/right separation | > 40 dB |
| Signal-to-noise ratio | approx. 65 dB |
| ADC gain | 12 (range 0–20, 1.5 dB per step) |
| Peak level, NTS-1 at full volume | approx. −13 dBFS |
| Input network, per channel | 10 kΩ series, 2.2 kΩ to ground |

Measurements of the finished board (THD+N, dynamic range, frequency response) will be published on the [`measurements`](../../tree/measurements) branch.

## Requirements

- An Android phone with a 5-pole headphone jack whose audio codec exposes a stereo (binaural) capture path
- Root access, for the mixer configuration and the capture tools
- Soldering tools, if you build the board yourself

## Repository layout

Each part of the project is developed on its own branch; `main` holds released snapshots.

| Branch | Contents |
|---|---|
| [`software`](../../tree/software) | Phone-side tools, scripts and setup notes |
| [`pcb`](../../tree/pcb) | Board: schematic, layout, fabrication files, BOM |
| [`enclosure`](../../tree/enclosure) | 3D-printed case |
| [`measurements`](../../tree/measurements) | Measurements of the finished device |

## To do

- [ ] Fabricate and assemble PCB Rev D
- [ ] Enclosure for Rev D
- [ ] Measurements on the finished device (THD+N, dynamic range, frequency response)
- [ ] Safe monitoring gain without feedback on the finished board
- [ ] One-step phone setup (Magisk module: start-up service, mixer configuration, recording control)
- [ ] Tests on other phones with a 5-pole jack

## License

[MIT](LICENSE) © LawChli. Third-party code keeps its own license (TinyALSA: BSD-3-Clause).
