// tests/test_kernel_slots.cpp — step 11b witness. Exit 0 = truth holds.
#include "../core/src/kernel.hpp"
#include <cstdio>

static int fails = 0, total = 0;
static void want(const char* n, bool ok) {
  ++total; if (!ok) ++fails;
  std::printf("[test_kernel] %-34s %s\n", n, ok ? "ok" : "DRIFT");
}

int main() {
  using namespace saem;
  qcos::g_arena.init();
  Kernel k;

  Proc* first = nullptr;
  bool spawned = true;
  for (int i = 0; i < 32; i++) {
    Proc* p = k.spawn("p" + std::to_string(i), 1, 0, 7);
    if (i == 0) first = p;
    spawned &= (p != nullptr);
  }
  want("32 procs spawn", spawned && k.proc_count() == 32);
  want("33rd refused", k.spawn("overflow", 1, 0, 7) == nullptr);
  want("long name refused", k.spawn(std::string(80, 'x'), 1, 0, 7) == nullptr);
  want("find hit", k.find("p0") == first);
  want("find miss", k.find("nope") == nullptr);

  Proc* p2 = nullptr;
  { Kernel k2; /* fresh kernel shares arena; use slot from reaps below */ }
  // bounded schedule on a scratch proc (reaped before any tick)
  Proc* scratch = nullptr;
  k.reap(k.find("p31"));
  scratch = k.spawn("scratch", 1, 0, 7);
  bool bounded = true;
  Gate g{};
  for (size_t i = 0; i < KSCHED_MAX; i++) bounded &= k.add_step(scratch, 1.0, g);
  bounded &= !k.add_step(scratch, 1.0, g);
  want("schedule bounded", bounded);
  k.reap(scratch);

  want("set/read round-trip", k.set("k", Json(1)) &&
       ({ Json v; k.read("k", &v) && v.asInt(0) == 1; }));
  uint64_t d0 = k.debt_bits();
  k.set("k", Json(2));
  want("overwrite priced", k.debt_bits() - d0 == 8ull * QCOS_SLOT_PAYLOAD);
  want("read miss visible", !k.read("absent", nullptr));
  bool board_full = true;
  for (int i = 0; i < 32; i++) board_full &= k.set("b" + std::to_string(i), Json(i));
  board_full &= !k.set("b32", Json(32));
  want("board full refuses", board_full);

  uint32_t id_before = qcos::g_arena.next_id;
  k.reap(first);
  Proc* reborn = k.spawn("p0", 1, 0, 7);
  want("reap frees slot", reborn != nullptr);
  want("identity monotonic", reborn && reborn->slot != QCOS_SLOT_NONE &&
       qcos::g_arena.next_id > id_before);
  k.tick();   // all-done procs: pc untouched, no crash
  want("tick on done procs", reborn && reborn->done());

  std::printf("[test_kernel] %d/%d passed\n", total - fails, total);
  return fails ? 1 : 0;
}
