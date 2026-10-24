// core/src/api.cpp
#include "api.hpp"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

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
  static std::map<std::string, Handler> t;
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
  return v;
}

// ---------- local helpers ----------
namespace {

uint64_t seed_of(const Json& a, uint64_t dflt) {
  if (!a.has("seed") || !a["seed"].isNum()) return dflt;
  return static_cast<uint64_t>(static_cast<int64_t>(a["seed"].asNum()));
}

void require_str(const Json& a, const char* key) {
  if (!a.has(key))
    throw std::runtime_error(std::string("missing required field: ") + key);
  if (!a[key].isStr())
    throw std::runtime_error(std::string("field '") + key + "' must be a string");
}

void require_num(const Json& a, const char* key) {
  if (!a.has(key))
    throw std::runtime_error(std::string("missing required field: ") + key);
  if (!a[key].isNum())
    throw std::runtime_error(std::string("field '") + key + "' must be a number");
}

void require_obj(const Json& a, const char* key) {
  if (!a.has(key))
    throw std::runtime_error(std::string("missing required field: ") + key);
  if (!a[key].isObj())
    throw std::runtime_error(std::string("field '") + key + "' must be an object");
}

std::string sup_exp(const std::string& digits, bool neg) {
  static const char* SUP[10] = {
    "\xe2\x81\xb0", "\xc2\xb9", "\xc2\xb2", "\xc2\xb3", "\xe2\x81\xb4",
    "\xe2\x81\xb5", "\xe2\x81\xb6", "\xe2\x81\xb7", "\xe2\x81\xb8",
    "\xe2\x81\xb9"};
  std::string out;
  if (neg) out += "\xe2\x81\xbb";
  for (char c : digits)
    if (c >= '0' && c <= '9') out += SUP[c - '0'];
  return out;
}

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

uint32_t hash32(const std::string& s) {
  uint32_t h = 0x811c9dc5u;
  for (unsigned char c : s) {
    h ^= static_cast<uint32_t>(c);
    h *= 0x01000193u;
  }
  return h;
}

struct MethodDoc {
  const char* name;
  const char* desc;
  const char* args;
};

const MethodDoc docs[] = {
  {"gen.make", "Generate a question from a template", "id: string, seed: number (optional)"},
  {"gen.questionWith", "Generate a question with specific parameters", "id: string, seed: number, params: object"},
  {"gen.solve", "Solve a question given parameters", "id: string, params: object"},
  {"gen.demoBank", "Generate a synthetic paper bank", "seed: number, y0: int, y1: int"},
  {"gen.topics", "List all available topics", "(none)"},
  {"gen.templates", "List all available templates", "(none)"},
  {"gen.format", "Format a number with 4 significant figures", "x: number"},
  {"gen.vectors", "Get hand-worked answer vectors", "(none)"},
  {"gen.hash32", "Compute FNV-1a 32-bit hash of a string", "s: string"},
  {"gen.makeBatch", "Generate multiple questions in one call", "items: array of {id, seed, params}"},
  {"gen.help", "Get documentation for a method or list all", "method: string (optional)"},
  {nullptr, nullptr, nullptr}
};

}  // namespace

// Fixed: Added proper lambda signatures `[](const Json& a)`
const Registrar g1("gen.make", [](const Json& a) {
  require_str(a, "id");
  return gen::make(a["id"].asStr(), seed_of(a, 1));
});

const Registrar g2("gen.questionWith", [](const Json& a) {
  require_str(a, "id");
  if (!a.has("params") || !a["params"].isObj())
    throw std::runtime_error("field 'params' must be an object");
  return gen::question_with(a["id"].asStr(), seed_of(a, 1), a["params"]);
});

const Registrar g3("gen.solve", [](const Json& a) {
  require_str(a, "id");
  if (!a.has("params") || !a["params"].isObj())
    throw std::runtime_error("field 'params' must be an object");
  return gen::solve(a["id"].asStr(), a["params"]);
});

const Registrar g4("gen.demoBank", [](const Json& a) {
  return gen::bank(seed_of(a, 11), a["y0"].asInt(0), a["y1"].asInt(0));
});

const Registrar g5("gen.topics", [](const Json& a) {
  Json o = Json::array();
  for (const auto& t : gen::topics()) o.push(t);
  return o;
});

const Registrar g6("gen.templates", [](const Json& a) {
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
  require_num(a, "x");
  return Json(fmt4(a["x"].asNum()));
});

const Registrar g8("gen.vectors", [](const Json& a) {
  return gen::vectors();
});

const Registrar g9("gen.hash32", [](const Json& a) {
  require_str(a, "s");
  return Json(static_cast<double>(hash32(a["s"].asStr())));
});

const Registrar g10("gen.makeBatch", [](const Json& a) {
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
      Json r;
      if (item.has("params") && item["params"].isObj()) {
        r = gen::question_with(item["id"].asStr(), seed_of(item, 1), item["params"]);
      } else {
        r = gen::make(item["id"].asStr(), seed_of(item, 1));
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

const Registrar g11("gen.help", [](const Json& a) {
  if (a.has("method") && a["method"].isStr()) {
    const std::string m = a["method"].asStr();
    for (const MethodDoc* d = docs; d->name; ++d) {
      if (m == d->name) {
        Json o = Json::object();
        o.set("name", d->name);
        o.set("description", d->desc);
        o.set("args", d->args);
        return o;
      }
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
