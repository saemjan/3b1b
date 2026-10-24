// core/src/qcos.hpp
#pragma once
#include <array>
#include <cmath>
#include <cstring>
#include <cstdint>
#include <limits>
#include <string>
#include <vector>
#include "cos.hpp"
#include "gen.hpp"
#include "json.hpp"
#include "qreg.hpp"
#include "rev.hpp"
#include "sha256.hpp"

namespace saem {
namespace qcos {
inline constexpr int WORKING_LIMIT = 32;
inline constexpr int EPISODIC_LIMIT = 64;
struct Slot { char key[24] = {0}; Json value; bool used = false; };
struct Working {
  std::array<Slot, WORKING_LIMIT> s;
  int find(const char* k) const {
    for (int i = 0; i < WORKING_LIMIT; ++i) if (s[i].used && std::strcmp(s[i].key, k) == 0) return i;
    return -1;
  }
  Json read(const std::string& k) const { const int i = find(k.c_str()); return i < 0 ? Json() : s[i].value; }
  bool latch(const std::string& k, const Json& v) {
    if (k.empty() || k.size() > 23) return false;
    int i = find(k.c_str());
    if (i < 0) for (int j = 0; j < WORKING_LIMIT; ++j) if (!s[j].used) { i = j; break; }
    if (i < 0) return false;
    std::memset(s[i].key, 0, sizeof(s[i].key));
    for (size_t c = 0; c < k.size() && c < 23; ++c) s[i].key[c] = k[c];
    s[i].value = v; s[i].used = true; return true;
  }
  Json snapshot() const {
    Json a = Json::array();
    for (int i = 0; i < WORKING_LIMIT; ++i)
      if (s[i].used) { Json e = Json::object(); e.set("key", Json(std::string(s[i].key))); e.set("value", s[i].value); a.push(e); }
    return a;
  }
  bool restore(const Json& a) {
    if (!a.isArr()) return false;
    for (int i = 0; i < WORKING_LIMIT; ++i) { s[i].used = false; s[i].key[0] = 0; s[i].value = Json(); }
    for (const Json& e : a.arr()) if (!latch(e["key"].asStr(), e["value"])) return false;
    return true;
  }
};
struct Episodic {
  std::array<Json, EPISODIC_LIMIT> r; uint64_t head = 0, count = 0;
  void push(const Json& e) { r[head % EPISODIC_LIMIT] = e; ++head; ++count; }
  Json recent(int n) const {
    const uint64_t stored = count < (uint64_t)EPISODIC_LIMIT ? count : (uint64_t)EPISODIC_LIMIT;
    const uint64_t take = (uint64_t)n < stored ? (uint64_t)n : stored;
    Json a = Json::array();
    for (uint64_t i = 0; i < take; ++i) {
      const uint64_t idx = (head - take + i) % EPISODIC_LIMIT;
      Json e = Json::object(); e.set("tick", (int)idx); e.set("event", r[idx]); a.push(e);
    }
    return a;
  }
};
struct Verdict { bool ok = true; Json reasons = Json::array(); };
inline void deny(Verdict& v, const std::string& why) { v.ok = false; v.reasons.push(Json(why)); }
inline bool finite_num(const Json& j) {
  if (j.isNum()) return std::isfinite(j.asNum());
  if (j.isArr()) { for (const Json& e : j.arr()) if (!finite_num(e)) return false; return true; }
  if (j.isObj()) { for (const auto& kv : j.obj()) if (!finite_num(kv.second)) return false; return true; }
  return true;
}
inline Verdict gate(const std::string& op, const Json& args) {
  Verdict v;
  static const char* ops[] = {"latch", "read", "episode", "lower", "exec", "snapshot", "restore", "cost", "provenance", "gate"};
  bool known = false; for (const char* o : ops) if (op == o) known = true;
  if (!known) { deny(v, "gate: unknown op " + op); return v; }
  if (!finite_num(args)) deny(v, "gate: non-finite number in args");
  if (args.has("key")) { const std::string k = args["key"].asStr(); if (k.empty() || k.size() > 23) deny(v, "gate: key length out of bounds"); }
  if (args.has("p")) { const double p = args["p"].asNum(); if (p > cos::MAXP || p < 1.0 - cos::MAXP) deny(v, "gate: p beyond MAXP"); }
  if (args.has("nudge") && std::fabs(args["nudge"].asNum()) > cos::MAX_NUDGE) deny(v, "gate: nudge beyond MAX_NUDGE");
  if (op == "exec" && args.has("cir") && (int)args["cir"]["steps"].size() > 4096) deny(v, "gate: cir steps beyond budget");
  return v;
}
inline Json lower_sir(const Json& intent) {
  Json ops = Json::array(); const std::string want = intent["want"].asStr();
  if (want == "store") { Json o = Json::object(); o.set("op", Json(std::string("latch"))); o.set("key", intent["key"]); o.set("value", intent["value"]); ops.push(o); }
  else if (want == "combine") { Json o = Json::object(); o.set("op", Json(std::string("add"))); o.set("a", intent["a"]); o.set("b", intent["b"]); o.set("dst", intent["dst"]); ops.push(o); }
  else if (want == "solve") { Json o = Json::object(); o.set("op", Json(std::string("solve"))); o.set("id", intent["id"]); o.set("params", intent["params"]); o.set("dst", intent["dst"]); ops.push(o); }
  else { Json o = Json::object(); o.set("op", Json(std::string("noop"))); ops.push(o); }
  Json sir = Json::object(); sir.set("ops", ops); return sir;
}
inline Json lower_dir(const Json& sir) {
  const int n = (int)sir["ops"].size(); Json mask = Json::array(); for (int i = 0; i < n; ++i) mask.push(Json(1));
  Json dir = Json::object(); dir.set("shape", Json(std::string(n > 1 ? "LINE" : "SCALAR"))); dir.set("topology", Json(std::string("LINE"))); dir.set("dims", n); dir.set("mask", mask); return dir;
}
inline Json lower_cir(const Json& sir, const Json& dir) {
  Json steps = Json::array(); const Json& ops = sir["ops"];
  for (size_t i = 0; i < ops.size(); ++i) {
    Json st = Json::object(); st.set("step", (int)i); st.set("op", ops[i]["op"]);
    if (ops[i].has("key")) st.set("key", ops[i]["key"]); if (ops[i].has("value")) st.set("value", ops[i]["value"]);
    if (ops[i].has("dst")) st.set("dst", ops[i]["dst"]); if (ops[i].has("a")) st.set("a", ops[i]["a"]);
    if (ops[i].has("b")) st.set("b", ops[i]["b"]); if (ops[i].has("id")) st.set("id", ops[i]["id"]);
    if (ops[i].has("params")) st.set("params", ops[i]["params"]);
    st.set("sync", Json(std::string("barrier"))); steps.push(st);
  }
  Json cir = Json::object(); cir.set("steps", steps); cir.set("shape", dir["shape"]); return cir;
}
inline Json lower_mir(const Json& cir, const std::string& target) {
  Json micro = Json::array();
  for (const Json& st : cir["steps"].arr()) { Json m = Json::object(); m.set("u", st["op"]); m.set("regs", st); micro.push(m); }
  Json mir = Json::object(); mir.set("target", Json(target)); mir.set("micro", micro); return mir;
}
struct ExecResult { bool ok = true; Json trace = Json::array(); };
inline ExecResult exec_cir(Working& w, const Json& cir) {
  ExecResult r;
  for (const Json& st : cir["steps"].arr()) {
    const std::string op = st["op"].asStr(); Json t = Json::object(); t.set("step", st["step"]); t.set("op", st["op"]);
    if (op == "latch") {
      if (!w.latch(st["key"].asStr(), st["value"])) { t.set("err", Json(std::string("working full or key out of bounds"))); r.trace.push(t); r.ok = false; break; }
    } else if (op == "add") {
      const double a = w.read(st["a"].asStr()).asNum(0) + w.read(st["b"].asStr()).asNum(0);
      if (!w.latch(st["dst"].asStr(), Json(a))) { t.set("err", Json(std::string("working full"))); r.trace.push(t); r.ok = false; break; }
      t.set("dst", st["dst"]); t.set("v", a);
    } else if (op == "solve") {
      const Json sol = gen::solve(st["id"].asStr(), st["params"]);
      if (!w.latch(st["dst"].asStr(), sol)) { t.set("err", Json(std::string("working full"))); r.trace.push(t); r.ok = false; break; }
      t.set("dst", st["dst"]);
    } else if (op == "noop") {
    } else { t.set("err", Json(std::string("unknown cir op"))); r.trace.push(t); r.ok = false; break; }
    r.trace.push(t);
  }
  return r;
}
inline bool verify_log(const Json& log) {
  std::string p = std::string(64, '0');
  for (const Json& e : log.arr()) {
    Json e0 = Json::object(); e0.set("tick", e["tick"]); e0.set("what", e["what"]); e0.set("where", e["where"]); e0.set("when", e["when"]); e0.set("why", e["why"]);
    Json payload = Json::array(); payload.push(Json(p)); payload.push(e0);
    const std::string h = sha256_hex(canon(payload)); if (h != e["hash"].asStr()) return false; p = h;
  }
  return true;
}
struct Provenance {
  std::string prev = std::string(64, '0'); int tick = 0; Json log = Json::array();
  std::string append(const std::string& what, const std::string& where, const std::string& why) {
    Json e0 = Json::object(); e0.set("tick", tick); e0.set("what", Json(what)); e0.set("where", Json(where)); e0.set("when", Json(std::string("tick"))); e0.set("why", Json(why));
    Json payload = Json::array(); payload.push(Json(prev)); payload.push(e0);
    const std::string h = sha256_hex(canon(payload)); Json e = e0; e.set("hash", Json(h)); log.push(e); prev = h; ++tick; return h;
  }
  bool verify() const { return verify_log(log); }
};

inline Json self_test() {
  Json failed = Json::array(); int checks = 0;
  // Fixed: Lambda capture syntax
  auto want = [&](bool ok, const char* name) { ++checks; if (!ok) failed.push(Json(std::string(name))); };
  want(sha256_hex("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "sha256_empty");
  QReg r(2, 7); r.h(0); r.cnot(0, 1);
  want(std::fabs(r.norm() - 1.0) < 1e-12 && std::fabs(r.prob1(0) - 0.5) < 1e-12, "bell");
  Bits b = {1, 1, 0, 0}; const std::vector<Gate> add = {gccnot(0, 1, 2), gcnot(0, 3), gcnot(1, 3)}; run(b, add);
  want(b[2] == 1 && b[3] == 0, "adder");
  want(jsnum(0.1 + 0.2) == "0.30000000000000004", "jsnum_half");
  Working w; want(w.latch("k", Json(1)) && w.read("k").asInt(0) == 1, "l1_latch");
  want(!w.latch(std::string(30, 'x'), Json(1)), "l1_key_bound");
  Episodic ep; for (int i = 0; i < EPISODIC_LIMIT + 5; ++i) ep.push(Json(i));
  want(ep.recent(1)[size_t(0)]["event"].asInt(0) == EPISODIC_LIMIT + 4, "l2_wrap");
  want(gate("latch", Json::object()).ok, "gate_allow");
  Json bad = Json::object(); bad.set("x", Json(std::numeric_limits<double>::infinity()));
  want(!gate("latch", bad).ok, "gate_nonfinite");
  Json intent = Json::object(); intent.set("want", Json(std::string("store"))); intent.set("key", Json(std::string("a"))); intent.set("value", Json(2));
  const Json s1 = lower_sir(intent); const Json cir1 = lower_cir(s1, lower_dir(s1));
  const Json s2 = lower_sir(intent); const Json cir2 = lower_cir(s2, lower_dir(s2));
  want(canon(cir1) == canon(cir2), "lower_deterministic");
  Working w2; const ExecResult er = exec_cir(w2, cir1);
  want(er.ok && w2.read("a").asInt(0) == 2, "exec_store");
  Provenance pv; pv.append("t1", "here", "why"); const std::string h1 = pv.prev; pv.append("t2", "here", "why");
  want(pv.verify() && pv.prev != h1, "prov_chain");
  Json o = Json::object(); o.set("ok", failed.size() == 0); o.set("checks", checks); o.set("failed", failed);
  return o;
}
}}
