// core/src/kernel_trace.hpp — kernel-layer v3, additive-only.
// The frozen saem::Kernel (kernel.hpp @ c944399) is NOT modified: every
// call below goes through its original public surface (canon, board(),
// get(), set(), spawn(), status(), entropy_debt_kTln2(), soul()).
// Vision discipline lands as wrappers: integer Landauer ledger, arena
// provenance, bounded traced spawn (A8), caps report. Legacy callers keep
// the original unbounded path; traced callers get the constitutional one.
// Priced debt (ledgered): original Kernel::set debt stays double here;
// the integer mirror lives in ::qcos::g_arena.bits_erased.
#pragma once
#include <string>

#include "arena.hpp"    // ::qcos::g_arena (global namespace, no clash with saem::)
#include "kernel.hpp"   // frozen: saem::canon / Proc / Kernel

namespace saem {
namespace ktrace {

// 8 bits per canonical byte of the OLD value (original physics, integer form).
inline uint64_t price_of(const Json& old_value) {
  return 8ull * static_cast<uint64_t>(canon(old_value).size());
}

// Traced set: price + provenance FIRST, then delegate to frozen Kernel::set.
// Returns true iff the key pre-existed (i.e. an erasure was priced).
inline bool set_traced(Kernel& k, const std::string& key, const Json& v) {
  const bool pre = k.board().has(key);
  if (pre) {
    ::qcos::g_arena.bits_erased += price_of(k.get(key));
    ::qcos::g_arena.record(::qcos::OP_FREE, 0, ::qcos::g_arena.next_id);
  }
  k.set(key, v);
  ::qcos::g_arena.record(::qcos::OP_ALLOC, 0, ++::qcos::g_arena.next_id);
  return pre;
}

// Traced spawn: bounded by the working cap (A8). Refusal = nullptr + priced
// refusal; the frozen Kernel::spawn is only called when capacity allows.
inline Proc* spawn_traced(Kernel& k, const std::string& name,
                          size_t nreg, size_t nk, uint64_t seed = 0x5AEE) {
  if (k.status().arr().size() >= QCOS_WORKING_LIMIT) {
    ::qcos::g_arena.debt_refusals++;
    ::qcos::g_arena.record(::qcos::OP_FREE, 0, 0);
    return nullptr;
  }
  Proc& p = k.spawn(name, nreg, nk, seed);
  ::qcos::g_arena.record(::qcos::OP_ALLOC,
                         (uint32_t)(k.status().arr().size() - 1),
                         ++::qcos::g_arena.next_id);
  return &p;
}

inline void reap_traced(Kernel& k, Proc* p) {
  (void)k; (void)p;   // original Kernel has no reap; procs live with the
                      // Kernel (vector semantics). Recorded as priced debt:
  ::qcos::g_arena.record(::qcos::OP_FREE, 0, 0);
}

inline Json caps_report(const Kernel& k) {
  Json o = Json::object();
  o.set("procs", (int)k.status().arr().size());
  o.set("proc_limit", (int)QCOS_WORKING_LIMIT);
  o.set("board_keys", (int)k.board().obj().size());
  o.set("board_limit", (int)QCOS_WORKING_LIMIT);
  o.set("debt_bits_double", k.entropy_debt_kTln2());   // frozen view
  o.set("debt_bits_int", (double)::qcos::g_arena.bits_erased);
  o.set("refusals", (double)::qcos::g_arena.debt_refusals);
  return o;
}

// Additive witness suite (v3 kernel-layer). Uses ONLY original public API.
inline int selftest_trace() {
  int fails = 0, total = 0;
  auto want = [&](const char* n, bool ok) {
    ++total; if (!ok) ++fails;
    std::printf("[ktrace-selftest] %-30s %s\n", n, ok ? "ok" : "DRIFT");
  };
  ::qcos::g_arena.init();
  Kernel k;

  want("price_int", price_of(Json(1)) == 8ull);
  want("set_new_unpriced", !set_traced(k, "k", Json(1)) && k.get("k").asInt(0) == 1);
  uint64_t d0 = ::qcos::g_arena.bits_erased;
  want("set_overwrite_priced", set_traced(k, "k", Json(2)) &&
       ::qcos::g_arena.bits_erased - d0 == 8ull);
  want("frozen_soul_intact", k.soul() == sha256_hex(canon(k.board())));
  bool spawned = true; Proc* first = nullptr;
  for (int i = 0; i < 32; i++) {
    Proc* p = spawn_traced(k, "p" + std::to_string(i), 1, 0, 7);
    if (i == 0) first = p;
    spawned &= (p != nullptr);
  }
  want("32 traced spawns", spawned && first != nullptr);
  want("33rd refused", spawn_traced(k, "overflow", 1, 0, 7) == nullptr &&
       ::qcos::g_arena.debt_refusals == 1);
  want("caps_report", caps_report(k)["proc_limit"].asInt(0) == 32 &&
       caps_report(k)["procs"].asInt(0) == 32);
  k.tick();   // all-done procs: no-op, frozen semantics
  want("tick_frozen_semantics", first && first->done());

  std::printf("[ktrace-selftest] %d/%d passed\n", total - fails, total);
  return fails ? 1 : 0;
}

}  // namespace ktrace
}  // namespace saem
