#pragma once
#include "json.hpp"
#include <string>
#include <vector>

namespace saem { namespace gen {
    std::vector<std::string> topics();
    struct Template { std::string id; std::string topic; };
    std::vector<Template> templates();
    Json known(const std::string& id);
    Json make(const std::string& id, uint64_t seed);
    Json question_with(const std::string& id, uint64_t seed, const Json& params);
    Json solve(const std::string& id, const Json& params);
    Json bank(uint64_t seed, int y0, int y1);
    Json vectors();
}}
