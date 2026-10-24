// The registry, the JSON text wrapper, the C door (saem_call), and the
// Math Brain's methods.
//
// v3 (after runs #172/#176): THIS repository's gen.hpp is JSON-native.
//   - gen::make          returns saem::Json           (no Question struct, no Rng)
//   - gen::question_with takes  (id, seed, params)    (gen.hpp line 12)
//   - gen::solve / bank / topics / templates / vectors return saem::Json
//   - gen exports NO fmt, NO hash32, NO question_json
// The door passes Json straight through and provides fmt4/hash32 locally.
// A lambda whose body fails to compile poisons every Registrar call
// behind it, so every handler here is a minimal pass-through.
#include "api.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <map>
#include <stdexcept>
#include <string>

#include "gen.hpp"
#include "numfmt.hpp"
#include "sha256.hpp"

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
  static std::map<std::string, Handler> t;  // first use: any init order
  return t;
}
}  // namespace

Registrar::Registrar(const char* name, Handler h) { table()[name] = std::move(h); }

Json call(const std::string& method, const Json& args) {
  auto it = table().find(method);
  if (it == table().end())
    throw std::runtime_error("unknown method: " + method);
  return it->second(args);
}

std::string call_json(const std::string& method, const std::string& args_json) {
  Json out = Json::object();
  try {
    const Json args = args_json.empty() ? Json::object() : Json::parse(args_json);
    Json r = call(method, args);
    out.set("ok", true);
    out.set("result", std::move(r));
  } catch (const std::exception& e) {
    out = Json::object();
    out.set("ok", false);
    out.set("error", std::string(e.what()));
  } catch (...) {
    out = Json::object();
    out.set("ok", false);
    out.set("error", "unknown failure");
  }
  return out.dump();
}

std::vector<std::string> methods() {
  std::vector<std::string> v;
  for (const auto& kv : table()) v.push_back(kv.first);
  return v;  // std::map keeps them sorted
}

// ---------- local helpers: symbols this gen.hpp does not export --------
namespace {

uint32_t seed_of(const Json& a, uint32_t dflt) {
  if (!a.has("seed") || !a["seed"].isNum()) return dflt;
  return static_cast<uint32_t>(static_cast<int64_t>(a["seed"].asNum()));
}

// Superscript digits for the x10^n form (GEN.fmt mirror).
std::string sup_exp(const std::string& digits, bool neg) {
  static const char* SUP[10] = {
    "\xe2\x81\xb0", "\xc2\xb9", "\xc2\xb2", "\xc2\xb3", "\xe2\x81\xb4",
    "\xe2\x81\xb5", "\xe2\x81\xb6", "\xe2\x81\xb7", "\xe2\x81\xb8",
    "\xe2\x81\xb9"};
  std::string out;
  if (neg) out += "\xe2\x81\xbb";  // superscript minus
  for (char c : digits)
    if (c >= '0' && c <= '9') out += SUP[c - '0'];
  return out;
}

// 4 significant figures, x10^n form for very large or small values.
std::string fmt4(double x) {
  const std::string s = round_sig(x, 4);
  const size_t e = s.find('e');
  if (e == std::string::npos) return s;
  std::string ex = s.substr(e + 1);
  bool neg = !ex.empty() && ex[0] == '-';
  if (!ex.empty() && (ex[0] == '+' || ex[0] == '-')) ex = ex.substr(1);
  while (ex.size() > 1 && ex[0] == '0') ex = ex.substr(1);
  return s.substr(0, e) + " \xc3\x97 10" + sup_exp(ex, neg);
}

// FNV-1a 32-bit: the string hash the reference calls hash32.
uint32_t hash32(const std::string& s) {
  uint32_t h = 0x811c9dc5u;
  for (unsigned char c : s) {
    h ^= static_cast<uint32_t>(c);
    h *= 0x01000193u;
  }
  return h;
}

// ---------- Math Brain, bound to THIS gen.hpp (JSON-native) ----------
const Registrar g1("gen.make", [](const Json& a) {
  return gen::make(a["id"].asStr(), seed_of(a, 1));
});
const Registrar g2("gen.questionWith", [](const Json& a) {
  return gen::question_with(a["id"].asStr(), seed_of(a, 1), a["params"]);
});
const Registrar g3("gen.solve", [](const Json& a) {
  return gen::solve(a["id"].asStr(), a["params"]);
});
const Registrar g4("gen.demoBank", [](const Json& a) {
  return gen::bank(seed_of(a, 11), a["y0"].asInt(0), a["y1"].asInt(0));
});
const Registrar g5("gen.topics", [](const Json&) {
  Json o = Json::array();
  for (const auto& t : gen::topics()) o.push(t);
  return o;
});
const Registrar g6("gen.templates", [](const Json&) {
  Json o = Json::array();
  for (const auto& t : gen::templates()) {
    Json e = Json::object();
    e.set("id", t.id);
    e.set("topic", t.topic);
    o.push(e);
  }
  return o;
});
const Registrar g7("gen.format", [](const Json& a) {
  return Json(fmt4(a["x"].asNum()));
});
const Registrar g8("gen.vectors", [](const Json&) { return gen::vectors(); });
const Registrar g9("gen.hash32", [](const Json& a) {
  return Json(static_cast<double>(hash32(a["s"].asStr())));
});

}  // namespace
}  // namespace saem

extern "C" SAEM_EXPORT const char* saem_call(const char* method,
                                             const char* args_json) {
  static thread_local std::string out;
  out = saem::call_json(method ? method : "", args_json ? args_json : "");
  return out.c_str();
}
extern "C" SAEM_EXPORT const char* saem_methods(void) {
  static thread_local std::string out;
  saem::Json a = saem::Json::array();
  for (const auto& m : saem::methods()) a.push(saem::Json(m));
  out = a.dump();
  return out.c_str();
}
