// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <functional>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>

namespace repository_indexes {
namespace fs = std::filesystem;
using Loader = std::function<std::optional<fs::path>(const std::string&)>;
using Hasher = std::function<std::string(const std::string&, const fs::path&)>;
inline constexpr const char* manifest_path = "catalogue/apt-index-history.tsv";
inline constexpr std::int64_t retention_seconds = 24 * 60 * 60;
inline constexpr std::uintmax_t maximum_index_size = 16 * 1024 * 1024;
using Key = std::tuple<std::string, std::string, std::string>;

inline bool valid_hash(const std::string& algorithm, const std::string& value) {
    const auto length = algorithm == "SHA256" ? 64U : algorithm == "SHA512" ? 128U : 0U;
    return length && value.size() == length &&
        value.find_first_not_of("0123456789abcdef") == std::string::npos;
}

inline std::string index_path(const Key& key) {
    return "dists/" + std::get<0>(key) + "/main/binary-amd64/by-hash/" +
        std::get<1>(key) + "/" + std::get<2>(key);
}

inline std::string bounded_text(const fs::path& path, std::uintmax_t maximum) {
    if (!fs::is_regular_file(path) || fs::file_size(path) > maximum)
        throw std::runtime_error("invalid or oversized APT history metadata");
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("unable to read APT history metadata");
    return {std::istreambuf_iterator<char>(input), {}};
}

// The caller supplies a fresh generated tree. Only immutable index bytes are
// carried forward; eligible package selection and five-version retention stay
// with the publisher. Transport and hashing are replaceable mechanisms.
inline std::string retain(const fs::path& current, const Loader& load,
                          const Hasher& hash, std::int64_t now) {
    if (now < 0 || now > INT64_MAX - retention_seconds)
        throw std::runtime_error("invalid APT history clock");
    std::map<Key, std::int64_t> leases;
    std::map<Key, std::string> canonical_fallback;
    std::map<std::pair<std::string, std::string>, fs::path> known;
    const auto remember = [&](const fs::path& file) {
        if (!fs::is_regular_file(file) || fs::file_size(file) == 0 ||
            fs::file_size(file) > maximum_index_size)
            throw std::runtime_error("invalid or oversized APT index");
        for (const std::string algorithm : {"SHA256", "SHA512"}) {
            auto identity = hash(algorithm, file);
            if (!valid_hash(algorithm, identity))
                throw std::runtime_error("invalid APT index digest");
            known[{algorithm, identity}] = file;
        }
    };
    if (const auto previous = load(manifest_path)) {
        std::istringstream input(bounded_text(*previous, 1024 * 1024));
        std::string line;
        if (!std::getline(input, line) || line != "# apt-index-history-v1")
            throw std::runtime_error("unsupported APT index history format");
        std::size_t records = 0;
        std::set<Key> seen;
        while (std::getline(input, line)) {
            if (++records > 4096) throw std::runtime_error("APT index history exceeds its bound");
            std::istringstream fields(line);
            std::int64_t until;
            std::string suite, algorithm, identity, extra;
            if (!(fields >> until >> suite >> algorithm >> identity) || (fields >> extra) ||
                (suite != "alpha" && suite != "beta") ||
                !valid_hash(algorithm, identity) || until < 0 || until > now + retention_seconds)
                throw std::runtime_error("invalid APT index history record");
            const Key key{suite, algorithm, identity};
            if (!seen.insert(key).second)
                throw std::runtime_error("duplicate APT index history record");
            if (until > now) leases[key] = until;
        }
    }
    // Seed an existing deployment even when it predates the history manifest.
    for (const std::string suite : {"alpha", "beta"}) {
        const auto previous = load("dists/" + suite + "/Release");
        if (!previous) continue;
        std::istringstream input(bounded_text(*previous, 1024 * 1024));
        std::string line, algorithm;
        std::set<std::pair<std::string, std::string>> seen;
        while (std::getline(input, line)) {
            if (line == "SHA256:") { algorithm = "SHA256"; continue; }
            if (line == "SHA512:") { algorithm = "SHA512"; continue; }
            if (line.empty() || line.front() != ' ') { algorithm.clear(); continue; }
            if (algorithm.empty()) continue;
            std::istringstream fields(line);
            std::string identity, relative, extra;
            std::uintmax_t size;
            if (!(fields >> identity >> size >> relative) || (fields >> extra))
                throw std::runtime_error("malformed previous APT Release checksum");
            if (relative != "main/binary-amd64/Packages" &&
                relative != "main/binary-amd64/Packages.gz") continue;
            if (!valid_hash(algorithm, identity) || size == 0 || size > maximum_index_size ||
                !seen.insert({algorithm, relative}).second)
                throw std::runtime_error("invalid previous APT index identity");
            const Key key{suite, algorithm, identity};
            leases[key] = now + retention_seconds;
            canonical_fallback[key] = "dists/" + suite + "/" + relative;
        }
        if (!seen.count({"SHA256", "main/binary-amd64/Packages"}) ||
            !seen.count({"SHA256", "main/binary-amd64/Packages.gz"}))
            throw std::runtime_error("previous APT Release is missing its SHA256 indexes");
    }
    for (const std::string suite : {"alpha", "beta"}) {
        for (const std::string file : {"Packages", "Packages.gz"}) {
            const auto path = current / "dists" / suite / "main/binary-amd64" / file;
            remember(path);
            for (const std::string algorithm : {"SHA256", "SHA512"})
                leases[{suite, algorithm, hash(algorithm, path)}] = now + retention_seconds;
        }
    }
    if (leases.size() > 4096)
        throw std::runtime_error("APT index history exceeds its bound");
    std::ostringstream result;
    result << "# apt-index-history-v1\n";
    for (const auto& entry : leases) {
        const auto& [suite, algorithm, identity] = entry.first;
        auto found = known.find({algorithm, identity});
        if (found == known.end()) {
            auto previous = load(index_path(entry.first));
            const auto fallback = canonical_fallback.find(entry.first);
            if (!previous && fallback != canonical_fallback.end())
                previous = load(fallback->second);
            if (!previous || !fs::is_regular_file(*previous) ||
                fs::file_size(*previous) > maximum_index_size ||
                hash(algorithm, *previous) != identity)
                throw std::runtime_error("retained APT index is missing or corrupt");
            remember(*previous);
            found = known.find({algorithm, identity});
        }
        const auto target = current / index_path(entry.first);
        fs::create_directories(target.parent_path());
        if (fs::exists(target)) {
            if (hash(algorithm, target) != identity)
                throw std::runtime_error("existing immutable APT index changed");
        } else {
            fs::copy_file(found->second, target);
        }
        result << entry.second << '\t' << suite << '\t' << algorithm << '\t' << identity << '\n';
    }
    return result.str();
}
}  // namespace repository_indexes
