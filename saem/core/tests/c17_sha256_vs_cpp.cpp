// The C17 kernel's SHA-256 against the C++ engine's SHA-256 (core/src/sha256.hpp), written separately and used for the engine fingerprint.
// Two implementations in two languages must give the same digest for every length around the block boundaries and for random data,
// one shot and fed in uneven pieces. Built and run by tools/check_c17.py.
#include <cstdint>
#include <cstdio>
#include <string>

#include "../src/sha256.hpp"
extern "C" {
#include "cos_sha256.h"
}

static uint64_t g_state = 0x243F6A8885A308D3ull;  // test-only generator; xorshift64*
static uint64_t next() {
  g_state ^= g_state >> 12;
  g_state ^= g_state << 25;
  g_state ^= g_state >> 27;
  return g_state * 2685821657736338717ull;
}

static std::string hex_of(const uint8_t* d) {
  char out[65];
  cos_hex(d, 32, out);
  return std::string(out);
}

int main() {
  int checks = 0, bad = 0;
  // every length 0..700 (covers 55/56/63/64/65/119/120/127/128 boundaries), one shot and split at a random point
  for (size_t n = 0; n <= 700; ++n) {
    std::string msg(n, '\0');
    for (size_t i = 0; i < n; ++i) msg[i] = static_cast<char>(next() & 0xFF);
    const std::string want = saem::sha256_hex(msg);
    uint8_t d[32];
    cos_sha256(msg.data(), n, d);
    ++checks;
    if (hex_of(d) != want) { ++bad; std::fprintf(stderr, "one-shot mismatch at length %zu\n", n); }
    const size_t cut = n == 0 ? 0 : static_cast<size_t>(next() % (n + 1));
    CosSha256 c;
    cos_sha256_init(&c);
    cos_sha256_update(&c, msg.data(), cut);
    cos_sha256_update(&c, msg.data() + cut, n - cut);
    cos_sha256_final(&c, d);
    ++checks;
    if (hex_of(d) != want) { ++bad; std::fprintf(stderr, "split mismatch at length %zu cut %zu\n", n, cut); }
  }
  // some long random messages fed byte by byte in uneven bursts
  for (int round = 0; round < 20; ++round) {
    const size_t n = 1000 + static_cast<size_t>(next() % 9000);
    std::string msg(n, '\0');
    for (size_t i = 0; i < n; ++i) msg[i] = static_cast<char>(next() & 0xFF);
    CosSha256 c;
    cos_sha256_init(&c);
    size_t at = 0;
    while (at < n) {
      const size_t take = 1 + static_cast<size_t>(next() % 130);
      const size_t t = take < n - at ? take : n - at;
      cos_sha256_update(&c, msg.data() + at, t);
      at += t;
    }
    uint8_t d[32];
    cos_sha256_final(&c, d);
    ++checks;
    if (hex_of(d) != saem::sha256_hex(msg)) { ++bad; std::fprintf(stderr, "burst mismatch round %d\n", round); }
  }
  std::printf("c17_sha256_vs_cpp           %5d checks, %d failed\n", checks, bad);
  return bad == 0 ? 0 : 1;
}
