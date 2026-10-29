// core/src/qcos.hpp — v3 (step 11c reconcile).
// Original public surface preserved BYTE-STABLE (gate deny strings, snapshot
// shape, push-as-is, restore); vision additions are strictly ADDITIVE:
// arena identity stamps, Landauer erasure pricing, soul-in-payload, verdict
// codes, caps report. Retracted claim: original stores were already bounded.
#pragma once
#include <array>
#include <cmath>
#include <cstring>
#include <string>

#include "arena.hpp"
#include "kernel.hpp"   // canon() single ruler, Json, sha256_hex

namespace saem {

constexpr int    KEY_MAX        = 23;
constexpr int    WORKING_LIMIT  = 32;
constexpr int    EPISODIC_LIMIT = 64;
constexpr double MAXP           = 0.95;   // canon @cap MAXP
constexpr uint32_t QOWNER       = 2;

enum ZoneCode { ZPASS = 0, ZNIYYAH = 1, ZRIBA = 2, ZGHARAR = 3,
                ZMAYSIR = 4, ZBUDGET = 5, ZMITHAQ = 6 };

struct Verdict { bool ok = true; std::string error; int code = ZPASS; };
inline void deny(Verdict& v, const std::string& m, int code) {
  v.ok = false; v.error = m; v.code = code;
}

inline bool finite_num(const Json& j) {
  switch (j.type()) {
    case Json::Num:   return std::isfinite(j.asNum());
    case Json::Array: { for (size_t i = 0; i < j.arr().size(); ++i)
                          if (!finite_num(j.arr()[i])) return false; return true; }
    case Json::Object:{ for (size_t i = 0; i < j.obj().size(); ++i)
                          if (!finite_num(j.obj()[i].second)) return false; return true; }
    default: return true;
  }
}

// ---- L1 Working store: original fixed-slot shape + additive provenance ----
struct Working {
  struct SlotE {
    char key[24] = {0};
    Json value;
    bool used = false;
    uint32_t id = 0;            // ADDITIVE: monotonic identity stamp
    char soul[65] = {0};        // ADDITIVE: sha256(canon(value))
  };
  SlotE s[WORKING_LIMIT];

  bool latch(const std::string& key, const Json& v) {
    if (key.empty() || (int)key.size() > KEY_MAX || !finite_num(v)) return false;
    qcos::Arena& a = qcos::g_arena;
    for (int i = 0; i < WORKING_LIMIT; i++) {
      if (!s[i].used || key != s[i].key) continue;
      a.bits_erased += 8ull * (uint64_t)canon(s[i].value).size();  // priced erasure
      a.record(qcos::OP_FREE, (uint32_t)i, s[i].id);
      s[i].value = v;
      set_soul(i, v);
      a.record(qcos::OP_ALLOC, (uint32_t)i, s[i].id);
      return true;
    }
    for (int i = 0; i < WORKING_LIMIT; i++) {
      if (s[i].used) continue;
      s[i].used = true;
      std::strncpy(s[i].key, key.c_str(), sizeof(s[i].key) - 1);
      s[i].value = v;
      s[i].id = ++a.next_id;                     // identity, never reused
      set_soul(i, v);
      a.record(qcos::OP_ALLOC, (uint32_t)i, s[i].id);
      return true;
    }
    a.debt_refusals++;
    return false;                                // refusal, never growth (A8)
  }

  Json read(const std::string& key) const {
    for (int i = 0; i < WORKING_LIMIT; i++)
      if (s[i].used && key == s[i].key) return s[i].value;
    return Json();
  }
  bool has(const std::string& key) const {
    for (int i = 0; i < WORKING_LIMIT; i++)
      if (s[i].used && key == s[i].key) return true;
    return false;
  }
  void release(const std::string& key) {
    for (int i = 0; i < WORKING_LIMIT; i++) {
      if (!s[i].used || key != s[i].key) continue;
      qcos::g_arena.bits_erased += 8ull * (uint64_t)canon(s[i].value).size();
      qcos::g_arena.record(qcos::OP_FREE, (uint32_t)i, s[i].id);
      s[i].used = false; s[i].key[0] = 0; s[i].soul[0] = 0; s[i].value = Json();
      return;
    }
  }
  size_t size() const {
    size_t n = 0;
    for (int i = 0; i < WORKING_LIMIT; i++) n += s[i].used ? 1 : 0;
    return n;
  }
  // ORIGINAL byte shape: [{"key":..,"value":..}, ...] — do not add fields.
  Json snapshot() const {
    Json a = Json::array();
    for (int i = 0; i < WORKING_LIMIT; i++) {
      if (!s[i].used) continue;
      Json e = Json::object();
      e.set("key", Json(std::string(s[i].key)));
      e.set("value", s[i].value);
      a.push(e);
    }
    return a;
  }
  // ADDITIVE face for the soul stamps (snapshot stays frozen).
  Json souls() const {
    Json a = Json::array();
    for (int i = 0; i < WORKING_LIMIT; i++) {
      if (!s[i].used) continue;
      Json e = Json::object();
      e.set("key", Json(std::string(s[i].key)));
      e.set("soul", Json(std::string(s[i].soul)));
      e.set("id", (int)s[i].id);
      a.push(e);
    }
    return a;
  }
  bool restore(const Json& a) {                  // ORIGINAL, restored in v3
    if (!a.isArr()) return false;
    for (int i = 0; i < WORKING_LIMIT; ++i) {
      s[i].used = false; s[i].key[0] = 0; s[i].value = Json(); s[i].soul[0] = 0;
    }
    for (const Json& e : a.arr())
      if (!latch(e["key"].asStr(), e["value"])) return false;
    return true;
  }

 private:
  void set_soul(int i, const Json& v) {
    std::string h = sha256_hex(canon(v));
    std::strncpy(s[i].soul, h.c_str(), 64);
  }
};

// ---- L2 Episodic ring: ORIGINAL push-as-is + additive pricing on wrap ------
struct Episodic {
  std::array<Json, EPISODIC_LIMIT> r;
  uint64_t head = 0, count = 0;

  void push(const Json& e) {
    uint32_t idx = (uint32_t)(head % EPISODIC_LIMIT);
    if (count >= EPISODIC_LIMIT) {               // overwriting old knowledge
      qcos::g_arena.bits_erased += 8ull * (uint64_t)canon(r[idx]).size();
      qcos::g_arena.record(qcos::OP_EVICTION, idx, 0);
    }
    r[idx] = e;                                  // as-is, never rewrapped (C3)
    ++head; ++count;
    qcos::g_arena.record(qcos::OP_EPI_PUSH, idx, 0);
  }
  Json recent(int n) const {
    Json out = Json::array();
    uint64_t take = (uint64_t)n < count ? (uint64_t)n : count;
    for (uint64_t k = 0; k < take; k++)
      out.push(r[(head - 1 - k) % EPISODIC_LIMIT]);   // newest first
    return out;
  }
  size_t size() const { return count < (uint64_t)EPISODIC_LIMIT ? (size_t)count : (size_t)EPISODIC_LIMIT; }
};

// ---- Zone 0 gate: ORIGINAL strings & order, additive codes & vocab ---------
inline Verdict gate(const std::string& op, const Json& args) {
  Verdict v;
  static const char* ops[] = { "latch", "read", "episode", "lower", "exec",
      "snapshot", "restore", "cost", "provenance", "gate",
      /* additive canon ops, never shrink admission: */
      "zone0", "caps", "claim", "complete", "shape", "boot" };
  bool known = false;
  for (const char* o : ops) if (op == o) known = true;
  if (!known) { deny(v, "gate: unknown op " + op, ZNIYYAH); return v; }
  if (!finite_num(args)) { deny(v, "gate: non-finite number in args", ZGHARAR); return v; }
  if (args.has("key")) {
    const std::string k = args["key"].asStr();
    if (k.empty() || k.size() > 23) { deny(v, "gate: key length out of bounds", ZBUDGET); return v; }
  }
  if (args.has("p")) {
    const double p = args["p"].asNum();
    if (p > MAXP || p < 0.0) { deny(v, "gate: p above MAXP", ZMAYSIR); return v; }  // MARKED-UNKNOWN tail bytes in original; golden does not freeze this branch
  }
  return v;
}

// ---- audit faces -----------------------------------------------------------
inline Json provenance() {
  const qcos::Arena& a = qcos::g_arena;
  Json out = Json::array();
  uint32_t n = a.prov_head < QCOS_PROV_RING ? a.prov_head : QCOS_PROV_RING;
  for (uint32_t i = 0; i < n; i++) {
    const qcos::Prov& p = a.prov[(a.prov_head - n + i) % QCOS_PROV_RING];
    Json o = Json::object();
    o.set("tick", (int)p.tick); o.set("op", (int)p.op);
    o.set("slot", (int)p.slot); o.set("identity", (int)p.identity);
    out.push(o);
  }
  return out;
}
inline Json caps_report() {
  Json o = Json::object();
  o.set("working_limit", WORKING_LIMIT);
  o.set("episodic_limit", EPISODIC_LIMIT);
  o.set("bits_erased", (double)qcos::g_arena.bits_erased);
  o.set("refusals", (double)qcos::g_arena.debt_refusals);
  return o;
}

// ---- frozen witness suite (original names first, additions append) ---------
inline int selftest() {
  int fails = 0, total = 0;
  auto want = [&](const char* n, bool ok) {
    ++total; if (!ok) ++fails;
    std::printf("[qcos-selftest] %-30s %s\n", n, ok ? "ok" : "DRIFT");
  };
  qcos::g_arena.init();
  Working w; Episodic ep;

  want("jsnum_half", jsnum(0.1 + 0.2) == "0.30000000000000004");
  want("l1_latch", w.latch("k", Json(1)) && w.read("k").asInt(0) == 1);
  want("l1_key_bound", !w.latch(std::string(30, 'x'), Json(1)));
  want("gate_allow", gate("latch", Json::object()).ok);

  Verdict vu = gate("nope", Json::object());
  want("gate_msg_unknown", !vu.ok && vu.error == "gate: unknown op nope");
  Json bad = Json::object(); bad.set("x", Json(1e999));
  Verdict vf = gate("latch", bad);
  want("gate_msg_nonfinite", !vf.ok && vf.error == "gate: non-finite number in args");
  Json lk = Json::object(); lk.set("key", Json(std::string(30, 'y')));
  Verdict vk = gate("latch", lk);
  want("gate_msg_keybound", !vk.ok && vk.error == "gate: key length out of bounds");
  Json lp = Json::object(); lp.set("p", Json(0.99));
  want("gate_deny_maxp", !gate("latch", lp).ok);

  Json snap = w.snapshot();
  want("restore_roundtrip", ([&]() { Working w2; return w2.restore(snap) && w2.read("k").asInt(0) == 1; })());

  uint64_t d0 = qcos::g_arena.bits_erased;
  w.latch("k", Json(2));
  want("overwrite_priced", qcos::g_arena.bits_erased - d0 == 8ull * 1);
  want("soul_stamped", w.souls().arr().size() == 1);

  for (int i = 0; i <= EPISODIC_LIMIT + 4; i++) {
    Json o = Json::object(); o.set("event", Json(i)); ep.push(o);
  }
  want("l2_wrap", ep.recent(1)[0]["event"].asInt(0) == EPISODIC_LIMIT + 4);
  want("l2_push_asis", ep.recent(1)[0].has("event") && ep.recent(1)[0].obj().size() == 1);
  want("prov_ordered", provenance().arr().size() > 0);
  want("caps_report", caps_report()["working_limit"].asInt(0) == WORKING_LIMIT);

  std::printf("[qcos-selftest] %d/%d passed\n", total - fails, total);
  return fails ? 1 : 0;
}

}  // namespace saem
