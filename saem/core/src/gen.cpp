// Math Brain: C++ port of reference/src/gen.js. Same templates, same random stream, same wording.
#include "gen.hpp"

#include <cmath>
#include <functional>
#include <map>
#include <set>

namespace saem {
namespace gen {
namespace {

// ---------------------------------------------------------------- text building (the stand-in for JS template literals)
void app(std::string& r, const char* s) { r += s; }
void app(std::string& r, const std::string& s) { r += s; }
void app(std::string& r, double d) { r += jsnum(d); }
template <class... A>
std::string cat(const A&... a) {
  std::string r;
  int dummy[] = {0, (app(r, a), 0)...};
  (void)dummy;
  return r;
}

const char* SUP_DIGITS[10] = {"⁰", "¹", "²", "³", "⁴", "⁵", "⁶", "⁷", "⁸", "⁹"};
std::string sup(int n) {
  std::string out;
  for (char c : std::to_string(n)) out += (c == '-') ? "⁻" : SUP_DIGITS[c - '0'];
  return out;
}

double SINV(double th) { return th == 30 ? 0.5 : th == 37 ? 0.6 : th == 53 ? 0.8 : 1.0; }
double COSV(double th) { return th == 30 ? 0.866 : th == 37 ? 0.8 : th == 53 ? 0.6 : 0.0; }

const char* SH_NAME[4] = {"ring", "disc", "solid sphere", "hollow sphere"};
const char* SH_FRAC[4] = {"1/2", "1/3", "2/7", "2/5"};
const char* PR_NAME[2] = {"√2", "√3"};
const double PR_DEG[2] = {30, 60};
const char* CR_N[3] = {"2", "√2", "2/√3"};
const double CR_DEG[3] = {30, 45, 60};
const char* CR_SIN[3] = {"0.5", "0.707", "0.866"};
const char* LG_NAME[5] = {"AND", "OR", "NAND", "NOR", "XOR"};
const char* LG_TEXT[5] = {"gives output 1 only when both inputs are 1", "gives output 1 when at least one input is 1",
                          "gives output 0 only when both inputs are 1", "gives output 1 only when both inputs are 0",
                          "gives output 1 only when its two inputs differ"};

std::string with_unit(double x, const std::string& U) {
  std::string s = fmt(x);
  if (!U.empty()) {
    if (!(U == "%" || U == "°")) s += " ";
    s += U;
  }
  return s;
}

// ---------------------------------------------------------------- templates
struct Par {
  std::vector<std::pair<std::string, std::vector<double>>> kv;
  double operator()(const char* k) const { return at(k, 0); }
  double at(const char* k, size_t i) const {
    for (const auto& e : kv)
      if (e.first == k) return i < e.second.size() ? e.second[i] : std::nan("");
    return std::nan("");
  }
};
using Pool = std::vector<std::vector<double>>;
Pool pool(std::initializer_list<double> xs) {
  Pool p;
  for (double x : xs) p.push_back({x});
  return p;
}

struct Tpl {
  std::string id, topic;
  std::vector<std::pair<std::string, Pool>> P;  // independent pools, in key order
  std::vector<std::string> sKeys;               // dependent tuples (S)
  Pool sRows;
  std::function<std::string(const Par&)> q;
  std::function<double(const Par&)> a;                              // numeric answer
  std::function<std::string(const Par&)> sa;                        // text answer (with o)
  std::string U;
  std::function<std::vector<double>(const Par&)> X;                 // typical slips
  std::function<std::vector<std::string>(const Par&)> o;            // all option texts (non-numeric)
  std::function<std::string(const Par&, const std::string&)> e;     // worked solution
};

Tpl indep(const char* id, const char* topic, std::vector<std::pair<std::string, Pool>> P) {
  Tpl t;
  t.id = id;
  t.topic = topic;
  t.P = std::move(P);
  return t;
}
Tpl tuples(const char* id, const char* topic, const char* keys, Pool rows) {
  Tpl t;
  t.id = id;
  t.topic = topic;
  for (const auto& k : split_char(to_u32(keys), ',')) t.sKeys.push_back(to_u8(k));
  t.sRows = std::move(rows);
  return t;
}
Pool rows(std::initializer_list<std::vector<double>> xs) { return Pool(xs); }

const std::vector<Tpl>& TPL() {
  static const std::vector<Tpl> T = [] {
    std::vector<Tpl> t;
    auto add = [&](Tpl x) { t.push_back(std::move(x)); };
    const double PI = 3.14159265358979323846;
    Tpl x;

    // ---- Kinematics
    x = indep("K1", "Kinematics", {{"v", pool({10, 20, 30, 40})}});
    x.q = [](const Par& p) { return cat("A ball is thrown vertically upward with a speed of ", p("v"), " m/s. Find the maximum height it reaches. (g = 10 m/s²)"); };
    x.a = [](const Par& p) { return p("v") * p("v") / 20; };
    x.U = "m";
    x.X = [](const Par& p) { return std::vector<double>{p("v") * p("v") / 10, p("v") / 10, p("v") * p("v") / 40}; };
    x.e = [](const Par& p, const std::string& A) { return cat("At the top the speed is zero, so H = v²/2g = ", p("v"), "²/(2 × 10) = ", A, "."); };
    add(x);

    x = indep("K2", "Kinematics", {{"v", pool({10, 20, 25, 50})}, {"th", pool({30, 37, 53})}});
    x.q = [](const Par& p) { return cat("A projectile is fired at ", p("v"), " m/s at ", p("th"), "° above the horizontal. Find its time of flight. (g = 10 m/s², sin ", p("th"), "° = ", SINV(p("th")), ")"); };
    x.a = [](const Par& p) { return 2 * p("v") * SINV(p("th")) / 10; };
    x.U = "s";
    x.X = [](const Par& p) { return std::vector<double>{p("v") * SINV(p("th")) / 10, 2 * p("v") / 10, 2 * p("v") * SINV(p("th"))}; };
    x.e = [](const Par& p, const std::string& A) { return cat("T = 2v sinθ / g = 2 × ", p("v"), " × ", SINV(p("th")), " / 10 = ", A, "."); };
    add(x);

    x = indep("K3", "Kinematics", {{"w", pool({100, 200, 300, 400})}, {"b", pool({5, 10, 20})}, {"c", pool({2, 3, 4})}});
    x.q = [](const Par& p) { return cat("A boat is steered perpendicular to the banks of a river ", p("w"), " m wide. Its speed in still water is ", p("b"), " m/s and the current is ", p("c"), " m/s. How long does it take to cross?"); };
    x.a = [](const Par& p) { return p("w") / p("b"); };
    x.U = "s";
    x.X = [](const Par& p) { return std::vector<double>{p("w") / js_hypot2(p("b"), p("c")), p("w") / (p("b") + p("c")), p("w") / (p("b") - p("c"))}; };
    x.e = [](const Par& p, const std::string& A) { return cat("Only the velocity across the river carries the boat over, so t = ", p("w"), "/", p("b"), " = ", A, ". The current only drifts it downstream."); };
    add(x);

    // ---- Laws of Motion
    x = indep("L1", "Laws of Motion", {{"m", pool({2, 5, 10, 20})}, {"mu", pool({0.2, 0.25, 0.4, 0.5})}});
    x.q = [](const Par& p) { return cat("A block of mass ", p("m"), " kg slides on a rough horizontal floor. The coefficient of kinetic friction is ", p("mu"), ". Find the friction force on the block. (g = 10 m/s²)"); };
    x.a = [](const Par& p) { return p("mu") * p("m") * 10; };
    x.U = "N";
    x.X = [](const Par& p) { return std::vector<double>{p("mu") * p("m"), p("m") * 10, p("mu") * p("m") * 20}; };
    x.e = [](const Par& p, const std::string& A) { return cat("The normal force is mg = ", p("m"), " × 10 = ", p("m") * 10, " N, so f = μN = ", p("mu"), " × ", p("m") * 10, " = ", A, "."); };
    add(x);

    x = tuples("L2", "Laws of Motion", "m1,m2", rows({{1, 3}, {2, 3}, {3, 5}, {2, 6}, {4, 6}, {1, 4}, {3, 7}}));
    x.q = [](const Par& p) { return cat("Two blocks of masses ", p("m1"), " kg and ", p("m2"), " kg hang from the ends of a light string passing over a smooth pulley. Find the acceleration of the blocks. (g = 10 m/s²)"); };
    x.a = [](const Par& p) { return (p("m2") - p("m1")) * 10 / (p("m1") + p("m2")); };
    x.U = "m/s²";
    x.X = [](const Par& p) { return std::vector<double>{(p("m2") - p("m1")) * 10 / p("m2"), (p("m1") + p("m2")) * 10 / (p("m2") - p("m1")), (p("m2") - p("m1")) * 10 / p("m1")}; };
    x.e = [](const Par& p, const std::string& A) { return cat("The net pulling force is (m₂ − m₁)g and the whole ", p("m1") + p("m2"), " kg moves, so a = (", p("m2"), " − ", p("m1"), ") × 10 / (", p("m1"), " + ", p("m2"), ") = ", A, "."); };
    add(x);

    x = indep("L3", "Laws of Motion", {{"m", pool({50, 60, 70, 80})}, {"a", pool({2, 4, 5})}});
    x.q = [](const Par& p) { return cat("A person of mass ", p("m"), " kg stands on a weighing scale in a lift accelerating upward at ", p("a"), " m/s². What does the scale read, in newtons? (g = 10 m/s²)"); };
    x.a = [](const Par& p) { return p("m") * (10 + p("a")); };
    x.U = "N";
    x.X = [](const Par& p) { return std::vector<double>{p("m") * (10 - p("a")), p("m") * 10, p("m") * p("a")}; };
    x.e = [](const Par& p, const std::string& A) { return cat("In an upward-accelerating lift N − mg = ma, so N = m(g + a) = ", p("m"), " × (10 + ", p("a"), ") = ", A, "."); };
    add(x);

    // ---- Work Energy Power
    x = indep("W1", "Work Energy Power", {{"m", pool({2, 4, 5, 10})}, {"v1", pool({2, 4, 6})}, {"v2", pool({8, 10, 12})}});
    x.q = [](const Par& p) { return cat("A body of mass ", p("m"), " kg speeds up from ", p("v1"), " m/s to ", p("v2"), " m/s. Find the net work done on it."); };
    x.a = [](const Par& p) { return 0.5 * p("m") * (p("v2") * p("v2") - p("v1") * p("v1")); };
    x.U = "J";
    x.X = [](const Par& p) {
      const double d = p("v2") - p("v1");
      return std::vector<double>{0.5 * p("m") * (d * d), p("m") * (p("v2") * p("v2") - p("v1") * p("v1")), 0.5 * p("m") * p("v2") * p("v2")};
    };
    x.e = [](const Par& p, const std::string& A) { return cat("By the work–energy theorem W = ΔK = ½m(v₂² − v₁²) = ½ × ", p("m"), " × (", p("v2"), "² − ", p("v1"), "²) = ", A, "."); };
    add(x);

    x = tuples("W2", "Work Energy Power", "k,x", rows({{100, 20}, {200, 10}, {400, 10}, {500, 20}, {200, 5}, {100, 10}}));
    x.q = [](const Par& p) { return cat("A spring of spring constant ", p("k"), " N/m is compressed by ", p("x"), " cm. Find the potential energy stored in it."); };
    x.a = [](const Par& p) { const double d = p("x") / 100; return 0.5 * p("k") * (d * d); };
    x.U = "J";
    x.X = [](const Par& p) { const double d = p("x") / 100; return std::vector<double>{p("k") * (d * d), 0.5 * p("k") * p("x") * p("x"), 0.5 * p("k") * p("x") / 100}; };
    x.e = [](const Par& p, const std::string& A) { return cat("U = ½kx² with x = ", p("x"), " cm = ", p("x") / 100, " m, so U = ½ × ", p("k"), " × (", p("x") / 100, ")² = ", A, "."); };
    add(x);

    x = indep("W3", "Work Energy Power", {{"m", pool({100, 200, 300, 500})}, {"h", pool({10, 20, 30})}, {"t", pool({10, 20, 50})}});
    x.q = [](const Par& p) { return cat("A pump raises ", p("m"), " kg of water through ", p("h"), " m in ", p("t"), " s. Find the power it delivers. (g = 10 m/s²)"); };
    x.a = [](const Par& p) { return p("m") * 10 * p("h") / p("t"); };
    x.U = "W";
    x.X = [](const Par& p) { return std::vector<double>{p("m") * p("h") / p("t"), p("m") * 10 * p("h") * p("t"), p("m") * 10 * p("t") / p("h")}; };
    x.e = [](const Par& p, const std::string& A) { return cat("Work = mgh = ", p("m"), " × 10 × ", p("h"), " = ", p("m") * 10 * p("h"), " J, and power = work/time = ", p("m") * 10 * p("h"), "/", p("t"), " = ", A, "."); };
    add(x);

    // ---- Rotational Motion
    x = indep("R1", "Rotational Motion", {{"m", pool({2, 4, 10})}, {"r", pool({10, 20, 50})}});
    x.q = [](const Par& p) { return cat("Find the moment of inertia of a uniform disc of mass ", p("m"), " kg and radius ", p("r"), " cm about an axis through its centre, perpendicular to its plane."); };
    x.a = [](const Par& p) { const double d = p("r") / 100; return 0.5 * p("m") * (d * d); };
    x.U = "kg m²";
    x.X = [](const Par& p) { const double d = p("r") / 100; return std::vector<double>{p("m") * (d * d), 0.5 * p("m") * p("r") * p("r"), 0.25 * p("m") * (d * d)}; };
    x.e = [](const Par& p, const std::string& A) { return cat("For a disc I = ½MR² with R = ", p("r"), " cm = ", p("r") / 100, " m, so I = ½ × ", p("m"), " × (", p("r") / 100, ")² = ", A, "."); };
    add(x);

    x = indep("R2", "Rotational Motion", {{"s", pool({0, 1, 2, 3})}});
    x.q = [](const Par& p) { return cat("A ", SH_NAME[static_cast<int>(p("s"))], " rolls without slipping on a horizontal surface. What fraction of its total kinetic energy is rotational?"); };
    x.o = [](const Par&) { return std::vector<std::string>{SH_FRAC[0], SH_FRAC[1], SH_FRAC[2], SH_FRAC[3]}; };
    x.sa = [](const Par& p) { return std::string(SH_FRAC[static_cast<int>(p("s"))]); };
    x.e = [](const Par& p, const std::string& A) { return cat("Rolling without slipping: K = ½mv²(1 + k²) where I = mk²R². The rotational share is k²/(1 + k²) = ", A, " for a ", SH_NAME[static_cast<int>(p("s"))], "."); };
    add(x);

    x = indep("R3", "Rotational Motion", {{"m", pool({2, 3, 5})}, {"r", pool({2, 4, 5})}, {"v", pool({3, 4, 6})}});
    x.q = [](const Par& p) { return cat("A particle of mass ", p("m"), " kg moves on a circle of radius ", p("r"), " m at a constant speed of ", p("v"), " m/s. Find its angular momentum about the centre of the circle."); };
    x.a = [](const Par& p) { return p("m") * p("v") * p("r"); };
    x.U = "kg m²/s";
    x.X = [](const Par& p) { return std::vector<double>{p("m") * p("v") * p("r") / 2, p("m") * p("v") / p("r"), p("m") * p("v") * p("v") / p("r")}; };
    x.e = [](const Par& p, const std::string& A) { return cat("The velocity is perpendicular to the radius, so L = mvr = ", p("m"), " × ", p("v"), " × ", p("r"), " = ", A, "."); };
    add(x);

    // ---- Gravitation
    x = indep("G1", "Gravitation", {{"n", pool({4, 9, 16, 25})}});
    x.q = [](const Par& p) { return cat("A planet has the same radius as the earth but ", p("n"), " times its mass. The escape velocity from the earth is 11.2 km/s. What is the escape velocity from the planet?"); };
    x.a = [](const Par& p) { return 11.2 * std::sqrt(p("n")); };
    x.U = "km/s";
    x.X = [](const Par& p) { return std::vector<double>{11.2 * p("n"), 11.2 / std::sqrt(p("n")), 11.2 * p("n") / 2}; };
    x.e = [](const Par& p, const std::string& A) { return cat("v = √(2GM/R) ∝ √M for the same radius, so v = 11.2 × √", p("n"), " = ", A, "."); };
    add(x);

    x = indep("G2", "Gravitation", {{"f", rows({{1, 2}, {1, 4}, {1, 5}, {3, 4}})}});
    x.q = [](const Par& p) { return cat("Find the acceleration due to gravity at a depth equal to ", p.at("f", 0), "/", p.at("f", 1), " of the earth's radius below its surface. (g at the surface = 10 m/s²)"); };
    x.a = [](const Par& p) { return 10 * (1 - p.at("f", 0) / p.at("f", 1)); };
    x.U = "m/s²";
    x.X = [](const Par& p) {
      const double a = p.at("f", 0), b = p.at("f", 1);
      return std::vector<double>{10 * a / b, 10 / (1 - a / b), 10 * (1 - 2 * a / b)};
    };
    x.e = [](const Par& p, const std::string& A) { return cat("Inside the earth g′ = g(1 − d/R) = 10 × (1 − ", p.at("f", 0), "/", p.at("f", 1), ") = ", A, "."); };
    add(x);

    x = indep("G3", "Gravitation", {{"n", pool({4, 16, 25, 64})}});
    x.q = [](const Par& p) { return cat("A satellite moves in a circular orbit of radius ", p("n"), "R about a planet of radius R. A satellite just above the surface moves at 8 km/s. What is the orbital speed of this satellite?"); };
    x.a = [](const Par& p) { return 8 / std::sqrt(p("n")); };
    x.U = "km/s";
    x.X = [](const Par& p) { return std::vector<double>{8 / p("n"), 8 * std::sqrt(p("n")), 8 / (p("n") - 1)}; };
    x.e = [](const Par& p, const std::string& A) { return cat("Orbital speed v = √(GM/r) ∝ 1/√r, so v = 8/√", p("n"), " = ", A, "."); };
    add(x);

    // ---- Thermodynamics
    x = indep("T1", "Thermodynamics", {{"T", pool({200, 300, 400, 500})}});
    x.q = [](const Par& p) { return cat("One mole of an ideal gas expands isothermally at ", p("T"), " K until its volume doubles. Find the work done by the gas. (R = 8.3 J/mol K, ln 2 = 0.69)"); };
    x.a = [](const Par& p) { return 8.3 * p("T") * 0.69; };
    x.U = "J";
    x.X = [](const Par& p) { return std::vector<double>{8.3 * p("T"), 8.3 * p("T") * 2, 8.3 * p("T") / 0.69}; };
    x.e = [](const Par& p, const std::string& A) { return cat("For an isothermal process W = nRT ln(V₂/V₁) = 1 × 8.3 × ", p("T"), " × 0.69 = ", A, "."); };
    add(x);

    x = tuples("T2", "Thermodynamics", "a,b", rows({{400, 300}, {500, 300}, {600, 300}, {800, 400}, {500, 400}, {1000, 600}}));
    x.q = [](const Par& p) { return cat("A Carnot engine works between a source at ", p("a"), " K and a sink at ", p("b"), " K. Find its efficiency in percent."); };
    x.a = [](const Par& p) { return (1 - p("b") / p("a")) * 100; };
    x.U = "%";
    x.X = [](const Par& p) { return std::vector<double>{p("b") / p("a") * 100, (p("a") - p("b")) / p("b") * 100, (1 - p("b") / p("a")) * 50}; };
    x.e = [](const Par& p, const std::string& A) { return cat("η = 1 − T₂/T₁ = 1 − ", p("b"), "/", p("a"), " = ", fmt(1 - p("b") / p("a")), ", which is ", A, "."); };
    add(x);

    x = indep("T3", "Thermodynamics", {{"pr", pool({100, 200, 300, 400})}, {"v", pool({2, 3, 5})}});
    x.q = [](const Par& p) { return cat("On a p–V diagram a gas goes round a rectangular cycle. The pressure side is ", p("pr"), " kPa and the volume side is ", p("v"), " litres. Find the net work done by the gas in one cycle."); };
    x.a = [](const Par& p) { return p("pr") * p("v"); };
    x.U = "J";
    x.X = [](const Par& p) { return std::vector<double>{p("pr") * p("v") / 2, 2 * p("pr") * p("v"), p("pr") * p("v") / 10}; };
    x.e = [](const Par& p, const std::string& A) { return cat("Net work in a cycle is the enclosed area: ", p("pr"), " kPa × ", p("v"), " L = ", A, ", since 1 kPa × 1 L = 1 J."); };
    add(x);

    // ---- Oscillations
    x = indep("O1", "Oscillations", {{"A", pool({2, 5, 10})}, {"w", pool({2, 5, 10})}});
    x.q = [](const Par& p) { return cat("A particle in simple harmonic motion has amplitude ", p("A"), " cm and angular frequency ", p("w"), " rad/s. Find its maximum speed."); };
    x.a = [](const Par& p) { return p("A") * p("w"); };
    x.U = "cm/s";
    x.X = [](const Par& p) { return std::vector<double>{p("A") / p("w"), p("A") * p("w") * p("w"), p("A") * p("w") / 2}; };
    x.e = [](const Par& p, const std::string& A) { return cat("v_max = Aω = ", p("A"), " × ", p("w"), " = ", A, "."); };
    add(x);

    x = indep("O2", "Oscillations", {{"l", pool({1, 4, 9, 0.25, 2.25})}});
    x.q = [](const Par& p) { return cat("Find the time period of a simple pendulum of length ", p("l"), " m. (Take g = π² m/s².)"); };
    x.a = [](const Par& p) { return 2 * std::sqrt(p("l")); };
    x.U = "s";
    x.X = [](const Par& p) { return std::vector<double>{std::sqrt(p("l")), 4 * std::sqrt(p("l")), p("l")}; };
    x.e = [](const Par& p, const std::string& A) { return cat("T = 2π√(l/g) = 2π√(", p("l"), "/π²) = 2√", p("l"), " = ", A, "."); };
    add(x);

    x = tuples("O3", "Oscillations", "m,k", rows({{1, 100}, {4, 100}, {2, 50}, {0.5, 50}, {1, 25}, {4, 64}}));
    x.q = [](const Par& p) { return cat("A block of mass ", p("m"), " kg attached to a spring of spring constant ", p("k"), " N/m oscillates on a smooth surface. Find the angular frequency of the oscillation."); };
    x.a = [](const Par& p) { return std::sqrt(p("k") / p("m")); };
    x.U = "rad/s";
    x.X = [PI](const Par& p) { return std::vector<double>{p("k") / p("m"), std::sqrt(p("m") / p("k")), 2 * PI * std::sqrt(p("m") / p("k"))}; };
    x.e = [](const Par& p, const std::string& A) { return cat("ω = √(k/m) = √(", p("k"), "/", p("m"), ") = ", A, "."); };
    add(x);

    // ---- Electrostatics
    x = tuples("E1", "Electrostatics", "q1,q2,d", rows({{4, 1, 20}, {3, 1, 30}, {5, 2, 30}, {6, 2, 20}, {8, 2, 40}}));
    x.q = [](const Par& p) { return cat("Two like point charges of +", p("q1"), " μC and +", p("q2"), " μC are ", p("d"), " cm apart in air. Find the magnitude of E at the midpoint of the line joining them. (k = 9 × 10⁹ N m²/C²)"); };
    x.a = [](const Par& p) { const double r = p("d") / 200; return 9e9 * (p("q1") - p("q2")) * 1e-6 / (r * r); };
    x.U = "N/C";
    x.X = [](const Par& p) {
      const double r1 = p("d") / 200, r2 = p("d") / 100;
      return std::vector<double>{9e9 * (p("q1") + p("q2")) * 1e-6 / (r1 * r1), 9e9 * (p("q1") - p("q2")) * 1e-6 / (r2 * r2), 9e9 * p("q1") * 1e-6 / (r1 * r1)};
    };
    x.e = [](const Par& p, const std::string& A) { return cat("At the midpoint the two fields point in opposite directions, so E = k(q₁ − q₂)/r² with r = ", p("d") / 2, " cm = ", p("d") / 200, " m. E = 9 × 10⁹ × ", p("q1") - p("q2"), " × 10⁻⁶ / (", p("d") / 200, ")² = ", A, "."); };
    add(x);

    x = indep("E2", "Electrostatics", {{"q", pool({1, 2, 5, 10})}});
    x.q = [](const Par& p) { return cat("Find the flux through a closed surface enclosing a charge of ", p("q"), " μC in vacuum. (ε₀ = 8.85 × 10⁻¹² C²/N m²)"); };
    x.a = [](const Par& p) { return p("q") * 1e-6 / 8.85e-12; };
    x.U = "N m²/C";
    x.X = [PI](const Par& p) { return std::vector<double>{p("q") * 1e-6 / (4 * PI * 8.85e-12), p("q") * 1e-6 / 8.85e-12 * 4 * PI, p("q") * 1e-6 / 8.85e-9}; };
    x.e = [](const Par& p, const std::string& A) { return cat("By Gauss's law Φ = q/ε₀ = ", p("q"), " × 10⁻⁶ / (8.85 × 10⁻¹²) = ", A, ", whatever the shape of the surface."); };
    add(x);

    x = indep("E3", "Electrostatics", {{"pm", pool({2, 4, 5})}, {"E", pool({1000, 2000, 5000})}, {"th", pool({30, 37, 53, 90})}});
    x.q = [](const Par& p) { return cat("A dipole of moment p = ", p("pm"), " × 10⁻⁶ C m is held in a uniform field of ", p("E"), " N/C at ", p("th"), "° to the field. Find the torque on the dipole. (sin ", p("th"), "° = ", SINV(p("th")), ")"); };
    x.a = [](const Par& p) { return p("pm") * 1e-6 * p("E") * SINV(p("th")); };
    x.U = "N m";
    x.X = [](const Par& p) { return std::vector<double>{p("pm") * 1e-6 * p("E") * COSV(p("th")), p("pm") * 1e-6 * p("E"), p("pm") * 1e-6 * p("E") * SINV(p("th")) * 2}; };
    x.e = [](const Par& p, const std::string& A) { return cat("τ = pE sinθ = ", p("pm"), " × 10⁻⁶ × ", p("E"), " × ", SINV(p("th")), " = ", A, "."); };
    add(x);

    // ---- Current Electricity
    x = indep("C1", "Current Electricity", {{"pa", pool({5, 10, 20})}, {"qa", pool({10, 20, 40})}, {"ra", pool({5, 10, 15, 20})}});
    x.q = [](const Par& p) { return cat("A Wheatstone bridge is balanced with P = ", p("pa"), " Ω, Q = ", p("qa"), " Ω and R = ", p("ra"), " Ω, where P/Q = R/S. Find the unknown resistance S."); };
    x.a = [](const Par& p) { return p("qa") * p("ra") / p("pa"); };
    x.U = "Ω";
    x.X = [](const Par& p) { return std::vector<double>{p("pa") * p("ra") / p("qa"), p("pa") * p("qa") / p("ra"), p("qa") + p("ra") - p("pa")}; };
    x.e = [](const Par& p, const std::string& A) { return cat("At balance P/Q = R/S, so S = QR/P = ", p("qa"), " × ", p("ra"), " / ", p("pa"), " = ", A, "."); };
    add(x);

    x = tuples("C2", "Current Electricity", "E,r,R", rows({{12, 1, 5}, {12, 2, 4}, {10, 1, 4}, {6, 1, 2}, {9, 1, 2}, {6, 2, 4}}));
    x.q = [](const Par& p) { return cat("A cell of emf ", p("E"), " V and internal resistance ", p("r"), " Ω is connected across an external resistor of ", p("R"), " Ω. Find the terminal voltage of the cell."); };
    x.a = [](const Par& p) { return p("E") * p("R") / (p("R") + p("r")); };
    x.U = "V";
    x.X = [](const Par& p) { return std::vector<double>{p("E"), p("E") * p("r") / (p("R") + p("r")), p("E") * (p("R") - p("r")) / (p("R") + p("r"))}; };
    x.e = [](const Par& p, const std::string& A) { return cat("The current is I = E/(R + r) = ", p("E"), "/(", p("R"), " + ", p("r"), ") = ", fmt(p("E") / (p("R") + p("r"))), " A, so V = IR = ", fmt(p("E") / (p("R") + p("r"))), " × ", p("R"), " = ", A, "."); };
    add(x);

    x = indep("C3", "Current Electricity", {{"R", pool({2, 5, 10})}, {"I", pool({2, 3, 5})}, {"t", pool({10, 20, 60})}});
    x.q = [](const Par& p) { return cat("A heater coil of resistance ", p("R"), " Ω carries a steady current of ", p("I"), " A for ", p("t"), " s. Find the heat produced."); };
    x.a = [](const Par& p) { return p("I") * p("I") * p("R") * p("t"); };
    x.U = "J";
    x.X = [](const Par& p) { return std::vector<double>{p("I") * p("R") * p("t"), p("I") * p("I") * p("R"), p("I") * p("I") * p("t") / p("R")}; };
    x.e = [](const Par& p, const std::string& A) { return cat("Joule heating H = I²Rt = ", p("I"), "² × ", p("R"), " × ", p("t"), " = ", A, "."); };
    add(x);

    // ---- Ray Optics
    x = tuples("P1", "Ray Optics", "u,f", rows({{30, 10}, {20, 10}, {15, 10}, {60, 20}, {30, 20}, {24, 8}, {36, 12}}));
    x.q = [](const Par& p) { return cat("A real object is placed ", p("u"), " cm in front of a concave mirror of focal length ", p("f"), " cm. Find the distance of the image from the mirror."); };
    x.a = [](const Par& p) { return p("u") * p("f") / (p("u") - p("f")); };
    x.U = "cm";
    x.X = [](const Par& p) { return std::vector<double>{p("u") * p("f") / (p("u") + p("f")), p("u") - p("f"), p("u") + p("f")}; };
    x.e = [](const Par& p, const std::string& A) { return cat("The mirror formula 1/v + 1/u = 1/f gives 1/v = 1/", p("f"), " − 1/", p("u"), ", so v = ", A, ", a real image in front of the mirror."); };
    add(x);

    x = indep("P2", "Ray Optics", {{"c", pool({0, 1, 2, 3})}});
    x.q = [](const Par& p) {
      const int c = static_cast<int>(p("c"));
      return c < 2 ? cat("An equilateral prism has refractive index ", PR_NAME[c], ". Find its angle of minimum deviation.")
                   : cat("An equilateral prism shows a minimum deviation of ", PR_DEG[c - 2], "°. Find its refractive index.");
    };
    x.o = [](const Par& p) {
      return static_cast<int>(p("c")) < 2 ? std::vector<std::string>{"30°", "45°", "60°", "75°"} : std::vector<std::string>{"√2", "√3", "1.5", "2"};
    };
    x.sa = [](const Par& p) {
      const int c = static_cast<int>(p("c"));
      return c < 2 ? cat(PR_DEG[c], "°") : std::string(PR_NAME[c - 2]);
    };
    x.e = [](const Par& p, const std::string&) {
      const int c = static_cast<int>(p("c")) % 2;
      const double d = PR_DEG[c];
      return cat("At minimum deviation n = sin((A + δ)/2) / sin(A/2), with A = 60°. For δ = ", d, "°, n = sin ", (60 + d) / 2, "° / sin 30° = ", PR_NAME[c], ".");
    };
    add(x);

    x = indep("P3", "Ray Optics", {{"c", pool({0, 1, 2})}});
    x.q = [](const Par& p) { return cat("Light travelling in glass meets the glass–air boundary. The refractive index of the glass is ", CR_N[static_cast<int>(p("c"))], ". Find the critical angle."); };
    x.o = [](const Par&) { return std::vector<std::string>{"30°", "37°", "45°", "60°"}; };
    x.sa = [](const Par& p) { return cat(CR_DEG[static_cast<int>(p("c"))], "°"); };
    x.e = [](const Par& p, const std::string& A) { const int c = static_cast<int>(p("c")); return cat("sin C = 1/n = 1/", CR_N[c], " = ", CR_SIN[c], ", so C = ", A, "."); };
    add(x);

    // ---- Nuclei
    x = indep("N1", "Nuclei", {{"h", pool({5, 10, 20, 30})}, {"k", pool({1, 2, 3, 4})}});
    x.q = [](const Par& p) { return cat("The half-life of a radioactive sample is ", p("h"), " days. What fraction of the sample remains after ", p("h") * p("k"), " days?"); };
    x.o = [](const Par&) { return std::vector<std::string>{"1/2", "1/4", "1/8", "1/16", "1/32"}; };
    x.sa = [](const Par& p) { return cat("1/", std::pow(2.0, p("k"))); };
    x.e = [](const Par& p, const std::string& A) { return cat(p("h") * p("k"), " days is ", p("k"), " half-lives, so the fraction left is (1/2)^", p("k"), " = ", A, "."); };
    add(x);

    x = indep("N2", "Nuclei", {{"d", pool({0.01, 0.02, 0.03, 0.05, 0.1, 0.2})}});
    x.q = [](const Par& p) { return cat("A nucleus has a mass defect of ", p("d"), " u. Find its binding energy. (1 u = 931.5 MeV/c²)"); };
    x.a = [](const Par& p) { return p("d") * 931.5; };
    x.U = "MeV";
    x.X = [](const Par& p) { return std::vector<double>{p("d") * 931.5 / 2, p("d") * 931.5 * 2, p("d") * 93.15}; };
    x.e = [](const Par& p, const std::string& A) { return cat("Binding energy = Δm c² = ", p("d"), " × 931.5 = ", A, "."); };
    add(x);

    x = indep("N3", "Nuclei", {{"l", pool({0.05, 0.1, 0.2, 0.25, 0.5})}});
    x.q = [](const Par& p) { return cat("A nuclide has a decay constant of ", p("l"), " s⁻¹. Find its mean life."); };
    x.a = [](const Par& p) { return 1 / p("l"); };
    x.U = "s";
    x.X = [](const Par& p) { return std::vector<double>{0.693 / p("l"), p("l"), 2 / p("l")}; };
    x.e = [](const Par& p, const std::string& A) { return cat("Mean life τ = 1/λ = 1/", p("l"), " = ", A, ". (The half-life would be 0.693τ.)"); };
    add(x);

    // ---- Semiconductors & Electronics
    x = indep("S1", "Semiconductors & Electronics", {{"g", pool({0, 1, 2, 3, 4})}});
    x.q = [](const Par& p) { return cat("Which logic gate ", LG_TEXT[static_cast<int>(p("g"))], "?"); };
    x.o = [](const Par&) { return std::vector<std::string>{LG_NAME[0], LG_NAME[1], LG_NAME[2], LG_NAME[3], LG_NAME[4]}; };
    x.sa = [](const Par& p) { return std::string(LG_NAME[static_cast<int>(p("g"))]); };
    x.e = [](const Par& p, const std::string& A) { return cat("A gate that ", LG_TEXT[static_cast<int>(p("g"))], " is the ", A, " gate."); };
    add(x);

    x = indep("S2", "Semiconductors & Electronics", {{"b", pool({0, 1})}});
    x.q = [](const Par& p) { return cat("The depletion layer of a p–n junction diode ______ when the diode is ", p("b") != 0 ? "reverse" : "forward", " biased."); };
    x.o = [](const Par&) { return std::vector<std::string>{"becomes narrower", "becomes wider", "remains unchanged", "first widens and then narrows"}; };
    x.sa = [](const Par& p) { return std::string(p("b") != 0 ? "becomes wider" : "becomes narrower"); };
    x.e = [](const Par& p, const std::string&) {
      return std::string(p("b") != 0 ? "Reverse bias pulls majority carriers away from the junction, so the depletion layer widens."
                                     : "Forward bias pushes majority carriers toward the junction, so the depletion layer narrows.");
    };
    add(x);

    x = indep("S3", "Semiconductors & Electronics", {{"b", pool({50, 100, 150, 200})}, {"ib", pool({10, 20, 40, 50})}});
    x.q = [](const Par& p) { return cat("In a common-emitter transistor circuit the current gain β is ", p("b"), " and the base current is ", p("ib"), " μA. Find the collector current."); };
    x.a = [](const Par& p) { return p("b") * p("ib") / 1000; };
    x.U = "mA";
    x.X = [](const Par& p) { return std::vector<double>{p("b") * p("ib"), p("ib") / p("b") / 1000, (p("b") + 1) * p("ib") / 1000}; };
    x.e = [](const Par& p, const std::string& A) { return cat("I_C = βI_B = ", p("b"), " × ", p("ib"), " μA = ", p("b") * p("ib"), " μA = ", A, "."); };
    add(x);

    return t;
  }();
  return T;
}

const Tpl* by_id(const std::string& id) {
  static const std::map<std::string, const Tpl*> M = [] {
    std::map<std::string, const Tpl*> m;
    for (const auto& t : TPL()) m[t.id] = &t;
    return m;
  }();
  auto it = M.find(id);
  return it == M.end() ? nullptr : it->second;
}

// ---------------------------------------------------------------- building one question
Par sample(const Tpl& t, Rng& R) {
  Par p;
  if (!t.sKeys.empty()) {
    const auto& row = pick_from(R, t.sRows);
    for (size_t i = 0; i < t.sKeys.size(); ++i) p.kv.push_back({t.sKeys[i], {row[i]}});
    return p;
  }
  for (const auto& e : t.P) p.kv.push_back({e.first, pick_from(R, e.second)});
  return p;
}

std::vector<double> numeric_options(double ans, const std::vector<double>& slips) {
  std::set<std::string> seen{fmt(ans)};
  std::vector<double> extra;
  auto add = [&](double v) {
    if (!std::isfinite(v) || (ans > 0 && v <= 0)) return;
    const std::string s = fmt(v);
    if (seen.insert(s).second) extra.push_back(v);
  };
  for (double v : slips) add(v);
  for (double m : {2.0, 0.5, 1.5, 0.75, 4.0, 0.25, 10.0, 0.1}) add(ans * m);
  std::vector<double> out{ans};
  for (size_t i = 0; i < extra.size() && i < 3; ++i) out.push_back(extra[i]);
  return out;
}

Question build_from(const Tpl& t, const Par& p, Rng& R) {
  Question q;
  q.text = t.q(p);
  std::string correct;
  std::vector<std::string> opts;
  if (t.o) {
    correct = t.sa(p);
    std::vector<std::string> rest;
    for (const auto& x : t.o(p)) if (x != correct) rest.push_back(x);
    rest = shuffled(rest, R);
    if (rest.size() > 3) rest.resize(3);
    opts.push_back(correct);
    for (const auto& x : rest) opts.push_back(x);
  } else {
    const double ans = t.a(p);
    correct = with_unit(ans, t.U);
    for (double v : numeric_options(ans, t.X ? t.X(p) : std::vector<double>{})) opts.push_back(with_unit(v, t.U));
  }
  const auto order = shuffled(opts, R);
  static const char* KEYS = "ABCD";
  for (size_t i = 0; i < order.size(); ++i) q.options.push_back({std::string(1, i < 4 ? KEYS[i] : '?'), order[i]});
  for (const auto& o : q.options) if (o.text == correct) { q.answer = o.key; break; }
  q.explanation = t.e(p, correct);
  q.topic = t.topic;
  q.gen = t.id;
  q.src = "math";
  return q;
}

}  // namespace

// ---------------------------------------------------------------- public
std::string fmt(double x) {
  if (!std::isfinite(x)) return jsnum(x);
  if (x == 0) return "0";
  const double a = std::fabs(x);
  if (a >= 1e5 || a < 1e-3) {
    int e = static_cast<int>(std::floor(std::log10(a)));
    double m = round_sig(x / std::pow(10.0, e), 4);
    if (std::fabs(m) >= 10) { m /= 10; e++; }
    return jsnum(m) + " × 10" + sup(e);
  }
  return jsnum(round_sig(x, 4));
}

const std::vector<TplInfo>& templates() {
  static const std::vector<TplInfo> v = [] {
    std::vector<TplInfo> o;
    for (const auto& t : TPL()) o.push_back({t.id, t.topic});
    return o;
  }();
  return v;
}
const std::vector<std::string>& topics() {
  static const std::vector<std::string> v = [] {
    std::vector<std::string> o;
    for (const auto& t : TPL()) if (std::find(o.begin(), o.end(), t.topic) == o.end()) o.push_back(t.topic);
    return o;
  }();
  return v;
}
bool known(const std::string& id) { return by_id(id) != nullptr; }

Question make(const std::string& id, Rng& R) {
  const Tpl* t = by_id(id);
  if (!t) throw std::runtime_error("unknown template " + id);
  return build_from(*t, sample(*t, R), R);
}

static Par par_from_json(const Json& j) {
  Par p;
  for (const auto& kv : j.obj()) {
    std::vector<double> v;
    if (kv.second.isArr()) for (const auto& x : kv.second.arr()) v.push_back(x.asNum());
    else v.push_back(kv.second.asNum());
    p.kv.push_back({kv.first, v});
  }
  return p;
}

Question question_with(const std::string& id, const Json& params, uint32_t seed) {
  const Tpl* t = by_id(id);
  if (!t) throw std::runtime_error("unknown template " + id);
  Rng R(seed ? seed : 1);
  return build_from(*t, par_from_json(params), R);
}

Json solve(const std::string& id, const Json& params) {
  const Tpl* t = by_id(id);
  if (!t) throw std::runtime_error("unknown template " + id);
  const Par p = par_from_json(params);
  if (t->o) return Json(t->sa(p));
  return Json(t->a(p));
}

Json question_json(const Question& q) {
  Json o = Json::object();
  o.set("text", q.text);
  Json opts = Json::array();
  for (const auto& x : q.options) {
    Json e = Json::object();
    e.set("key", x.key);
    e.set("text", x.text);
    opts.push(e);
  }
  o.set("options", opts);
  o.set("answer", q.answer);
  o.set("explanation", q.explanation);
  o.set("topic", q.topic);
  o.set("gen", q.gen);
  o.set("src", q.src);
  return o;
}

Json demo_bank(uint32_t seed, int y0, int y1) {
  if (!y0) y0 = 2006;
  if (!y1) y1 = 2026;
  Rng R(seed ? seed : 11);
  static const std::vector<std::string> NQ = {"potential", "energy", "momentum", "period", "frequency", "pressure", "charge", "current", "field", "torque", "wavelength", "speed", "force", "power", "flux"};
  static const std::vector<std::string> NO = {"uniform rod", "thin ring", "metallic sphere", "copper wire", "glass block", "gas cylinder", "light bulb", "magnetic needle", "steel wire", "iron bar", "water jet", "liquid drop", "wooden cube", "hollow shell", "long cylinder"};
  static const std::vector<std::string> NC = {"when it is heated by 20 K", "at a distance of 3 m", "after 5 s", "if its length is doubled", "if its radius is halved", "when the temperature rises", "if its mass is increased", "near the surface", "in a vacuum chamber", "under constant force", "when it moves slowly", "if it is cut into two equal parts"};
  static const char* KINDS[12] = {"steady", "cycle", "rise", "cycle", "fade", "low", "steady", "cycle", "rise", "low", "fade", "steady"};
  Json items = Json::array();
  for (int y = y0; y <= y1; ++y) {
    const int t = y - y0, span = y1 - y0;
    int n = 0;
    const auto& tpls = TPL();
    for (size_t i = 0; i < tpls.size(); ++i) {
      const std::string kind = KINDS[i % 12];
      const int per = 3 + static_cast<int>(i % 3), ph = static_cast<int>(i % static_cast<size_t>(per));
      double pr;
      if (kind == "steady") pr = 0.5;
      else if (kind == "low") pr = 0.12;
      else if (kind == "rise") pr = 0.08 + 0.6 * t / span;
      else if (kind == "fade") pr = 0.66 - 0.56 * t / span;
      else pr = ((t - ph) % per == 0) ? 0.85 : 0.05;
      if (R() < pr) {
        auto emit = [&]() {
          Json it = Json::object();
          it.set("year", y);
          it.set("concept", Json());
          Json q = question_json(build_from(tpls[i], sample(tpls[i], R), R));
          for (const auto& kv : q.obj()) it.set(kv.first, kv.second);
          items.push(it);
          ++n;
        };
        emit();
        if (R() < 0.12) emit();
      }
    }
    while (n < 30) {
      Json it = Json::object();
      it.set("year", y);
      const std::string a = pick_from(R, NQ), b = pick_from(R, NO), c = pick_from(R, NC);
      it.set("text", "Find the " + a + " of a " + b + " " + c + ".");
      it.set("topic", pick_from(R, topics()));
      it.set("concept", Json());
      items.push(it);
      ++n;
    }
  }
  return items;
}

Json vectors() {
  static const char* SRC =
#include "data/vectors.inc"
      ;
  return Json::parse(SRC);
}

}  // namespace gen
}  // namespace saem
