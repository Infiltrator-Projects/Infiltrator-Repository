// SPDX-License-Identifier: GPL-3.0-or-later
// Exercise the production index owner with disposable publication generations.
#define main repository_tool_main
#include "../scripts/repository-tool.cpp"
#undef main

static void require(bool value, const char* message) {
  if (!value) throw std::runtime_error(message);
}

static void put(const fs::path& path, const std::string& value) {
  fs::create_directories(path.parent_path());
  write(path, value);
}

static void indexes(const fs::path& root, const std::string& value) {
  for (const std::string suite : {"alpha", "beta"}) {
    const auto directory = root / "dists" / suite / "main/binary-amd64";
    put(directory / "Packages", value);
    put(directory / "Packages.gz", std::string("\x1f\x8b\0", 3) + value);
  }
}

static void release_metadata(const fs::path& root) {
  for (const std::string suite : {"alpha", "beta"}) {
    std::ostringstream release;
    release << "Codename: " << suite << "\nAcquire-By-Hash: yes\n";
    for (const std::string algorithm : {"SHA256", "SHA512"}) {
      release << algorithm << ":\n";
      for (const std::string name : {"Packages", "Packages.gz"}) {
        const auto file = root / "dists" / suite / "main/binary-amd64" / name;
        release << ' ' << index_digest(algorithm, file) << ' ' << fs::file_size(file)
                << " main/binary-amd64/" << name << '\n';
      }
    }
    put(root / "dists" / suite / "Release", release.str());
  }
}

int main() {
  try {
    PrivateDirectory previous("apt-history-previous");
    PrivateDirectory current("apt-history-current");
    PrivateDirectory next("apt-history-next");
    PrivateDirectory failed("apt-history-failed");
    const std::int64_t now = 100000;
    indexes(previous.path(), "previous package index");
    release_metadata(previous.path());
    indexes(current.path(), "current package index");
    release_metadata(current.path());
    indexes(next.path(), "next package index");
    indexes(failed.path(), "failed candidate index");
    const auto canonical = current.path() / "dists/beta/main/binary-amd64/Packages";
    const auto current_bytes = read(canonical);

    // The legacy server only provides SHA256 by-hash. SHA512 must be repaired
    // from exactly those verified bytes rather than trusting a mutable name.
    for (const std::string suite : {"alpha", "beta"}) {
      for (const std::string name : {"Packages", "Packages.gz"}) {
        const auto file = previous.path() / "dists" / suite / "main/binary-amd64" / name;
        const auto target = previous.path() /
            repository_indexes::index_path({suite, "SHA256", index_digest("SHA256", file)});
        put(target, read(file));
      }
    }
    const auto ancient = previous.path() / "ancient";
    const auto expired = previous.path() / "expired";
    put(ancient, "older retained index");
    put(expired, "expired and unavailable index");
    const auto ancient_hash = index_digest("SHA256", ancient);
    const auto expired_hash = index_digest("SHA256", expired);
    std::ostringstream history;
    history << "# apt-index-history-v1\n";
    for (const std::string suite : {"alpha", "beta"}) {
      put(previous.path() / repository_indexes::index_path({suite, "SHA256", ancient_hash}),
          read(ancient));
      for (const std::string algorithm : {"SHA256", "SHA512"}) {
        history << now + 120 << '\t' << suite << '\t' << algorithm << '\t'
                << index_digest(algorithm, ancient) << '\n';
        history << now - 1 << '\t' << suite << '\t' << algorithm << '\t'
                << index_digest(algorithm, expired) << '\n';
      }
    }
    put(previous.path() / repository_indexes::manifest_path, history.str());
    std::vector<std::string> requests;
    const repository_indexes::Loader load = [&](const std::string& relative)
        -> std::optional<fs::path> {
      requests.push_back(relative);
      const auto source = previous.path() / relative;
      if (!fs::exists(source)) return std::nullopt;
      return source;
    };
    const auto manifest = repository_indexes::retain(current.path(), load, index_digest, now);
    put(current.path() / repository_indexes::manifest_path, manifest);
    require(read(canonical) == current_bytes, "canonical current index changed");
    for (const auto& requested : requests)
      require(requested.find(expired_hash) == std::string::npos, "expired index was downloaded");
    for (const std::string suite : {"alpha", "beta"}) {
      for (const std::string algorithm : {"SHA256", "SHA512"}) {
        for (const auto& source : {
                 previous.path() / "dists" / suite / "main/binary-amd64/Packages",
                 previous.path() / "dists" / suite / "main/binary-amd64/Packages.gz",
                 current.path() / "dists" / suite / "main/binary-amd64/Packages",
                 current.path() / "dists" / suite / "main/binary-amd64/Packages.gz",
                 ancient}) {
          const auto target = current.path() /
              repository_indexes::index_path({suite, algorithm, index_digest(algorithm, source)});
          require(fs::is_regular_file(target) && read(target) == read(source),
                  "current or previous by-hash bytes are missing");
        }
      }
    }
    // A later clean generation retains the previous current snapshot even after
    // a long gap, while expired older history is not carried forward.
    const repository_indexes::Loader from_current = [&](const std::string& relative)
        -> std::optional<fs::path> {
      const auto source = current.path() / relative;
      return fs::exists(source) ? std::optional<fs::path>(source) : std::nullopt;
    };
    const auto next_manifest = repository_indexes::retain(
        next.path(), from_current, index_digest, now + repository_indexes::retention_seconds + 1);
    require(next_manifest.find(ancient_hash) == std::string::npos, "expired history survived");
    const auto previous_current_hash = index_digest("SHA512", canonical);
    require(fs::exists(next.path() /
            repository_indexes::index_path({"beta", "SHA512", previous_current_hash})),
            "previous canonical index was lost after a long publication gap");

    const auto must_fail = [&](const repository_indexes::Loader& loader) {
      bool rejected = false;
      try { (void)repository_indexes::retain(failed.path(), loader, index_digest, now); }
      catch (const std::runtime_error&) { rejected = true; }
      require(rejected, "invalid previous state was accepted");
      require(!fs::exists(failed.path() / repository_indexes::manifest_path),
              "failed candidate acquired a complete history manifest");
    };
    const auto corrupt = previous.path() / "corrupt";
    put(corrupt, "wrong bytes");
    must_fail([&](const std::string& relative) -> std::optional<fs::path> {
      if (relative.find(ancient_hash) != std::string::npos) return corrupt;
      return load(relative);
    });
    must_fail([&](const std::string& relative) -> std::optional<fs::path> {
      if (relative.find(ancient_hash) != std::string::npos) return std::nullopt;
      return load(relative);
    });
    const auto invalid = previous.path() / "invalid-history";
    put(invalid, "# apt-index-history-v1\n100001\t../escape\tSHA256\t" + ancient_hash + "\n");
    must_fail([&](const std::string& relative) -> std::optional<fs::path> {
      return relative == repository_indexes::manifest_path ? std::optional<fs::path>(invalid) : load(relative);
    });
    // First publication and migration from a deployment without a manifest.
    const repository_indexes::Loader absent = [](const std::string&) -> std::optional<fs::path> {
      return std::nullopt;
    };
    require(!repository_indexes::retain(failed.path(), absent, index_digest, now).empty(),
            "first publication failed");
    const repository_indexes::Loader legacy = [&](const std::string& relative)
        -> std::optional<fs::path> {
      return relative == repository_indexes::manifest_path ? std::nullopt : load(relative);
    };
    require(!repository_indexes::retain(failed.path(), legacy, index_digest, now).empty(),
            "legacy metadata migration failed");
    std::cout << "APT index transitions, SHA512, expiry and corruption contracts passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "APT index history fixture: " << error.what() << '\n';
    return 1;
  }
}
