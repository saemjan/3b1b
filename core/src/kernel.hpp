// core/src/kernel.hpp — gen-3 (step 11b): quantum process kernel on static arenas.
// Doctrine: xv6 proc[] fixed pool + ZOMBIE two-phase reap; arena.hpp four-axis
// slots; Landauer integer pricing (debt_bits_ double -> physical bits, A4/A9).
// ASSUMPTIONS REGISTER (every item proven by the prior fragment unless marked):
//   qreg.hpp: QProg(nreg,k,seed), hop(size_t,Gate), split(size_t,Gate,double),
//             prob_halt() const; Gate default-constructible + copyable (marked).
//   json.hpp: Json copy-assign, Json(int), Json::object(), .set/.has/.asInt (marked: copy-assign).
//   Unseen Kernel methods, if any, are merged at step 12 from qcos_api.cpp paste.
#ifndef SAEM_KERNEL_HPP
#define SAEM_KERNEL_HPP

#include <cstdint>
#include <cstring>
#include <new>
#include <string>

#include "arena.hpp"
#include "json.hpp"
#include "qreg.hpp"

namespace saem {

constexpr size_t   KCOS_NAME_MAX  = 64;        // mirrors canon NAME_MAX cap
constexpr size_t   KSCHED_MAX     = 64;        // fixed schedule horizon per proc
constexpr uint64_t KDEFAULT_SEED  = 0x5AEE;    // streamU contract seed

struct ScheduleStep {
  double prob = 0.0;
  Gate   gate{};
};

struct Proc {
  uint32_t slot = QCOS_SLOT_NONE;              // working-arena index (identity axis)
  char     name[KCOS_NAME_MAX] = {0};          // was std::string (heap) -> fixed
  QProg    prog;
  ScheduleStep schedule[KSCHED_MAX] = {};      // was std::vector (heap) -> fixed
  size_t   sched_n = 0;
  size_t   pc      = 0;

  Proc(const char* n, size_t nreg, size_t k, uint64_t seed)
      : prog(nreg, k, seed) {
    std::strncpy(name, n, KCOS_NAME_MAX - 1);
  }
  bool   done()   const { return pc >= sched_n; }
  double halted() const { return prog.prob_halt(); }
};

class Kernel {
 public:
  // Refusal, never growth: nullptr on name-bound or pool exhaustion (A8).
  Proc* spawn(const std::string& name, size_t nreg, size_t k,
              uint64_t seed = KDEFAULT_SEED) {
    if (name.size() >= KCOS_NAME_MAX) return nullptr;
    uint32_t slot = qcos::w_alloc(qcos::g_arena, KOWNER);
    if (slot == QCOS_SLOT_NONE) return nullptr;
    for (PSlot& s : procs_) {
      if (s.used) continue;
      s.used = true;
      s.slot = slot;
      Proc* p = new (s.raw) Proc(name.c_str(), nreg, k, seed);
      p->slot = slot;
      return p;
    }
    qcos::w_free(qcos::g_arena, slot, KOWNER);   // symmetric unwind
    return nullptr;
  }

  Proc* find(const std::string& name) {
    for (PSlot& s : procs_)
      if (s.used && std::strcmp(P(s)->name, name.c_str()) == 0) return P(s);
    return nullptr;
  }

  bool add_step(Proc* p, double prob, const Gate& g) {
    if (!p || p->sched_n >= KSCHED_MAX) return false;   // bounded horizon
    p->schedule[p->sched_n].prob = prob;
    p->schedule[p->sched_n].gate = g;
    ++p->sched_n;
    return true;
  }

  void tick() {
    for (PSlot& s : procs_) {
      if (!s.used) continue;
      Proc& p = *P(s);
      if (p.done()) continue;
      const ScheduleStep st = p.schedule[p.pc];
      ++p.pc;
      if (st.prob >= 1.0) p.prog.hop(p.pc - 1, st.gate);
      else                p.prog.split(p.pc - 1, st.gate, st.prob);
    }
    qcos::tick_advance(qcos::g_arena);
  }

  // Overwrite = erasure = priced dissipation (physical bits, integer).
  bool set(const std::string& key, const Json& v) {
    if (key.size() >= sizeof(KV::key)) return nullptr_guard();
    for (KV& b : board_)
      if (b.used && key == b.key) {
        qcos::g_arena.bits_erased += 8ull * QCOS_SLOT_PAYLOAD;
        b.value = v;
        return true;
      }
    for (KV& b : board_)
      if (!b.used) {
        b.used = true;
        std::strncpy(b.key, key.c_str(), sizeof b.key - 1);
        b.value = v;
        return true;
      }
    return false;                                   // board full: refusal
  }

  bool read(const std::string& key, Json* out) const {
    for (const KV& b : board_)
      if (b.used && key == b.key) { if (out) *out = b.value; return true; }
    return false;                                   // absence is visible, not null
  }

  // Two-phase reap (ZOMBIE discipline): destruct, then free the arena slot.
  void reap(Proc* p) {
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
  uint64_t debt_bits() const { return qcos::g_arena.bits_erased; }

 private:
  static constexpr uint32_t KOWNER = 1;            // kernel owner id for locks
  struct PSlot {                                   // static storage, no heap
    alignas(alignof(Proc)) unsigned char raw[sizeof(Proc)];
    bool     used = false;
    uint32_t slot = QCOS_SLOT_NONE;
  };
  struct KV { char key[24] = {0}; Json value; bool used = false; };
  static Proc* P(PSlot& s) { return reinterpret_cast<Proc*>(s.raw); }
  static bool nullptr_guard() { return false; }
  PSlot procs_[QCOS_WORKING_LIMIT];
  KV    board_[QCOS_WORKING_LIMIT];
};

}  // namespace saem
#endif  // SAEM_KERNEL_HPP
