// core/src/kernel.hpp — Fresh upgrade (2026-10-30)
// Zero-heap quantum process kernel with static arenas.
// Doctrine: xv6 proc[] fixed pool, arena.hpp four-axis slots,
// Landauer integer pricing (8 bits per canonical byte erased).
//
// API CONTRACT (frozen):
//   Proc{name, prog, schedule, pc}
//   Kernel::spawn/find/add_step/tick/set/get/board/entropy_debt_kTln2/soul/status/reap
//   canon(Json) — the single A1 ruler for JSON canonicalization
//
// CHANGES from original:
//   * std::string name -> char name[64] (KCOS_NAME_MAX)
//   * std::vector<pair> schedule -> Schedule struct with fixed array + same vocabulary
//   * debt_bits_ double -> uint64_t bits_erased (integer Landauer, A4)
//   * arena.hpp integration: every Proc gets a working-arena slot (identity axis)
//   * Exhaustion = refusal (QCOS_SLOT_NONE), never growth (A8)
#pragma once

#include <cstdint>
#include <cstring>
#include <new>
#include <string>
#include <utility>

#include "arena.hpp"
#include "cog.hpp"      // Json, jsnum
#include "qreg.hpp"     // QProg, Gate
#include "sha256.hpp"   // sha256_hex

namespace saem {

constexpr size_t   KCOS_NAME_MAX  = 64;      // mirrors canon @cap NAME_MAX
constexpr size_t   KSCHED_MAX     = 64;      // fixed schedule horizon per proc
constexpr uint64_t KDEFAULT_SEED  = 0x5AEE;  // streamU contract seed

// ---- A1 canonical printer (insertion order preserved, exact jsnum) ----
inline std::string canon(const Json& j) {
  switch (j.type()) {
    case Json::Null: return "null";
    case Json::Bool: return j.asBool() ? "true" : "false";
    case Json::Num:  return jsnum(j.asNum());
    case Json::Str: {
      std::string out; out += '"';
      for (unsigned char c : j.asStr()) {
        if (c == '"' || c == '\\') { out += '\\'; out += static_cast<char>(c); }
        else if (c == '\n') out += "\\n";
        else if (c == '\t') out += "\\t";
        else if (c == '\r') out += "\\r";
        else if (c < 0x20) {
          char b[8]; std::snprintf(b, sizeof b, "\\u%04x", c); out += b;
        } else out += static_cast<char>(c);
      }
      out += '"'; return out;
    }
    case Json::Array: {
      std::string s = "[";
      const Json::Arr& a = j.arr();
      for (size_t i = 0; i < a.size(); ++i) {
        if (i) s += ",";
        s += canon(a[i]);
      }
      return s + "]";
    }
    case Json::Object: {
      std::string s = "{";
      const Json::Obj& o = j.obj();
      for (size_t i = 0; i < o.size(); ++i) {
        if (i) s += ",";
        std::string k; k += '"';
        for (unsigned char c : o[i].first) {
          if (c == '"' || c == '\\') { k += '\\'; k += static_cast<char>(c); }
          else if (c == '\n') k += "\\n";
          else if (c == '\t') k += "\\t";
          else if (c == '\r') k += "\\r";
          else if (c < 0x20) {
            char b[8]; std::snprintf(b, sizeof b, "\\u%04x", c); k += b;
          } else k += static_cast<char>(c);
        }
        k += '"';
        s += k + ":" + canon(o[i].second);
      }
      return s + "}";
    }
  }
  return "null";
}

// ---- Fixed schedule with the original vector<pair> vocabulary ----
struct ScheduleStep { double first = 0.0; Gate second{}; };
struct Schedule {
  ScheduleStep step[KSCHED_MAX] = {};
  size_t n = 0;
  
  size_t size() const { return n; }
  bool empty() const { return n == 0; }
  void clear() { n = 0; }
  
  ScheduleStep& operator[](size_t i) { return step[i]; }
  const ScheduleStep& operator[](size_t i) const { return step[i]; }
  
  void push_back(const std::pair<double, Gate>& p) {
    if (n < KSCHED_MAX) {
      step[n].first = p.first;
      step[n].second = p.second;
      ++n;
    }
  }
  
  void push_back(double prob, const Gate& g) {
    push_back(std::make_pair(prob, g));
  }
  
  template <class... A>
  void emplace_back(A&&... a) {
    push_back(std::pair<double, Gate>(std::forward<A>(a)...));
  }
};

// ---- Proc: quantum process descriptor ----
struct Proc {
  uint32_t   slot = QCOS_SLOT_NONE;          // arena identity axis
  char       name[KCOS_NAME_MAX] = {0};
  QProg      prog;
  Schedule   schedule;
  size_t     pc = 0;

  Proc(const std::string& n, size_t nreg, size_t k, uint64_t seed)
      : prog(nreg, k, seed) {
    std::strncpy(name, n.c_str(), KCOS_NAME_MAX - 1);
  }
  
  bool done() const { return pc >= schedule.size(); }
  double halted() const { return prog.prob_halt(); }
};

// ---- Kernel: process manager with static storage ----
class Kernel {
 public:
  // Original signature preserved: returns Proc& (tombstone on exhaustion)
  Proc& spawn(const std::string& name, size_t nreg, size_t k,
              uint64_t seed = KDEFAULT_SEED) {
    Proc* p = try_spawn(name, nreg, k, seed);
    return p ? *p : tombstone();
  }
  
  // Vision-first: returns nullptr on pool exhaustion (A8 refusal)
  Proc* try_spawn(const std::string& name, size_t nreg, size_t k,
                  uint64_t seed = KDEFAULT_SEED) {
    if (name.size() >= KCOS_NAME_MAX) return nullptr;
    
    uint32_t slot = qcos::w_alloc(qcos::g_arena, KOWNER);
    if (slot == QCOS_SLOT_NONE) return nullptr;
    
    for (PSlot& s : procs_) {
      if (s.used) continue;
      s.used = true;
      s.slot = slot;
      Proc* p = new (s.raw) Proc(name, nreg, k, seed);
      p->slot = slot;
      return p;
    }
    qcos::w_free(qcos::g_arena, slot, KOWNER);  // symmetric unwind
    return nullptr;
  }
  
  bool refused(const Proc& p) const { return p.slot == QCOS_SLOT_NONE; }

  Proc* find(const std::string& name) {
    for (PSlot& s : procs_)
      if (s.used && std::strcmp(P(s)->name, name.c_str()) == 0) return P(s);
    return nullptr;
  }

  bool add_step(Proc& p, double prob, const Gate& g) {
    if (refused(p) || p.schedule.size() >= KSCHED_MAX) return false;
    p.schedule.push_back(prob, g);
    return true;
  }

  void tick() {
    for (PSlot& s : procs_) {
      if (!s.used) continue;
      Proc& p = *P(s);
      if (p.done()) continue;
      const ScheduleStep st = p.schedule[p.pc];
      ++p.pc;
      if (st.first >= 1.0) p.prog.hop(p.pc - 1, st.second);
      else                 p.prog.split(p.pc - 1, st.second, st.first);
    }
    qcos::tick_advance(qcos::g_arena);
  }

  // Board: key-value store with Landauer pricing (8 bits per canonical byte erased)
  bool set(const std::string& key, const Json& v) {
    if (board_.has(key)) {
      debt_bits_ += 8ull * static_cast<uint64_t>(canon(board_[key]).size());
      board_.set(key, v);
      return true;
    }
    const Json& b = board_;
    if (b.obj().size() >= QCOS_WORKING_LIMIT) return false;  // refusal (A8)
    board_.set(key, v);
    return true;
  }
  
  Json get(const std::string& key) const { return board_[key]; }
  const Json& board() const { return board_; }

  uint64_t debt_bits() const { return debt_bits_; }
  double entropy_debt_kTln2() const { return static_cast<double>(debt_bits_); }
  
  std::string soul() const { return sha256_hex(canon(board_)); }

  Json status() const {
    Json a = Json::array();
    for (const PSlot& s : procs_) {
      if (!s.used) continue;
      const Proc& p = *P(s);
      Json o = Json::object();
      o.set("name", std::string(p.name));
      o.set("pc", (int)p.pc);
      o.set("halt", p.halted());
      o.set("done", p.done());
      a.push(o);
    }
    return a;
  }

  // Two-phase reap (ZOMBIE discipline): destruct, then free the arena slot
  void reap(Proc* p) {
    if (!p || refused(*p)) return;
    for (PSlot& s : procs_)
      if (s.used && P(s) == p) {
        p->~Proc();
        s.used = false;
        qcos::w_free(qcos::g_arena, s.slot, KOWNER);
        s.slot = QCOS_SLOT_NONE;
        return;
      }
  }
  
  uint32_t proc_count() const {
    uint32_t n = 0;
    for (const PSlot& s : procs_) n += s.used ? 1 : 0;
    return n;
  }

 private:
  static constexpr uint32_t KOWNER = 1;
  
  struct PSlot {
    alignas(alignof(Proc)) unsigned char raw[sizeof(Proc)];
    bool     used = false;
    uint32_t slot = QCOS_SLOT_NONE;
  };
  
  static Proc* P(PSlot& s) { return reinterpret_cast<Proc*>(s.raw); }
  static const Proc* P(const PSlot& s) { return reinterpret_cast<const Proc*>(s.raw); }
  
  static Proc& tombstone() {
    static Proc t(std::string("[refused]"), 0, 0, 0);
    return t;
  }
  
  PSlot    procs_[QCOS_WORKING_LIMIT];
  Json     board_ = Json::object();
  uint64_t debt_bits_ = 0;
};

}  // namespace saem
