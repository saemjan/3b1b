// core/src/qcos_api.cpp
#include <algorithm>
#include <stdexcept>
#include "api.hpp"
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>
#include "cog.hpp"
#include "kernel.hpp"
#include "qreg.hpp"
#include "rev.hpp"
#include "sha256.hpp"

namespace saem {
namespace {
Json amp_json(const std::vector<Cx>& a) {
  Json out = Json::array();
  for (const Cx& c : a) { Json e = Json::array(); e.push(Json(c.re)); e.push(Json(c.im)); out.push(e); }
  return out;
}
std::vector<Cx> amp_of(const Json& a) {
  std::vector<Cx> v;
  for (const Json& e : a.arr()) v.push_back(Cx(e[size_t(0)].asNum(), e[size_t(1)].asNum()));
  return v;
}
Gate gate_of(const Json& g) {
  Gate q{}; q.kind = static_cast<uint8_t>(g["kind"].asInt(0));
  q.a = static_cast<uint8_t>(g["a"].asInt(0)); q.b = static_cast<uint8_t>(g["b"].asInt(0));
  q.c = static_cast<uint8_t>(g["c"].asInt(0)); return q;
}
Bits bits_of(const Json& a) { Bits b; for (const Json& e : a.arr()) b.push_back(static_cast<uint8_t>(e.asInt(0))); return b; }
Json bits_json(const Bits& b) { Json o = Json::array(); for (uint8_t x : b) o.push(Json((int)x)); return o; }
std::vector<Gate> prog_of(const Json& a) { std::vector<Gate> p; for (const Json& g : a.arr()) p.push_back(gate_of(g)); return p; }
double stream_u(uint32_t seed, uint32_t i) {
  uint32_t x = seed ? seed : 0x5AEEu;
  for (uint32_t t = 0; t <= i; ++t) { x ^= x << 13; x ^= x >> 17; x ^= x << 5; }
  return double(x) / 4294967296.0;
}
// Cursor-machine step on a raw amplitude vector laid out v[site*M + reg],
// M = 1<<n (same layout program.halt sums over).  sin(theta)=1 is a full
// hop, matching the qcos.hpp schedule comment "sin(theta), gate; 1 = full
// hop".  The gate rides on the moving branch; the staying branch is
// multiplied by cos(theta).  STATELESS: everything travels in the JSON.
void prog_move(std::vector<Cx>& v, size_t n, size_t i, const Gate& g,
               double sin_theta) {
  const size_t M = size_t(1) << n;
  if (M == 0 || v.size() % M != 0)
    throw std::runtime_error("program.step: amp size not a multiple of 2^n");
  const size_t sites = v.size() / M;
  if (i + 1 >= sites)
    throw std::runtime_error("program.step: cursor already at last site");
  const double cos_theta =
      std::sqrt(std::max(0.0, 1.0 - sin_theta * sin_theta));

  std::vector<Cx> moved(v.begin() + static_cast<long>(i * M),
                        v.begin() + static_cast<long>((i + 1) * M));
  apply_amp(moved.data(), n, g);

  for (size_t r = 0; r < M; ++r) {
    v[i * M + r] = v[i * M + r] * Cx(cos_theta, 0);
    v[(i + 1) * M + r] = v[(i + 1) * M + r] + moved[r] * Cx(sin_theta, 0);
  }
}

// Fixed: Added `[](const Json& a)` signatures
const Registrar w0("stream.u", [](const Json& a) {
  Json o = Json::object();
  o.set("u", stream_u(static_cast<uint32_t>(a["seed"].asInt(1)), static_cast<uint32_t>(a["i"].asInt(0))));
  return o;
});
const Registrar w1("quantum.apply", [](const Json& a) {
  std::vector<Cx> v = amp_of(a["amp"]);
  apply_amp(v.data(), static_cast<size_t>(a["n"].asInt(0)), gate_of(a["gate"]));
  Json o = Json::object(); o.set("amp", amp_json(v)); return o;
});
const Registrar w2("quantum.probs", [](const Json& a) {
  const std::vector<Cx> v = amp_of(a["amp"]);
  const size_t n = static_cast<size_t>(a["n"].asInt(0));
  double norm = 0; for (const Cx& c : v) norm += c.abs2();
  Json p1 = Json::array();
  for (size_t q = 0; q < n; ++q) {
    double p = 0;
    for (size_t i = 0; i < v.size(); ++i) if ((i >> q) & 1) p += v[i].abs2();
    p1.push(Json(p));
  }
  Json o = Json::object(); o.set("norm", norm); o.set("p1", p1); return o;
});
const Registrar w3("quantum.measure", [](const Json& a) {
  std::vector<Cx> v = amp_of(a["amp"]);
  const size_t q = static_cast<size_t>(a["q"].asInt(0));
  double p = 0; for (size_t i = 0; i < v.size(); ++i) if ((i >> q) & 1) p += v[i].abs2();
  const int out = a["u"].asNum() < p ? 1 : 0; double nrm = 0;
  for (size_t i = 0; i < v.size(); ++i) {
    if (int((i >> q) & 1) != out) v[i] = Cx(0, 0); else nrm += v[i].abs2();
  }
  nrm = std::sqrt(nrm); for (Cx& c : v) c = c * Cx(1.0 / nrm, 0);
  Json o = Json::object(); o.set("out", out); o.set("amp", amp_json(v)); return o;
});
const Registrar w4("program.step", [](const Json& a) {
  std::vector<Cx> v = amp_of(a["amp"]);
  prog_move(v, static_cast<size_t>(a["n"].asInt(0)), static_cast<size_t>(a["i"].asInt(0)), gate_of(a["gate"]), a["sin"].asNum());
  Json o = Json::object(); o.set("amp", amp_json(v)); return o;
});
const Registrar w5("program.halt", [](const Json& a) {
  const std::vector<Cx> v = amp_of(a["amp"]);
  const size_t n = static_cast<size_t>(a["n"].asInt(0));
  const size_t k = static_cast<size_t>(a["k"].asInt(0));
  const size_t M = size_t(1) << n; double p = 0;
  for (size_t r = 0; r < M; ++r) p += v[k * M + r].abs2();
  Json o = Json::object(); o.set("p", p); return o;
});
const Registrar w6("rev.run", [](const Json& a) {
  Bits b = bits_of(a["bits"]); run(b, prog_of(a["prog"]), a["backwards"].asBool(false));
  Json o = Json::object(); o.set("bits", bits_json(b)); return o;
});
const Registrar w7("rev.bennett", [](const Json& a) {
  Bits b = bits_of(a["bits"]);
  compute_copy_uncompute(b, prog_of(a["prog"]), static_cast<uint8_t>(a["out"].asInt(0)), static_cast<uint8_t>(a["dest"].asInt(0)));
  Json o = Json::object(); o.set("bits", bits_json(b)); return o;
});
const Registrar w8("cog.observe", [](const Json& a) {
  const double slip = a["slip"].asNum(0.10), guess = a["guess"].asNum(0.25);
  const double p = 1.0 - slip, q = guess;
  const double lo = a["logodds"].asNum(0) + std::log(a["correct"].asBool(false) ? p / q : (1.0 - p) / (1.0 - q));
  Json o = Json::object();
  o.set("logodds", lo); o.set("shots", a["shots"].asNum(0) + 1);
  o.set("p", 1.0 / (1.0 + std::exp(-lo))); o.set("moral", std::fabs(lo) >= std::log(a["bar"].asNum(1000.0)));
  return o;
});
const Registrar w9("cog.update", [](const Json& a) {
  Belief b; b.logodds = a["logodds"].asNum(0); b.shots = a["shots"].asNum(0);
  update(b, a["k"].asNum(0), a["n"].asNum(0), a["p"].asNum(0.5), a["q"].asNum(0.5));
  Json o = Json::object();
  o.set("logodds", b.logodds); o.set("shots", b.shots);
  o.set("p", b.prob()); o.set("moral", moral(b, a["bar"].asNum(1000.0)));
  return o;
});
const Registrar w10("cog.next", [](const Json& a) {
  double best = -1; std::string topic;
  for (const Json& e : a["beliefs"].arr()) {
    const double lo = std::fabs(e["logodds"].asNum(0));
    if (best < 0 || lo < best) { best = lo; topic = e["topic"].asStr(); }
  }
  Json o = Json::object(); o.set("topic", topic); return o;
});
const Registrar w11("kernel.canon", [](const Json& a) {
  Json o = Json::object(); o.set("text", canon(a["value"])); return o;
});
const Registrar w12("kernel.soul", [](const Json& a) {
  Json o = Json::object(); o.set("hex", sha256_hex(canon(a["value"]))); return o;
});
const Registrar w13("kernel.set", [](const Json& a) {
  Json board = a["board"]; double debt = a["debt"].asNum(0);
  const std::string key = a["key"].asStr();
  if (board.has(key)) debt += 8.0 * double(canon(board[key]).size());
  board.set(key, a["value"]);
  Json o = Json::object(); o.set("board", board); o.set("debt", debt); o.set("soul", sha256_hex(canon(board)));
  return o;
});
const Registrar w14("qcos.smoke", [](const Json& a) {
  Json o = Json::object();
  QReg r(2, 7); r.h(0); r.cnot(0, 1);
  o.set("bell_norm", r.norm()); o.set("bell_p0", r.prob1(0));
  QProg p(2, 2, 11); p.hop(0, gh(0)); p.hop(1, gcnot(0, 1));
  o.set("halt", p.prob_halt()); o.set("readout", p.readout());
  Bits b = {1, 1, 0, 0};
  std::vector<Gate> adder = {gccnot(0, 1, 2), gcnot(0, 3), gcnot(1, 3)};
  run(b, adder);
  o.set("carry", (int)b[2]); o.set("sum", (int)b[3]);
  return o;
});
}}
