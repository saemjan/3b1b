#include "gen.hpp"
#include "numfmt.hpp"
#include "util.hpp"
#include <cmath>
#include <random>

namespace saem { namespace gen {
    std::vector<std::string> topics() { return {"kinematics", "electromagnetism", "quantum", "thermodynamics"}; }
    std::vector<Template> templates() { return {{"falling_energy", "kinematics"}, {"coulomb_force", "electromagnetism"}, {"two_path_interference", "quantum"}}; }
    Json known(const std::string& id) { Json o = Json::object(); o.set("id", id); o.set("status", "known"); return o; }
    Json vectors() { Json a = Json::array(); Json v1 = Json::object(); v1.set("x", 1.0); v1.set("y", 0.0); v1.set("z", 0.0); a.push(v1); return a; }

    Json make(const std::string& id, uint64_t seed) {
        std::mt19937_64 rng(seed); Json o = Json::object(); o.set("id", id); o.set("seed", std::to_string(seed));
        if (id == "falling_energy") {
            double m = 0.1 + (rng() % 100) / 10.0, h = 1.0 + (rng() % 500) / 10.0, g = 9.80665, E = m * g * h;
            o.set("m", m); o.set("h", h); o.set("E_joules", E); o.set("E_str", jsnum(E));
        }
        return o;
    }
    Json question_with(const std::string& id, uint64_t seed, const Json& params) { return make(id, seed); }
    
    Json solve(const std::string& id, const Json& params) {
        Json o = Json::object();
        if (id == "falling_energy" && params.is_obj() && params.get("m").is_num() && params.get("h").is_num()) {
            double m = params.get("m").as_num(), h = params.get("h").as_num(), E = m * 9.80665 * h;
            o.set("E_joules", E); o.set("E_str", jsnum(E)); o.set("verified", true);
        } else { o.set("verified", false); }
        return o;
    }

    // Bernoulli's Ars Conjectandi: expectation over a bank of years
    Json bank(uint64_t seed, int y0, int y1) {
        std::mt19937_64 rng(seed); Json a = Json::array();
        for (int y = y0; y <= y1; ++y) {
            Json row = Json::object(); row.set("year", y);
            double p = 0.5 + (rng() % 1000) / 2000.0; 
            row.set("probability", p);
            row.set("moral_certainty", std::abs(std::log(p / (1.0 - p))) > std::log(1000.0)); // Bernoulli's 1000:1 bar
            a.push(row);
        }
        return a;
    }
}}
