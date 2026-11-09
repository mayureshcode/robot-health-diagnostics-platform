#include <gtest/gtest.h>
#include "rhm_aggregator/logic.hpp"
TEST(Health, Score) {
  EXPECT_DOUBLE_EQ(rhm::score({rhm::Status::OK, rhm::Status::ERROR}), 60.0);
  EXPECT_DOUBLE_EQ(rhm::score({}), 0.0);
}
TEST(Health, Debounce) {
  rhm::Debouncer d(2);
  EXPECT_EQ(d.update(rhm::Status::OK), rhm::Status::STALE);
  EXPECT_EQ(d.update(rhm::Status::OK), rhm::Status::OK);
  EXPECT_EQ(d.update(rhm::Status::STALE), rhm::Status::STALE);
}
