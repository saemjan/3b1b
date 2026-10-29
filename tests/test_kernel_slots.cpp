// tests/test_kernel_slots.cpp — step 11b-reconcile witness. Exit 0 = truth.
#include "../core/src/kernel.hpp"
#include <cstdio>

static int fails = 0, total = 0;
static void want(const char* n, bool ok) {
  ++total; if (!ok) ++fails;
  std::printf("[test_kernel] %-36s %s\n", n, ok ? "ok" : "DRIFT");
}

int main() {
  using namespace saem;
  qcos::g_arena.init();
  Kernel k;

  want("canon number (jsnum half-even)", canon(Json(0.1 + 0.2)) == "0.30000000000000004");
  Json o = Json::object(); o.set("b", Json(1)); o.set("a", Json(2));
  want("canon insertion order", canon(o) == "{\"b\":1,\"a\":2}");

  Proc* first = nullptr; bool spawned = true;
  for (int i = 0; i < 32; i++) {
    Proc* p = k.try_spawn("p" + std::to_string(i), 1, 0, 7);
    if (i == 0) first = p;
    spawned &= (p != nullptr && !k.refused(*p));
  }
  want("32 procs spawn", spawned && k.proc_count() == 32);
  Proc& over = k.spawn("overflow", 1, 0, 7);
  want("33rd -> tombstone, refused visible", k.refused(over));
  want("long name refused", k.try_spawn(std::string(80, 'x'), 1, 0, 7) == nullptr);
  want("find hit / miss", k.find("p0") == first && k.find("nope") == nullptr);

  Gate g{};
  bool bounded = true;
  for (size_t i = 0; i < KSCHED_MAX; i++) bounded &= k.add_step(*first, 1.0, g);
  bounded &= !k.add_step(*first, 1.0, g);
  want("schedule bounded (push_back vocab)", bounded && first->schedule.size() == KSCHED_MAX);

  want("set/get round-trip", k.set("k", Json(1)) && k.get("k").asInt(0) == 1);
  uint64_t d0 = k.debt_bits();
  k.set("k", Json(2));
  want("overwrite priced 8*canon(old)", k.debt_bits() - d0 == 8ull * 1);
  want("entropy view matches ledger", k.entropy_debt_kTln2() == (double)k.debt_bits());
  bool board_ok = true;
  for (int i = 0; i < 31; i++) board_ok &= k.set("b" + std::to_string(i), Json(i));
  board_ok &= !k.set("b31", Json(31));           // 1 + 31 keys = cap 32
  want("board bounded by WORKING cap", board_ok);
  want("soul = sha256(canon(board))", k.soul() == sha256_hex(canon(k.board()))
       && k.soul().size() == 64);
  want("status fields frozen", k.status().arr().size() == k.proc_count());

  uint32_t id_before = qcos::g_arena.next_id;
  k.reap(first);
  k.reap(&over);                                  // tombstone reap = no-op
  Proc* reborn = k.try_spawn("p0", 1, 0, 7);
  want("reap frees slot; tombstone safe", reborn != nullptr);
  want("identity monotonic", qcos::g_arena.next_id > id_before);
  k.tick();                                       // done/tombstone procs untouched
  want("tick skips done & tombstone", reborn && reborn->done());

  std::printf("[test_kernel] %d/%d passed\n", total - fails, total);
  return fails ? 1 : 0;
}
