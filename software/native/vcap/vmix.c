/* vmix: set one multi-value INTEGER mixer control through the phone's own
 * libtinyalsa.so (dlopen), which unlike TinyALSA 2.0 tinymix does not reject
 * values outside the control's declared range. Needed for the tasha IIR band
 * coefficients (declared 0..255, real values are Q28, e.g. 268435456 = 1.0).
 *
 *   vmix <card> <ctl id> <v0> [v1 ...]     prints the values read back */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

struct mixer;
struct mixer_ctl;

int main(int argc, char **argv) {
    if (argc < 4 || argc > 3 + 32) { fprintf(stderr, "usage: vmix card ctl v0 [v1 ...]\n"); return 2; }
    void *lib = dlopen("libtinyalsa.so", RTLD_NOW);
    if (!lib) { fprintf(stderr, "dlopen: %s\n", dlerror()); return 1; }
    struct mixer *(*m_open)(unsigned) = dlsym(lib, "mixer_open");
    struct mixer_ctl *(*m_ctl)(struct mixer *, unsigned) = dlsym(lib, "mixer_get_ctl");
    const char *(*c_name)(struct mixer_ctl *) = dlsym(lib, "mixer_ctl_get_name");
    unsigned (*c_num)(struct mixer_ctl *) = dlsym(lib, "mixer_ctl_get_num_values");
    int (*c_set)(struct mixer_ctl *, const void *, size_t) = dlsym(lib, "mixer_ctl_set_array");
    int (*c_get)(struct mixer_ctl *, unsigned) = dlsym(lib, "mixer_ctl_get_value");
    void (*m_close)(struct mixer *) = dlsym(lib, "mixer_close");
    if (!m_open || !m_ctl || !c_name || !c_num || !c_set || !c_get || !m_close) { fprintf(stderr, "dlsym failed\n"); return 1; }

    struct mixer *mixer = m_open(atoi(argv[1]));
    if (!mixer) { fprintf(stderr, "mixer_open failed\n"); return 1; }
    struct mixer_ctl *ctl = m_ctl(mixer, atoi(argv[2]));
    if (!ctl) { fprintf(stderr, "no control %s\n", argv[2]); return 1; }
    unsigned n = c_num(ctl), given = argc - 3;
    if (given != n) { fprintf(stderr, "%s has %u values, got %u\n", c_name(ctl), n, given); return 2; }
    long vals[32];
    for (unsigned i = 0; i < n; i++) vals[i] = strtol(argv[3 + i], NULL, 0);
    int rc = c_set(ctl, vals, n);
    printf("%s:", c_name(ctl));
    for (unsigned i = 0; i < n; i++) printf(" %d", c_get(ctl, i));
    printf("%s\n", rc ? "  (set failed)" : "");
    m_close(mixer);
    return rc ? 1 : 0;
}
