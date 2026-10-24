#pragma once
#include <string>
#include <vector>
#include <sstream>
#include <algorithm>

namespace saem {
inline std::string trim(const std::string& s) {
    auto b = s.find_first_not_of(" \t\n\r");
    auto e = s.find_last_not_of(" \t\n\r");
    return (b == std::string::npos) ? "" : s.substr(b, e - b + 1);
}
inline std::vector<std::string> split(const std::string& s, char delim) {
    std::vector<std::string> out; std::stringstream ss(s); std::string item;
    while (std::getline(ss, item, delim)) out.push_back(item);
    return out;
}
}
