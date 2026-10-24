// The QCOS kernel: Feynman's file clerk (ch.1) as a shared blackboard,
// Feynman's cursor machines (ch.6) as processes, and Landauer's bill
// (ch.5) as an entropy-debt ledger. Overwriting a blackboard entry erases
// the old value; erasure costs kT ln 2 per bit, so the kernel counts the
// bits it destroys and reports the debt instead of hiding it. Note the
// debt grows even when you rewrite the identical value: the erasure
// happened physically either way.
#pragma once
#include <string>
#include <utility>
#include <vector>

#include "cog.hpp"
#include "qreg.hpp"
#include "sha256.hpp"

namespace saem {

// Canonical text of a Json value, built only from the visible reading API
// so C++ and the reference engine agree byte for byte. Numbers leave
// through jsnum, exactly as the contract demands.
inline std::string canon(const Json& j) {
  switch (j.type()) {
    case Json::Null: return "null";
    case Json::Bool: return j.asBool() ? "true" : "false";
    case Json::Num: return jsnum(j.asNum());
    case Json::Str: return "\"" + j.asStr() + "\"";
    case Json::Array: {
      std::string s = "[";
      const Json::Arr& a = j.arr();
      for (size_t i = 0; i < a.size(); ++i) { if (i) s += ","; s += canon(a[i]); }
      return s + "]";
    }
    case Json::Object: {
      std::string s = "{";
      const Json::Obj& o = j.obj();
      for (size_t i = 0; i < o.size(); ++i) {
        if (i) s += ",";
        s += "\"" + o[i].first + "\":" + canon(o[i].second);
      }
      return s + "}";
    }
  }
  return "null";
}

struct Proc {
  std::string name;
  QProg prog;
  std::vector<std::pair<double, Gate>> schedule;  // sin(theta), gate; 1 = full hop
  size_t pc = 0;
  Proc(const std::string& n, size_t nreg, size_t k, uint64_t seed)
      : name(n), prog(nreg, k, seed) {}
  bool done() const { return pc >= schedule.size(); }
  double halted() const { return prog.prob_halt(); }
};

class Kernel {
 public:
  Proc& spawn(const std::string& name, size_t nreg, size_t k, uint64_t seed = 0x5AEE) {
    procs_.push_back(Proc(name, nreg, k, seed));
    return procs_.back();
  }
  Proc* find(const std::string& name) {
    for (Proc& p : procs_) if (p.name == name) return &p;
    return nullptr;
  }

  // One clock: every live process executes its next scheduled hop.
  void tick() {
    for (Proc& p : procs_) {
      if (p.done()) continue;
      const auto st = p.schedule[p.pc];
      ++p.pc;
      if (st.first >= 1.0) p.prog.hop(p.pc - 1, st.second);
      else p.prog.split(p.pc - 1, st.second, st.first);
    }
  }

  // File-clerk memory with a Landauer ledger.
  void set(const std::string& key, const Json& v) {
    if (board_.has(key)) debt_bits_ += 8.0 * double(canon(board_[key]).size());
    board_.set(key, v);
  }
  Json get(const std::string& key) const { return board_[key]; }
  const Json& board() const { return board_; }
  double entropy_debt_kTln2() const { return debt_bits_; }  // units of kT ln 2

  std::string soul() const { return sha256_hex(canon(board_)); }

  Json status() const {
    Json a = Json::array();
    for (const Proc& p : procs_) {
      Json o = Json::object();
      o.set("name", p.name);
      o.set("pc", (int)p.pc);
      o.set("halt", p.halted());
      o.set("done", p.done());
      a.push(o);
    }
    return a;
  }

 private:
  Json board_ = Json::object();
  std::vector<Proc> procs_;
  double debt_bits_ = 0;
};

}  // namespace saem
