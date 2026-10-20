# Mono line input through the headset mic contact

Result of v0.2: a line-level source (tested with a Korg NTS-1) is detected as a headset microphone and records cleanly through the phone's wired-headset input. This is the mono groundwork for the stereo version.

## How the phone decides a mic is present

The headset detection (MBHC, in the WCD9335 codec driver `wcd-mbhc-v2.c`) looks at the **DC voltage on the mic contact** while it applies mic bias (1.8 V, raised to 2.75 V during detection):

| DC on the mic contact | Kernel decision |
|---|---|
| about 0.5–1.6 V (a suitable DC load) | HEADSET: microphone present |
| too low (a source output connected directly, low impedance) | button press or headphones without mic |
| too high (DC open, e.g. only a coupling capacitor) | extension cable / line-out, mic not enabled |

So a line output plugged straight into the mic contact is not detected as a microphone: its low output impedance pulls the voltage into the button range. A capacitor alone does not help either, because the contact then looks open.

Relevant parameters on the test phone (from the device tree and the matching kernel source): mic bias 1800 mV, `v_hs_max` 1600 mV, highest button threshold 500 mV, `linein_th` 5000 Ω, jack type `6-pole-jack`. Other phones may use different values.

## Circuit

```text
source (mono, or L only) ──[ 47 kΩ ]──┬── MIC (CTIA sleeve)
                                      │
                                  [ 2.2 kΩ ]
                                      │
source ground ────────────────────────┴── GND (CTIA ring 2)
```

- **2.2 kΩ to ground** gives the mic contact the DC load the detection expects. Together with the phone's bias resistor it puts the voltage inside the 0.5–1.6 V window. Detection succeeded on the first insertion and stayed stable.
- **47 kΩ in series** brings line level down towards mic level (about −33 dB) and keeps the source from loading the bias. It does not affect detection and can be changed to suit the source; later versions use 10 kΩ.
- Do not join a stereo source's L and R outputs together.

## Results

Detection: the kernel reports a HEADSET insertion, with `SW_HEADPHONE_INSERT`, `SW_MICROPHONE_INSERT` and `SW_JACK_PHYSICAL_INSERT` set, and Android lists a wired headset mic (type 3).

Recordings: 48 kHz mono, strict routing, no dropped frames and no clipping. Each row compares the level with the synth playing and stopped.

| NTS-1 volume | Source | Playing | Stopped | Difference |
|---|---|---|---|---|
| about 1/4 | MIC | −45 dBFS | −65 dBFS | about 20 dB |
| higher | MIC | −38.5 dBFS | −62 dBFS | about 24 dB |
| maximum | MIC | −32.3 dBFS | −66.2 dBFS | about 34 dB |
| maximum | UNPROCESSED | −51.4 dBFS | −83.5 dBFS | about 32 dB |

- The **MIC** source adds the vendor noise reduction. It is about 19 dB louder than UNPROCESSED, but signal and noise rise together, so the difference is digital gain or processing. It also produces a short spike at every note onset.
- **UNPROCESSED** has no vendor effects attached and is the better choice for instruments. Android reports the source as unsupported, yet this ROM accepts it. With 47 kΩ the signal needs about 20 dB more level, which the smaller series resistor in later versions provides.

## Recording a test

1. Find the current wired mic ID with the Probe app (it changes on every reconnect).
2. Start a 30 s strict recording:

   ```bash
   adb shell am start -S -n org.xz1.audio/.MainActivity --ei device_id <ID> --es source UNPROCESSED --ei seconds 30 --ez strict true --ez auto true
   ```

3. Alternate the source between playing and stopped every 5 s, then check the envelope with `scripts/analyze_wav.py`. Do not touch the screen while recording: the app restarts the recording if interrupted.

## Side finding: USB input channel masks

On this ROM, the vendor `audio_policy_configuration.xml` declares the USB Device In and USB Headset In profiles with output channel masks (`AUDIO_CHANNEL_OUT_MONO/STEREO`) instead of input masks. This breaks input enumeration for USB audio devices. Changing the four profiles to `AUDIO_CHANNEL_IN_MONO/STEREO` fixed USB recording in a temporary bind-mount test. The modified vendor file is not distributed here.

## Towards stereo

The kernel reports a stereo microphone (`SND_JACK_STEREO_MICROPHONE`) when:

1. the plug is first detected as a HEADSET (as above);
2. the extra microphone contact of a 5-pole plug (pole 3 from the tip: AMIC3, biased by MIC BIAS3) is detected as an ANC microphone; and
3. the left headphone impedance is above 5000 Ω.

Each microphone pole can therefore take the same series + load network. The open question at this point was that LineageOS ignores the stereo-mic switch event (SW 0x12), so the framework registers only a mono wired mic. v0.3 deals with that.
