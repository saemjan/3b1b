// Reversible classical substrate: the gate set beneath the quantum layer
// and the discipline above it. AND/OR throw information away and owe heat
// (Feynman ch.5, after Landauer); NOT, CNOT, CCNOT, SWAP, FREDKIN throw
// nothing away and owe nothing. A straight-line program of these is its
// own inverse run backwards, which is Bennett's move for uncomputing
// garbage (ch.6): compute, copy the answer out, run backwards.
#pragma once
#include <cstdint>
#include <vector>

namespace saem {

using Bits = std::vector<uint8_t>;

struct Gate {
  uint8_t kind;  // 0 not, 1 cnot, 2 ccnot, 3 swap, 4 fredkin, 5 h, 6 z, 7 s
  uint8_t a, b, c;
};
inline Gate gnot(uint8_t a) { return {0, a, 0, 0}; }
inline Gate gcnot(uint8_t c, uint8_t t) { return {1, c, t, 0}; }
inline Gate gccnot(uint8_t c1, uint8_t c2, uint8_t t) { return {2, c1, c2, t}; }
inline Gate gswap(uint8_t a, uint8_t b) { return {3, a, b, 0}; }
inline Gate gfredkin(uint8_t c, uint8_t a, uint8_t b) { return {4, c, a, b}; }
inline Gate gh(uint8_t a) { return {5, a, 0, 0}; }
inline Gate gz(uint8_t a) { return {6, a, 0, 0}; }
inline Gate gs(uint8_t a) { return {7, a, 0, 0}; }

inline void apply(Bits& b, const Gate& g) {
  uint8_t t;
  switch (g.kind) {
    case 0: b[g.a] ^= 1; break;
    case 1: if (b[g.a]) b[g.b] ^= 1; break;
    case 2: if (b[g.a] && b[g.b]) b[g.c] ^= 1; break;
    case 3: t = b[g.a]; b[g.a] = b[g.b]; b[g.b] = t; break;
    case 4: if (b[g.a]) { t = b[g.b]; b[g.b] = b[g.c]; b[g.c] = t; } break;
  }
}

inline void run(Bits& b, const std::vector<Gate>& p, bool backwards = false) {
  if (!backwards) { for (const Gate& g : p) apply(b, g); return; }
  for (size_t i = p.size(); i-- > 0;) apply(b, p[i]);
}

// Bennett: prog computes f(inputs) into bit `out`, leaving garbage.
// Copy out with a CNOT, run prog in reverse; inputs and garbage return
// home and only the clean copy remains.
// around line 50
inline void compute_copy_uncompute(Bits& b, const std::vector<Gate>& prog,
                                   uint8_t out, uint8_t dest) {
  run(b, prog);
  saem::apply(b, gcnot(out, dest));
  run(b, prog, true);
}

}  // namespace saem
