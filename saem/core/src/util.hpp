// Small helpers shared by every part of the Saem core.
// The goal is JavaScript-exact behaviour where the reference engine relies on it: string whitespace,
// UTF-16 lengths, the seeded random stream, the 32-bit hash, Math.round, and Map iteration order.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include "numfmt.hpp"

namespace saem {

using u32 = std::u32string;

// ------------------------------------------------------------------ UTF-8 <-> UTF-32
inline u32 to_u32(const std::string& s) {
  u32 out;
  out.reserve(s.size());
  const size_t n = s.size();
  size_t i = 0;
  while (i < n) {
    const unsigned char c = static_cast<unsigned char>(s[i]);
    char32_t cp = 0;
    size_t len = 0;
    if (c < 0x80) { cp = c; len = 1; }
    else if ((c & 0xE0) == 0xC0) { cp = c & 0x1F; len = 2; }
    else if ((c & 0xF0) == 0xE0) { cp = c & 0x0F; len = 3; }
    else if ((c & 0xF8) == 0xF0) { cp = c & 0x07; len = 4; }
    else { out.push_back(0xFFFD); ++i; continue; }
    if (i + len > n) { out.push_back(0xFFFD); ++i; continue; }
    bool ok = true;
    for (size_t k = 1; k < len; ++k) {
      const unsigned char d = static_cast<unsigned char>(s[i + k]);
      if ((d & 0xC0) != 0x80) { ok = false; break; }
      cp = (cp << 6) | (d & 0x3F);
    }
    if (!ok || (len == 2 && cp < 0x80) || (len == 3 && cp < 0x800) || (len == 4 && cp < 0x10000) || cp > 0x10FFFF ||
        (cp >= 0xD800 && cp <= 0xDFFF)) {
      out.push_back(0xFFFD);
      ++i;
      continue;
    }
    out.push_back(cp);
    i += len;
  }
  return out;
}

inline void put_u8(std::string& out, char32_t cp) {
  if (cp < 0x80) out += static_cast<char>(cp);
  else if (cp < 0x800) { out += static_cast<char>(0xC0 | (cp >> 6)); out += static_cast<char>(0x80 | (cp & 0x3F)); }
  else if (cp < 0x10000) {
    out += static_cast<char>(0xE0 | (cp >> 12));
    out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
    out += static_cast<char>(0x80 | (cp & 0x3F));
  } else {
    out += static_cast<char>(0xF0 | (cp >> 18));
    out += static_cast<char>(0x80 | ((cp >> 12) & 0x3F));
    out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
    out += static_cast<char>(0x80 | (cp & 0x3F));
  }
}
inline std::string to_u8(const u32& s) {
  std::string out;
  out.reserve(s.size());
  for (char32_t c : s) put_u8(out, c);
  return out;
}
inline u32 U(const char* ascii_or_utf8) { return to_u32(ascii_or_utf8); }

// ------------------------------------------------------------------ JavaScript character classes
// \s and String.prototype.trim: white space plus line terminators.
inline bool js_space(char32_t c) {
  switch (c) {
    case 9: case 10: case 11: case 12: case 13: case 32: case 0xA0: case 0x1680: case 0x2028: case 0x2029:
    case 0x202F: case 0x205F: case 0x3000: case 0xFEFF:
      return true;
    default:
      return c >= 0x2000 && c <= 0x200A;
  }
}
inline bool js_lineterm(char32_t c) { return c == 10 || c == 13 || c == 0x2028 || c == 0x2029; }
inline bool is_digit(char32_t c) { return c >= '0' && c <= '9'; }
inline bool is_alpha(char32_t c) { return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'); }
inline bool is_alnum(char32_t c) { return is_digit(c) || is_alpha(c); }
inline bool is_word(char32_t c) { return is_alnum(c) || c == '_'; }  // JavaScript \w (ASCII only)

// toLowerCase for the scripts that matter here (ASCII, Latin-1, Greek, Cyrillic); everything else is unchanged.
inline char32_t lower1(char32_t c) {
  if (c >= 'A' && c <= 'Z') return c + 32;
  if (c < 0x80) return c;
  if (c >= 0xC0 && c <= 0xDE && c != 0xD7) return c + 32;
  if (c >= 0x391 && c <= 0x3A9 && c != 0x3A2) return c + 32;
  if (c >= 0x410 && c <= 0x42F) return c + 32;
  if (c >= 0x400 && c <= 0x40F) return c + 80;
  if (c == 0x212A) return 'k';  // Kelvin sign
  return c;
}
inline u32 lower(const u32& s) {
  u32 o = s;
  for (auto& c : o) c = lower1(c);
  return o;
}
inline u32 trim(const u32& s) {
  size_t a = 0, b = s.size();
  while (a < b && js_space(s[a])) ++a;
  while (b > a && js_space(s[b - 1])) --b;
  return s.substr(a, b - a);
}
// s.replace(/\s+/g, ' ')
inline u32 collapse_ws(const u32& s) {
  u32 o;
  o.reserve(s.size());
  bool in = false;
  for (char32_t c : s) {
    if (js_space(c)) { if (!in) o.push_back(' '); in = true; }
    else { o.push_back(c); in = false; }
  }
  return o;
}
// clean(): collapse and trim
inline u32 clean(const u32& s) { return trim(collapse_ws(s)); }

// length in UTF-16 code units, the way JavaScript counts
inline size_t js_len(const u32& s) {
  size_t n = 0;
  for (char32_t c : s) n += c >= 0x10000 ? 2 : 1;
  return n;
}
// s.slice(0, n) (never leaves half a surrogate pair)
inline u32 js_slice(const u32& s, size_t n) {
  size_t units = 0, i = 0;
  for (; i < s.size(); ++i) {
    const size_t w = s[i] >= 0x10000 ? 2 : 1;
    if (units + w > n) break;
    units += w;
  }
  return s.substr(0, i);
}
inline std::vector<uint16_t> utf16_units(const std::string& utf8) {
  std::vector<uint16_t> out;
  for (char32_t c : to_u32(utf8)) {
    if (c >= 0x10000) {
      const char32_t v = c - 0x10000;
      out.push_back(static_cast<uint16_t>(0xD800 + (v >> 10)));
      out.push_back(static_cast<uint16_t>(0xDC00 + (v & 0x3FF)));
    } else out.push_back(static_cast<uint16_t>(c));
  }
  return out;
}

inline std::vector<u32> split_char(const u32& s, char32_t sep) {
  std::vector<u32> out;
  size_t a = 0;
  for (size_t i = 0; i <= s.size(); ++i) {
    if (i == s.size() || s[i] == sep) { out.push_back(s.substr(a, i - a)); a = i + 1; }
  }
  return out;
}
inline u32 remove_char(const u32& s, char32_t c) {
  u32 o;
  o.reserve(s.size());
  for (char32_t x : s) if (x != c) o.push_back(x);
  return o;
}
inline bool starts_ci(const u32& s, size_t i, const char* word, size_t* end) {
  size_t k = 0;
  for (; word[k]; ++k) {
    if (i + k >= s.size() || lower1(s[i + k]) != static_cast<char32_t>(word[k])) return false;
  }
  if (end) *end = i + k;
  return true;
}
inline size_t skip_ws(const u32& s, size_t i) {
  while (i < s.size() && js_space(s[i])) ++i;
  return i;
}
// everything from i to the end has no line terminators (what `.*$` needs)
inline bool no_lineterm_from(const u32& s, size_t i) {
  for (; i < s.size(); ++i) if (js_lineterm(s[i])) return false;
  return true;
}
// normKey: lower-case, collapse white space, trim
inline std::string norm_key(const std::string& s) { return to_u8(clean(lower(to_u32(s)))); }

// ------------------------------------------------------------------ numbers
// Math.round: halves go toward +infinity
inline double js_round(double x) {
  if (!std::isfinite(x)) return x;
  const double r = std::floor(x);
  return (x - r >= 0.5) ? r + 1 : r;
}
inline double clampd(double x, double a, double b) { return std::min(b, std::max(a, x)); }
// Math.hypot, the algorithm V8 uses (scaled Kahan sum), so results match bit for bit.
inline double js_hypot2(double a, double b) {
  const double v[2] = {std::fabs(a), std::fabs(b)};
  double mx = 0;
  for (double x : v) if (x > mx) mx = x;
  if (std::isinf(mx)) return mx;
  if (std::isnan(a) || std::isnan(b)) return std::nan("");
  if (mx == 0) return 0;
  double sum = 0, comp = 0;
  for (double x : v) {
    const double n = x / mx, summand = n * n - comp, prelim = sum + summand;
    comp = (prelim - sum) - summand;
    sum = prelim;
  }
  return std::sqrt(sum) * mx;
}
// (n >>> 0).toString(36)
inline std::string base36(uint32_t n) {
  if (n == 0) return "0";
  std::string s;
  while (n) { const unsigned d = n % 36; s += static_cast<char>(d < 10 ? '0' + d : 'a' + (d - 10)); n /= 36; }
  std::reverse(s.begin(), s.end());
  return s;
}
// Number.prototype.toString(36) for non-negative integers that fit a double exactly
inline std::string base36_u64(unsigned long long n) {
  if (n == 0) return "0";
  std::string s;
  while (n) { const unsigned d = static_cast<unsigned>(n % 36); s += static_cast<char>(d < 10 ? '0' + d : 'a' + (d - 10)); n /= 36; }
  std::reverse(s.begin(), s.end());
  return s;
}

// ------------------------------------------------------------------ the seeded random stream (mulberry32)
struct Rng {
  uint32_t a;
  explicit Rng(uint32_t seed = 1) : a(seed) {}
  double operator()() {
    a += 0x6D2B79F5u;
    uint32_t t = (a ^ (a >> 15)) * (1u | a);
    t = (t + ((t ^ (t >> 7)) * (61u | t))) ^ t;
    return static_cast<double>(t ^ (t >> 14)) / 4294967296.0;
  }
};
// FNV-1a over UTF-16 code units
inline uint32_t hash32(const std::string& utf8) {
  uint32_t h = 2166136261u;
  for (uint16_t u : utf16_units(utf8)) { h ^= u; h *= 16777619u; }
  return h;
}
template <class T>
std::vector<T> shuffled(const std::vector<T>& a, Rng& R) {
  std::vector<T> b = a;
  for (size_t i = b.size(); i-- > 1;) {
    const size_t j = static_cast<size_t>(std::floor(R() * static_cast<double>(i + 1)));
    std::swap(b[i], b[j]);
  }
  return b;
}
template <class T>
const T& pick_from(Rng& R, const std::vector<T>& a) {
  return a[static_cast<size_t>(std::floor(R() * static_cast<double>(a.size())))];
}

// ------------------------------------------------------------------ a map that remembers insertion order (like a JS Map)
// References returned by get_or_add() stay valid only until the next insertion.
template <class V>
class OMap {
 public:
  using Entry = std::pair<std::string, V>;
  V* find(const std::string& k) {
    auto it = ix_.find(k);
    return it == ix_.end() ? nullptr : &e_[it->second].second;
  }
  const V* find(const std::string& k) const {
    auto it = ix_.find(k);
    return it == ix_.end() ? nullptr : &e_[it->second].second;
  }
  bool has(const std::string& k) const { return ix_.find(k) != ix_.end(); }
  V& get_or_add(const std::string& k, V init = V()) {
    auto it = ix_.find(k);
    if (it != ix_.end()) return e_[it->second].second;
    ix_.emplace(k, e_.size());
    e_.emplace_back(k, std::move(init));
    return e_.back().second;
  }
  void set(const std::string& k, V v) { get_or_add(k) = std::move(v); }
  size_t size() const { return e_.size(); }
  bool empty() const { return e_.empty(); }
  const std::vector<Entry>& entries() const { return e_; }
  std::vector<Entry>& entries_mut() { return e_; }

 private:
  std::vector<Entry> e_;
  std::unordered_map<std::string, size_t> ix_;
};

}  // namespace saem
