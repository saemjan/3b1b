// Forecast engine: ridge logistic regression over learner events, Platt
// calibration, Bernoulli-gated method choice, and verdicts under the
// constitutional caps. This is the classical baseline of THINK.md H7: the
// quantum-probability track may replace it only by beating it on frozen
// held-out data (gates Q0-Q4), never by fiat.
#pragma once
#include <cmath>
#include <string>
#include <vector>

#include "cos.hpp"
#include "json.hpp"

namespace saem {
namespace ef {

struct LRModel {
  std::vector<double> w;
  double b = 0, lam = 0;
};

inline double sigmoid(double z) { return 1.0 / (1.0 + std::exp(-z)); }

inline LRModel fitLR(const std::vector<std::vector<double>>& rows,
                     const std::vector<double>& ys, double lam, int iters = 300) {
  LRModel m;
  const size_t n = rows.size();
  if (!n) return m;
  const size_t d = rows[0].size();
  m.w.assign(d, 0.0);
  m.lam = lam;
  const double lr = 0.1;
  for (int it = 0; it < iters; ++it) {
    std::vector<double> g(d, 0.0);
    double gb = 0.0;
    for (size_t i = 0; i < n; ++i) {
      double z = m.b;
      for (size_t j = 0; j < d; ++j) z += m.w[j] * rows[i][j];
      const double e = sigmoid(z) - ys[i];
      for (size_t j = 0; j < d; ++j) g[j] += e * rows[i][j];
      gb += e;
    }
    for (size_t j = 0; j < d; ++j) m.w[j] -= lr * (g[j] / double(n) + lam * m.w[j]);
    m.b -= lr * (gb / double(n));
  }
  return m;
}
inline double predictLR(const LRModel& m, const std::vector<double>& x) {
  double z = m.b;
  for (size_t j = 0; j < m.w.size() && j < x.size(); ++j) z += m.w[j] * x[j];
  return sigmoid(z);
}
inline Json model_json(const LRModel& m) {
  Json o = Json::object();
  Json w = Json::array();
  for (double v : m.w) w.push(Json(v));
  o.set("w", w);
  o.set("b", m.b);
  o.set("lam", m.lam);
  return o;
}
inline LRModel model_of(const Json& o) {
  LRModel m;
  for (const Json& v : o["w"].arr()) m.w.push_back(v.asNum());
  m.b = o["b"].asNum();
  m.lam = o["lam"].asNum();
  return m;
}

// Platt scaling: fit a,b so sigmoid(a*logit+b) matches observed outcomes.
inline Json calibrate(const Json& logits, const Json& ys) {
  double a = 1.0, b = 0.0;
  const size_t n = logits.size();
  if (!n) { Json o = Json::object(); o.set("a", a); o.set("b", b); return o; }
  for (int it = 0; it < 200; ++it) {
    double ga = 0, gb = 0;
    for (size_t i = 0; i < n; ++i) {
      const double l = logits[i].asNum(), y = ys[i].asNum();
      const double e = sigmoid(a * l + b) - y;
      ga += e * l; gb += e;
    }
    a -= 0.1 * ga / double(n);
    b -= 0.1 * gb / double(n);
  }
  Json o = Json::object();
  o.set("a", a);
  o.set("b", b);
  return o;
}

// Bernoulli's gate: the logistic method earns the wheel only if its
// held-out log-likelihood margin over the prior reaches the moral bar.
inline Json chooseMethod(double ll_prior, double ll_lr) {
  const double loglr = ll_lr - ll_prior;
  Json o = Json::object();
  o.set("loglr", loglr);
  o.set("moral", loglr >= std::log(1000.0));
  o.set("method", Json(std::string(loglr >= std::log(1000.0) ? "lr" : "prior")));
  return o;
}

// Per-concept forecast at horizon T: events decay toward the 1/2 prior
// with time constant tau (forgetting curve), Laplace-smoothed by weights.
inline Json analyze(const Json& items, int K, double tau, double T, const Json& excluded) {
  Json out = Json::array();
  for (int c = 0; c < K; ++c) {
    bool skip = false;
    for (const Json& e : excluded.arr()) if (e.asInt(-1) == c) skip = true;
    if (skip) continue;
    double wsum = 0, acc = 0, tlast = -1;
    int n = 0;
    for (const Json& it : items.arr()) {
      if (it["c"].asInt(-1) != c) continue;
      const double t = it["t"].asNum(0);
      if (t > T) continue;
      const double w = std::exp(-(T - t) / (tau > 0 ? tau : 1.0));
      wsum += w;
      acc += w * (it["ok"].asBool(false) ? 1.0 : 0.0);
      if (t > tlast) tlast = t;
      ++n;
    }
    const double p0 = (acc + 0.5 * 1.0) / (wsum + 1.0);
    const double p = n ? p0 + (0.5 - p0) * std::exp(-(T - (tlast < 0 ? T : tlast)) / (tau > 0 ? tau : 1.0)) : 0.5;
    Json o = Json::object();
    o.set("c", c);
    o.set("p", p);
    o.set("n", n);
    o.set("t_last", tlast);
    out.push(o);
  }
  return out;
}

// Verdict under the constitution: clamp, nudge-cap, attempt-cap, trim.
inline Json verdict(const Json& fc) {
  Json capped = Json::array();
  double p = fc["p"].asNum(0.5);
  const double prior = fc["prior"].asNum(0.5);
  if (p > cos::MAXP) { p = cos::MAXP; capped.push(Json(std::string("maxp"))); }
  if (p < 1.0 - cos::MAXP) { p = 1.0 - cos::MAXP; capped.push(Json(std::string("maxp"))); }
  double d = p - prior;
  if (d > cos::MAX_NUDGE) { d = cos::MAX_NUDGE; capped.push(Json(std::string("nudge"))); }
  if (d < -cos::MAX_NUDGE) { d = -cos::MAX_NUDGE; capped.push(Json(std::string("nudge"))); }
  p = prior + d;
  const int attempts = fc["attempts"].asInt(0);
  std::string v = "allow";
  if (attempts > cos::CAP_ATTEMPTS) { v = "stop"; capped.push(Json(std::string("attempts"))); }
  Json detail = fc["detail"];
  if (detail.isArr() && (int)detail.size() > cos::KEEP_DETAIL) {
    Json t = Json::array();
    for (int i = 0; i < cos::KEEP_DETAIL; ++i) t.push(detail[size_t(i)]);
    detail = t;
    capped.push(Json(std::string("detail")));
  }
  Json o = Json::object();
  o.set("p", p);
  o.set("verdict", Json(v));
  o.set("capped", capped);
  o.set("detail", detail);
  return o;
}

}  // namespace ef
}  // namespace saem
