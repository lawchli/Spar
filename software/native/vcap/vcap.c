/* vcap: minimal raw PCM capture through the phone's own libtinyalsa.so
 * (the library the vendor audio HAL uses), loaded with dlopen, to compare
 * against the bundled TinyALSA 2.0.0 tinycap.
 *
 *   vcap <out.raw> <card> <device> <channels> <rate> <period_size> <period_count> <seconds>
 *
 * Writes raw S16_LE interleaved frames. Stops after <seconds> of frames or on
 * the first read error, so it can never write more than requested.
 *
 * Holds a kernel wakelock while capturing: with the screen off the phone
 * otherwise suspends between periods and the old libtinyalsa silently
 * recovers from the overruns, losing about 30% of the audio (2026-10-09).
 * Warns when the capture took clearly longer than real time. */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

struct pcm;
/* Old tinyalsa layout; trailing fields stay zero. */
struct pcm_config {
    unsigned int channels, rate, period_size, period_count;
    int format; /* PCM_FORMAT_S16_LE = 0 */
    unsigned int start_threshold, stop_threshold, silence_threshold;
    unsigned int silence_size, avail_min;
    unsigned int pad[8];
};
#define PCM_IN 0x10000000

static void wakelock(const char *file) {
    FILE *f = fopen(file, "w");
    if (!f) { fprintf(stderr, "warning: cannot open %s (not root?)\n", file); return; }
    fputs("xz1vcap", f);
    fclose(f);
}

static double now(void) {
    struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec / 1e9;
}

int main(int argc, char **argv) {
    if (argc != 9) { fprintf(stderr, "usage: vcap out card dev ch rate period count seconds\n"); return 2; }
    void *lib = dlopen("libtinyalsa.so", RTLD_NOW);
    if (!lib) { fprintf(stderr, "dlopen: %s\n", dlerror()); return 1; }
    struct pcm *(*p_open)(unsigned, unsigned, unsigned, struct pcm_config *) = dlsym(lib, "pcm_open");
    int (*p_ready)(struct pcm *) = dlsym(lib, "pcm_is_ready");
    int (*p_read)(struct pcm *, void *, unsigned) = dlsym(lib, "pcm_read");
    const char *(*p_err)(struct pcm *) = dlsym(lib, "pcm_get_error");
    int (*p_close)(struct pcm *) = dlsym(lib, "pcm_close");
    if (!p_open || !p_ready || !p_read || !p_err || !p_close) { fprintf(stderr, "dlsym failed\n"); return 1; }

    struct pcm_config cfg; memset(&cfg, 0, sizeof(cfg));
    cfg.channels = atoi(argv[4]); cfg.rate = atoi(argv[5]);
    cfg.period_size = atoi(argv[6]); cfg.period_count = atoi(argv[7]);
    double seconds = atof(argv[8]);
    if (seconds <= 0 || seconds > 600) { fprintf(stderr, "seconds must be 0..600\n"); return 2; }

    struct pcm *pcm = p_open(atoi(argv[2]), atoi(argv[3]), PCM_IN, &cfg);
    if (!pcm || !p_ready(pcm)) { fprintf(stderr, "pcm_open: %s\n", pcm ? p_err(pcm) : "null"); return 1; }
    FILE *f = fopen(argv[1], "wb");
    if (!f) { perror("fopen"); return 1; }

    wakelock("/sys/power/wake_lock");
    unsigned bytes = cfg.period_size * cfg.channels * 2;
    char *buf = malloc(bytes);
    unsigned long long want = (unsigned long long)(seconds * cfg.rate), got = 0;
    unsigned errors = 0;
    double t0 = now();
    while (got < want) {
        if (p_read(pcm, buf, bytes) != 0) {
            fprintf(stderr, "pcm_read error after %llu frames: %s\n", got, p_err(pcm));
            errors++;
            break;
        }
        fwrite(buf, 1, bytes, f);
        got += cfg.period_size;
    }
    double wall = now() - t0, expect = (double)got / cfg.rate;
    printf("frames=%llu wall=%.3f errors=%u\n", got, wall, errors);
    if (wall > expect * 1.02 + 0.2)
        fprintf(stderr, "warning: took %.1f s for %.1f s of audio; overruns likely dropped data\n", wall, expect);
    fclose(f); free(buf); p_close(pcm);
    wakelock("/sys/power/wake_unlock");
    return errors ? 1 : 0;
}
