# TinyALSA provenance

Unmodified upstream source: https://github.com/tinyalsa/tinyalsa/tree/v2.0.0
Tag object: 1c5fb68ced57d838f2b7ecd0c00bc1fefc9ab60d.
Source archive: https://github.com/tinyalsa/tinyalsa/archive/refs/tags/v2.0.0.tar.gz

Upstream licensing is preserved in tinyalsa-2.0.0/NOTICE and individual source headers.
The binary artifacts link TinyALSA directly; Bionic/libdl remain Android system dependencies.
They target arm64 Android API 28+, built with official NDK r27c.
Cross-compilation does not establish that this ROM's ALSA ioctls or capture routes work.

This tinymix uses `tinymix -D 0 contents` and `tinymix -D 0 get NAME`.
Do not assume the older vendor tinymix command syntax.
No mixer workaround is supplied without actual route evidence.
