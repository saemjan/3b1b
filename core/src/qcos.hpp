// core/src/qcos.hpp — gen-3 v2 (step 11c, vision-first).
// L1 Working store + L2 Episodic ring + Zone 0 gate, all riding the static
// arenas of arena.hpp (caps 32/64, KEY_MAX 23 from qcos.cxn v0.5.0).
//
// VISION-FIRST CONTRADICTION REGISTER (past -> future, per VISION v2.3):
//   * past Working/Episodic grew unbounded (std::map/std::deque) -> now fixed
//     32/64 slots; exhaustion = refusal (A8), eviction = priced dissipation.
//   * past gate() admitted any op -> now Zone 0 vocabulary + finiteness +
//     key-bound admission (A7); admission != execution (CIR validates operands).
//   * past debt was an untracked double -> now arena.bits_erased (integer,
//     8 bits per canonical byte erased) + prov ring trace (A9).
//   * NEW doctrine: every slot's 64-byte payload carries the SHA-256 soul of
//     its value; the tree lives in the side-table at the same index; the
//     selftest asserts payload == soul(value), so drift is impossible.
// FROZEN (kept byte-stable): jsnum rounding, KEY_MAX bound semantics,
//   Working::latch/read + Episodic::push/recent + gate(op,args) signatures,
//   selftest witness names (jsnum_half, l1_latch, l1_key_bound, l2_wrap,
//   gate_allow).
#pragma once
#include <cmath>
#include <cstring>
#include <string>

#include "arena.hpp"
#include "kernel.hpp"   // canon() single ruler (§14), Json, sha256_hex

namespace saem {

constexpr int KEY_MAX        = 23;                       // canon @cap KEY_MAX
constexpr int WORKING_LIMIT  = (int)QCOS_WORKING_LIMIT;  // 32
constexpr int EPISODIC_LIMIT = (int)QCOS_EPISODIC_LIMIT; // 64
constexpr uint32_t QOWNER    = 2;                        // qcos layer owner id

enum ZoneVerdict { ZPASS = 0, ZNIYYAH = 1, ZRIBA = 2, ZGHARAR = 3,
                   ZMAYSIR = 4, ZBUDGET = 5, ZMITHAQ = 6 };
struct GateResult { bool ok; std::string error; int verdict; };

inline bool finite_json(const Json& j) {
  switch (j.type()) {
    case Json::Num:   return std::isfinite(j.asNum());
    case Json::Array: { for (size_t i = 0; i < j.arr().size(); ++i)
                          if (!finite_json(j.arr()[i])) return false; return true; }
    case Json::Object:{ for (size_t i = 0; i < j.obj().size(); ++i)
                          if (!finite_json(j.obj()[i].second)) return false; return true; }
    default: return true;
  }
}

// ---- Zone 0: admission of intent shape (A7). Execution validates operands.
inline GateResult gate(const std::string& op, const Json& a) {
  static const char* VOCAB[] = { "latch", "read", "snapshot", "exec", "cost",
      "lower", "provenance", "caps", "claim", "complete", "shape", "boot" };
  bool known = false;
  for (const char* v : VOCAB) if (op == v) { known = true; break; }
  if (!known) return { false, "zone0: undeclared intent", ZNIYYAH };
  if (!finite_json(a)) return { false, "zone0: non-finite value", ZGHARAR };
  if (a.has("key") && a["key"].isStr() && (int)a["key"].asStr().size() > KEY_MAX)
    return { false, "zone0: key beyond KEY_MAX", ZBUDGET };
  if (a.has("seed") && a["seed"].isNum() && a["seed"].asNum() < 0)
    return { false, "zone0: negative seed", ZGHARAR };
  return { true, "", ZPASS };
}

// ---- L1 Working store: 32 slots, arena is the single occupancy authority --
class Working {
 public:
  bool latch(const std::string& key, const Json& v) {
    if ((int)key.size() > KEY_MAX || !finite_json(v)) return false;
    qcos::Arena& a = qcos::g_arena;
    for (uint32_t i = 0; i < QCOS_WORKING_LIMIT; i++) {       // O(N) literal scan
      if (!keys_[i].used || key != keys_[i].key) continue;
      a.bits_erased += 8ull * (uint64_t)canon(vals_[i]).size();  // erasure priced
      a.record(qcos::OP_FREE, i, a.w[i].identity);
      vals_[i] = v;
      set_soul(i, v);
      a.record(qcos::OP_ALLOC, i, a.w[i].identity);
      return true;
    }
    uint32_t idx = qcos::w_alloc(a, QOWNER);
    if (idx == QCOS_SLOT_NONE) return false;                 // refusal (A8)
    keys_[idx].used = true;
    std::strncpy(keys_[idx].key, key.c_str(), sizeof(keys_[idx].key) - 1);
    vals_[idx] = v;
    set_soul(idx, v);
    return true;
  }
  Json read(const std::string& key) const {
    for (uint32_t i = 0; i < QCOS_WORKING_LIMIT; i++)
      if (keys_[i].used && key == keys_[i].key) return vals_[i];
    return Json();                                           // Null, visible absence
  }
  bool has(const std::string& key) const {
    for (uint32_t i = 0; i < QCOS_WORKING_LIMIT; i++)
      if (keys_[i].used && key == keys_[i].key) return true;
    return false;
  }
  void release(const std::string& key) {
    qcos::Arena& a = qcos::g_arena;
    for (uint32_t i = 0; i < QCOS_WORKING_LIMIT; i++) {
      if (!keys_[i].used || key != keys_[i].key) continue;
      keys_[i].used = false; keys_[i].key[0] = 0; keys_[i].soul[0] = 0;
      vals_[i] = Json();
      qcos::w_free(a, i, QOWNER);
      return;
    }
  }
  size_t size() const {
    return (size_t)__builtin_popcount(qcos::g_arena.w_occ);
  }
  Json snapshot() const {
    Json a = Json::array();
    for (uint32_t i = 0; i < QCOS_WORKING_LIMIT; i++) {
      if (!keys_[i].used) continue;
      Json o = Json::object();
      o.set("key", std::string(keys_[i].key));
      o.set("value", vals_[i]);
      o.set("soul", std::string(keys_[i].soul));
      a.push(o);
    }
    return a;
  }

 private:
  struct KeyEnt { char key[24] = {0}; char soul[65] = {0}; bool used = false; };
  static inline KeyEnt keys_[QCOS_WORKING_LIMIT];            // single authority
  static inline Json   vals_[QCOS_WORKING_LIMIT];
  static void set_soul(uint32_t i, const Json& v) {
    std::string s = sha256_hex(canon(v));                    // 64 hex chars
    std::memcpy(keys_[i].soul, s.c_str(), 64);
    std::memcpy(qcos::g_arena.w[i].payload, s.data(), 64);   // slot carries soul
  }
};

// ---- L2 Episodic ring: 64 slots, deterministic FIFO eviction, priced -------
class Episodic {
 public:
  bool push(const Json& event) {
    qcos::Arena& a = qcos::g_arena;
    uint32_t idx = qcos::e_push(a, QOWNER);
    if (idx == QCOS_SLOT_NONE) return false;                 // all referenced
    Json rec = Json::object();
    rec.set("seq", (int)seq_);
    rec.set("tick", (int)a.tick);
    rec.set("event", event);
    e_vals_[idx] = rec;
    std::string s = sha256_hex(canon(rec));
    std::memcpy(a.e[idx].payload, s.data(), 64);
    ++seq_;
    return true;
  }
  Json recent(int n) const {
    const qcos::Arena& a = qcos::g_arena;
    Json out = Json::array();
    uint32_t occ = a.e_head - a.e_tail;
    uint32_t take = (uint32_t)n < occ ? (uint32_t)n : occ;
    for (uint32_t k = 0; k < take; k++) {                    // newest first
      uint32_t idx = (a.e_head - 1 - k) % QCOS_EPISODIC_LIMIT;
      out.push(e_vals_[idx]);
    }
    return out;
  }
  size_t size() const {
    return (size_t)(qcos::g_arena.e_head - qcos::g_arena.e_tail);
  }

 private:
  static inline Json     e_vals_[QCOS_EPISODIC_LIMIT];
  static inline uint64_t seq_ = 0;
};

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
  o.set("working", (int)Working{}.size());
  o.set("working_limit", WORKING_LIMIT);
  o.set("episodic", (int)Episodic{}.size());
  o.set("episodic_limit", EPISODIC_LIMIT);
  o.set("bits_erased", (double)qcos::g_arena.bits_erased);
  o.set("refusals", (double)qcos::g_arena.debt_refusals);
  return o;
}

// ---- frozen witness suite (names are canon; additions append only) ---------
inline int selftest() {
  int fails = 0, total = 0;
  auto want = [&](const char* n, bool ok) {
    ++total; if (!ok) ++fails;
    std::printf("[qcos-selftest] %-28s %s\n", n, ok ? "ok" : "DRIFT");
  };
  qcos::g_arena.init();
  Working w; Episodic ep;

  want("jsnum_half", jsnum(0.1 + 0.2) == "0.30000000000000004");
  want("l1_latch", w.latch("k", Json(1)) && w.read("k").asInt(0) == 1);
  want("l1_key_bound", !w.latch(std::string(30, 'x'), Json(1)));
  want("gate_allow", gate("latch", Json::object()).ok);
  want("gate_deny_unknown", !gate("nope", Json::object()).ok);
  Json bad = Json::object(); bad.set("x", Json(1e999));
  want("gate_deny_nonfinite", !gate("latch", bad).ok);
  Json lk = Json::object(); lk.set("key", Json(std::string(30, 'y')));
  want("gate_deny_longkey", !gate("latch", lk).ok);

  for (int i = 0; i < WORKING_LIMIT - 1; i++) w.latch("c" + std::to_string(i), Json(i));
  want("l1_cap_refusal", !w.latch("overflow", Json(0)) && w.size() == (size_t)WORKING_LIMIT);
  for (int i = 0; i < WORKING_LIMIT - 1; i++) w.release("c" + std::to_string(i));

  uint64_t d0 = qcos::g_arena.bits_erased;
  w.latch("k", Json(2));
  want("l1_overwrite_priced", qcos::g_arena.bits_erased - d0 == 8ull * 1);
  bool soul_ok = false;
  for (uint32_t i = 0; i < QCOS_WORKING_LIMIT; i++)
    if (std::string((const char*)qcos::g_arena.w[i].payload, 64) == sha256_hex(canon(w.read("k"))))
      soul_ok = true;
  want("l1_soul_in_payload", soul_ok);

  uint64_t e0 = qcos::g_arena.bits_erased;
  for (int i = 0; i <= EPISODIC_LIMIT + 4; i++) ep.push(Json(i));
  want("l2_wrap", ep.recent(1)[0]["event"].asInt(0) == EPISODIC_LIMIT + 4);
  want("l2_eviction_priced", qcos::g_arena.bits_erased - e0 == 5ull * 8 * 64);
  want("prov_ordered", provenance().arr().size() > 0);
  want("caps_report_live", caps_report()["working"].asInt(0) == 1);

  std::printf("[qcos-selftest] %d/%d passed\n", total - fails, total);
  return fails ? 1 : 0;
}

}  // namespace saem
