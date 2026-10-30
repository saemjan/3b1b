#include "cos_gate.h"

const char *cos_rule_name(CosRule r) {
  switch (r) {
    case COS_RULE_NONE: return "none";
    case COS_RULE_LENGTH: return "length";
    case COS_RULE_UTF8: return "utf8";
    case COS_RULE_NUL: return "nul";
    case COS_RULE_CONTROL: return "control";
    case COS_RULE_BIDI: return "bidi";
    case COS_RULE_INVISIBLE: return "invisible";
    case COS_RULE_JOINER: return "joiner";
    case COS_RULE_PRIVATE_USE: return "private_use";
    case COS_RULE_NONCHARACTER: return "noncharacter";
    case COS_RULE_DEPTH: return "depth";
    case COS_RULE_BRACKETS: return "brackets";
    case COS_RULE_METHOD: return "method";
    case COS_RULE_QUARANTINE: return "quarantine";
    case COS_RULE_FROZEN: return "frozen";
    case COS_RULE_SEAL: return "seal";
  }
  return "?";
}

/* ZWJ (U+200D) and ZWNJ (U+200C) are part of the spelling in Indic scripts (half forms, conjuncts) and in Arabic-script languages such as
 * Urdu and Persian. Rejecting them would reject Hindi. Everywhere else they hide text, so they are refused. */
static int joiner_ok(uint32_t prev) {
  return (prev >= 0x0900u && prev <= 0x0DFFu) || (prev >= 0xA8E0u && prev <= 0xA8FFu) ||                      /* Devanagari .. Sinhala, Devanagari Extended */
         (prev >= 0x0600u && prev <= 0x06FFu) || (prev >= 0x0750u && prev <= 0x077Fu) || (prev >= 0x0870u && prev <= 0x08FFu) || /* Arabic, Supplement, Extended-A and -B */
         (prev >= 0xFB50u && prev <= 0xFDFFu) || (prev >= 0xFE70u && prev <= 0xFEFEu);                                         /* Arabic presentation forms A and B */
}

static CosRule forbidden(uint32_t cp, uint32_t prev) {
  if (cp == 0u) return COS_RULE_NUL;
  if (cp < 0x20u) return (cp == 9u || cp == 10u || cp == 13u) ? COS_RULE_NONE : COS_RULE_CONTROL;
  if (cp == 0x7Fu || (cp >= 0x80u && cp <= 0x9Fu)) return COS_RULE_CONTROL;
  if ((cp >= 0x202Au && cp <= 0x202Eu) || (cp >= 0x2066u && cp <= 0x2069u)) return COS_RULE_BIDI;
  if (cp == 0x200Bu || (cp >= 0x2060u && cp <= 0x2064u) || cp == 0xFEFFu || cp == 0x180Eu) return COS_RULE_INVISIBLE;
  if (cp == 0x200Cu || cp == 0x200Du) return joiner_ok(prev) ? COS_RULE_NONE : COS_RULE_JOINER;
  if ((cp >= 0xE0000u && cp <= 0xE007Fu) || (cp >= 0xE0100u && cp <= 0xE01EFu)) return COS_RULE_INVISIBLE;
  if ((cp >= 0xFDD0u && cp <= 0xFDEFu) || (cp & 0xFFFEu) == 0xFFFEu) return COS_RULE_NONCHARACTER; /* U+xFFFE and U+xFFFF in every plane */
  if (cp == 0xFFFDu || (cp >= 0xFFF9u && cp <= 0xFFFCu)) return COS_RULE_NONCHARACTER;
  if ((cp >= 0xE000u && cp <= 0xF8FFu) || (cp >= 0xF0000u && cp <= 0x10FFFDu)) return COS_RULE_PRIVATE_USE;
  return COS_RULE_NONE;
}

static CosScan fail(CosStatus st, CosRule rule, size_t off, uint32_t cps, uint32_t depth) {
  CosScan o = {st, rule, (uint32_t)off, cps, depth};
  return o;
}

/* Strict UTF-8 (Unicode Table 3-7). Returns the byte length, or 0 for a malformed sequence. */
static size_t decode(const uint8_t *p, size_t left, uint32_t *cp) {
  const uint8_t b0 = p[0];
  if (b0 < 0x80u) { *cp = b0; return 1; }
  size_t need;
  uint8_t lo = 0x80u, hi = 0xBFu;
  uint32_t v;
  if (b0 >= 0xC2u && b0 <= 0xDFu) { need = 2; v = b0 & 0x1Fu; }
  else if (b0 >= 0xE0u && b0 <= 0xEFu) {
    need = 3; v = b0 & 0x0Fu;
    if (b0 == 0xE0u) lo = 0xA0u;      /* no overlong */
    if (b0 == 0xEDu) hi = 0x9Fu;      /* no surrogates */
  } else if (b0 >= 0xF0u && b0 <= 0xF4u) {
    need = 4; v = b0 & 0x07u;
    if (b0 == 0xF0u) lo = 0x90u;      /* no overlong */
    if (b0 == 0xF4u) hi = 0x8Fu;      /* nothing above U+10FFFF */
  } else {
    return 0;
  }
  if (left < need) return 0;
  if (p[1] < lo || p[1] > hi) return 0;
  v = (v << 6) | (p[1] & 0x3Fu);
  for (size_t k = 2; k < need; ++k) {
    if ((p[k] & 0xC0u) != 0x80u) return 0;
    v = (v << 6) | (p[k] & 0x3Fu);
  }
  *cp = v;
  return need;
}

CosScan cos_gate_scan(const uint8_t *in, size_t n, uint32_t max_len, uint32_t flags) {
  const uint32_t limit = (max_len == 0u || max_len > COS_MAX_INPUT) ? COS_MAX_INPUT : max_len;
  if (n > limit) return fail(COS_E_TOO_BIG, COS_RULE_LENGTH, limit, 0, 0);
  if (n > 0u && in == NULL) return fail(COS_E_INVALID, COS_RULE_UTF8, 0, 0, 0);
  uint32_t cps = 0, prev = 0, stack = 0, depth = 0, depth_max = 0;
  int in_str = 0, esc = 0;
  size_t i = 0;
  while (i < n) {
    uint32_t cp = 0;
    const size_t len = decode(in + i, n - i, &cp);
    if (len == 0u) return fail(COS_E_FORBIDDEN, COS_RULE_UTF8, i, cps, depth_max);
    const CosRule bad = forbidden(cp, prev);
    if (bad != COS_RULE_NONE) return fail(COS_E_FORBIDDEN, bad, i, cps, depth_max);
    if ((flags & COS_SCAN_JSON) != 0u) {
      if (in_str) {
        if (esc) esc = 0;                 /* a backslash consumes exactly one code point, ASCII or not */
        else if (cp == '\\') esc = 1;
        else if (cp == '"') in_str = 0;
      } else if (cp >= 0x80u) {
        /* non-ASCII outside a string cannot open or close anything */
      } else if (cp == '"') {
        in_str = 1;
      } else if (cp == '{' || cp == '[') {
        if (depth >= COS_MAX_DEPTH) return fail(COS_E_FORBIDDEN, COS_RULE_DEPTH, i, cps, depth_max);
        stack = (stack << 1) | (cp == '[' ? 1u : 0u);
        depth++;
        if (depth > depth_max) depth_max = depth;
      } else if (cp == '}' || cp == ']') {
        if (depth == 0u || ((stack & 1u) != 0u) != (cp == ']')) return fail(COS_E_FORBIDDEN, COS_RULE_BRACKETS, i, cps, depth_max);
        stack >>= 1;
        depth--;
      }
    }
    prev = cp;
    i += len;
    cps++;
  }
  if ((flags & COS_SCAN_JSON) != 0u && (in_str || depth != 0u)) return fail(COS_E_FORBIDDEN, COS_RULE_BRACKETS, n, cps, depth_max);
  CosScan ok = {COS_OK, COS_RULE_NONE, 0u, cps, depth_max};
  return ok;
}
