// Schrödinger's layer: true time evolution of the cursor machine.
//   H = sum_i ( |i+1><i| (x) A_i  +  |i><i+1| (x) A_i^dagger )
// is Feynman's ch.6 Hamiltonian; e^{-iHt} is applied to a state vector by
// Taylor series with scaling-and-squaring, so no matrix is ever formed.
// A wave packet on the cursor sites propagates, reflects at the ends, and
// accumulates halt amplitude -- ballistic control flow, not a clock.
#pragma once
#include <cmath>
#include <vector>

#include "qreg.hpp"

namespace saem {

// (H v)[i] = A_{i-1} v[i-1] + A_i^dagger v[i+1]
inline void h_apply(std::vector<Cx>& out, const std::vector<Cx>& v,
                    size_t n, size_t k, const std::vector<Gate>& prog) {
  const size_t M = size_t(1) << n;
  out.assign(v.size(), Cx(0, 0));
  for (size_t i = 0; i <= k; ++i) {
    if (i > 0) {
      std::vector<Cx> s(v.begin() + (i - 1) * M, v.begin() + i * M);
      apply_amp(s.data(), n, prog[i - 1], false);
      for (size_t r = 0; r < M; ++r) out[i * M + r] = out[i * M + r] + s[r];
    }
    if (i < k) {
      std::vector<Cx> s(v.begin() + (i + 1) * M, v.begin() + (i + 2) * M);
      apply_amp(s.data(), n, prog[i], true);
      for (size_t r = 0; r < M; ++r) out[i * M + r] = out[i * M + r] + s[r];
    }
  }
}

inline std::vector<Cx> evolve(std::vector<Cx> v, size_t n, size_t k,
                              const std::vector<Gate>& prog, double t,
                              int terms = 18) {
  int p = 0;
  double ts = t;
  while (std::fabs(ts) > 0.25) { ts *= 0.5; ++p; }
  auto step = [&](const std::vector<Cx>& x) {
    std::vector<Cx> term = x, acc = x, ht;
    for (int m = 1; m <= terms; ++m) {
      h_apply(ht, term, n, k, prog);
      const double c = ts / double(m);
      for (size_t j = 0; j < ht.size(); ++j)
        term[j] = Cx(c * ht[j].im, -c * ht[j].re);   // (-i ts / m) * H term
      for (size_t j = 0; j < acc.size(); ++j) acc[j] = acc[j] + term[j];
    }
    return acc;
  };
  std::vector<Cx> out = step(v);
  for (int s = 1; s < (1 << p); ++s) out = step(out);   // (e^{-iH ts})^{2^p}
  return out;
}

}  // namespace saem
