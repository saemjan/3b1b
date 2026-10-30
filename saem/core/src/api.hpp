// The one door into the core. Every capability is a named method: JSON in, JSON out, no hidden state.
// A module registers its methods with a file-level Registrar; nothing else in the core knows about callers.
//
//   static const saem::Registrar r1("forecast.analyze", [](const saem::Json& a) { ... return saem::Json(...); });
//
// The same names are served by tools/ref_bridge.js (the JavaScript reference) so the two can be compared line for line.
#pragma once
#include <functional>
#include <string>
#include <vector>

#include "json.hpp"

namespace saem {

using Handler = std::function<Json(const Json&)>;

struct Registrar {
  Registrar(const char* name, Handler h);
};

// Runs one method. Throws std::runtime_error for an unknown method; a handler may throw to report a bad argument.
Json call(const std::string& method, const Json& args);

// Never throws. Returns {"ok":true,"result":...} or {"ok":false,"error":"..."} as JSON text.
std::string call_json(const std::string& method, const std::string& args_json);

// Registered method names, sorted.
std::vector<std::string> methods();

// SHA-256 of the sources this binary was built from (see tools/build.py); "dev" when built some other way.
const char* source_id();

}  // namespace saem
