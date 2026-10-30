// Number <-> text exactly the way JavaScript does it, so the C++ engine prints what the reference engine prints.
#pragma once
#include <charconv>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>

namespace saem {

// Locale-proof strtod for plain ASCII numbers.
inline double parse_double(const std::string& s) {
  double v = 0;
#if defined(__cpp_lib_to_chars) && __cpp_lib_to_chars >= 201611L
  const char* b = s.data();
  const char* e = b + s.size();
  if (b < e && *b == '+') ++b;
  auto r = std::from_chars(b, e, v);
  if (r.ec == std::errc() ) return v;
#endif
  return std::strtod(s.c_str(), nullptr);
}

// Shortest decimal digits that read back as exactly x (x > 0, finite). value = 0.DIGITS * 10^n10
inline void shortest_digits(double x, std::string& digits, int& n10) {
  char buf[64];
  int len = 0;
#if defined(__cpp_lib_to_chars) && __cpp_lib_to_chars >= 201611L
  auto r = std::to_chars(buf, buf + sizeof buf, x, std::chars_format::scientific);
  len = static_cast<int>(r.ptr - buf);
#else
  for (int prec = 0; prec <= 17; ++prec) {
    len = std::snprintf(buf, sizeof buf, "%.*e", prec, x);
    if (std::strtod(buf, nullptr) == x) break;
  }
#endif
  buf[len] = '\0';  // std::to_chars does not terminate its output
  digits.clear();
  int i = 0;
  for (; i < len && buf[i] != 'e'; ++i) if (buf[i] >= '0' && buf[i] <= '9') digits += buf[i];
  int e10 = (i < len) ? std::atoi(buf + i + 1) : 0;
  while (digits.size() > 1 && digits.back() == '0') digits.pop_back();
  n10 = e10 + 1;
}

// Number.prototype.toString()
inline std::string jsnum(double x) {
  if (std::isnan(x)) return "NaN";
  if (x == 0) return "0";
  if (std::isinf(x)) return x < 0 ? "-Infinity" : "Infinity";
  bool neg = x < 0;
  if (neg) x = -x;
  std::string d;
  int n;
  shortest_digits(x, d, n);
  const int k = static_cast<int>(d.size());
  std::string out;
  if (k <= n && n <= 21) out = d + std::string(static_cast<size_t>(n - k), '0');
  else if (0 < n && n <= 21) out = d.substr(0, static_cast<size_t>(n)) + "." + d.substr(static_cast<size_t>(n));
  else if (-6 < n && n <= 0) out = "0." + std::string(static_cast<size_t>(-n), '0') + d;
  else {
    int e = n - 1;
    std::string es = (e < 0 ? "-" : "+") + std::to_string(e < 0 ? -e : e);
    out = (k == 1) ? d + "e" + es : d.substr(0, 1) + "." + d.substr(1) + "e" + es;
  }
  return neg ? "-" + out : out;
}

// +x.toPrecision(p): round to p significant digits, halves go up (as the spec says), return the double.
inline double round_sig(double x, int p) {
  if (x == 0 || !std::isfinite(x)) return x;
  bool neg = x < 0;
  double a = neg ? -x : x;
  char buf[200];
  int len = 0;
#if defined(__cpp_lib_to_chars) && __cpp_lib_to_chars >= 201611L
  auto r = std::to_chars(buf, buf + sizeof buf, a, std::chars_format::scientific, 90);
  len = static_cast<int>(r.ptr - buf);
#else
  len = std::snprintf(buf, sizeof buf, "%.90e", a);
#endif
  buf[len] = '\0';
  std::string d;
  int i = 0;
  for (; i < len && buf[i] != 'e'; ++i) if (buf[i] >= '0' && buf[i] <= '9') d += buf[i];
  int e10 = (i < len) ? std::atoi(buf + i + 1) : 0;
  if (static_cast<int>(d.size()) > p) {
    bool up = d[static_cast<size_t>(p)] >= '5';
    d.resize(static_cast<size_t>(p));
    if (up) {
      int j = p - 1;
      while (j >= 0 && d[static_cast<size_t>(j)] == '9') { d[static_cast<size_t>(j)] = '0'; --j; }
      if (j >= 0) d[static_cast<size_t>(j)]++;
      else { d.insert(d.begin(), '1'); d.resize(static_cast<size_t>(p)); ++e10; }
    }
  }
  std::string s = d.substr(0, 1) + "." + (d.size() > 1 ? d.substr(1) : std::string("0")) + "e" + std::to_string(e10);
  double v = parse_double(s);
  return neg ? -v : v;
}

}  // namespace saem
