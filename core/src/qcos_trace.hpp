// core/src/qcos_trace.hpp — Step 12 additive vision layer.
// WRAPS the frozen saem::qcos surface (qcos.hpp) with the arena-backed
// thermodynamic/provenance discipline (OS.md P9, A3/A9). It mutates NOTHING
// in qcos.hpp / qcos_api.cpp / qreg.hpp; all frozen bytes stay byte-stable.
// Namespace note (dated cleanup at step 14): arena.hpp lives at ::qcos,
// the frozen core at saem::qcos — qualify explicitly here.
#pragma once
#include <string>

#include "arena.hpp"    // ::qcos::g_arena, OP_*, caps
#include "kernel.hpp"   // saem::canon (single ruler, §14)
#include "qcos.hpp"     // frozen: saem::qcos::Working/Episodic/Provenance/gate

namespace saem {
namespace qtrace {

// Integer Landauer mirror of qcos_api w13's double debt:
// erasure of the old value costs 8 bits per canonical byte (A4: integers).
inline uint64_t price_overwrite(const Json& old_value) {
  return 8ull * static_cast<uint64_t>(canon(old_value).size());
}

inline std::string soul_of(const Json& v) { return sha256_hex(canon(v)); }

// Traced latch: price + record FIRST, then delegate to the frozen Working.
// Returns exactly what w.latch returns; refusal propagates unchanged (A8).
inline bool latch_traced(qcos::Working& w, const std::string& k, const Json& v) {
  if (w.has(k)) {
    ::qcos::g_arena.bits_erased += price_overwrite(w.read(k));
    ::qcos::g_arena.record(::qcos::OP_FREE, 0, ::qcos::g_arena.next_id);
  }
  const bool ok = w.latch(k, v);
  if (ok) ::qcos::g_arena.record(::qcos::OP_ALLOC, 0, ++::qcos::g_arena.next_id);
  return ok;
}

// Traced episodic push: price wrap-overwrites, then delegate (frozen wrap
// semantics {tick, event} preserved verbatim inside Episodic::recent).
inline void push_traced(qcos::Episodic& ep, const Json& e) {
  if (ep.count >= (uint64_t)qcos::EPISODIC_LIMIT)
    ::qcos::g_arena.bits_erased += 8ull * (uint64_t)canon(ep.r[ep.head % qcos::EPISODIC_LIMIT]).size();
  ep.push(e);
  ::qcos::g_arena.record(::qcos::OP_EPI_PUSH, (uint32_t)(ep.head % qcos::EPISODIC_LIMIT), 0);
}

inline Json caps_report() {
  Json o = Json::object();
  o.set("working_limit", qcos::WORKING_LIMIT);
  o.set("episodic_limit", qcos::EPISODIC_LIMIT);
  o.set("bits_erased", (double)::qcos::g_arena.bits_erased);
  o.set("refusals", (double)::qcos::g_arena.debt_refusals);
  o.set("prov_len", (int)(::qcos::g_arena.prov_head < QCOS_PROV_RING
                          ? ::qcos::g_arena.prov_head : QCOS_PROV_RING));
  return o;
}

// Additive witness suite (names prefixed v_ so frozen names stay unique).
inline int selftest_trace() {
  int fails = 0, total = 0;
  auto want = [&](const char* n, bool ok) {
    ++total; if (!ok) ++fails;
    std::printf("[trace-selftest] %-30s %s\n", n, ok ? "ok" : "DRIFT");
  };
  ::qcos::g_arena.init();
  qcos::Working w; qcos::Episodic ep;

  want("v_price_int", price_overwrite(Json(1)) == 8ull);
  want("v_soul", soul_of(Json(1)) == sha256_hex("1"));
  want("v_latch_traced", latch_traced(w, "k", Json(1)) && w.read("k").asInt(0) == 1);
  uint64_t d0 = ::qcos::g_arena.bits_erased;
  latch_traced(w, "k", Json(2));
  want("v_overwrite_priced", ::qcos::g_arena.bits_erased - d0 == 8ull);
  want("v_frozen_shape_kept", w.snapshot().arr().size() == 1 &&
       w.snapshot().arr()[0].obj().size() == 2);   // {key,value} only
  for (int i = 0; i < qcos::EPISODIC_LIMIT + 2; i++) push_traced(ep, Json(i));
  want("v_wrap_priced", ::qcos::g_arena.bits_erased - d0 - 8ull == 2ull * 8 * 4);
  want("v_recent_wrap_frozen", ep.recent(1).arr()[0].has("event") &&
       ep.recent(1).arr()[0].has("tick"));
  want("v_caps", caps_report()["working_limit"].asInt(0) == 32 &&
       caps_report()["episodic_limit"].asInt(0) == 64);
  qcos::Provenance pv;
  pv.append("t1", "here", "why");
  want("v_frozen_prov_chain", pv.verify());

  std::printf("[trace-selftest] %d/%d passed\n", total - fails, total);
  return fails ? 1 : 0;
}

}  // namespace qtrace
}  // namespace saem
