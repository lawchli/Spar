# Stereo capture on the 5-pole jack

Result of v0.3: two independent line inputs recorded through the two microphone contacts of a 5-pole jack, with headphone monitoring at the same time. Tested on an Xperia XZ1 Compact (WCD9335 codec) running LineageOS 23.2 (Android 16).

## 5-pole pinout

Counted from the tip:

| Pole | Function | Spar connection |
|---|---|---|
| 1 | Left headphone | headphone jack tip |
| 2 | Right headphone | headphone jack ring |
| 3 | Left microphone (AMIC3 / ADC3) | line-in left, through the input network |
| 4 | Common ground | both jacks' sleeves |
| 5 | Right microphone (AMIC2 / ADC2) | line-in right, through the input network |

Each microphone pole gets the same network as the mono version: a series resistor and 2.2 kΩ to ground.

## Detection and the Android 16 crash

With a DC load on both microphone poles, the kernel detects the extra microphone contact (pole 3, AMIC3, biased by MIC BIAS3) and reports the extra switch event `SW 0x12`. Pole 5 is the standard headset microphone contact (the CTIA sleeve). Depending on the left headphone impedance it classifies the plug as:

| Left headphone impedance | Kernel plug type |
|---|---|
| ≤ 5 kΩ (headphones connected) | ANC_HEADPHONE |
| > 5 kΩ (open or high impedance) | STEREO_MICROPHONE |

Both types work for capture.

On Android 16, the input framework aborts `system_server` when it receives a switch code above `SW_MAX` (`EventHub: received invalid EV_SW event code: 18`), so plugging in causes a soft reboot. `jackguard` works around this:

- it grabs the codec's `Headset Jack` input device exclusively (`EVIOCGRAB`);
- it republishes it through `uinput` as `jackguard Headset Jack`, forwarding switch codes 0x00–0x11 and dropping 0x12/0x13;
- stopping it releases the device; no system file is changed.

Android then treats the plug as an ordinary wired headset; it does not know about the second microphone. Capture therefore goes around the framework, directly to the ALSA device.

## Capture

`scripts/binaural-mixer.sh apply` sets the vendor `binaural-mic` route without its monitoring part:

- ADC3 → DEC7 → SLIM TX7 → channel 0 (left)
- ADC2 → DEC8 → SLIM TX8 → channel 1 (right)
- `SLIM_0_TX` two channels, `MultiMedia1 Mixer SLIM_0_TX` on, so PCM 0 delivers stereo
- `Audio Stream Capture 0 App Type Cfg` = `69938 147 48000 3`. This is the value the HAL sets for its own headset-mic capture. Without it the ADSP refuses to start the SLIMBUS port (`backend prepare failed -131`).

Every control ID is checked against its name before writing; on a mismatch the script aborts without writing anything. `restore` writes back the idle values.

Record with `vcap`, not `tinycap`:

```bash
adb shell su -c '/data/local/tmp/xz1audio/vcap /data/local/tmp/take.raw 0 0 2 48000 960 4 30'
#                                             out                    card dev ch rate period count seconds
```

The output is raw S16_LE, interleaved stereo. TinyALSA 2.0.0's `tinycap` silently loses data on this kernel: it calls `SYNC_PTR` with flags 0 before every read, which resets the kernel's application pointer and causes an xrun every 40 periods. This is fixed on TinyALSA master but not in any release; see [native/PROVENANCE.md](../native/PROVENANCE.md). `vcap` uses the phone's own `libtinyalsa.so`, holds a wake lock while recording (screen-off suspend otherwise drops data) and warns when a capture takes longer than real time.

## Channel check

- Disconnecting one input drops that channel to the noise floor while the other is unaffected: at least 28–33 dB isolation, limited by noise.
- With a ping-pong delay, each echo appears only on its own side, more than 40 dB above the other channel. So the inputs are independent and not swapped.

## Monitoring

`scripts/binaural-mixer.sh monitor-on` adds the vendor `binaural-mic-monitoring` route: DEC7 → IIR0 → RX INT1 (left headphone) and DEC8 → IIR1 → RX INT2 (right headphone). The loop stays inside the codec: the signal is digitised once and sent back to the headphones without passing through Android or an app, so latency is very low. `monitor-off` removes it.

The IIR filters must hold pass-through coefficients (`268435456 0 0 0 0` per band, 1.0 in Q28). On the test phone they were once found zeroed, which mutes monitoring completely. TinyALSA 2.0's `tinymix` rejects these values (it checks the declared range 0–255 but still exits 0), so the script writes them with `vmix` through the phone's `libtinyalsa.so`.

## Gain and series resistor

- `ADC2/ADC3 Volume` is the codec's analog gain, from 0 to 20 in 1.5 dB steps (30 dB in total).
- `DEC7/DEC8 Volume` is digital gain (84 = 0 dB). It does not improve signal-to-noise ratio; keep it at 0 dB and normalise afterwards.
- The noise floor barely depends on the series resistor, so most of it comes from the phone's side (mic bias and codec front end). A smaller series resistor therefore raises the signal-to-noise ratio by as much as it raises the level.

Measured with a Korg NTS-1 at full volume, monitoring off:

| Series resistor | ADC | RMS (dBFS) | Peak (dBFS) | SNR L / R (dB) |
|---|---|---|---|---|
| 47 kΩ | 20 | −28.5 | −13.1 | 53.0 / 54.1 |
| 20 kΩ | 20 | −21.2 | −5.9 | 60.4 / 61.4 |
| 10 kΩ | 17 | −20.2 | −5.3 | 65.7 / 66.2 |
| 10 kΩ | 14 | −24.7 | −9.9 | 65.3 / 65.5 |
| 10 kΩ | 11 | −29.2 | −14.4 | 63.9 / 64.5 |

Detection was unchanged at 20 kΩ and 10 kΩ, with no button events while recording: the series resistor does not change the DC on the mic contact.

**Chosen: 10 kΩ series, 2.2 kΩ to ground, ADC 12.** This gives a peak of about −13 dBFS and an SNR of about 64.5 dB with the NTS-1 at full volume (interpolated from ADC 11 and 14). Aim for peaks of −12 to −6 dBFS. Hotter sources such as Eurorack (±5 V) should start at a low output level: a large negative swing on the mic contact can reach the button-detection range.

`scripts/level-test.sh` repeats this measurement at several ADC gains and logs any jack or button events during the run.

## Monitoring feedback

With monitoring on and high gain, a breadboard build oscillated at about 3.2 kHz from ADC 14 upwards. The likely cause is the shared ground on pole 4 between headphone current and the microphone inputs. Keep the ground short and thick, joined at a single point.

`scripts/howl-sweep.sh` finds the onset safely: it raises the monitoring gain step by step, records 2 s per step, mutes the monitor between steps and stops at the first clear tone. Use headphones plugged in but not worn, and the source connected but silent. A safe monitoring gain is the onset minus 6 dB. This still has to be measured on the finished board.

## Setup summary

```bash
./native/build.sh && ./native/jackguard/build.sh      # or use the release binaries
./scripts/install-native.sh                            # tinymix, tinypcminfo, tinycap, vcap, vmix
adb push artifacts/arm64-v8a/jackguard /data/local/tmp/xz1audio/
adb shell su -c '/data/local/tmp/xz1audio/jackguard' & # keep running; start before plugging in
./scripts/binaural-mixer.sh apply
./scripts/binaural-mixer.sh monitor-on                 # optional
# record with vcap (see above), then:
./scripts/binaural-mixer.sh monitor-off
./scripts/binaural-mixer.sh restore
```

All changes are temporary: the mixer returns to normal with `restore` or a reboot, and stopping `jackguard` releases the input device.
