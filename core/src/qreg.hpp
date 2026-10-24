// Quantum layer: amplitudes over two-state atoms (Feynman ch.6) and the
// cursor machine that makes a program out of them. The gate set is rev.hpp
// lifted to amplitudes; every gate is unitary by construction, so nothing
// here owes heat until measurement.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <utility>
#include <vector>

#include "json.hpp"
#include "rev.hpp"

namespace saem {

struct Cx {
  double re = 0, im = 0;
  Cx() = default;
  Cx(double r, double i = 0) : re(r), im(i) {}
  Cx operator+(Cx o) const { return {re + o.re, im + o.im}; }
  Cx operator-(Cx o) const { return {re - o.re, im - o.im}; }
  Cx operator*(Cx o) const {
    return {re * o.re - im * o.im, re * o.im + im * o.re};
  }
  Cx conj() const { return {re, -im}; }
  double abs2() const { return re * re + im * im; }
};

// One gate on one register slice of 2^n amplitudes. adj flips the sign of
// the S phase; every other gate in the set is its own adjoint.
inline void apply_amp(Cx* buf, size_t n, const Gate& g, bool adj = false) {
  const size_t M = size_t(1) << n;
  const size_t ba = size_t(1) << g.a;
  const size_t bb = size_t(1) << g.b;
  const size_t bc = size_t(1) << g.c;
  switch (g.kind) {
    case 5: {
      const double r = 0.70710678118654752440;
      for (size_t i = 0; i < M; ++i)
        if (!(i & ba)) {
          Cx x = buf[i], y = buf[i | ba];
          buf[i] = Cx(r * (x.re + y.re), r * (x.im + y.im));
          buf[i | ba] = Cx(r * (x.re - y.re), r * (x.im - y.im));
        }
      break;
    }
    case 6:
      for (size_t i = 0; i < M; ++i)
        if (i & ba) buf[i] = Cx(-buf[i].re, -buf[i].im);
      break;
    case 7:
      for (size_t i = 0; i < M; ++i)
        if (i & ba)
          buf[i] = adj ? Cx(buf[i].im, -buf[i].re) : Cx(-buf[i].im, buf[i].re);
      break;
    default:
      for (size_t i = 0; i < M; ++i) {
        bool fire = false;
        size_t j = 0;
        switch (g.kind) {
          case 0: fire = !(i & ba); j = i | ba; break;
          case 1: fire = (i & ba) && !(i & bb); j = i | bb; break;
          case 2: fire = (i & ba) && (i & bb) && !(i & bc); j = i | bc; break;
          case 3: fire = (i & ba) && !(i & bb); j = (i & ~ba) | bb; break;
          case 4: fire = (i & ba) && (i & bb) && !(i & bc); j = (i & ~bb) | bc; break;
        }
        if (fire) std::swap(buf[i], buf[j]);
      }
  }
}

class QReg {
 public:
  explicit QReg(size_t nq, uint64_t seed = 0x5AEE)
      : n_(nq), amp_(size_t(1) << nq), rng_(seed) {
    amp_[0] = Cx(1, 0);
  }
  size_t qubits() const { return n_; }
  const std::vector<Cx>& amp() const { return amp_; }
  double norm() const {
    double s = 0;
    for (const Cx& a : amp_) s += a.abs2();
    return s;
  }
  void apply(const Gate& g) { apply_amp(amp_.data(), n_, g); }
  void x(uint8_t q) { apply(gnot(q)); }
  void h(uint8_t q) { apply(gh(q)); }
  void z(uint8_t q) { apply(gz(q)); }
  void s(uint8_t q) { apply(gs(q)); }
  void cnot(uint8_t c, uint8_t t) { apply(gcnot(c, t)); }
  void ccnot(uint8_t a, uint8_t b, uint8_t t) { apply(gccnot(a, b, t)); }
  void swapq(uint8_t a, uint8_t b) { apply(gswap(a, b)); }
  void fredkin(uint8_t c, uint8_t a, uint8_t b) { apply(gfredkin(c, a, b)); }

  double prob1(size_t q) const {
    double p = 0;
    for (size_t i = 0; i < amp_.size(); ++i)
      if ((i >> q) & 1) p += amp_[i].abs2();
    return p;
  }
  int measure(size_t q) {
    int out = uniform01() < prob1(q) ? 1 : 0;
    double n = 0;
    for (size_t i = 0; i < amp_.size(); ++i) {
      if (int((i >> q) & 1) != out) amp_[i] = Cx(0, 0);
      else n += amp_[i].abs2();
    }
    n = std::sqrt(n);
    for (Cx& a : amp_) a = a * Cx(1.0 / n, 0);
    return out;
  }
  size_t measure_all() {
    double u = uniform01(), acc = 0;
    size_t pick = amp_.size() - 1;
    for (size_t i = 0; i < amp_.size(); ++i) {
      acc += amp_[i].abs2();
      if (u < acc) { pick = i; break; }
    }
    std::fill(amp_.begin(), amp_.end(), Cx(0, 0));
    amp_[pick] = Cx(1, 0);
    return pick;
  }

 private:
  double uniform01() {
    rng_ ^= rng_ << 13; rng_ ^= rng_ >> 7; rng_ ^= rng_ << 17;
    return double(rng_ >> 11) * (1.0 / double(1ULL << 53));
  }
  size_t n_;
  std::vector<Cx> amp_;
  uint64_t rng_;
};

class QProg {
  // Feynman's cursor machine (ch.6, §6.3): n register atoms plus k+1
  // program-counter sites, one electron wide. A hop trades site i for
  // site i+1 and runs the step's gate on the moving branch; a split hop
  // is a beam splitter, so control flow itself can be in superposition.
  // The machine reports finished the only way it can: amplitude at k.
 public:
  QProg(size_t nreg, size_t k, uint64_t seed = 0x5AEE)
      : n_(nreg), k_(k), M_(size_t(1) << nreg), amp_((k + 1) * M_), rng_(seed) {
    amp_[0] = Cx(1, 0);
  }
  size_t reg_qubits() const { return n_; }
  size_t sites() const { return k_ + 1; }
  double norm() const {
    double s = 0;
    for (const Cx& a : amp_) s += a.abs2();
    return s;
  }
  void load(size_t reg_basis) {
    std::fill(amp_.begin(), amp_.end(), Cx(0, 0));
    amp_[reg_basis] = Cx(1, 0);
  }
  void hop(size_t i, const Gate& g) { move(i, g, 1.0, 0.0); }
  void split(size_t i, const Gate& g, double sin_theta) {
    move(i, g, sin_theta, std::sqrt(1.0 - sin_theta * sin_theta));
  }
  double prob_cursor(size_t i) const {
    double p = 0;
    for (size_t r = 0; r < M_; ++r) p += amp_[i * M_ + r].abs2();
    return p;
  }
  double prob_halt() const { return prob_cursor(k_); }

  Json readout(size_t top = 8) const {  // register, conditioned on halt
    std::vector<std::pair<double, size_t>> v;
    for (size_t r = 0; r < M_; ++r) {
      double p = amp_[k_ * M_ + r].abs2();
      if (p > 1e-12) v.push_back({p, r});
    }
    std::sort(v.begin(), v.end(),
              [](const std::pair<double, size_t>& a,
                 const std::pair<double, size_t>& b) { return a.first > b.first; });
    Json a = Json::array();
    for (size_t i = 0; i < v.size() && i < top; ++i) {
      Json o = Json::object();
      o.set("basis", (int)v[i].second);
      o.set("p", v[i].first);
      a.push(o);
    }
    return a;
  }

  int measure_halt() {
    int out = uniform01() < prob_halt() ? 1 : 0;
    double n = 0;
    for (size_t i = 0; i < amp_.size(); ++i) {
      bool at_halt = (i / M_) == k_;
      if (int(at_halt) != out) amp_[i] = Cx(0, 0);
      else n += amp_[i].abs2();
    }
    n = std::sqrt(n);
    if (n > 0) for (Cx& a : amp_) a = a * Cx(1.0 / n, 0);
    return out;
  }

 private:
  // Unitary on the two-site cursor subspace {i, i+1}:
  //   u' = c*u - s*A^dagger*v ;  v' = s*A*u + c*v
  void move(size_t i, const Gate& g, double s, double c) {
    Cx* u = amp_.data() + i * M_;
    Cx* v = amp_.data() + (i + 1) * M_;
    std::vector<Cx> u0(u, u + M_), v0(v, v + M_);
    std::vector<Cx> au = u0, av = v0;
    apply_amp(au.data(), n_, g, false);  // A u
    apply_amp(av.data(), n_, g, true);   // A^dagger v
    for (size_t r = 0; r < M_; ++r) {
      u[r] = u0[r] * Cx(c, 0) - av[r] * Cx(s, 0);
      v[r] = au[r] * Cx(s, 0) + v0[r] * Cx(c, 0);
    }
  }
  double uniform01() {
    rng_ ^= rng_ << 13; rng_ ^= rng_ >> 7; rng_ ^= rng_ << 17;
    return double(rng_ >> 11) * (1.0 / double(1ULL << 53));
  }
  size_t n_, k_, M_;
  std::vector<Cx> amp_;
  uint64_t rng_;
};

}  // namespace saem
