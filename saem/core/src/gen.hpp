// Math Brain: exact, deterministic physics question solvers (C++ port of reference/src/gen.js).
// Every answer is computed from the numbers in the question, never guessed.
#pragma once
#include <string>
#include <vector>

#include "json.hpp"
#include "util.hpp"

namespace saem {
namespace gen {

struct Option {
  std::string key, text;
};
struct Question {
  std::string text, answer, explanation, topic, gen, src;
  std::vector<Option> options;
};
struct TplInfo {
  std::string id, topic;
};

const std::vector<TplInfo>& templates();           // in table order
const std::vector<std::string>& topics();          // 12 topics, first-seen order
std::string fmt(double x);                         // 4 significant figures, × 10ⁿ form for very large or small values
Question make(const std::string& id, Rng& R);     // a fresh question; R decides the numbers and the option order
Question question_with(const std::string& id, const Json& params, uint32_t seed);
Json solve(const std::string& id, const Json& params);  // the exact answer: a number or a string
Json question_json(const Question& q);
Json demo_bank(uint32_t seed, int y0, int y1);     // synthetic papers: 12 topics x 3 concepts across the years
Json vectors();                                    // hand-worked answers [[id, params, want, tol?], ...]
bool known(const std::string& id);

}  // namespace gen
}  // namespace saem
