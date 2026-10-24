// The registry, the JSON text wrapper, the C door (saem_call), and the
// Math Brain's methods. v5: validation restored (A0 fail-closed), parity
// defaults pinned to the ruler (A1), batch + help restored, Landauer debt
// reported on unhandled C++ failure (A3).
#include "api.hpp"

#include <cstdint>
#include <map>
#include <new>
#include <stdexcept>
#include <string>
#include <vector>

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
  static std::map<std::string, Handler> t;  // Meyers singleton: any init order
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
  } catch (const std::bad_alloc&) {
    out = Json::object();
    out.set("ok", false);
    out.set("error", "LANDAUER_DEBT_OOM");
  } catch (const std::exception& e) {
    out = Json::object();
    out.set("ok", false);
    out.set("error", std::string(e.what()));
  } catch (...) {
    out = Json::object();
    out.set("ok", false);
    out.set("error", "UNKNOWN_FAILURE_DEBT");
  }
  return out.dump();
}

std::vector<std::string> methods() {
  std::vector<std::string> v;
  for (const auto& kv : table()) v.push_back(kv.first);
  return v;
}

namespace {
uint32_t seed_of(const Json& a, uint32_t dflt) {
  if (!a.has("seed") || !a["seed"].isNum()) return dflt;
  return static_cast<uint32_t>(static_cast<int64_t>(a["seed"].asNum()));
}
void require_str(const Json& a, const char* key) {
  if (!a.has(key)) throw std::runtime_error(std::string("missing field: ") + key);
  if (!a[key].isStr())
    throw std::runtime_error(std::string("field '") + key + "' must be a string");
}
void require_num(const Json& a, const char* key) {
  if (!a.has(key)) throw std::runtime_error(std::string("missing field: ") + key);
  if (!a[key].isNum())
    throw std::runtime_error(std::string("field '") + key + "' must be a number");
}
void require_obj(const Json& a, const char* key) {
  if (!a.has(key)) throw std::runtime_error(std::string("missing field: ") + key);
  if (!a[key].isObj())
    throw std::runtime_error(std::string("field '") + key + "' must be an object");
}
uint32_t hash32(const std::string& s) {  // FNV-1a, the ruler's hash32
  uint32_t h = 0x811c9dc5u;
  for (unsigned char c : s) { h ^= c; h *= 0x01000193u; }
  return h;
}
struct MethodDoc { const char* name; const char* desc; const char* args; };
const MethodDoc docs[] = {
  {"gen.make", "Generate a question from a template", "id: string, seed: number (optional)"},
  {"gen.questionWith", "Generate a question with parameters", "id: string, params: object, seed: number (optional)"},
  {"gen.solve", "Solve a question given parameters", "id: string, params: object"},
  {"gen.demoBank", "Synthetic paper bank", "seed: number (optional, 11), y0: int, y1: int"},
  {"gen.topics", "List topics", "(none)"},
  {"gen.templates", "List templates", "(none)"},
  {"gen.format", "4 significant figures", "x: number"},
  {"gen.vectors", "Hand-worked answer vectors", "(none)"},
  {"gen.hash32", "FNV-1a 32-bit hash of a string", "s: string"},
  {"gen.makeBatch", "Generate many questions in one call", "items: array of {id, seed?, params?}"},
  {"gen.help", "Method documentation", "method: string (optional)"},
  {nullptr, nullptr, nullptr}};
}  // namespace

const Registrar g1("gen.make", [](const Json& a) -> Json {
  require_str(a, "id");
  Rng R(seed_of(a, 1));
  return gen::question_json(gen::make(a["id"].asStr(), R));
});
const Registrar g2("gen.questionWith", [](const Json& a) -> Json {
  require_str(a, "id");
  require_obj(a, "params");
  return gen::question_json(
      gen::question_with(a["id"].asStr(), a["params"], seed_of(a, 1)));
});
const Registrar g3("gen.solve", [](const Json& a) -> Json {
  require_str(a, "id");
  require_obj(a, "params");
  return gen::solve(a["id"].asStr(), a["params"]);
});
const Registrar g4("gen.demoBank", [](const Json& a) -> Json {
  return gen::demo_bank(seed_of(a, 11), a["y0"].asInt(0), a["y1"].asInt(0));
});
const Registrar g5("gen.topics", [](const Json&) -> Json {
  Json o = Json::array();
  for (const auto& t : gen::topics()) o.push(t);
  return o;
});
const Registrar g6("gen.templates", [](const Json&) -> Json {
  Json o = Json::array();
  for (const auto& t : gen::templates()) {
    Json e = Json::object();
    e.set("id", t.id);
    e.set("topic", t.topic);
    o.push(e);
  }
  return o;
});
const Registrar g7("gen.format", [](const Json& a) -> Json {
  require_num(a, "x");
  return Json(gen::fmt(a["x"].asNum()));
});
const Registrar g8("gen.vectors", [](const Json&) -> Json {
  return gen::vectors();
});
const Registrar g9("gen.hash32", [](const Json& a) -> Json {
  require_str(a, "s");
  return Json(static_cast<double>(hash32(a["s"].asStr())));
});
const Registrar g10("gen.makeBatch", [](const Json& a) -> Json {
  if (!a.has("items") || !a["items"].isArr())
    throw std::runtime_error("field 'items' must be an array");
  Json results = Json::array();
  for (const Json& item : a["items"].arr()) {
    if (!item.isObj()) {
      Json err = Json::object();
      err.set("ok", false);
      err.set("error", "item must be an object");
      results.push(err);
      continue;
    }
    try {
      require_str(item, "id");
      Json r;
      if (item.has("params") && item["params"].isObj()) {
        r = gen::question_json(
            gen::question_with(item["id"].asStr(), item["params"], seed_of(item, 1)));
      } else {
        Rng R(seed_of(item, 1));
        r = gen::question_json(gen::make(item["id"].asStr(), R));
      }
      Json wrapped = Json::object();
      wrapped.set("ok", true);
      wrapped.set("result", r);
      results.push(wrapped);
    } catch (const std::exception& e) {
      Json err = Json::object();
      err.set("ok", false);
      err.set("error", std::string(e.what()));
      results.push(err);
    }
  }
  return results;
});
const Registrar g11("gen.help", [](const Json& a) -> Json {
  if (a.has("method") && a["method"].isStr()) {
    const std::string m = a["method"].asStr();
    for (const MethodDoc* d = docs; d->name; ++d)
      if (m == d->name) {
        Json o = Json::object();
        o.set("name", d->name);
        o.set("description", d->desc);
        o.set("args", d->args);
        return o;
      }
    throw std::runtime_error("unknown method: " + m);
  }
  Json o = Json::array();
  for (const MethodDoc* d = docs; d->name; ++d) {
    Json e = Json::object();
    e.set("name", d->name);
    e.set("description", d->desc);
    o.push(e);
  }
  return o;
});

}  // namespace saem

extern "C" SAEM_EXPORT const char* saem_call(const char* method, const char* args_json) {
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
