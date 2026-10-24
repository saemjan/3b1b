#pragma once
#include "json.hpp"
#include <cstdint>
#include <string>
#include <vector>

namespace saem {
namespace gen {

std::vector<std::string> topics();

struct Template {
  std::string id;
  std::string topic;
};
std::vector<Template> templates();

Json known(const std::string& id);

// Returns a full question object (the old "question_json" role).
Json make(const std::string& id, uint64_t seed);
Json question_with(const std::string& id, uint64_t seed, const Json& params);

// Convenience alias used by api.cpp
inline Json question_json(const Json& q) { return q; }

Json solve(const std::string& id, const Json& params);

// Named "bank" in implementation; api.cpp calls demo_bank → provide both.
Json bank(uint64_t seed, int y0, int y1);
inline Json demo_bank(uint64_t seed, int y0, int y1) {
  return bank(seed, y0, y1);
}

Json vectors();

}  // namespace gen
}  // namespace saem
