// The constitution: the immutable core of the Saem system, as data.
// Articles are the faith the core is held to; the caps are the governance
// limits the forecast engine must obey. coreHash() fingerprints exactly
// this object through canon()+sha256, so amending one article changes the
// soul -- and the CI soul gate becomes a constitutional court: no amendment
// slips in without a run# ref, mirroring THINK.md I2.
#pragma once
#include <string>
#include <vector>

#include "json.hpp"
#include "kernel.hpp"   // canon()
#include "sha256.hpp"

namespace saem {
namespace cos {

inline const char* VERSION() { return "0.3.0"; }

// Governance caps. Semantics implemented in ef.hpp/verdict():
//   MAXP          reported probability is clamped to [1-MAXP, MAXP]
//   MAX_NUDGE     one forecast may move a belief by at most this much
//   CAP_ATTEMPTS  beyond this many attempts the verdict is "stop"
//   KEEP_DETAIL   audit detail lists are trimmed to this many entries
//   MAX_FACULTY   at most this many independent evidence sources per verdict
constexpr double MAXP = 0.95;
constexpr double MAX_NUDGE = 0.15;
constexpr int CAP_ATTEMPTS = 3;
constexpr int KEEP_DETAIL = 50;
constexpr int MAX_FACULTY = 4;

inline Json constitution() {
  Json a = Json::array();
  a.push(Json(std::string("A0: every answer is computed from the numbers in the question, never guessed.")));
  a.push(Json(std::string("A1: every number leaving the core prints exactly as the reference engine prints it.")));
  a.push(Json(std::string("A2: the door holds no hidden state; state travels in the JSON, in the caller's ledger.")));
  a.push(Json(std::string("A3: measurement and overwrite are the only irreversible acts; the core reports the debt it causes.")));
  a.push(Json(std::string("A4: no belief is declared without Bernoulli's bar of moral certainty, 1000:1.")));
  a.push(Json(std::string("A5: the ledger is append-only; rules without machine checks remain hypotheses.")));
  a.push(Json(std::string("A6: the JavaScript bridge is a ruler, never a fallback; the shipped product runs the core alone.")));
  return a;
}

// The object the hash commits to. Key order is part of the constitution.
inline Json core_object() {
  Json o = Json::object();
  o.set("version", Json(std::string(VERSION())));
  o.set("constitution", constitution());
  o.set("maxp", MAXP);
  o.set("maxFaculty", MAX_FACULTY);
  o.set("maxNudge", MAX_NUDGE);
  o.set("capAttempts", CAP_ATTEMPTS);
  o.set("keepDetail", KEEP_DETAIL);
  return o;
}
inline std::string coreHash() { return sha256_hex(canon(core_object())); }

// A receipt commits a core hash + item list + parameters to one digest.
inline Json receipt(const std::string& core, const Json& items, int K, const Json& notes) {
  Json payload = Json::array();
  payload.push(Json(core));
  payload.push(Json(K));
  payload.push(notes);
  payload.push(items);
  Json o = Json::object();
  o.set("core", Json(core));
  o.set("n", (int)items.size());
  o.set("K", K);
  o.set("notes", notes);
  o.set("hash", sha256_hex(canon(payload)));
  return o;
}
inline Json audit(const Json& a) {
  const std::string want = sha256_hex(canon([&] {
    Json p = Json::array();
    p.push(Json(a["core"].asStr()));
    p.push(Json(a["K"].asInt(0)));
    p.push(a["notes"]);
    p.push(a["items"]);
    return p;
  }()));
  Json o = Json::object();
  o.set("ok", want == a["hash"].asStr());
  o.set("expected", Json(want));
  o.set("got", a["hash"]);
  return o;
}

}  // namespace cos
}  // namespace saem
