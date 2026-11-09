#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <stdexcept>
#include <vector>
namespace rhm {
enum class Status : uint8_t { OK = 0, WARN = 1, ERROR = 2, STALE = 3 };
inline double score(const std::vector<Status> &statuses) {
  if (statuses.empty()) return 0.0;
  constexpr std::array<double, 4> weights{100.0, 65.0, 20.0, 0.0};
  double total = 0.0;
  for (const auto status : statuses) total += weights.at(static_cast<size_t>(status));
  return total / static_cast<double>(statuses.size());
}
class Debouncer {
 public:
  explicit Debouncer(unsigned int required = 3) : required_(required) {
    if (!required) throw std::invalid_argument("debounce count must be positive");
  }
  Status update(Status observed) {
    if (observed == Status::STALE) {
      stable_ = candidate_ = observed;
      count_ = 0;
    } else if (observed == stable_) {
      candidate_ = observed;
      count_ = 0;
    } else {
      count_ = (candidate_ == observed) ? count_ + 1 : 1;
      candidate_ = observed;
      if (count_ >= required_) { stable_ = observed; count_ = 0; }
    }
    return stable_;
  }
 private:
  unsigned int required_;
  unsigned int count_{0};
  Status stable_{Status::STALE};
  Status candidate_{Status::STALE};
};
}  // namespace rhm
