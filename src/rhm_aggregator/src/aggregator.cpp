#include <cmath>
#include <algorithm>
#include <chrono>
#include <map>
#include <mutex>
#include <string>
#include <vector>
#include "diagnostic_msgs/msg/diagnostic_array.hpp"
#include "rcl_interfaces/msg/parameter_descriptor.hpp"
#include "rcl_interfaces/msg/integer_range.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_lifecycle/lifecycle_node.hpp"
#include "rhm_interfaces/msg/health_status.hpp"
#include "rhm_interfaces/msg/subsystem_health.hpp"
#include "rhm_interfaces/msg/fault_event.hpp"
#include "rhm_interfaces/srv/get_report.hpp"
#include "rhm_interfaces/srv/reset_faults.hpp"
#include "rhm_aggregator/logic.hpp"

class Aggregator final : public rclcpp_lifecycle::LifecycleNode {
 public:
  Aggregator() : LifecycleNode("rhm_aggregator") {
    rcl_interfaces::msg::ParameterDescriptor descriptor;
    descriptor.description = "Consecutive diagnostic samples required to change status (startup only)";
    descriptor.read_only = true;
    rcl_interfaces::msg::IntegerRange range;
    range.from_value = 1;
    range.to_value = 100;
    range.step = 1;
    descriptor.integer_range.push_back(range);
    declare_parameter<int>("debounce_samples", 3, descriptor);
    rcl_interfaces::msg::ParameterDescriptor timeout_descriptor;
    timeout_descriptor.description = "Time in seconds until a missing diagnostic is stale (startup only)";
    timeout_descriptor.read_only = true;
    declare_parameter<double>("stale_timeout", 2.0, timeout_descriptor);
    parameter_callback_ = add_on_set_parameters_callback(
      [this](const std::vector<rclcpp::Parameter> &params) {
        rcl_interfaces::msg::SetParametersResult result;
        result.successful = true;
        for (const auto &p : params) {
          if (p.get_name() == "debounce_samples" && (p.as_int() < 1 || p.as_int() > 100)) {
            result.successful = false;
            result.reason = "debounce_samples must be 1..100";
          }
          if (p.get_name() == "stale_timeout" && (!std::isfinite(p.as_double()) || p.as_double() <= 0.0)) {
            result.successful = false;
            result.reason = "stale_timeout must be finite and > 0";
          }
        }
        return result;
      });
  }
 private:
  struct Sample {
    rhm::Status raw{rhm::Status::STALE};
    rclcpp::Time stamp{0, 0, RCL_ROS_TIME};
    rhm::Debouncer debounce;
    explicit Sample(unsigned int count) : debounce(count) {}
  };
  std::mutex mutex_;
  std::map<std::string, Sample> samples_;
  rclcpp::Subscription<diagnostic_msgs::msg::DiagnosticArray>::SharedPtr subscription_;
  rclcpp_lifecycle::LifecyclePublisher<rhm_interfaces::msg::HealthStatus>::SharedPtr publisher_;
  rclcpp_lifecycle::LifecyclePublisher<rhm_interfaces::msg::FaultEvent>::SharedPtr faults_publisher_;
  rclcpp::Service<rhm_interfaces::srv::GetReport>::SharedPtr report_service_;
  rclcpp::Service<rhm_interfaces::srv::ResetFaults>::SharedPtr reset_service_;
  rclcpp::TimerBase::SharedPtr timer_;
  OnSetParametersCallbackHandle::SharedPtr parameter_callback_;
  int debounce_samples_{3};
  double stale_timeout_{2.0};
  rhm_interfaces::msg::HealthStatus last_report_;

  CallbackReturn on_configure(const rclcpp_lifecycle::State &) override {
    try {
      debounce_samples_ = get_parameter("debounce_samples").as_int();
      stale_timeout_ = get_parameter("stale_timeout").as_double();
      if (debounce_samples_ < 1 || !std::isfinite(stale_timeout_) || stale_timeout_ <= 0.0) {
        RCLCPP_ERROR(get_logger(), "invalid aggregator startup parameters");
        return CallbackReturn::FAILURE;
      }
      auto qos = rclcpp::QoS(rclcpp::KeepLast(10)).reliable().durability_volatile();
      publisher_ = create_publisher<rhm_interfaces::msg::HealthStatus>("/robot_health", qos);
      faults_publisher_ = create_publisher<rhm_interfaces::msg::FaultEvent>("/fault_events", qos);
      subscription_ = create_subscription<diagnostic_msgs::msg::DiagnosticArray>(
        "/diagnostics", qos, [this](diagnostic_msgs::msg::DiagnosticArray::ConstSharedPtr msg) {
          try {
            std::lock_guard<std::mutex> guard(mutex_);
            for (const auto &entry : msg->status) {
              auto it = samples_.try_emplace(entry.name, static_cast<unsigned int>(debounce_samples_)).first;
              it->second.raw = static_cast<rhm::Status>(std::min<int>(entry.level, 3));
              it->second.stamp = now();
            }
          } catch (const std::exception &e) {
            RCLCPP_ERROR_THROTTLE(get_logger(), *get_clock(), 5000, "diagnostic error: %s", e.what());
          }
        });
      report_service_ = create_service<rhm_interfaces::srv::GetReport>(
        "/rhm/get_report", [this](const std::shared_ptr<rhm_interfaces::srv::GetReport::Request> req,
                                   std::shared_ptr<rhm_interfaces::srv::GetReport::Response> res) {
          std::lock_guard<std::mutex> guard(mutex_);
          if (!req->asset_id.empty() && req->asset_id != "mobile") {
            res->success = false;
            res->message = "unknown asset";
            return;
          }
          res->success = true;
          res->message = "snapshot";
          res->health = last_report_;
        });
      reset_service_ = create_service<rhm_interfaces::srv::ResetFaults>(
        "/rhm/reset_faults", [this](const std::shared_ptr<rhm_interfaces::srv::ResetFaults::Request> req,
                                     std::shared_ptr<rhm_interfaces::srv::ResetFaults::Response> res) {
          (void)req;
          res->success = false;
          res->message = "Reset unsupported until fault latching is implemented";
          res->cleared_count = 0;
        });
      return CallbackReturn::SUCCESS;
    } catch (const std::exception &e) {
      RCLCPP_ERROR(get_logger(), "configure failed: %s", e.what());
      return CallbackReturn::FAILURE;
    }
  }
  CallbackReturn on_activate(const rclcpp_lifecycle::State &) override {
    publisher_->on_activate();
    faults_publisher_->on_activate();
    timer_ = create_wall_timer(std::chrono::milliseconds(200), [this]() { publish_snapshot(); });
    return CallbackReturn::SUCCESS;
  }
  void publish_snapshot() {
    try {
      rhm_interfaces::msg::HealthStatus report;
      report.header.stamp = now();
      report.asset_id = "mobile";
      std::vector<rhm::Status> statuses;
      {
        std::lock_guard<std::mutex> guard(mutex_);
        for (auto &[name, sample] : samples_) {
          const bool stale = (now() - sample.stamp).seconds() > stale_timeout_;
          const auto status = sample.debounce.update(stale ? rhm::Status::STALE : sample.raw);
          rhm_interfaces::msg::SubsystemHealth subsystem;
          subsystem.asset_id = "mobile";
          subsystem.subsystem = name;
          subsystem.status = static_cast<uint8_t>(status);
          subsystem.score = rhm::score({status});
          subsystem.summary = stale ? "diagnostic timeout" : "diagnostic observed";
          subsystem.last_update = sample.stamp;
          report.subsystems.push_back(subsystem);
          statuses.push_back(status);
        }
        report.health_score = rhm::score(statuses);
        report.status = statuses.empty() ? 3 : static_cast<uint8_t>(*std::max_element(statuses.begin(), statuses.end()));
        last_report_ = report;
      }
      if (publisher_ && publisher_->is_activated()) publisher_->publish(report);
    } catch (const std::exception &e) {
      RCLCPP_ERROR_THROTTLE(get_logger(), *get_clock(), 5000, "aggregation error: %s", e.what());
    }
  }
  CallbackReturn on_deactivate(const rclcpp_lifecycle::State &) override {
    timer_.reset();
    publisher_->on_deactivate();
    faults_publisher_->on_deactivate();
    return CallbackReturn::SUCCESS;
  }
  CallbackReturn on_cleanup(const rclcpp_lifecycle::State &) override {
    timer_.reset(); subscription_.reset(); report_service_.reset(); reset_service_.reset();
    publisher_.reset(); faults_publisher_.reset();
    std::lock_guard<std::mutex> guard(mutex_);
    samples_.clear();
    return CallbackReturn::SUCCESS;
  }
};
int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<Aggregator>();
  rclcpp::spin(node->get_node_base_interface());
  rclcpp::shutdown();
  return 0;
}
