/* Tiny test harness for the C17 kernel: no framework, no globals. One CosSuite per test program. */
#ifndef C17_CHECK_H
#define C17_CHECK_H
#include <stdio.h>

typedef struct CosSuite {
  const char *name;
  int run;
  int failed;
} CosSuite;

#define CK(s, cond)                                                              \
  do {                                                                           \
    (s)->run++;                                                                  \
    if (!(cond)) {                                                               \
      (s)->failed++;                                                             \
      fprintf(stderr, "FAIL %s: %s (%s:%d)\n", (s)->name, #cond, __FILE__, __LINE__); \
    }                                                                            \
  } while (0)

static inline int suite_done(const CosSuite *s) {
  printf("%-26s %5d checks, %d failed\n", s->name, s->run, s->failed);
  return s->failed ? 1 : 0;
}
#endif
