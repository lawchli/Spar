# TinyALSA provenance

Upstream source (one local patch, see below): https://github.com/tinyalsa/tinyalsa/tree/v2.0.0
Tag object: 1c5fb68ced57d838f2b7ecd0c00bc1fefc9ab60d.
Source archive: https://github.com/tinyalsa/tinyalsa/archive/refs/tags/v2.0.0.tar.gz

Upstream licensing is preserved in tinyalsa-2.0.0/NOTICE and individual source headers.
The binary artifacts link TinyALSA directly; Bionic/libdl remain Android system dependencies.
They target arm64 Android API 28+. tinymix and tinypcminfo were built with official NDK r27c;
tinycap was rebuilt on 2026-10-05 and 2026-10-09 with NDK r30 after the patches below.

Local patch (utils/tinycap.c, capture_sample): upstream stores pcm_readi()'s negative
error return in an unsigned int, then calls fwrite() with ~4.29e9 frames. On this phone
a read error (jack unplugged mid-capture) dumped about 15.5 GB of memory into the WAV and
filled /data. The patched loop stops on any negative return.

Second local patch (2026-10-09, same loop): read one period per pcm_readi() instead of the
whole buffer. Even so, **TinyALSA 2.0.0 capture is unreliable on this 4.4 kernel**: after
about 40 periods the msm-pcm-q6 driver starts returning short / empty DSP buffers that
ALSA counts as full, so the WAV fills with stale data faster than real time (or fails with
EFAULT for non-power-of-two periods). The phone's own libtinyalsa.so does not show this.
Use `vcap` for captures; tinycap is kept only for comparison.

Root cause (found 2026-10-10): a TinyALSA v2.0.0 bug, not the driver. `pcm_state()` calls
`pcm_sync_ptr(pcm, 0)` before every transfer; on ARM status/control cannot be mmapped, so this
is a SYNC_PTR ioctl with flags 0, which makes the kernel overwrite its appl_ptr with the stale
user-space value (0). Capture avail then reaches stop_threshold (10 × buffer) and xruns every
40 periods, and TinyALSA silently re-prepares. Fixed upstream on master by 9b3b4f358a (#206,
2021-05), but v2.0.0 is still the latest release.

## vcap / vmix (native/vcap/)

Own code, no TinyALSA source. Both dlopen the phone's `libtinyalsa.so` (the library the
vendor audio HAL uses) at run time:

- `vcap out.raw card dev ch rate period count seconds` — raw S16_LE capture, stops after
  the requested frames or the first error. Holds the `xz1vcap` kernel wakelock while
  capturing (without it, screen-off suspend caused silent overruns and ~30% data loss) and
  warns when the capture took clearly longer than real time. Verified 20 / 60 / 120 s stereo 48 kHz with
  960×4 and 2048×4: wall time equals capture time, every block unique.
- `vmix card ctl v0 [v1 ...]` — sets a multi-value INTEGER control with
  mixer_ctl_set_array. TinyALSA 2.0 tinymix range-checks against the declared range and
  refuses the tasha IIR Q28 coefficients (declared 0..255), while still exiting 0.
Cross-compilation does not establish that this ROM's ALSA ioctls or capture routes work.

This tinymix uses `tinymix -D 0 contents` and `tinymix -D 0 get NAME`.
Do not assume the older vendor tinymix command syntax.
No mixer workaround is supplied without actual route evidence.
