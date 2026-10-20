// jackguard: grab the WCD "Headset Jack" input device and re-publish it via
// uinput without switch codes above SW_MAX. Android 16 EventHub aborts
// system_server on EV_SW code 0x12 (the 5-pole / extra-mic switch).
//
// Temporary debugging aid: run as root, stop with Ctrl-C / SIGTERM, which
// releases the grab and removes the virtual device. Every event from the real
// device (including the dropped ones) is printed to stdout.
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <linux/uinput.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

#define SRC_NAME "msm8998-tasha-snd-card Headset Jack"
#define DST_NAME "jackguard Headset Jack"
#define BITS_LONG (sizeof(unsigned long) * 8)
#define TEST_BIT(b, a) (((a)[(b) / BITS_LONG] >> ((b) % BITS_LONG)) & 1UL)

static volatile sig_atomic_t stop;
static void on_signal(int sig) { (void)sig; stop = 1; }

static int find_source(char *path, size_t len) {
  DIR *d = opendir("/dev/input");
  struct dirent *e;
  if (!d) return -1;
  while ((e = readdir(d))) {
    char p[64], name[256] = "";
    int fd;
    if (strncmp(e->d_name, "event", 5)) continue;
    snprintf(p, sizeof p, "/dev/input/%s", e->d_name);
    fd = open(p, O_RDONLY);
    if (fd < 0) continue;
    ioctl(fd, EVIOCGNAME(sizeof name - 1), name);
    if (!strcmp(name, SRC_NAME)) {
      closedir(d);
      snprintf(path, len, "%s", p);
      return fd;
    }
    close(fd);
  }
  closedir(d);
  return -1;
}

static void log_event(const char *tag, const struct input_event *ev) {
  struct timespec ts;
  clock_gettime(CLOCK_REALTIME, &ts);
  struct tm tm;
  localtime_r(&ts.tv_sec, &tm);
  printf("%02d:%02d:%02d.%03ld %s type=%d code=0x%02x value=%d\n", tm.tm_hour,
         tm.tm_min, tm.tm_sec, ts.tv_nsec / 1000000, tag, ev->type, ev->code,
         ev->value);
  fflush(stdout);
}

static int emit(int fd, int type, int code, int value) {
  struct input_event ev;
  memset(&ev, 0, sizeof ev);
  ev.type = type;
  ev.code = code;
  ev.value = value;
  return write(fd, &ev, sizeof ev) == sizeof ev ? 0 : -1;
}

int main(void) {
  char path[64];
  unsigned long swbits[SW_CNT / BITS_LONG + 2], swstate[SW_CNT / BITS_LONG + 2];
  unsigned long allsw[KEY_MAX / BITS_LONG + 1];
  struct uinput_user_dev udev;
  int src, dst, sw;

  src = find_source(path, sizeof path);
  if (src < 0) { fprintf(stderr, "jackguard: %s not found\n", SRC_NAME); return 1; }

  memset(allsw, 0, sizeof allsw);
  ioctl(src, EVIOCGBIT(EV_SW, sizeof allsw), allsw);
  memset(swbits, 0, sizeof swbits);
  memcpy(swbits, allsw, sizeof swbits);

  dst = open("/dev/uinput", O_WRONLY | O_NONBLOCK);
  if (dst < 0) { perror("jackguard: /dev/uinput"); return 1; }
  ioctl(dst, UI_SET_EVBIT, EV_SW);
  for (sw = 0; sw <= SW_MAX; sw++)
    if (TEST_BIT(sw, swbits)) ioctl(dst, UI_SET_SWBIT, sw);
  for (sw = SW_MAX + 1; sw < 0x20; sw++)
    if (TEST_BIT(sw, allsw)) printf("jackguard: will drop source switch 0x%02x\n", sw);

  memset(&udev, 0, sizeof udev);
  snprintf(udev.name, UINPUT_MAX_NAME_SIZE, "%s", DST_NAME);
  udev.id.bustype = BUS_VIRTUAL;
  udev.id.vendor = 0x5a31;
  udev.id.product = 0x0001;
  udev.id.version = 1;
  // Kernel 4.4 predates UI_DEV_SETUP; use the legacy uinput_user_dev write.
  if (write(dst, &udev, sizeof udev) != sizeof udev || ioctl(dst, UI_DEV_CREATE) < 0) {
    perror("jackguard: uinput create");
    return 1;
  }

  if (ioctl(src, EVIOCGRAB, 1) < 0) { perror("jackguard: EVIOCGRAB"); ioctl(dst, UI_DEV_DESTROY); return 1; }
  signal(SIGINT, on_signal);
  signal(SIGTERM, on_signal);
  signal(SIGHUP, on_signal);
  printf("jackguard: grabbed %s (%s), forwarding to \"%s\"\n", path, SRC_NAME, DST_NAME);

  usleep(200000);
  memset(swstate, 0, sizeof swstate);
  {
    unsigned long st[KEY_MAX / BITS_LONG + 1];
    memset(st, 0, sizeof st);
    ioctl(src, EVIOCGSW(sizeof st), st);
    for (sw = 0; sw < 0x20; sw++)
      if (TEST_BIT(sw, allsw)) printf("jackguard: initial switch 0x%02x = %lu\n", sw, TEST_BIT(sw, st));
    for (sw = 0; sw <= SW_MAX; sw++)
      if (TEST_BIT(sw, swbits)) emit(dst, EV_SW, sw, (int)TEST_BIT(sw, st));
    emit(dst, EV_SYN, SYN_REPORT, 0);
  }
  fflush(stdout);

  while (!stop) {
    struct input_event ev;
    ssize_t n = read(src, &ev, sizeof ev);
    if (n < 0) { if (errno == EINTR) continue; perror("jackguard: read"); break; }
    if (n != sizeof ev) continue;
    if (ev.type == EV_SW && ev.code > SW_MAX) { log_event("DROP", &ev); continue; }
    if (ev.type != EV_SYN) log_event("FWD ", &ev);
    emit(dst, ev.type, ev.code, ev.value);
  }

  ioctl(src, EVIOCGRAB, 0);
  ioctl(dst, UI_DEV_DESTROY);
  printf("jackguard: released\n");
  return 0;
}
