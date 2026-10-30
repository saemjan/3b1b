// A tiny test harness: no framework, no globals. One Suite per test program.
//   Suite s("nx_cap");  CHECK(s, 1 + 1 == 2);  return s.done();
#pragma once
#include <cstdio>

struct Suite {
  const char* name;
  int run = 0, failed = 0;
  explicit Suite(const char* n) : name(n) {}
  void check(bool ok, const char* what, const char* file, int line) {
    ++run;
    if (!ok) { ++failed; std::fprintf(stderr, "FAIL %s: %s (%s:%d)\n", name, what, file, line); }
  }
  int done() const {
    std::printf("%-26s %4d checks, %d failed\n", name, run, failed);
    return failed ? 1 : 0;
  }
};
#define CHECK(s, cond) (s).check((cond), #cond, __FILE__, __LINE__)
