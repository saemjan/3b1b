// core/src/kernel.hpp
#pragma once
#include <string>
#include <utility>
#include <vector>
#include "cog.hpp"
#include "qreg.hpp"
#include "sha256.hpp"

namespace saem {

inline std::string canon(const Json& j) {
  switch (j.type()) {
    case Json::Null: return "null";
    case Json::Bool: return j.asBool() ? "true" : "false";
    case Json::Num: return jsnum(j.asNum());
    case Json::Str: {
      std::string out;
      out += '"';
      for (unsigned char c : j.asStr()) {
        // Fixed: Restored backslashes for JSON string escaping
        if (c == '"' || c == '\\') { out += '\\'; out += static_cast<char>(c); }
        else if (c == '\n') out += "\\n";
        else if (c == '\t') out += "\\t";
        else if (c == '\r') out += "\\r";
        else if (c < 0x20) {
          char b[8]; std::snprintf(b, sizeof b, "\\u%04x", c); out += b;
        } else out += static_cast<char>(c);
      }
      out += '"';
      return out;
    }
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
        std::string k; k += '"';
        for (unsigned char c : o[i].first) {
          // Fixed: Restored backslashes for JSON string escaping
          if (c == '"' || c == '\\') { k += '\\'; k += static_cast<char>(c); }
          else if (c == '\n') k += "\\n";
          else if (c == '\t') k += "\\t";
          else if (c == '\r') k += "\\r";
          else if (c < 0x20) { char b[8]; std::snprintf(b, sizeof b, "\\u%04x", c); k += b; }
          else k += static_cast<char>(c);
        }
        k += '"';
        s += k + ":" + canon(o[i].second);
      }
      return s + "}";
    }
  }
  return "null";
}

struct Proc {
  std::string name;
  QProg prog;
  std::vector<std::pair<double, Gate>> schedule;
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
  void tick() {
    for (Proc& p : procs_) {
      if (p.done()) continue;
      const auto st = p.schedule[p.pc]; ++p.pc;
      if (st.first >= 1.0) p.prog.hop(p.pc - 1, st.second);
      else p.prog.split(p.pc - 1, st.second, st.first);
    }
  }
  void set(const std::string& key, const Json& v) {
    if (board_.has(key)) debt_bits_ += 8.0 * double(canon(board_[key]).size());
    board_.set(key, v);
  }
  Json get(const std::string& key) const { return board_[key]; }
  const Json& board() const { return board_; }
  double entropy_debt_kTln2() const { return debt_bits_; }
  std::string soul() const { return sha256_hex(canon(board_)); }
  Json status() const {
    Json a = Json::array();
    for (const Proc& p : procs_) {
      Json o = Json::object();
      o.set("name", p.name); o.set("pc", (int)p.pc);
      o.set("halt", p.halted()); o.set("done", p.done());
      a.push(o);
    }
    return a;
  }
 private:
  Json board_ = Json::object();
  std::vector<Proc> procs_;
  double debt_bits_ = 0;
};
}
