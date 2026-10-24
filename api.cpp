// core/src/api.cpp  — v6: door is self-sufficient. Serializes Question
// itself, rebuilds demo_bank from make(), no gen::question_json /
// gen::demo_bank / gen::fmt dependency. A0: require_* restored.
#include "api.hpp"

#include <cstdint>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

#include "gen.hpp"
#include "numfmt.hpp"

#ifndef SAEM_SOURCE_ID
#define SAEM_SOURCE_ID "dev"
#endif
#if defined(_WIN32)
#define SAEM_EXPORT __declspec(dllexport)
#else
#define SAEM_EXPORT __attribute__((visibility("default")))
#endif

namespace saem {
namespace {
std::map<std::string, Handler>& table() {
  static std::map<std::string, Handler> t;
  return t;
}
}  // namespace

Registrar::Registrar(const char* name, Handler h) { table()[name] = std::move(h); }

Json call(const std::string& method, const Json& args) {
  auto it = table().find(method);
  if (it == table().end()) throw std::runtime_error("unknown method: " + method);
  return it->second(args);
}

std::string call_json(const std::string& method, const std::string& args_json) {
  Json out = Json::object();
  try {
    const Json args = args_json.empty() ? Json::object() : Json::parse(args_json);
    out.set("ok", true);
    out.set("result", call(method, args));
  } catch (const std::exception& e) {
    out = Json::object();
    out.set("ok", false);
    out.set("error", std::string(e.what()));
  } catch (...) {
    out = Json::object();
    out.set("ok", false);
    out.set("error", "UNKNOWN_FAILURE_DEBT");   // A3
  }
  return out.dump();
}

std::vector<std::string> methods() {
  std::vector<std::string> v;
  for (const auto& kv : table()) v.push_back(kv.first);
  return v;
}

namespace {
uint64_t seed_of(const Json& a, uint64_t dflt) {
  if (!a.has("seed") || !a["seed"].isNum()) return dflt;
  return static_cast<uint64_t>(static_cast<int64_t>(a["seed"].asNum()));
}
void require_str(const Json& a, const char* k) {
  if (!a.has(k)) throw std::runtime_error(std::string("missing field: ") + k);
  if (!a[k].isStr()) throw std::runtime_error(std::string("field '") + k + "' must be a string");
}
void require_num(const Json& a, const char* k) {
  if (!a.has(k)) throw std::runtime_error(std::string("missing field: ") + k);
  if (!a[k].isNum()) throw std::runtime_error(std::string("field '") + k + "' must be a number");
}
void require_obj(const Json& a, const char* k) {
  if (!a.has(k)) throw std::runtime_error(std::string("missing field: ") + k);
  if (!a[k].isObj()) throw std::runtime_error(std::string("field '") + k + "' must be an object");
}

// ---- door-owned serializer: the brain returns a struct, we print it ----
Json q_to_json(const gen::Question& q) {
  Json o = Json::object();
  o.set("text", q.text); o.set("answer", q.answer);
  o.set("explanation", q.explanation); o.set("topic", q.topic);
  o.set("gen", q.gen); o.set("src", q.src);
  Json opts = Json::array();
  for (const auto& op : q.options) {
    Json e = Json::object();
    e.set("key", op.key); e.set("text", op.text);
    opts.push(e);
  }
  o.set("options", opts);
  return o;
}

// ---- door-owned demo bank: 12 topics x 3 concepts across years ----
Json demo_bank(uint64_t seed, int y0, int y1) {
  Json papers = Json::array();
  for (const auto& t : gen::templates()) {
    int taken = 0;
    for (int y = y0; y <= y1 && taken < 3; ++y, ++taken) {
      gen::Rng R(seed + static_cast<uint64_t>(hash32(t.id)) + static_cast<uint64_t>(y));
      papers.push(q_to_json(gen::make(t.id, R)));
    }
  }
  return papers;
}

uint32_t hash32(const std::string& s) {  // FNV-1a
  uint32_t h = 0x811c9dc5u;
  for (unsigned char c : s) { h ^= c; h *= 0x01000193u; }
  return h;
}
std::string sup_exp(const std::string& d, bool neg) {
  static const char* SUP[10] = {"\xe2\x81\xb0","\xc2\xb9","\xc2\xb2","\xc2\xb3","\xe2\x81\xb4",
                                "\xe2\x81\xb5","\xe2\x81\xb6","\xe2\x81\xb7","\xe2\x81\xb8","\xe2\x81\xb9"};
  std::string out; if (neg) out += "\xe2\x81\xbb";
  for (char c : d) if (c >= '0' && c <= '9') out += SUP[c - '0'];
  return out;
}
std::string fmt4(double x) {
  const std::string s = round_sig(x, 4);   // round_sig already returns a string (A1)
  const size_t e = s.find('e');
  if (e == std::string::npos) return s;
  std::string ex = s.substr(e + 1);
  bool neg = !ex.empty() && ex[0] == '-';
  if (!ex.empty() && (ex[0] == '+' || ex[0] == '-')) ex = ex.substr(1);
  while (ex.size() > 1 && ex[0] == '0') ex = ex.substr(1);
  return s.substr(0, e) + " \xc3\x97 10" + sup_exp(ex, neg);
}
}  // namespace

// ---------- Math Brain ----------
const Registrar g1("gen.make", [](const Json& a) -> Json {
  require_str(a, "id");
  gen::Rng R(seed_of(a, 1));
  return q_to_json(gen::make(a["id"].asStr(), R));
});
const Registrar g2("gen.questionWith", [](const Json& a) -> Json {
  require_str(a, "id");
  require_obj(a, "params");
  // committed signature: (id, seed, params)
  return q_to_json(gen::question_with(a["id"].asStr(), seed_of(a, 1), a["params"]));
});
const Registrar g3("gen.solve", [](const Json& a) -> Json {
  require_str(a, "id"); require_obj(a, "params");
  return gen::solve(a["id"].asStr(), a["params"]);
});
const Registrar g4("gen.demoBank", [](const Json& a) -> Json {
  return demo_bank(seed_of(a, 11), a["y0"].asInt(0), a["y1"].asInt(0));
});
const Registrar g5("gen.topics", [](const Json&) -> Json {
  Json o = Json::array(); for (const auto& t : gen::topics()) o.push(t); return o;
});
const Registrar g6("gen.templates", [](const Json&) -> Json {
  Json o = Json::array();
  for (const auto& t : gen::templates()) {
    Json e = Json::object(); e.set("id", t.id); e.set("topic", t.topic); o.push(e);
  }
  return o;
});
const Registrar g7("gen.format", [](const Json& a) -> Json {
  require_num(a, "x"); return Json(fmt4(a["x"].asNum()));
});
const Registrar g8("gen.vectors", [](const Json&) -> Json { return gen::vectors(); });
const Registrar g9("gen.hash32", [](const Json& a) -> Json {
  require_str(a, "s"); return Json(static_cast<double>(hash32(a["s"].asStr())));
});

}  // namespace saem

extern "C" SAEM_EXPORT const char* saem_call(const char* m, const char* a) {
  static thread_local std::string out;
  out = saem::call_json(m ? m : "", a ? a : "");
  return out.c_str();
}

// core.methods — required by tools/qcos_handshake.py (R22 / A6)
const Registrar c0("core.methods", [](const Json&) -> Json {
  Json o = Json::array();
  for (const auto& m : saem::methods())
    o.push(Json(m));
  return o;
});

extern "C" SAEM_EXPORT const char* saem_methods(void) {
  static thread_local std::string out;
  saem::Json a = saem::Json::array();
  for (const auto& m : saem::methods()) a.push(saem::Json(m));
  out = a.dump();
  return out.c_str();
}
