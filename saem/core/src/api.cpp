// The registry, the JSON text wrapper, and the C door (saem_call). Also the Math Brain's methods.
#include "api.hpp"

#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <map>
#include <stdexcept>

#include "gen.hpp"
#include "util.hpp"

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
  static std::map<std::string, Handler> t;  // built on first use, so file-level registrars may run in any order
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

const char* source_id() { return SAEM_SOURCE_ID; }

std::vector<std::string> methods() {
  std::vector<std::string> v;
  for (const auto& kv : table()) v.push_back(kv.first);
  return v;  // std::map keeps them sorted
}

// ---------------------------------------------------------------- Math Brain
namespace {
uint32_t seed_of(const Json& a, uint32_t dflt) {
  if (!a.has("seed") || !a["seed"].isNum()) return dflt;
  return static_cast<uint32_t>(static_cast<int64_t>(a["seed"].asNum()));
}

const Registrar g1("gen.make", [](const Json& a) {
  Rng R(seed_of(a, 1));
  return gen::question_json(gen::make(a["id"].asStr(), R));
});
const Registrar g2("gen.questionWith", [](const Json& a) {
  return gen::question_json(gen::question_with(a["id"].asStr(), a["params"], seed_of(a, 1)));
});
const Registrar g3("gen.solve", [](const Json& a) { return gen::solve(a["id"].asStr(), a["params"]); });
const Registrar g4("gen.demoBank", [](const Json& a) {
  return gen::demo_bank(seed_of(a, 11), a["y0"].asInt(0), a["y1"].asInt(0));
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
const Registrar g7("gen.format", [](const Json& a) { return Json(gen::fmt(a["x"].asNum())); });
const Registrar g8("gen.vectors", [](const Json&) { return gen::vectors(); });
const Registrar g9("gen.hash32", [](const Json& a) { return Json(static_cast<double>(hash32(a["s"].asStr()))); });
const Registrar g10("core.methods", [](const Json&) {
  Json o = Json::array();
  for (const auto& m : methods()) o.push(m);
  return o;
});
}  // namespace
}  // namespace saem

// ---------------------------------------------------------------- the C door
extern "C" {
SAEM_EXPORT int saem_abi(void) { return 1; }
SAEM_EXPORT const char* saem_source_id(void) { return SAEM_SOURCE_ID; }
SAEM_EXPORT char* saem_call(const char* method, const char* args_json) {
  const std::string r = saem::call_json(method ? method : "", args_json ? args_json : "");
  char* p = static_cast<char*>(std::malloc(r.size() + 1));
  if (!p) return nullptr;
  std::memcpy(p, r.c_str(), r.size() + 1);
  return p;
}
SAEM_EXPORT void saem_free(char* p) { std::free(p); }
}
