/* Zone 0 gate tests. The gate is a pure function, so the tests are tables and properties:
 *  1. hand-written expectations for every forbidden class, taken from the Unicode standard, not from the gate's own code;
 *  2. an independent UTF-8 validator (decides by VALUE; the gate decides by byte RANGES) compared on every 1-, 2- and 3-byte input
 *     that starts with a high byte, and on a dense sample of 4-byte inputs;
 *  3. prefix property on random bytes: the text before the reported offset is always accepted;
 *  4. JSON shape: random well-formed nests (accepted, depth measured), then one deliberate corruption each (rejected at the exact index);
 *  5. purity: four threads scan one shared buffer and all get the identical answer (run under -fsanitize=thread). */
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "c17_check.h"
#include "cos_gate.h"

static size_t enc(uint32_t cp, uint8_t *b) { /* naive encoder: it will happily encode surrogates and values past U+10FFFF, on purpose */
  if (cp < 0x80u) { b[0] = (uint8_t)cp; return 1; }
  if (cp < 0x800u) { b[0] = (uint8_t)(0xC0u | (cp >> 6)); b[1] = (uint8_t)(0x80u | (cp & 0x3Fu)); return 2; }
  if (cp < 0x10000u) {
    b[0] = (uint8_t)(0xE0u | (cp >> 12)); b[1] = (uint8_t)(0x80u | ((cp >> 6) & 0x3Fu)); b[2] = (uint8_t)(0x80u | (cp & 0x3Fu));
    return 3;
  }
  b[0] = (uint8_t)(0xF0u | (cp >> 18)); b[1] = (uint8_t)(0x80u | ((cp >> 12) & 0x3Fu));
  b[2] = (uint8_t)(0x80u | ((cp >> 6) & 0x3Fu)); b[3] = (uint8_t)(0x80u | (cp & 0x3Fu));
  return 4;
}

static CosScan scan(const void *p, size_t n, uint32_t flags) { return cos_gate_scan((const uint8_t *)p, n, 0, flags); }
#define LIT(s) (s), (sizeof(s) - 1u)

/* one code point, alone */
static CosScan scan_cp(uint32_t cp) {
  uint8_t b[4];
  const size_t n = enc(cp, b);
  return scan(b, n, 0);
}

typedef struct Row { uint32_t cp; CosRule rule; } Row;

static void test_classes(CosSuite *s) {
  static const Row rows[] = {
      /* allowed */
      {0x41, COS_RULE_NONE}, {0x09, COS_RULE_NONE}, {0x0A, COS_RULE_NONE}, {0x0D, COS_RULE_NONE}, {0x20, COS_RULE_NONE}, {0x7E, COS_RULE_NONE},
      {0xA0, COS_RULE_NONE}, {0xE9, COS_RULE_NONE}, {0x0905, COS_RULE_NONE}, {0x0915, COS_RULE_NONE}, {0x4E2D, COS_RULE_NONE},
      {0x10000, COS_RULE_NONE}, {0x1F600, COS_RULE_NONE}, {0x07FF, COS_RULE_NONE}, {0x0800, COS_RULE_NONE}, {0xD7FF, COS_RULE_NONE},
      /* allowed by decision (documented in cos_gate.c): marks that real Urdu/Arabic text and PDF extractions contain */
      {0x200E, COS_RULE_NONE}, {0x200F, COS_RULE_NONE}, {0x061C, COS_RULE_NONE}, {0x00AD, COS_RULE_NONE}, {0x2028, COS_RULE_NONE},
      {0x2029, COS_RULE_NONE}, {0xFE0F, COS_RULE_NONE}, {0xFE00, COS_RULE_NONE},
      /* NUL and controls */
      {0x00, COS_RULE_NUL}, {0x01, COS_RULE_CONTROL}, {0x08, COS_RULE_CONTROL}, {0x0B, COS_RULE_CONTROL}, {0x0C, COS_RULE_CONTROL},
      {0x0E, COS_RULE_CONTROL}, {0x1B, COS_RULE_CONTROL}, {0x1F, COS_RULE_CONTROL}, {0x7F, COS_RULE_CONTROL}, {0x80, COS_RULE_CONTROL},
      {0x85, COS_RULE_CONTROL}, {0x9F, COS_RULE_CONTROL},
      /* direction overrides, embeddings, isolates */
      {0x202A, COS_RULE_BIDI}, {0x202B, COS_RULE_BIDI}, {0x202C, COS_RULE_BIDI}, {0x202D, COS_RULE_BIDI}, {0x202E, COS_RULE_BIDI},
      {0x2066, COS_RULE_BIDI}, {0x2067, COS_RULE_BIDI}, {0x2068, COS_RULE_BIDI}, {0x2069, COS_RULE_BIDI},
      /* invisible */
      {0x200B, COS_RULE_INVISIBLE}, {0x2060, COS_RULE_INVISIBLE}, {0x2061, COS_RULE_INVISIBLE}, {0x2062, COS_RULE_INVISIBLE},
      {0x2063, COS_RULE_INVISIBLE}, {0x2064, COS_RULE_INVISIBLE}, {0x180E, COS_RULE_INVISIBLE}, {0xFEFF, COS_RULE_INVISIBLE},
      {0xE0000, COS_RULE_INVISIBLE}, {0xE0001, COS_RULE_INVISIBLE}, {0xE0020, COS_RULE_INVISIBLE}, {0xE007F, COS_RULE_INVISIBLE},
      {0xE0100, COS_RULE_INVISIBLE}, {0xE01EF, COS_RULE_INVISIBLE},
      /* joiners with nothing before them */
      {0x200C, COS_RULE_JOINER}, {0x200D, COS_RULE_JOINER},
      /* private use */
      {0xE000, COS_RULE_PRIVATE_USE}, {0xF8FF, COS_RULE_PRIVATE_USE}, {0xF0000, COS_RULE_PRIVATE_USE}, {0xFFFFD, COS_RULE_PRIVATE_USE},
      {0x100000, COS_RULE_PRIVATE_USE}, {0x10FFFD, COS_RULE_PRIVATE_USE},
      /* noncharacters and damaged-text markers */
      {0xFDD0, COS_RULE_NONCHARACTER}, {0xFDEF, COS_RULE_NONCHARACTER}, {0xFFFE, COS_RULE_NONCHARACTER}, {0xFFFF, COS_RULE_NONCHARACTER},
      {0x1FFFE, COS_RULE_NONCHARACTER}, {0x1FFFF, COS_RULE_NONCHARACTER}, {0xFFFFE, COS_RULE_NONCHARACTER}, {0xFFFFF, COS_RULE_NONCHARACTER},
      {0x10FFFE, COS_RULE_NONCHARACTER}, {0x10FFFF, COS_RULE_NONCHARACTER}, {0xFFFD, COS_RULE_NONCHARACTER}, {0xFFF9, COS_RULE_NONCHARACTER},
      {0xFFFA, COS_RULE_NONCHARACTER}, {0xFFFB, COS_RULE_NONCHARACTER}, {0xFFFC, COS_RULE_NONCHARACTER},
      /* not UTF-8 at all */
      {0xD800, COS_RULE_UTF8}, {0xDBFF, COS_RULE_UTF8}, {0xDC00, COS_RULE_UTF8}, {0xDFFF, COS_RULE_UTF8}, {0x110000, COS_RULE_UTF8},
      {0x1FFFFF, COS_RULE_UTF8}, {0x140000, COS_RULE_UTF8},
  };
  int wrong = 0;
  for (size_t i = 0; i < sizeof rows / sizeof rows[0]; ++i) {
    const CosScan r = scan_cp(rows[i].cp);
    int good;
    if (rows[i].rule == COS_RULE_NONE) good = r.status == COS_OK && r.rule == COS_RULE_NONE && r.codepoints == 1u;
    else good = r.status == COS_E_FORBIDDEN && r.rule == rows[i].rule && r.offset == 0u && r.codepoints == 0u;
    if (!good) {
      wrong++;
      fprintf(stderr, "class U+%04X: got status %d rule %s offset %u, wanted rule %s\n", (unsigned)rows[i].cp, (int)r.status, cos_rule_name(r.rule),
              (unsigned)r.offset, cos_rule_name(rows[i].rule));
    }
  }
  CK(s, wrong == 0);
  /* every C0 control except tab, LF, CR is refused; those three pass */
  int c0 = 0;
  for (uint32_t cp = 1; cp < 0x20u; ++cp) {
    const CosScan r = scan_cp(cp);
    const int pass = cp == 9u || cp == 10u || cp == 13u;
    if (pass ? r.status != COS_OK : (r.status != COS_E_FORBIDDEN || r.rule != COS_RULE_CONTROL)) c0++;
  }
  CK(s, c0 == 0);
  /* the whole C1 block is refused */
  int c1 = 0;
  for (uint32_t cp = 0x80; cp <= 0x9Fu; ++cp) {
    const CosScan r = scan_cp(cp);
    if (r.status != COS_E_FORBIDDEN || r.rule != COS_RULE_CONTROL) c1++;
  }
  CK(s, c1 == 0);
  /* all noncharacters of every plane, and the whole private-use planes' edges */
  int nc = 0;
  for (uint32_t plane = 0; plane <= 16u; ++plane) {
    const CosScan a = scan_cp((plane << 16) | 0xFFFEu), b = scan_cp((plane << 16) | 0xFFFFu);
    if (a.rule != COS_RULE_NONCHARACTER || b.rule != COS_RULE_NONCHARACTER) nc++;
  }
  CK(s, nc == 0);
  /* offsets and counts: the first violation is reported, with the code points before it */
  CosScan r = scan(LIT("ab\xE2\x82\xAC" "c\x01" "d"), 0);
  CK(s, r.status == COS_E_FORBIDDEN && r.rule == COS_RULE_CONTROL && r.offset == 6u && r.codepoints == 4u);
  r = scan(LIT("abc\xE2\x80\xAE" "x"), 0); /* U+202E in the middle */
  CK(s, r.rule == COS_RULE_BIDI && r.offset == 3u && r.codepoints == 3u);
  r = scan(LIT("a\0b"), 0);
  CK(s, r.rule == COS_RULE_NUL && r.offset == 1u);
  /* two violations: the earlier one wins */
  r = scan(LIT("\x01\xE2\x80\xAE"), 0);
  CK(s, r.rule == COS_RULE_CONTROL && r.offset == 0u);
  /* a NUL in the last position is still found */
  r = scan(LIT("hello\0"), 0);
  CK(s, r.rule == COS_RULE_NUL && r.offset == 5u);
  /* counting */
  r = scan(LIT("a\xC3\xA9\xE2\x82\xAC\xF0\x9F\x98\x80"), 0); /* a é € 😀 */
  CK(s, r.status == COS_OK && r.codepoints == 4u);
  r = scan(NULL, 0, 0);
  CK(s, r.status == COS_OK && r.codepoints == 0u);
  r = cos_gate_scan(NULL, 5, 0, 0);
  CK(s, r.status == COS_E_INVALID);
  /* rule names exist for every rule */
  int names = 0;
  for (int k = 0; k <= (int)COS_RULE_SEAL; ++k) {
    const char *nm = cos_rule_name((CosRule)k);
    if (nm == NULL || nm[0] == '\0' || nm[0] == '?') names++;
  }
  CK(s, names == 0);
}

static void test_joiners(CosSuite *s) {
  CosScan r;
  /* Hindi: KA + VIRAMA + ZWJ + SSA (half form) and a ZWNJ after a virama: both are spelling, both pass */
  r = scan(LIT("\xE0\xA4\x95\xE0\xA5\x8D\xE2\x80\x8D\xE0\xA4\xB7"), 0);
  CK(s, r.status == COS_OK && r.codepoints == 4u);
  r = scan(LIT("\xE0\xA4\x95\xE0\xA5\x8D\xE2\x80\x8C\xE0\xA4\xB7"), 0);
  CK(s, r.status == COS_OK && r.codepoints == 4u);
  /* Malayalam chillu with ZWJ, Bengali RA + virama + ZWJ */
  r = scan(LIT("\xE0\xB4\xA8\xE0\xB5\x8D\xE2\x80\x8D"), 0);
  CK(s, r.status == COS_OK);
  r = scan(LIT("\xE0\xA7\xB0\xE0\xA7\x8D\xE2\x80\x8D"), 0);
  CK(s, r.status == COS_OK);
  /* Persian/Urdu: ZWNJ after an Arabic letter (mi-khaham) */
  r = scan(LIT("\xD9\x85\xDB\x8C\xE2\x80\x8C\xD8\xAE\xD9\x88\xD8\xA7\xD9\x87\xD9\x85"), 0);
  CK(s, r.status == COS_OK);
  /* ZWNJ after Arabic presentation form B (U+FEE0 area) */
  r = scan(LIT("\xEF\xBB\xA0\xE2\x80\x8C"), 0);
  CK(s, r.status == COS_OK);
  /* Latin letter + ZWJ, digit + ZWNJ, ZWJ first, emoji + ZWJ, a space + ZWJ: refused as hidden text */
  r = scan(LIT("a\xE2\x80\x8D"), 0);
  CK(s, r.rule == COS_RULE_JOINER && r.offset == 1u);
  r = scan(LIT("7\xE2\x80\x8C" "7"), 0);
  CK(s, r.rule == COS_RULE_JOINER && r.offset == 1u);
  r = scan(LIT("\xE2\x80\x8D"), 0);
  CK(s, r.rule == COS_RULE_JOINER && r.offset == 0u);
  r = scan(LIT("\xF0\x9F\x91\xA8\xE2\x80\x8D\xF0\x9F\x91\xA9"), 0); /* man ZWJ woman: emoji sequences are refused on purpose */
  CK(s, r.rule == COS_RULE_JOINER && r.offset == 4u);
  r = scan(LIT(" \xE2\x80\x8D"), 0);
  CK(s, r.rule == COS_RULE_JOINER);
  /* two joiners in a row: the second has a joiner before it, which is not a letter of the script */
  r = scan(LIT("\xE0\xA4\x95\xE0\xA5\x8D\xE2\x80\x8D\xE2\x80\x8D"), 0);
  CK(s, r.rule == COS_RULE_JOINER && r.offset == 9u);
  /* a joiner right after a Devanagari letter that follows Latin text still counts by its own predecessor */
  r = scan(LIT("abc \xE0\xA4\x95\xE2\x80\x8D"), 0);
  CK(s, r.status == COS_OK);
  /* the joiner is judged by what came before it, even after a skipped ASCII run */
  r = scan(LIT("\xE0\xA4\x95 \xE2\x80\x8D"), 0);
  CK(s, r.rule == COS_RULE_JOINER && r.offset == 4u);
}

/* independent UTF-8 validator: decides by value */
static size_t ref_first_bad(const uint8_t *p, size_t n) {
  size_t i = 0;
  while (i < n) {
    const uint8_t b = p[i];
    uint32_t v, min;
    size_t len;
    if (b < 0x80u) { i++; continue; }
    if ((b & 0xE0u) == 0xC0u) { len = 2; v = b & 0x1Fu; min = 0x80u; }
    else if ((b & 0xF0u) == 0xE0u) { len = 3; v = b & 0x0Fu; min = 0x800u; }
    else if ((b & 0xF8u) == 0xF0u) { len = 4; v = b & 0x07u; min = 0x10000u; }
    else return i;
    if (i + len > n) return i;
    for (size_t k = 1; k < len; ++k) {
      if ((p[i + k] & 0xC0u) != 0x80u) return i;
      v = (v << 6) | (p[i + k] & 0x3Fu);
    }
    if (v < min || v > 0x10FFFFu || (v >= 0xD800u && v <= 0xDFFFu)) return i;
    i += len;
  }
  return n;
}

/* the gate agrees with the reference: a malformed buffer is refused either as UTF-8 at the first bad byte, or earlier for another rule;
 * a well-formed buffer is never refused as UTF-8 */
static int agree(const uint8_t *p, size_t n) {
  const size_t bad = ref_first_bad(p, n);
  const CosScan r = cos_gate_scan(p, n, 0, 0);
  if (bad == n) return r.rule != COS_RULE_UTF8;
  if (r.rule == COS_RULE_UTF8) return r.status == COS_E_FORBIDDEN && r.offset == bad;
  return r.status == COS_E_FORBIDDEN && r.offset < bad;
}

static void test_utf8(CosSuite *s) {
  CosScan r;
  /* named malformed forms */
  static const struct { const char *name; uint8_t b[4]; size_t n; } bad[] = {
      {"lone continuation", {0x80}, 1}, {"lone continuation 2", {0xBF}, 1}, {"C0 lead", {0xC0, 0x80}, 2}, {"C1 lead", {0xC1, 0xBF}, 2},
      {"E0 overlong", {0xE0, 0x80, 0x80}, 3}, {"E0 overlong 2", {0xE0, 0x9F, 0xBF}, 3}, {"F0 overlong", {0xF0, 0x80, 0x80, 0x80}, 4},
      {"F0 overlong 2", {0xF0, 0x8F, 0xBF, 0xBF}, 4}, {"surrogate D800", {0xED, 0xA0, 0x80}, 3}, {"surrogate DFFF", {0xED, 0xBF, 0xBF}, 3},
      {"above 10FFFF", {0xF4, 0x90, 0x80, 0x80}, 4}, {"F5 lead", {0xF5, 0x80, 0x80, 0x80}, 4}, {"FF", {0xFF}, 1}, {"FE", {0xFE}, 1},
      {"truncated 2", {0xC3}, 1}, {"truncated 3", {0xE2, 0x82}, 2}, {"truncated 4", {0xF0, 0x9F, 0x98}, 3},
      {"2 then ASCII", {0xE2, 0x82, 'a'}, 3}, {"4 then ASCII", {0xF0, 0x9F, 'a', 'b'}, 4}, {"bad cont 2nd", {0xC3, 0x28}, 2},
      {"bad cont 3rd", {0xE2, 0x82, 0x28}, 3}, {"bad cont 4th", {0xF0, 0x9F, 0x98, 0x28}, 4},
  };
  int wrong = 0;
  for (size_t i = 0; i < sizeof bad / sizeof bad[0]; ++i) {
    uint8_t *exact = (uint8_t *)malloc(bad[i].n); /* exact-size heap copy: an over-read by the gate would be caught by AddressSanitizer */
    memcpy(exact, bad[i].b, bad[i].n);
    r = cos_gate_scan(exact, bad[i].n, 0, 0);
    if (!(r.status == COS_E_FORBIDDEN && r.rule == COS_RULE_UTF8 && r.offset == 0u)) {
      wrong++;
      fprintf(stderr, "utf8 case '%s' not refused as utf8\n", bad[i].name);
    }
    free(exact);
  }
  CK(s, wrong == 0);
  /* the same forms after valid text report the right offset and count */
  r = scan(LIT("ab\xC3"), 0);
  CK(s, r.rule == COS_RULE_UTF8 && r.offset == 2u && r.codepoints == 2u);
  r = scan(LIT("\xE2\x82\xAC\xE2\x82"), 0);
  CK(s, r.rule == COS_RULE_UTF8 && r.offset == 3u && r.codepoints == 1u);
  /* boundary code points that ARE valid */
  static const uint32_t good[] = {0x41, 0x7F + 0x21, 0x7FF, 0x800, 0x0FFF, 0xD7FF, 0x10000, 0x1F600, 0x2FA1D, 0x3FFFD, 0xEFFFD};
  int gw = 0;
  for (size_t i = 0; i < sizeof good / sizeof good[0]; ++i) gw += scan_cp(good[i]).status != COS_OK;
  CK(s, gw == 0);

  /* every 1-byte and 2-byte buffer whose first byte is high; every 3-byte buffer whose first byte is high */
  long cases = 0, mismatch = 0;
  for (uint32_t a = 0x80u; a <= 0xFFu; ++a) {
    uint8_t b1[1] = {(uint8_t)a};
    cases++; mismatch += !agree(b1, 1);
    for (uint32_t b = 0; b <= 0xFFu; ++b) {
      uint8_t b2[2] = {(uint8_t)a, (uint8_t)b};
      cases++; mismatch += !agree(b2, 2);
      for (uint32_t c = 0; c <= 0xFFu; ++c) {
        uint8_t b3[3] = {(uint8_t)a, (uint8_t)b, (uint8_t)c};
        cases++; mismatch += !agree(b3, 3);
      }
    }
  }
  CK(s, mismatch == 0);
  printf("  utf8: %ld buffers of 1..3 bytes compared with the reference, %ld disagreements\n", cases, mismatch);
  /* 4-byte buffers: every lead from F0 to FF, every second and third byte, a dense set of fourth bytes */
  static const uint8_t fourth[] = {0x00, 0x20, 0x7F, 0x80, 0x81, 0x8F, 0x90, 0xA0, 0xBF, 0xC0, 0xC2, 0xFF};
  long cases4 = 0, mismatch4 = 0;
  for (uint32_t a = 0xF0u; a <= 0xFFu; ++a)
    for (uint32_t b = 0; b <= 0xFFu; ++b)
      for (uint32_t c = 0; c <= 0xFFu; ++c)
        for (size_t d = 0; d < sizeof fourth; ++d) {
          uint8_t b4[4] = {(uint8_t)a, (uint8_t)b, (uint8_t)c, fourth[d]};
          cases4++; mismatch4 += !agree(b4, 4);
        }
  CK(s, mismatch4 == 0);
  printf("  utf8: %ld buffers of 4 bytes compared with the reference, %ld disagreements\n", cases4, mismatch4);
}

typedef struct Rng { uint64_t s; } Rng;
static uint64_t rnd(Rng *r) {
  r->s ^= r->s >> 12; r->s ^= r->s << 25; r->s ^= r->s >> 27;
  return r->s * 2685821657736338717ull;
}

static void test_prefix_property(CosSuite *s) {
  /* random bytes biased towards the interesting ones; the text before a reported offset must itself be accepted */
  static const uint8_t pool[] = {'a', 'b', ' ', '{', '}', '[', ']', '"', '\\', 0x00, 0x01, 0x09, 0x0A, 0x7F, 0xC2, 0xC3, 0xA9, 0x80, 0x85, 0xE0, 0xE2,
                                  0x80, 0x8D, 0x8E, 0xAE, 0xA4, 0x95, 0xEE, 0xEF, 0xBB, 0xBF, 0xF0, 0x9F, 0x98, 0xF4, 0x8F, 0xED, 0xA0, 0xFF, 0xBD};
  Rng r = {0x9E3779B97F4A7C15ull};
  long bad = 0, tried = 0, refused = 0;
  uint8_t buf[96];
  for (int it = 0; it < 200000; ++it) {
    const size_t n = (size_t)(rnd(&r) % sizeof buf);
    for (size_t i = 0; i < n; ++i) buf[i] = pool[rnd(&r) % sizeof pool];
    const CosScan full = cos_gate_scan(buf, n, 0, 0);
    tried++;
    if (full.status == COS_OK) {
      if (ref_first_bad(buf, n) != n) bad++;
      continue;
    }
    refused++;
    if (full.status != COS_E_FORBIDDEN || full.offset >= n) { bad++; continue; }
    const CosScan pre = cos_gate_scan(buf, full.offset, 0, 0);
    if (pre.status != COS_OK || pre.codepoints != full.codepoints) bad++;
    /* and the verdict is repeatable */
    const CosScan again = cos_gate_scan(buf, n, 0, 0);
    if (memcmp(&again, &full, sizeof full) != 0) bad++;
  }
  CK(s, bad == 0);
  printf("  prefix property: %ld random buffers (%ld refused), %ld violations\n", tried, refused, bad);
}

/* second random mode: strings built from whole characters (mostly valid), so many are accepted and the code point count can be checked
 * against a count that needs no decoding: every byte that is not a continuation byte starts one code point */
static void test_atoms(CosSuite *s) {
  static const char *atoms[] = {"a", "Z", "7", " ", "\n", "\t", "{", "}", "[", "]", "\"", ",", ":", "\xC3\xA9", "\xE2\x82\xAC",
                                "\xE0\xA4\x95", "\xE0\xA5\x8D", "\xE2\x80\x8D", "\xE2\x80\x8C", "\xD9\x85", "\xDB\x8C", "\xF0\x9F\x98\x80",
                                "\xE2\x80\xAE", "\xEF\xBB\xBF", "\xE2\x80\x8B", "\x01", "\xC3", "\xE0\xA4", "\xEE\x80\x80", "\xEF\xBF\xBF"};
  const size_t na = sizeof atoms / sizeof atoms[0];
  Rng r = {0xA0761D6478BD642Full};
  long bad = 0, accepted = 0, tried = 0;
  uint8_t buf[256];
  for (int it = 0; it < 200000; ++it) {
    size_t n = 0;
    const unsigned parts = (unsigned)(rnd(&r) % 24u);
    for (unsigned k = 0; k < parts; ++k) {
      /* the last six atoms are the bad ones: pick them rarely */
      const uint64_t x = rnd(&r);
      const size_t idx = (x % 10u == 0u) ? na - 8u + (size_t)((x >> 8) % 8u) : (size_t)((x >> 8) % (na - 8u));
      const size_t l = strlen(atoms[idx]);
      memcpy(buf + n, atoms[idx], l);
      n += l;
    }
    tried++;
    const CosScan v = cos_gate_scan(buf, n, 0, 0);
    if (v.status == COS_OK) {
      accepted++;
      uint32_t count = 0;
      for (size_t i = 0; i < n; ++i) count += (buf[i] & 0xC0u) != 0x80u;
      if (v.codepoints != count || ref_first_bad(buf, n) != n) bad++;
    } else if (v.status == COS_E_FORBIDDEN && v.offset < n) {
      const CosScan pre = cos_gate_scan(buf, v.offset, 0, 0);
      if (pre.status != COS_OK || pre.codepoints != v.codepoints) bad++;
    } else {
      bad++;
    }
  }
  CK(s, bad == 0);
  CK(s, accepted > 20000); /* the mode really exercises the accepting path */
  printf("  atoms: %ld random strings, %ld accepted, %ld violations\n", tried, accepted, bad);
}

static void test_limits(CosSuite *s) {
  CosScan r;
  uint8_t tiny[1] = {'a'};
  /* the length is judged before a single byte is read: a 1-byte buffer with a huge claimed length is refused without touching memory */
  r = cos_gate_scan(tiny, (size_t)COS_MAX_INPUT + 1u, 0, 0);
  CK(s, r.status == COS_E_TOO_BIG && r.rule == COS_RULE_LENGTH && r.offset == COS_MAX_INPUT);
  r = cos_gate_scan(tiny, (size_t)1 << 40, 0, 0);
  CK(s, r.status == COS_E_TOO_BIG);
  r = cos_gate_scan(tiny, 11, 10, 0);
  CK(s, r.status == COS_E_TOO_BIG && r.offset == 10u);
  r = cos_gate_scan(tiny, 1, 1, 0);
  CK(s, r.status == COS_OK);
  uint8_t *big = (uint8_t *)malloc((size_t)COS_MAX_INPUT + 1u);
  memset(big, 'a', (size_t)COS_MAX_INPUT + 1u);
  r = cos_gate_scan(big, COS_MAX_INPUT, 0, 0); /* max_len 0 means the global ceiling */
  CK(s, r.status == COS_OK && r.codepoints == COS_MAX_INPUT);
  r = cos_gate_scan(big, (size_t)COS_MAX_INPUT + 1u, 0, 0);
  CK(s, r.status == COS_E_TOO_BIG);
  r = cos_gate_scan(big, COS_MAX_INPUT, 1000000u, 0); /* a bigger per-method limit is clamped to the ceiling */
  CK(s, r.status == COS_OK);
  r = cos_gate_scan(big, (size_t)COS_MAX_INPUT + 1u, 1000000u, 0);
  CK(s, r.status == COS_E_TOO_BIG);
  r = cos_gate_scan(big, 100, 100, 0);
  CK(s, r.status == COS_OK && r.codepoints == 100u);
  r = cos_gate_scan(big, 101, 100, 0);
  CK(s, r.status == COS_E_TOO_BIG);
  /* a violation on the very last byte of a maximum-size input is found */
  big[COS_MAX_INPUT - 1u] = 0x01;
  r = cos_gate_scan(big, COS_MAX_INPUT, 0, 0);
  CK(s, r.rule == COS_RULE_CONTROL && r.offset == COS_MAX_INPUT - 1u);
  free(big);
}

static CosScan js(const char *t) { return cos_gate_scan((const uint8_t *)t, strlen(t), 0, COS_SCAN_JSON); }

static void test_json_named(CosSuite *s) {
  CosScan r;
  r = js("{}");                              CK(s, r.status == COS_OK && r.depth_max == 1u);
  r = js("");                                CK(s, r.status == COS_OK && r.depth_max == 0u);
  r = js("[[[]]]");                          CK(s, r.status == COS_OK && r.depth_max == 3u);
  r = js("{\"a\":[1,2,{\"b\":\"}]\"}]}");    CK(s, r.status == COS_OK && r.depth_max == 3u);   /* brackets inside strings do not count */
  r = js("{\"a\":\"x\\\"}\"}");              CK(s, r.status == COS_OK);                        /* an escaped quote does not end the string */
  r = js("{\"a\":\"\\\\\"}");                CK(s, r.status == COS_OK);                        /* an escaped backslash does not escape the quote after it */
  r = js("{\"a\":\"\\\"}");                  CK(s, r.rule == COS_RULE_BRACKETS);               /* ...but this quote IS escaped: unterminated */
  r = js("{\"a\":\"\xC3\xA9\"}");            CK(s, r.status == COS_OK);                        /* non-ASCII inside a string */
  r = js("{\"a\":\"\\\xC3\xA9\"}");          CK(s, r.status == COS_OK);                        /* an escape consumes one whole code point */
  r = js("{\"\xE0\xA4\x95\":[\"\xE0\xA4\x95\"]}"); CK(s, r.status == COS_OK && r.depth_max == 2u);
  r = js("{");                               CK(s, r.rule == COS_RULE_BRACKETS && r.offset == 1u);
  r = js("}");                               CK(s, r.rule == COS_RULE_BRACKETS && r.offset == 0u);
  r = js("]");                               CK(s, r.rule == COS_RULE_BRACKETS && r.offset == 0u);
  r = js("{]");                              CK(s, r.rule == COS_RULE_BRACKETS && r.offset == 1u);
  r = js("[}");                              CK(s, r.rule == COS_RULE_BRACKETS && r.offset == 1u);
  r = js("{[}]");                            CK(s, r.rule == COS_RULE_BRACKETS && r.offset == 2u);
  r = js("{\"a");                            CK(s, r.rule == COS_RULE_BRACKETS && r.offset == 3u);
  r = js("{}}");                             CK(s, r.rule == COS_RULE_BRACKETS && r.offset == 2u);
  r = js("{}{");                             CK(s, r.rule == COS_RULE_BRACKETS);
  r = js("{}{}[]");                          CK(s, r.status == COS_OK && r.depth_max == 1u);
  /* depth: 32 deep is fine, 33 is refused at the 33rd opener */
  char deep[80];
  memset(deep, '[', 32); memset(deep + 32, ']', 32); deep[64] = 0;
  r = js(deep);                              CK(s, r.status == COS_OK && r.depth_max == 32u);
  char deep33[80];
  memset(deep33, '[', 33); memset(deep33 + 33, ']', 33); deep33[66] = 0;
  r = js(deep33);                            CK(s, r.rule == COS_RULE_DEPTH && r.offset == 32u);
  char alt[80];
  for (int i = 0; i < 32; ++i) { alt[i] = (i & 1) ? '[' : '{'; alt[63 - i] = (i & 1) ? ']' : '}'; }
  alt[64] = 0;
  r = js(alt);                               CK(s, r.status == COS_OK && r.depth_max == 32u);
  /* no JSON flag: brackets are just text */
  r = scan(LIT("{{{{[[["), 0);               CK(s, r.status == COS_OK);
  r = scan(LIT("\"unterminated"), 0);        CK(s, r.status == COS_OK);
  /* other rules still fire in JSON mode, and first */
  r = js("{\"a\":\"\x01\"}");                CK(s, r.rule == COS_RULE_CONTROL && r.offset == 6u);
  r = js("{\"a\":\"\xE2\x80\xAE\"}");        CK(s, r.rule == COS_RULE_BIDI);
}

static size_t gen_shape(Rng *r, char *buf, size_t cap, unsigned maxd, unsigned *depth_max, size_t *closers, size_t *ncl) {
  static const char *fill[] = {"\"x\"", "\"}]\"", "\"a\\\"]\"", "\"\\\\\"", "1", ",", ":", " ", "\xC3\xA9", "\"\xC3\xA9{\"", "true", "\"[[[\""};
  char stack[40];
  unsigned depth = 0;
  size_t n = 0;
  *depth_max = 0;
  *ncl = 0;
  const unsigned steps = 1u + (unsigned)(rnd(r) % 150u);
  for (unsigned st = 0; st < steps; ++st) {
    const uint64_t x = rnd(r);
    if (depth < maxd && (depth == 0u || (x & 3u) != 0u)) {
      const char o = (x & 4u) ? '[' : '{';
      stack[depth++] = o;
      buf[n++] = o;
      if (depth > *depth_max) *depth_max = depth;
    } else if (depth > 0u) {
      closers[(*ncl)++] = n;
      buf[n++] = stack[--depth] == '[' ? ']' : '}';
    }
    const char *f = fill[(x >> 8) % (sizeof fill / sizeof fill[0])];
    const size_t fl = strlen(f);
    if (n + fl + 80u < cap) { memcpy(buf + n, f, fl); n += fl; }
  }
  while (depth > 0u) {
    closers[(*ncl)++] = n;
    buf[n++] = stack[--depth] == '[' ? ']' : '}';
  }
  buf[n] = 0;
  return n;
}

static void test_json_random(CosSuite *s) {
  Rng r = {0xD1B54A32D192ED03ull};
  long bad = 0, shapes = 0;
  static char buf[4096];
  static size_t closers[2048];
  for (int it = 0; it < 20000; ++it) {
    unsigned dm = 0;
    size_t ncl = 0;
    const unsigned maxd = 1u + (unsigned)(rnd(&r) % 32u);
    const size_t n = gen_shape(&r, buf, sizeof buf, maxd, &dm, closers, &ncl);
    shapes++;
    CosScan ok = cos_gate_scan((const uint8_t *)buf, n, 0, COS_SCAN_JSON);
    if (ok.status != COS_OK || ok.depth_max != dm) { bad++; fprintf(stderr, "shape rejected: %s\n", buf); continue; }
    if (ncl == 0u) continue;
    /* (a) flip one closer: refused at exactly that index */
    const size_t k = closers[rnd(&r) % ncl];
    char saved = buf[k];
    buf[k] = (saved == '}') ? ']' : '}';
    CosScan fl = cos_gate_scan((const uint8_t *)buf, n, 0, COS_SCAN_JSON);
    if (fl.status != COS_E_FORBIDDEN || fl.rule != COS_RULE_BRACKETS || fl.offset != k) bad++;
    buf[k] = saved;
    /* (b) cut the text at the last closer: an opener stays open, refused at the end */
    const size_t cut = closers[ncl - 1u];
    CosScan tr = cos_gate_scan((const uint8_t *)buf, cut, 0, COS_SCAN_JSON);
    if (tr.status != COS_E_FORBIDDEN || tr.rule != COS_RULE_BRACKETS || tr.offset != cut) bad++;
    /* (c) one closer too many at the end */
    buf[n] = '}'; buf[n + 1] = 0;
    CosScan ex = cos_gate_scan((const uint8_t *)buf, n + 1u, 0, COS_SCAN_JSON);
    if (ex.status != COS_E_FORBIDDEN || ex.rule != COS_RULE_BRACKETS || ex.offset != n) bad++;
    buf[n] = 0;
    /* (d) at full depth one more opener is refused as depth, at its own index */
    if (dm == 32u) {
      /* find a position where depth is 32: the text so far ends with all openers closed, so rebuild from the opener run */
      char deep[40];
      memset(deep, (rnd(&r) & 1u) ? '[' : '{', 33);
      CosScan dp = cos_gate_scan((const uint8_t *)deep, 33, 0, COS_SCAN_JSON);
      if (dp.rule != COS_RULE_DEPTH || dp.offset != 32u) bad++;
    }
  }
  CK(s, bad == 0);
  printf("  json shapes: %ld random nests, %ld violations\n", shapes, bad);
}

/* ---- purity under threads ---- */
typedef struct Shared { const uint8_t *buf; size_t n; CosScan want; int bad; } Shared;
static void *worker(void *p) {
  Shared *sh = (Shared *)p;
  int bad = 0;
  for (int i = 0; i < 4000; ++i) {
    const CosScan r = cos_gate_scan(sh->buf, sh->n, 0, COS_SCAN_JSON);
    if (memcmp(&r, &sh->want, sizeof r) != 0) bad++;
  }
  sh->bad = bad; /* each thread has its own Shared copy; the buffer itself is only read */
  return NULL;
}

static void test_threads(CosSuite *s) {
  static const char text[] =
      "{\"q\":\"\xE0\xA4\xA8\xE0\xA4\xAE\xE0\xA4\xB8\xE0\xA5\x8D\xE0\xA4\xA4\xE0\xA5\x87 \xE0\xA4\x95\xE0\xA5\x8D\xE2\x80\x8D\xE0\xA4\xB7\","
      "\"u\":\"\xD9\x85\xDB\x8C\xE2\x80\x8C\xD8\xAE\xD9\x88\xD8\xA7\xD9\x87\xD9\x85\",\"v\":[1,2,[3,[4]]]}";
  const CosScan want = cos_gate_scan((const uint8_t *)text, sizeof text - 1u, 0, COS_SCAN_JSON);
  Shared sh[4];
  pthread_t th[4];
  for (int i = 0; i < 4; ++i) { sh[i].buf = (const uint8_t *)text; sh[i].n = sizeof text - 1u; sh[i].want = want; sh[i].bad = -1; }
  for (int i = 0; i < 4; ++i) pthread_create(&th[i], NULL, worker, &sh[i]);
  for (int i = 0; i < 4; ++i) pthread_join(th[i], NULL);
  CK(s, want.status == COS_OK && want.depth_max == 4u);
  CK(s, sh[0].bad == 0 && sh[1].bad == 0 && sh[2].bad == 0 && sh[3].bad == 0);
}

int main(void) {
  CosSuite s = {"c17_gate", 0, 0};
  test_classes(&s);
  test_joiners(&s);
  test_utf8(&s);
  test_prefix_property(&s);
  test_atoms(&s);
  test_limits(&s);
  test_json_named(&s);
  test_json_random(&s);
  test_threads(&s);
  return suite_done(&s);
}
