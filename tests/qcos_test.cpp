// The QCOS smoke test: every layer of the model in one binary, and every
// number printed through the reference contract (jsnum / canon).
#include <cstdio>
#include "kernel.hpp"
#include "gen.hpp"

using namespace saem;

int main() {
  // 1. Payload: a Bell pair from the gate set alone.
  QReg r(2, 7);
  r.h(0); r.cnot(0, 1);
  std::printf("bell norm=%s p0=%s p1=%s\n", jsnum(r.norm()).c_str(),
              jsnum(r.prob1(0)).c_str(), jsnum(r.prob1(1)).c_str());

  // 2. Control: the same circuit as a cursor program. Two hops walk the
  //    cursor to the halt site; a split hop leaves it superposed.
  QProg p(2, 2, 11);
  p.hop(0, gh(0));
  p.hop(1, gcnot(0, 1));
  std::printf("prog halt=%s readout=%s\n", jsnum(p.prob_halt()).c_str(),
              canon(p.readout()).c_str());
  QProg q(2, 2, 11);
  q.split(0, gh(0), 0.70710678118654752440);
  q.hop(1, gcnot(0, 1));
  std::printf("split halt=%s\n", jsnum(q.prob_halt()).c_str());

  // 3. Substrate: reversible half adder, then Bennett uncomputation.
  Bits b = {1, 1, 0, 0};
  std::vector<Gate> adder = {gccnot(0, 1, 2), gcnot(0, 3), gcnot(1, 3)};
  run(b, adder);
  std::printf("adder 1+1 -> carry=%d sum=%d\n", b[2], b[3]);
  run(b, adder, true);
  std::printf("uncomputed -> %d%d%d%d\n", b[0], b[1], b[2], b[3]);
  Bits c = {1, 0, 0, 0};
  compute_copy_uncompute(c, {gcnot(0, 2), gcnot(0, 1)}, 2, 3);
  std::printf("bennett in=%d garbage=%d out=%d copy=%d\n", c[0], c[1], c[2], c[3]);

  // 4. Cognition: a report card over the Math Brain's own topic list.
  Learner L;
  const std::vector<std::string>& ts = gen::topics();
  for (size_t i = 0; i < ts.size(); ++i) {
    int rights = (i % 3 == 0) ? 7 : (i % 3 == 1) ? 2 : 4;
    for (int t = 0; t < 8; ++t) L.observe(ts[i], t < rights);
  }
  std::printf("learner next=%s\n", L.next().c_str());
  std::printf("learner[2]=%s\n", canon(snapshot(L.bs)[2]).c_str());

  // 5. Kernel: spawn, schedule, tick, blackboard, soul, entropy debt.
  Kernel K;
  Proc& P = K.spawn("bell", 2, 2, 5);
  P.schedule = {{1.0, gh(0)}, {1.0, gcnot(0, 1)}};
  K.tick(); K.tick();
  K.set("receipt", P.prog.readout());
  const std::string s1 = K.soul();
  K.set("receipt", P.prog.readout());  // overwrite pays Landauer, even identical
  std::printf("kernel halt=%s debt=%s soul_stable=%d\n",
              jsnum(P.halted()).c_str(), jsnum(K.entropy_debt_kTln2()).c_str(),
              int(s1 == K.soul()));
  std::printf("kernel %s\n", canon(K.status()).c_str());
  return 0;
}
