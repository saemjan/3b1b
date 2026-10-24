// Number <-> text exactly the way JavaScript does it (article A1).
#pragma once
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

namespace saem {

inline double parse_double(const std::string& s) {
  size_t b = s.find_first_not_of(" \t\n\r\f\v");
  if (b == std::string::npos) return 0.0;
  size_t e = s.find_last_not_of(" \t\n\r\f\v");
  if (e == std::string::npos) return 0.0;
  const char* p = s.c_str() + b;
  char* stop = nullptr;
  double v = std::strtod(p, &stop);
  if (stop == p) return 0.0;
  return v;
}

// Shortest decimal digits that read back as exactly x.
inline void shortest_digits(double x, std::string& digits, int& n10) {
  char buf[64];
  int len = 0;
  for (int prec = 0; prec <= 17; ++prec) {
    len = std::snprintf(buf, sizeof buf, "%.*e", prec, x);
    if (std::strtod(buf, nullptr) == x) break;
  }
  digits.clear();
  int i = 0;
  for (; i < len && buf[i] != 'e'; ++i)
    if (buf[i] >= '0' && buf[i] <= '9') digits += buf[i];
  int e10 = (i < len) ? std::atoi(buf + i + 1) : 0;
  while (digits.size() > 1 && digits.back() == '0') digits.pop_back();
  n10 = e10 + 1;
}

inline std::string jsnum(double x) {
  if (std::isnan(x)) return "NaN";
  if (std::isinf(x)) return x < 0 ? "-Infinity" : "Infinity";
  bool neg = x < 0;
  if (neg) x = -x;
  if (x == 0.0) return "0";
  std::string d;
  int n;
  shortest_digits(x, d, n);
  const int k = static_cast<int>(d.size());
  std::string out;
  if (k <= n && n <= 21) {
    out = d + std::string(static_cast<size_t>(n - k), '0');
  } else if (0 < n && n <= 21) {
    out = d.substr(0, static_cast<size_t>(n)) + "." +
          d.substr(static_cast<size_t>(n));
  } else if (-6 < n && n <= 0) {
    out = "0." + std::string(static_cast<size_t>(-n), '0') + d;
  } else {
    int e = n - 1;
    std::string es = (e < 0 ? "-" : "+") + std::to_string(e < 0 ? -e : e);
    out = (k == 1) ? d + "e" + es
                   : d.substr(0, 1) + "." + d.substr(1) + "e" + es;
  }
  return neg ? "-" + out : out;
}

// toPrecision(p): p significant digits.
inline std::string round_sig(double x, int p) {
  if (x == 0.0 || !std::isfinite(x) || p < 1) return jsnum(x);
  bool neg = x < 0;
  if (neg) x = -x;

  std::string d;
  int n;
  shortest_digits(x, d, n);

  if (static_cast<int>(d.size()) > p) {
    bool up = d[static_cast<size_t>(p)] >= '5';
    d = d.substr(0, static_cast<size_t>(p));
    if (up) {
      int i = static_cast<int>(d.size()) - 1;
      for (; i >= 0; --i) {
        if (d[i] == '9') d[i] = '0';
        else { ++d[i]; break; }
      }
      if (i < 0) { d = "1" + d; ++n; }
    }
  } else {
    d += std::string(static_cast<size_t>(p) - d.size(), '0');
  }

  // Reconstruct value from rounded digits and re-emit via jsnum (A1).
  double v = 0.0;
  for (char c : d) v = v * 10.0 + (c - '0');
  double val = v * std::pow(10.0, n - static_cast<int>(d.size()));
  return jsnum(neg ? -val : val);
}

}  // namespace saem
