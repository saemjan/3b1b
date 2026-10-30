// Shared vocabulary of the Nucleus modules (saem::nx). Header only, no state.
// Adapted in spirit from Open Math Harness (Apache License 2.0); see third_party/NOTICE-open-math-harness.md.
#pragma once
#include <cstddef>
#include <cstdint>
#include <string>
#include <utility>

namespace saem {
namespace nx {

using Tick = std::uint64_t;  // logical time given by the caller; nothing in nx ever reads a clock
using Id = std::uint64_t;    // an identity or a handle; 0 means nobody / nothing
constexpr std::size_t kCacheLine = 64;

// Why an operation was refused. Refusal is the default answer; Ok has to be earned.
enum class Err : std::uint8_t {
  Ok = 0, Denied, Expired, Revoked, NotFound, Exists, Full, Closed, Invalid, Frozen, Duplicate, Unverified
};

inline const char* err_name(Err e) {
  switch (e) {
    case Err::Ok: return "ok";
    case Err::Denied: return "denied";
    case Err::Expired: return "expired";
    case Err::Revoked: return "revoked";
    case Err::NotFound: return "not_found";
    case Err::Exists: return "exists";
    case Err::Full: return "full";
    case Err::Closed: return "closed";
    case Err::Invalid: return "invalid";
    case Err::Frozen: return "frozen";
    case Err::Duplicate: return "duplicate";
    case Err::Unverified: return "unverified";
  }
  return "unknown";
}

// A value or a reason. Never throws, so the C boundary can rely on it.
template <class T>
struct Result {
  Err err = Err::Denied;
  T value{};
  bool ok() const { return err == Err::Ok; }
  static Result good(T v) { Result r; r.err = Err::Ok; r.value = std::move(v); return r; }
  static Result bad(Err e) { Result r; r.err = e; return r; }
};

}  // namespace nx
}  // namespace saem
