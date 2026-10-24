// Cognitive layer: beliefs at log-odds, moved by cases the way Bernoulli
// moved expectation by observed cases (Ars Conjectandi I.2-3), declared
// at his Part IV bar of 1000:1 moral certainty. Keeping belief in the log
// domain is Napier's trick once more: evidence multiplies, so here it
// adds. The learner is a library, not a publisher: per the repo's own
// gates it may advise, never ship.
#pragma once
#include <cmath>
#include <string>
#include <vector>

#include "json.hpp"

namespace saem {

struct Belief {
  Json prop;
  double logodds = 0;  // ln(P/(1-P)); 0 is exactly undecided
  double shots = 0;    // cases folded in so far
  double prob() const { return 1.0 / (1.0 + std::exp(-logodds)); }
  double odds() const { return std::exp(logodds); }
};

inline double binom_lr(double k, double n, double p, double q) {
  return k * std::log(p / q) + (n - k) * std::log((1 - p) / (1 - q));
}
inline void update(Belief& b, double k, double n, double p, double q) {
  if (p <= 0 || p >= 1 || q <= 0 || q >= 1 || n <= 0) return;
  b.logodds += binom_lr(k, n, p, q);
  b.shots += n;
}
inline bool moral(const Belief& b, double bar = 1000.0) {
  return std::fabs(b.logodds) >= std::log(bar);
}
// Bernoulli proved enough trials always reach the bar (his own count:
// 25,550 for 1000:1 at margin 1/50). Hoeffding is the tight scheduler.
inline double shots_for(double bar, double margin) {
  return std::log(2.0 * bar) / (2.0 * margin * margin);
}

struct Learner {
  double slip = 0.10;   // P(slip | mastered)
  double guess = 0.25;  // P(lucky | not mastered)
  std::vector<Belief> bs;

  Belief& topic(const std::string& t) {
    for (Belief& b : bs) if (b.prop.asStr() == t) return b;
    Belief b;
    b.prop = Json(t);
    bs.push_back(b);
    return bs.back();
  }
  void observe(const std::string& t, bool correct) {
    Belief& b = topic(t);
    double p = 1.0 - slip, q = guess;
    b.logodds += std::log(correct ? p / q : (1.0 - p) / (1.0 - q));
    b.shots += 1;
  }
  bool mastered(const std::string& t) const {
    for (const Belief& b : bs)
      if (b.prop.asStr() == t) return moral(b) && b.logodds > 0;
    return false;
  }
  // Bernoulli's next case: the topic farthest from moral certainty is
  // the one whose next trial carries the most information.
  std::string next() const {
    const Belief* best = nullptr;
    for (const Belief& b : bs)
      if (!best || std::fabs(b.logodds) < std::fabs(best->logodds)) best = &b;
    return best ? best->prop.asStr() : std::string();
  }
};

inline Json snapshot(const std::vector<Belief>& bs) {
  Json out = Json::array();
  for (const Belief& b : bs) {
    Json e = Json::object();
    e.set("prop", b.prop);
    e.set("p", b.prob());
    e.set("shots", b.shots);
    e.set("moral", moral(b));
    out.push(e);
  }
  return out;
}
inline Json snapshot(const Learner& L) { return snapshot(L.bs); }

}  // namespace saem
