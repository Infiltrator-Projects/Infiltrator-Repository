// SPDX-License-Identifier: GPL-3.0-or-later
// Exercise the production capture/scratch owner without adding a public CLI.
#define main repository_tool_main
#include "../scripts/repository-tool.cpp"
#undef main
#include <atomic>
#include <thread>

int main() {
  std::atomic<bool> passed{true};
  std::vector<std::thread> workers;
  for (int worker = 0; worker < 8; ++worker) {
    workers.emplace_back([worker, &passed] {
      try {
        const auto expected = "worker-" + std::to_string(worker);
        for (int attempt = 0; attempt < 20; ++attempt) {
          if (command_output("sleep 0.01; printf " + quote(expected)) != expected)
            passed = false;
        }
      } catch (...) { passed = false; }
    });
  }
  for (auto& worker : workers) worker.join();
  fs::path scratch;
  try {
    PrivateDirectory temporary("repository-unwind-test");
    scratch = temporary.path();
    const auto permissions = fs::status(scratch).permissions();
    if ((permissions & (fs::perms::group_all | fs::perms::others_all)) != fs::perms::none)
      passed = false;
    std::ofstream(scratch / "secret") << "fixture";
    throw std::runtime_error("fixture");
  } catch (const std::runtime_error&) {}
  if (scratch.empty() || fs::exists(scratch)) passed = false;
  try {
    (void)command_output("exit 7");
    passed = false;
  } catch (const std::runtime_error&) {}
  if (!passed) {
    std::cerr << "Concurrent command capture or private scratch lifetime failed\n";
    return 1;
  }
  std::cout << "Concurrent capture and private scratch contracts passed\n";
  return 0;
}
