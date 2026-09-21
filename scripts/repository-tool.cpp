// Portable C++17 entry point for repository release automation.
//
// The tool deliberately uses the distribution's curl, jq, dpkg-deb and
// sha256sum helpers rather than embedding an HTTP, Debian or OpenPGP stack.
// This keeps the executable small and makes it usable on GitHub's Ubuntu
// runners as well as ordinary Debian-based development systems.
#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <infiltratr/core.h>
#include <infiltratr/escape.h>
#include <infiltratr/posix.h>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <cctype>
#include <regex>
#include <iomanip>
#include <stdexcept>
#include <utility>

namespace fs = std::filesystem;

static std::string quote(const std::string& value) {
  std::string result = "'";
  for (char c : value) result += (c == '\'') ? "'\\''" : std::string(1, c);
  return result + "'";
}

static std::string github_headers() {
  std::string headers =
      "-H 'Accept: application/vnd.github+json' "
      "-H 'User-Agent: Infiltrator-Repository' "
      "-H 'X-GitHub-Api-Version: 2022-11-28'";
  if (const char* token = std::getenv("GITHUB_TOKEN"); token && *token)
    headers += " -H \"Authorization: Bearer $GITHUB_TOKEN\"";
  return headers;
}

static int run(const std::string& command) {
  std::cout << "+ " << command << '\n';
  return std::system(command.c_str());
}

static std::string read(const fs::path& path) {
  std::ifstream input(path, std::ios::binary);
  if (!input) throw std::runtime_error("unable to read " + path.string());
  return {std::istreambuf_iterator<char>(input), {}};
}

static std::string command_output(const std::string& command) {
  fs::path output = fs::current_path() / ".repository-tool-output";
  if (run(command + " > " + quote(output.string()))) throw std::runtime_error("command failed");
  auto value = read(output);
  fs::remove(output);
  return value;
}

static std::string trim_eol(const std::string& value) {
  std::vector<char> buffer(value.begin(), value.end());
  buffer.push_back('\0');
  infiltratr_trim_line_end(buffer.data());
  return std::string(buffer.data());
}

static std::string common_escape(
    const std::string& value,
    bool (*encoder)(const char*, char*, size_t, size_t*)) {
  size_t required = 0;
  if (!encoder(value.c_str(), nullptr, 0, &required) || required == 0)
    throw std::runtime_error("COMMON output escaping measurement failed");
  std::vector<char> buffer(required);
  if (!encoder(value.c_str(), buffer.data(), buffer.size(), nullptr))
    throw std::runtime_error("COMMON output escaping failed");
  return std::string(buffer.data());
}

static std::string url_encode_component(const std::string& value) {
  return common_escape(value, infiltratr_escape_uri_component);
}

static void write(const fs::path& path, const std::string& value) {
  const int error = infiltratr_atomic_file_write_bytes(
      path.c_str(), INFILTRATR_ATOMIC_FILE_PRESERVE_PERMISSIONS,
      value.data(), value.size());
  if (error != 0)
    throw std::runtime_error("COMMON atomic write failed for " + path.string() +
                             ": " + std::strerror(error));
}

static std::string digest(const fs::path& file) {
  fs::path output = file;
  output += ".sha256.tmp";
  if (run("sha256sum " + quote(file.string()) + " > " + quote(output.string())))
    throw std::runtime_error("sha256sum failed for " + file.string());
  std::istringstream line(read(output));
  std::string value;
  line >> value;
  fs::remove(output);
  return value;
}

static void check_deb(const fs::path& file, const std::string& version,
                      const std::string& expected_package = "intune-zabbix-bridge",
                      const std::string& expected_architecture = "all") {
  for (const auto& field : {"Package", "Version", "Architecture"}) {
    fs::path out = file;
    out += "." + std::string(field) + ".tmp";
    if (run("dpkg-deb --field " + quote(file.string()) + " " + field +
            " > " + quote(out.string())))
      throw std::runtime_error("dpkg-deb failed for " + file.string());
    const auto value = read(out);
    fs::remove(out);
    const std::string field_name(field);
    const std::string expected = field_name == "Package" ? expected_package :
      field_name == "Version" ? version : expected_architecture;
    if (value != expected + "\n" && value != expected + "\r\n")
      throw std::runtime_error("unexpected DEB " + std::string(field) + " in " + file.string());
  }
}

static std::string json_escape(const std::string& value) {
    return common_escape(value, infiltratr_escape_json);
  }

  static std::string tsv_unescape(const std::string& value) {
    std::string result;
    result.reserve(value.size());
    for (size_t i = 0; i < value.size(); ++i) {
      if (value[i] != '\\' || i + 1 >= value.size()) {
        result += value[i];
        continue;
      }
      switch (value[++i]) {
        case 't': result += '\t'; break;
        case 'n': result += '\n'; break;
        case 'r': result += '\r'; break;
        case '\\': result += '\\'; break;
        default: result += value[i]; break;
      }
    }
    return result;
  }

  static std::string deb_field(const fs::path& file, const std::string& field, bool optional = false) {
    fs::path out = file; out += "." + field + ".tmp";
    const int status = run("dpkg-deb --field " + quote(file.string()) + " " + field + " > " + quote(out.string()));
    if (status) {
      fs::remove(out);
      if (optional) return {};
      throw std::runtime_error("unable to read DEB field " + field);
    }
    auto value = read(out); fs::remove(out);
    return trim_eol(value);
  }

static void check_deb_expected(const fs::path& file,
                               const std::string& expected_version,
                               const std::string& expected_package_regex,
                               const std::string& expected_architecture) {
  const auto package = deb_field(file, "Package");
  try {
    if (!std::regex_match(package, std::regex(expected_package_regex)))
      throw std::runtime_error("unexpected DEB Package in " + file.string() + ": " + package);
  } catch (const std::regex_error&) {
    throw std::runtime_error("invalid expected package regex: " + expected_package_regex);
  }
  check_deb(file, expected_version, package, expected_architecture);
}

static std::string release_version(const std::string& tag) {
  if (tag.size() < 2 || tag.front() != 'v' ||
      tag.find_first_of("/\\\r\n") != std::string::npos)
    throw std::runtime_error("release tag is not a canonical v<version> identity: " + tag);
  return tag.substr(1);
}

static std::string package_version_from_identity(const std::string& release_tag,
                                                 const std::string& asset,
                                                 const std::string& version_regex) {
  if (version_regex.empty()) return release_version(release_tag);
  try {
    const std::regex rx(version_regex);
    std::smatch match;
    if (!std::regex_match(asset, match, rx) || match.size() != 2 ||
        match[1].str().empty())
      throw std::runtime_error("asset filename does not provide exactly one package version: " + asset);
    const auto version = match[1].str();
    if (version.find_first_of("/\\\r\n") != std::string::npos)
      throw std::runtime_error("asset-derived package version is unsafe: " + version);
    return version;
  } catch (const std::regex_error&) {
    throw std::runtime_error("invalid asset package-version regex: " + version_regex);
  }
}

static bool newer(const std::string& left, const std::string& right) {
    const int status = run("dpkg --compare-versions " + quote(left) + " gt " + quote(right));
    return status == 0;
  }

struct Package {
    fs::path path;
    std::string version;
    std::string release_tag, release_url, published;
    std::string asset, sha;
  };

static std::vector<Package> local_packages(const fs::path& root, const std::string& glob) {
    const auto slash = glob.find_last_of('/');
    const fs::path directory = root / (slash == std::string::npos ? "." : glob.substr(0, slash));
    const std::string pattern = slash == std::string::npos ? glob : glob.substr(slash + 1);
    std::string expression = "^";
    for (char c : pattern) {
      if (c == '*') expression += ".*";
      else if (c == '.') expression += "\\.";
      else if (std::isalnum(static_cast<unsigned char>(c)) || c == '_' || c == '-') expression += c;
      else expression += "\\" + std::string(1, c);
    }
    expression += "$";
    std::regex rx(expression);
    std::vector<Package> result;
    if (!fs::exists(directory)) return result;
    for (const auto& entry : fs::directory_iterator(directory))
      if (fs::is_regular_file(entry) && std::regex_match(entry.path().filename().string(), rx))
        result.push_back({entry.path(), deb_field(entry.path(), "Version"), "", "", "", entry.path().filename().string(), ""});
    std::sort(result.begin(), result.end(), [](const Package& a, const Package& b) { return newer(a.version, b.version); });
    // Retention must happen before publication: dpkg-scanpackages indexes every
    // DEB copied into the pool, not merely the five versions listed in JSON.
    if (result.size() > 5) result.resize(5);
    return result;
  }

static std::string metadata_json(const Package& package, const std::string& id,
                                   const std::string& name, const std::string& repo,
                                   const std::string& owner, const std::string& category,
                                   const std::string& description) {
    const auto field = [&](const std::string& key, bool optional = false) {
      return deb_field(package.path, key, optional);
    };
    std::ostringstream out;
    out << "{\"id\":\"" << json_escape(id) << "\",\"name\":\"" << json_escape(name)
        << "\",\"repo\":\"" << json_escape(repo) << "\",\"category\":\"" << json_escape(category)
        << "\",\"description\":\"" << json_escape(description) << "\",\"package\":\"" << json_escape(field("Package"))
        << "\",\"version\":\"" << json_escape(package.version) << "\",\"architecture\":\"" << json_escape(field("Architecture"))
        << "\",\"depends\":\"" << json_escape(field("Depends", true)) << "\",\"homepage\":\"" << json_escape(field("Homepage", true))
        << "\",\"section\":\"" << json_escape(field("Section", true)) << "\",\"maintainer\":\"" << json_escape(field("Maintainer", true))
        << "\",\"package_description\":\"" << json_escape(field("Description", true).substr(0, field("Description", true).find('\n')))
        << "\",\"installed_size_kib\":\"" << json_escape(field("Installed-Size", true)) << "\",\"asset\":\"" << json_escape(package.asset)
        << "\",\"download_size\":" << fs::file_size(package.path) << ",\"sha256\":\"" << package.sha
        << "\",\"release_tag\":\"" << json_escape(package.release_tag.empty() ? "v" + package.version : package.release_tag)
        << "\",\"release_url\":\"" << json_escape(package.release_url.empty() ? "https://github.com/" + owner + "/" + repo + "/releases/tag/v" + package.version : package.release_url)
        << "\",\"published_at\":\"" << json_escape(package.published) << "\"}";
    return out.str();
}

static std::string base64(const std::string& input) {
  static constexpr char table[] =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  std::string output;
  int val = 0, bits = -6;
  for (unsigned char c : input) {
    val = (val << 8) + c; bits += 8;
    while (bits >= 0) { output += table[(val >> bits) & 0x3f]; bits -= 6; }
  }
  if (bits > -6) output += table[((val << 8) >> (bits + 8)) & 0x3f];
  while (output.size() % 4) output += '=';
  return output;
}

static void fetch_public_intune_export(const fs::path& root) {
  const std::string package = "intune-zabbix-bridge";
  const std::string manifest_url =
      "https://infiltrator-projects.github.io/Intune-Zabbix-Bridge/manifest.json";
  const fs::path manifest = root / ".intune-public-manifest.json";
  if (run("curl -fsSL --retry 2 --max-time 30 " + quote(manifest_url) +
          " -o " + quote(manifest.string()))) {
    fs::remove(manifest);
    std::cout << "Intune public export unavailable; retaining verified local history\n";
    return;
  }

  const fs::path values = root / ".intune-public-values";
  const std::string jq =
      "jq -er '[.package,.version,.filename,.sha256] | @tsv' " +
      quote(manifest.string()) + " > " + quote(values.string());
  if (run(jq)) {
    fs::remove(manifest);
    fs::remove(values);
    throw std::runtime_error("Intune public export manifest is malformed");
  }

  std::istringstream line(read(values));
  std::vector<std::string> v(4);
  for (auto& value : v) std::getline(line, value, '\t');
  for (auto& value : v) value = tsv_unescape(value);
  fs::remove(manifest);
  fs::remove(values);

  const auto& manifest_package = v[0];
  const auto& version = v[1];
  const auto& filename = v[2];
  auto expected = v[3];
  std::transform(expected.begin(), expected.end(), expected.begin(),
                 [](unsigned char c) { return static_cast<char>(std::tolower(c)); });

  if (manifest_package != package || version.empty() ||
      version.find_first_of("/\\\r\n") != std::string::npos ||
      filename != package + "_" + version + "_all.deb" ||
      expected.size() != 64 ||
      !std::all_of(expected.begin(), expected.end(),
                   [](unsigned char c) { return std::isxdigit(c) != 0; }))
    throw std::runtime_error("Intune public export manifest failed validation");

  const fs::path mirror = root / "mirrored-packages";
  fs::create_directories(mirror);
  const fs::path target = mirror / filename;
  const fs::path temporary = mirror / ("." + filename + ".download");
  const std::string download_url =
      "https://infiltrator-projects.github.io/Intune-Zabbix-Bridge/" +
      url_encode_component(filename);

  if (run("curl -fsSL --retry 2 --max-time 90 " + quote(download_url) +
          " -o " + quote(temporary.string()))) {
    fs::remove(temporary);
    std::cout << "Intune public package unavailable; retaining verified local history\n";
    return;
  }

  if (digest(temporary) != expected) {
    fs::remove(temporary);
    throw std::runtime_error("Intune public export SHA-256 mismatch");
  }
  check_deb(temporary, version);

  if (fs::exists(target)) {
    if (digest(target) != expected) {
      fs::remove(temporary);
      throw std::runtime_error("refusing to replace immutable Intune mirror with different content");
    }
    fs::remove(temporary);
  } else {
    fs::rename(temporary, target);
  }
  std::cout << "Verified public Intune mirror " << filename << '\n';
}

static int materialize(const fs::path& root) {
  const fs::path mirror = root / "mirrored-packages";
  fs::create_directories(mirror);
  const std::string package = "intune-zabbix-bridge";
  const std::string seed_version = "0.7.5";
  const std::string seed_hash = "dfde41c90846e6c30daf605bc9def9ffba104d77dfe6707778db22e26ca8611b";
  for (const auto& entry : fs::directory_iterator(mirror)) {
    const auto name = entry.path().filename().string();
    if (name.rfind(package + "_", 0) != 0 ||
        name.find(".deb.b64.part-") == std::string::npos) continue;
    const auto marker = std::string("_all.deb.b64.part-00");
    if (name.size() <= marker.size() ||
        name.substr(name.size() - marker.size()) != marker) continue;
    const auto version = name.substr(package.size() + 1, name.size() - package.size() - marker.size() - 1);
    const auto base = package + "_" + version + "_all.deb";
    std::string encoded;
    std::vector<fs::path> part_paths;
    for (const auto& part : fs::directory_iterator(mirror)) {
      const auto part_name = part.path().filename().string();
      if (part_name.rfind(base + ".b64.part-", 0) == 0) part_paths.push_back(part.path());
    }
    std::sort(part_paths.begin(), part_paths.end());
    for (const auto& part : part_paths) encoded += read(part);
    encoded.erase(std::remove(encoded.begin(), encoded.end(), '\n'), encoded.end());
    // base64 decoding is delegated to the ubiquitous coreutils helper.
    const auto target = mirror / base;
    const auto encoded_file = mirror / ("." + base + ".encoded");
    write(encoded_file, encoded);
    if (run("base64 --decode " + quote(encoded_file.string()) + " > " + quote(target.string())))
      throw std::runtime_error("invalid base64 for " + base);
    fs::remove(encoded_file);
    const auto sha_file = mirror / (base + ".sha256");
    if (!fs::exists(sha_file) || read(sha_file).substr(0, 64) != digest(target))
      throw std::runtime_error("SHA-256 mismatch for " + base);
    check_deb(target, version);
  }
  // The historical seed is also checked without relying on a checked-in binary.
  const auto seed = mirror / (package + "_" + seed_version + "_all.deb");
  std::string payload;
  std::vector<fs::path> seed_parts;
  for (const auto& entry : fs::directory_iterator(mirror))
    if (entry.path().filename().string().rfind(seed.filename().string() + ".part-", 0) == 0)
      seed_parts.push_back(entry.path());
  std::sort(seed_parts.begin(), seed_parts.end());
  for (const auto& part : seed_parts) payload += read(part);
  if (!payload.empty()) {
    write(seed, payload);
    if (digest(seed) != seed_hash) throw std::runtime_error("seed mirror SHA-256 mismatch");
    check_deb(seed, seed_version);
  }
  fetch_public_intune_export(root);
  return 0;
}

static int sync_intune(const fs::path& root) {
  const std::string package = "intune-zabbix-bridge";
  const fs::path mirror = root / "mirrored-packages";
  const fs::path json = root / ".intune-release.json";
  fs::create_directories(mirror);
  const std::string api = "https://api.github.com/repos/St-Augustines-College-Kyabram/Intune-Zabbix-Bridge/releases/latest";
  if (run("curl -fsSL --retry 5 " + github_headers() + " " + quote(api) +
          " -o " + quote(json.string()))) throw std::runtime_error("unable to read Intune release");
  const fs::path values = root / ".intune-values";
  const std::string jq = "jq -er 'select((.draft|not) and (.prerelease|not)) | .tag_name as $tag | [$tag, (.assets[] | select(.name == (\"intune-zabbix-bridge_\" + ($tag|ltrimstr(\"v\")) + \"_all.deb\")) | .browser_download_url), (.assets[] | select(.name == (\"intune-zabbix-bridge_\" + ($tag|ltrimstr(\"v\")) + \"_all.deb\")) | .digest)] | @tsv' " + quote(json.string()) + " > " + quote(values.string());
  if (run(jq)) throw std::runtime_error("jq failed while reading Intune release");
  std::istringstream line(read(values));
  std::string tag, url, digest_value; line >> tag >> url >> digest_value;
  fs::remove(json); fs::remove(values);
  if (tag.rfind("v", 0) != 0 || url.empty() || digest_value.rfind("sha256:", 0) != 0)
    throw std::runtime_error("latest Intune release has no valid DEB asset");
  const auto version = tag.substr(1);
  if (version.empty() || version.find_first_of("/\\\r\n") != std::string::npos ||
      version.find('\0') != std::string::npos ||
      url.rfind("https://github.com/St-Augustines-College-Kyabram/Intune-Zabbix-Bridge/releases/download/", 0) != 0)
    throw std::runtime_error("latest Intune release contains an unsafe tag or asset URL");
  const auto filename = package + "_" + version + "_all.deb";
  const auto tmp = mirror / ("." + filename);
  if (run("curl -fsSL --retry 5 " + quote(url) + " -o " + quote(tmp.string())))
    throw std::runtime_error("unable to download " + filename);
  const auto expected = digest_value.substr(7);
  if (expected.size() != 64 ||
      !std::all_of(expected.begin(), expected.end(), [](unsigned char c) { return std::isxdigit(c) != 0; }))
    throw std::runtime_error("latest Intune release contains an invalid SHA-256 digest");
  if (digest(tmp) != expected) throw std::runtime_error("GitHub digest mismatch for " + filename);
  check_deb(tmp, version);
  const auto encoded = base64(read(tmp));
  fs::remove(tmp);
  const auto prefix = filename + ".b64.part-";
  for (const auto& entry : fs::directory_iterator(mirror)) {
    const auto name = entry.path().filename().string();
    if (name.rfind(prefix, 0) == 0) fs::remove(entry.path());
  }
  for (size_t offset = 0, index = 0; offset < encoded.size(); offset += 8000, ++index) {
    const auto part = mirror / (filename + ".b64.part-" + (index < 10 ? "0" : "") + std::to_string(index));
    write(part, encoded.substr(offset, 8000) + "\n");
  }
  write(mirror / (filename + ".sha256"), expected + "\n");
  std::cout << "Prepared verified public Intune mirror " << filename << '\n';
  return 0;
}

  static std::vector<Package> remote_packages(const fs::path& root, const std::string& owner,
                                              const std::string& repo, const std::string& rx_text,
                                              const std::string& expected_package_regex,
                                              const std::string& expected_architecture,
                                              const std::string& version_regex) {
    const fs::path json = root / (".releases-" + repo + ".json");
    const auto api = "https://api.github.com/repos/" + owner + "/" + repo + "/releases?per_page=5";
    if (run("curl -fsSL --retry 5 " + github_headers() + " " + quote(api) +
            " -o " + quote(json.string())))
      throw std::runtime_error("unable to read releases for " + repo);
    const auto query = "jq -er --arg rx " + quote(rx_text) +
      " '[.[] | select((.draft|not) and (.prerelease|not))] | .[:5][] as $r | "
      "($r.assets // []) | map(select(.name|test($rx))) | if length==1 then .[0] as $a | "
      "[$r.tag_name,$r.html_url,($r.published_at // $r.created_at // \"\"),$a.name,"
      "$a.browser_download_url,($a.digest // \"\"),($a.size // 0)] | @tsv else empty end' " +
      quote(json.string());
    const auto latest_check = "jq -e --arg rx " + quote(rx_text) +
      " '([.[] | select((.draft|not) and (.prerelease|not))][0] // {}) as $r | "
      "((($r.assets // []) | map(select(.name|test($rx)))) | length) == 1' " +
      quote(json.string());
    if (run(latest_check))
      throw std::runtime_error(repo + ": latest eligible release does not contain exactly one matching DEB");
    std::istringstream lines(command_output(query));
    fs::remove(json);
    std::vector<Package> packages;
    std::string line;
    while (std::getline(lines, line)) {
      std::istringstream fields(line);
      Package p; std::string size;
      std::getline(fields, p.release_tag, '\t'); std::getline(fields, p.release_url, '\t');
      std::getline(fields, p.published, '\t'); std::getline(fields, p.asset, '\t');
      std::string url; std::getline(fields, url, '\t'); std::getline(fields, p.sha, '\t'); std::getline(fields, size, '\t');
      if (p.sha.rfind("sha256:", 0) != 0 || p.sha.size() != 71) throw std::runtime_error("release asset has no SHA-256 digest");
      p.sha = p.sha.substr(7);
      p.version = package_version_from_identity(p.release_tag, p.asset, version_regex);
      const auto existing = std::find_if(packages.begin(), packages.end(),
          [&](const Package& item) { return item.version == p.version; });
      if (existing != packages.end()) {
        if (existing->sha != p.sha || existing->asset != p.asset)
          throw std::runtime_error(repo + ": package version " + p.version +
                                   " is reused by different release content");
        continue;
      }
      p.path = root / "public" / "pool" / "main" / p.asset;
      const auto mirror_url =
          "https://infiltrator-projects.github.io/Infiltrator-Repository/pool/main/" +
          url_encode_component(p.asset);
      bool materialized = false;
      if (!run("curl -fsSL --retry 2 --max-time 30 " + quote(mirror_url) +
               " -o " + quote(p.path.string()))) {
        if (digest(p.path) == p.sha) {
          materialized = true;
          std::cout << "Reused published mirror for " << p.asset << '\n';
        } else {
          fs::remove(p.path);
          std::cout << "Published mirror digest mismatch for " << p.asset
                    << "; falling back to GitHub release asset\n";
        }
      } else {
        fs::remove(p.path);
      }
      if (!materialized) {
        if (run("curl -fsSL --retry 5 " + quote(url) + " -o " + quote(p.path.string())))
          throw std::runtime_error("unable to download " + p.asset);
        if (digest(p.path) != p.sha) {
          fs::remove(p.path);
          throw std::runtime_error("SHA-256 mismatch for " + p.asset);
        }
      }
      check_deb_expected(p.path, p.version, expected_package_regex, expected_architecture);
      packages.push_back(std::move(p));
    }
    if (packages.empty()) throw std::runtime_error(repo + ": no usable packages found");
    std::sort(packages.begin(), packages.end(), [](const Package& a, const Package& b) { return newer(a.version, b.version); });
    return packages;
  }

static void create_transition_package(const fs::path& root,
                                      const fs::path& public_dir,
                                      const std::string& old_package,
                                      const std::string& new_package,
                                      const std::string& version,
                                      const std::string& product_name) {
  const fs::path staging = root / "build" / (old_package + "-transition");
  fs::remove_all(staging);
  fs::create_directories(staging / "DEBIAN");

  std::ostringstream control;
  control << "Package: " << old_package << "\n"
          << "Version: " << version << "\n"
          << "Section: oldlibs\n"
          << "Priority: optional\n"
          << "Architecture: all\n"
          << "Depends: " << new_package << " (= " << version << ")\n"
          << "Maintainer: Shannon Smith <The-First-Infiltrator@users.noreply.github.com>\n"
          << "Description: transitional package for " << product_name << "\n"
          << " This empty package migrates installations from the previous package name.\n";
  write(staging / "DEBIAN" / "control", control.str());

  const fs::path target = public_dir / "pool" / "main" /
      (old_package + "_" + version + "_all.deb");
  fs::remove(target);
  const std::string command =
      "SOURCE_DATE_EPOCH=315532800 dpkg-deb -Zxz --build --root-owner-group " +
      quote(staging.string()) + " " + quote(target.string());
  if (run(command))
    throw std::runtime_error("unable to build " + product_name + " transition package");

  check_deb(target, version, old_package, "all");
  const std::string expected_depends = new_package + " (= " + version + ")";
  if (deb_field(target, "Depends") != expected_depends)
    throw std::runtime_error(product_name + " transition dependency is incorrect");
  fs::remove_all(staging);
}

static std::string publish_package_icon(const fs::path& root,
                                        const fs::path& public_dir,
                                        const std::string& id,
                                        const fs::path& package) {
  if (!std::regex_match(id, std::regex("^[A-Za-z0-9._-]+$")))
    throw std::runtime_error("unsafe catalogue id for icon publication: " + id);
  const fs::path staging = root / "build" / ("catalogue-icon-" + id);
  fs::remove_all(staging);
  fs::create_directories(staging);
  if (run("dpkg-deb -x " + quote(package.string()) + " " + quote(staging.string())))
    throw std::runtime_error("unable to extract icon from " + package.string());

  fs::path best;
  int best_kind = -1;
  std::uintmax_t best_size = 0;
  for (const auto& entry : fs::recursive_directory_iterator(
           staging, fs::directory_options::skip_permission_denied)) {
    if (!entry.is_regular_file()) continue;
    const auto path = entry.path();
    const auto generic = path.generic_string();
    const auto ext = path.extension().string();
    const bool icon_tree = generic.find("/usr/share/icons/") != std::string::npos &&
                           generic.find("/apps/") != std::string::npos;
    const bool pixmap = generic.find("/usr/share/pixmaps/") != std::string::npos;
    if (!icon_tree && !pixmap) continue;
    const int kind = ext == ".svg" ? 2 : ext == ".png" ? 1 : -1;
    if (kind < 0) continue;
    std::error_code ec;
    const auto size = fs::file_size(path, ec);
    const auto usable_size = ec ? std::uintmax_t{0} : size;
    if (kind > best_kind || (kind == best_kind && usable_size > best_size)) {
      best = path; best_kind = kind; best_size = usable_size;
    }
  }
  if (best.empty()) {
    fs::remove_all(staging);
    return {};
  }
  const auto icons = public_dir / "catalogue" / "icons";
  fs::create_directories(icons);
  const auto target = icons / (id + best.extension().string());
  fs::copy_file(best, target, fs::copy_options::overwrite_existing);
  fs::remove_all(staging);
  return "catalogue/icons/" + target.filename().string();
}


struct SoftwareManagerAlias {
  std::string package;
  fs::path icon;
};

static std::string software_manager_data_version(
    const std::string& newest_release_timestamp) {
  std::string digits;
  for (unsigned char character : newest_release_timestamp) {
    if (std::isdigit(character)) digits += static_cast<char>(character);
  }
  if (digits.size() > 14U) digits.resize(14U);
  if (digits.size() < 8U) return "2.0.0";
  return "2.0." + digits;
}

static void create_software_manager_data_package(
    const fs::path& root,
    const fs::path& public_dir,
    std::vector<SoftwareManagerAlias> aliases,
    const std::string& newest_release_timestamp) {
  if (aliases.empty()) {
    std::cout << "No application artwork in this publication; "
                 "skipping Linux Mint Software Manager data package\n";
    return;
  }

  std::sort(aliases.begin(), aliases.end(),
            [](const SoftwareManagerAlias& left,
               const SoftwareManagerAlias& right) {
              return left.package < right.package;
            });
  aliases.erase(
      std::unique(aliases.begin(), aliases.end(),
                  [](const SoftwareManagerAlias& left,
                     const SoftwareManagerAlias& right) {
                    return left.package == right.package;
                  }),
      aliases.end());

  const fs::path staging = root / "build" / "app-install-data-ssmithnet";
  fs::remove_all(staging);
  fs::create_directories(staging / "DEBIAN");
  fs::create_directories(staging / "usr/share/app-install/icons");

  std::size_t installed_icons = 0U;
  for (const auto& alias : aliases) {
    if (!std::regex_match(alias.package, std::regex("^[a-z0-9][a-z0-9+.-]*$")))
      throw std::runtime_error(
          "unsafe Debian package name for Software Manager icon: " +
          alias.package);
    if (!fs::is_regular_file(alias.icon)) continue;
    const std::string extension = alias.icon.extension().string();
    if (extension != ".svg" && extension != ".png" && extension != ".xpm")
      continue;
    const fs::path target =
        staging / "usr/share/app-install/icons" /
        (alias.package + extension);
    fs::copy_file(alias.icon, target, fs::copy_options::overwrite_existing);
    ++installed_icons;
  }
  if (installed_icons == 0U)
    throw std::runtime_error(
        "Linux Mint Software Manager data package contains no application icons");

  const std::string version =
      software_manager_data_version(newest_release_timestamp);
  std::ostringstream control;
  control << "Package: app-install-data-ssmithnet\n"
          << "Version: " << version << "\n"
          << "Section: misc\n"
          << "Priority: optional\n"
          << "Architecture: all\n"
          << "Conflicts: infiltrator-app-install-data\n"
          << "Replaces: infiltrator-app-install-data\n"
          << "Provides: infiltrator-app-install-data\n"
          << "Maintainer: Shannon Smith <The-First-Infiltrator@users.noreply.github.com>\n"
          << "Description: Linux Mint Software Manager data for Infiltrator applications\n"
          << " Package-name icon aliases for repository applications before they are\n"
          << " installed. Installing or upgrading this metadata also invalidates Mint's\n"
          << " system package cache so newly published applications are discoverable.\n";
  write(staging / "DEBIAN" / "control", control.str());

  const char postinst[] =
      "#!/bin/sh\n"
      "set -e\n"
      "rm -f /var/cache/mintinstall/pkginfo.json\n"
      "exit 0\n";
  const char postrm[] =
      "#!/bin/sh\n"
      "set -e\n"
      "rm -f /var/cache/mintinstall/pkginfo.json\n"
      "exit 0\n";
  write(staging / "DEBIAN" / "postinst", postinst);
  write(staging / "DEBIAN" / "postrm", postrm);
  fs::permissions(staging / "DEBIAN" / "postinst",
                  fs::perms::owner_exec | fs::perms::owner_read |
                      fs::perms::owner_write | fs::perms::group_exec |
                      fs::perms::group_read | fs::perms::others_exec |
                      fs::perms::others_read,
                  fs::perm_options::replace);
  fs::permissions(staging / "DEBIAN" / "postrm",
                  fs::perms::owner_exec | fs::perms::owner_read |
                      fs::perms::owner_write | fs::perms::group_exec |
                      fs::perms::group_read | fs::perms::others_exec |
                      fs::perms::others_read,
                  fs::perm_options::replace);

  const fs::path target = public_dir / "pool" / "main" /
      ("app-install-data-ssmithnet_" + version + "_all.deb");
  const std::string command =
      "SOURCE_DATE_EPOCH=315532800 dpkg-deb -Zxz --build --root-owner-group " +
      quote(staging.string()) + " " + quote(target.string());
  if (run(command))
    throw std::runtime_error(
        "unable to build Linux Mint Software Manager data package");
  check_deb(target, version, "app-install-data-ssmithnet", "all");
  std::cout << "Published " << installed_icons
            << " Linux Mint Software Manager package-name icon aliases\n";
  fs::remove_all(staging);
}

  static int publish(const fs::path& root) {
    const fs::path public_dir = root / "public";
    fs::remove_all(public_dir);
    fs::create_directories(public_dir / "pool" / "main");
    fs::create_directories(public_dir / "catalogue");
    fs::copy_file(root / "site" / "index.html", public_dir / "index.html");
    write(public_dir / ".nojekyll", "");

    const auto source = command_output("jq -r '.[] | [.id,.name,.repo,.category,.description,(.deb_regex // \"\"),(.local_deb_glob // \"\"),(.owner // \"Infiltrator-Projects\"),(.icon // \"\"),(.version_regex // \"\"),(.expected_package_regex // \"\"),(.expected_architecture // \"\"),(.optional_until_release // false)] | @tsv' " + quote((root / "catalogue/apps-source.json").string()));
    std::istringstream app_lines(source);
    std::vector<std::string> catalogue_items;
    std::vector<SoftwareManagerAlias> software_manager_aliases;
    std::string newest_release_timestamp;
    size_t package_version_count = 0;
    std::string line;
    while (std::getline(app_lines, line)) {
      std::istringstream f(line); std::vector<std::string> v(13);
      for (auto& value : v) std::getline(f, value, '\t');
      const auto& id=v[0]; const auto& name=v[1]; const auto& repo=v[2]; const auto& category=v[3];
      for (auto& value : v) value = tsv_unescape(value);
      const auto& description=v[4]; const auto& regex_text=v[5]; const auto& local_glob=v[6]; const auto& owner=v[7];
      const auto& version_regex=v[9]; const auto& expected_package_regex=v[10]; const auto& expected_architecture=v[11];
      const bool optional_until_release = v[12] == "true";
      if (expected_package_regex.empty() || expected_architecture.empty())
        throw std::runtime_error(name + ": expected package identity is not configured");
      std::vector<Package> packages;
      try {
        packages = local_glob.empty()
          ? remote_packages(root, owner, repo, regex_text, expected_package_regex, expected_architecture, version_regex)
          : local_packages(root, local_glob);
      } catch (const std::exception& error) {
        if (!optional_until_release) throw;
        std::cout << name << ": no eligible published package yet; catalogue entry remains pending ("
                  << error.what() << ")\n";
        continue;
      }
      if (!local_glob.empty())
        for (const auto& package : packages)
          check_deb_expected(package.path, package.version, expected_package_regex, expected_architecture);
      if (id == "calendar") {
        packages.erase(
            std::remove_if(packages.begin(), packages.end(),
                           [](const Package& package) {
                             if (deb_field(package.path, "Package") ==
                                 "infiltrator-calendar")
                               return false;
                             fs::remove(package.path);
                             return true;
                           }),
            packages.end());
      }
      if (packages.empty()) throw std::runtime_error(name + ": no mirrored DEBs");
      for (auto& package : packages) {
        const auto target = public_dir / "pool" / "main" / package.asset;
        if (package.path != target) fs::copy_file(package.path, target, fs::copy_options::overwrite_existing);
        package.path = target; package.sha = digest(target);
      }
      const std::string current_package =
          deb_field(packages.front().path, "Package");
      if (id == "system-monitor") {
        if (current_package == "system-monitor") {
          create_transition_package(root, public_dir,
                                    "linux-system-monitor", "system-monitor",
                                    packages.front().version, "System Monitor");
        } else if (current_package == "infiltrator-system-monitor") {
          create_transition_package(root, public_dir,
                                    "system-monitor", "infiltrator-system-monitor",
                                    packages.front().version, "System Monitor");
          create_transition_package(root, public_dir,
                                    "linux-system-monitor", "infiltrator-system-monitor",
                                    packages.front().version, "System Monitor");
        }
      }
      // Calculator intentionally has one public APT identity.  The renamed
      // package itself carries Breaks/Replaces/Provides for old installations;
      // do not emit an empty infiltrator-calc transition package because Mint
      // Software Manager exposes transition packages as duplicate applications.
      if (id == "defragger" &&
          current_package == "infiltrator-defragmenter")
        create_transition_package(root, public_dir,
                                  "linux-defragger", "infiltrator-defragmenter",
                                  packages.front().version, "Defragmenter");
      if (id == "runnerscope" &&
          current_package == "infiltrator-runner-monitor")
        create_transition_package(root, public_dir,
                                  "runnerscope", "infiltrator-runner-monitor",
                                  packages.front().version, "Runner Monitor");
      if (packages.size() > 5) packages.resize(5);
      package_version_count += packages.size();
      std::ostringstream history;
      for (size_t i=0; i<packages.size(); ++i) {
        if (i) history << ',';
        history << metadata_json(packages[i], id, name, repo, owner, category, description);
      }
      auto latest = metadata_json(packages.front(), id, name, repo, owner, category, description);
      latest.pop_back();
      const auto icon_url = publish_package_icon(root, public_dir, id, packages.front().path);
      if (!packages.front().published.empty() &&
          packages.front().published > newest_release_timestamp)
        newest_release_timestamp = packages.front().published;
      latest += ",\"icon\":\"" + json_escape(v[8]) + "\"";
      if (!icon_url.empty()) {
        latest += ",\"icon_url\":\"" + json_escape(icon_url) + "\"";
        latest += ",\"icon_sha256\":\"" +
                  digest(public_dir / fs::path(icon_url)) + "\"";
        software_manager_aliases.push_back(
            {current_package, public_dir / fs::path(icon_url)});
      }
      latest += ",\"source_url\":\"https://github.com/" + json_escape(owner) + "/" + json_escape(repo) + "\",\"history\":[" + history.str() + "]}";
      catalogue_items.push_back(std::move(latest));
    }

    create_software_manager_data_package(
        root, public_dir, software_manager_aliases, newest_release_timestamp);

    // Some products publish companion Debian packages that belong in APT but
    // should not appear as duplicate Software Centre application cards.  Each
    // supplemental package is independently release-discovered, digest-verified
    // and Debian-metadata-verified, then copied into the same multiversion pool.
    const auto supplemental_source = command_output(
      "jq -r '.[] as $app | ($app.supplemental_packages // [])[] | "
      "[$app.repo,($app.owner // \"Infiltrator-Projects\"),.deb_regex,"
      ".expected_package_regex,.expected_architecture,(.version_regex // \"\")] | @tsv' " +
      quote((root / "catalogue/apps-source.json").string()));
    std::istringstream supplemental_lines(supplemental_source);
    while (std::getline(supplemental_lines, line)) {
      std::istringstream f(line);
      std::vector<std::string> v(6);
      for (auto& value : v) std::getline(f, value, '\t');
      for (auto& value : v) value = tsv_unescape(value);
      const auto& repo_name = v[0];
      const auto& owner = v[1];
      const auto& regex_text = v[2];
      const auto& expected_package_regex = v[3];
      const auto& expected_architecture = v[4];
      const auto& version_regex = v[5];
      if (repo_name.empty() || regex_text.empty() || expected_package_regex.empty() ||
          expected_architecture.empty())
        throw std::runtime_error("supplemental package identity is incomplete");
      auto packages = remote_packages(root, owner, repo_name, regex_text,
                                      expected_package_regex, expected_architecture,
                                      version_regex);
      if (packages.size() > 5) packages.resize(5);
      for (auto& package : packages) {
        const auto target = public_dir / "pool" / "main" / package.asset;
        if (package.path != target)
          fs::copy_file(package.path, target, fs::copy_options::overwrite_existing);
        package.path = target;
        package.sha = digest(target);
      }
      package_version_count += packages.size();
    }

    std::ostringstream apps; apps << "[\n";
    for (size_t i=0; i<catalogue_items.size(); ++i) apps << (i ? ",\n" : "") << "  " << catalogue_items[i];
    apps << "\n]\n";
    write(public_dir / "catalogue" / "apps.json", apps.str());

    for (const std::string suite : {"beta"}) {
      const std::string suite_label = "Beta";
      const auto binary = public_dir / "dists" / suite / "main" / "binary-amd64";
      fs::create_directories(binary);
      const auto packages_text = command_output("cd " + quote(public_dir.string()) + " && dpkg-scanpackages --multiversion pool/main /dev/null");
      write(binary / "Packages", packages_text);
      if (run("gzip -9 -n -c " + quote((binary / "Packages").string()) + " > " + quote((binary / "Packages.gz").string())))
        throw std::runtime_error("gzip failed");
      const auto release = public_dir / "dists" / suite / "Release";
      const auto temp = public_dir / (".Release-" + suite + ".tmp");
      const auto command = "cd " + quote(public_dir.string()) + " && apt-ftparchive "
        "-o APT::FTPArchive::Release::Origin=Infiltrator "
        "-o APT::FTPArchive::Release::Label='Infiltrator " + suite_label + "' "
        "-o APT::FTPArchive::Release::Suite=" + suite + " -o APT::FTPArchive::Release::Codename=" + suite +
        " -o APT::FTPArchive::Release::Architectures=amd64 -o APT::FTPArchive::Release::Components=main "
        "-o APT::FTPArchive::Release::Description='Infiltrator Software Repository " + suite + "' release dists/" + suite;
      if (run(command + " > " + quote(temp.string()))) throw std::runtime_error("apt-ftparchive failed");
      auto release_text = read(temp); fs::remove(temp);
      const auto marker = "Codename: " + suite + "\n";
      const auto pos = release_text.find(marker);
      release_text.insert(pos == std::string::npos ? 0 : pos + marker.size(), "Acquire-By-Hash: yes\n");
      write(release, release_text);
      const auto by_hash = binary / "by-hash" / "SHA256"; fs::create_directories(by_hash);
      for (const auto& file : {binary / "Packages", binary / "Packages.gz"}) fs::copy_file(file, by_hash / digest(file), fs::copy_options::overwrite_existing);
    }
    bool signed_repo = false;
    const char* key = std::getenv("APT_SIGNING_KEY_B64");
    const char* fingerprint = std::getenv("APT_SIGNING_KEY_FINGERPRINT");
    if ((key && *key) || (fingerprint && *fingerprint)) {
      if (!key || !*key || !fingerprint || !*fingerprint) throw std::runtime_error("APT signing requires key and fingerprint");
      const fs::path ghome = root / ".repository-gnupg"; fs::remove_all(ghome); fs::create_directories(ghome);
      const fs::path keyfile = root / ".repository-signing-key.b64"; write(keyfile, key);
      if (run("base64 --decode " + quote(keyfile.string()) + " | GNUPGHOME=" + quote(ghome.string()) + " gpg --batch --import"))
        throw std::runtime_error("unable to import APT signing key");
      if (run("GNUPGHOME=" + quote(ghome.string()) + " gpg --batch --list-secret-keys " +
              quote(fingerprint) + " >/dev/null"))
        throw std::runtime_error("configured APT signing fingerprint was not found in imported secret key");
      const std::string pass = std::getenv("APT_SIGNING_PASSPHRASE") ? std::getenv("APT_SIGNING_PASSPHRASE") : "";
      const std::string common = "GNUPGHOME=" + quote(ghome.string()) + " gpg --batch --yes --pinentry-mode loopback " +
        (pass.empty() ? "" : "--passphrase \"$APT_SIGNING_PASSPHRASE\" ");
      for (const std::string suite : {"beta"}) {
        const auto dir = public_dir / "dists" / suite;
        if (run(common + "--local-user " + quote(fingerprint) + " --clearsign --output " + quote((dir / "InRelease").string()) + " " + quote((dir / "Release").string())) ||
            run(common + "--local-user " + quote(fingerprint) + " --detach-sign --output " + quote((dir / "Release.gpg").string()) + " " + quote((dir / "Release").string())))
          throw std::runtime_error("repository signing failed");
      }
      if (run("GNUPGHOME=" + quote(ghome.string()) + " gpg --batch --export " + quote(fingerprint) + " > " + quote((public_dir / "repository-key.gpg").string())))
        throw std::runtime_error("unable to export repository key");
      fs::remove_all(ghome); fs::remove(keyfile); signed_repo = true;
    }
    const auto generated_at = trim_eol(command_output("date -u +%Y-%m-%dT%H:%M:%SZ"));
    write(public_dir / "catalogue" / "repository.json",
          "{\"name\":\"Infiltrator Software\",\"suite\":\"beta\","
          "\"stable_reserved\":true,"
          "\"signed\":" + std::string(signed_repo ? "true" : "false") +
          ",\"history_limit\":5,\"app_count\":" +
          std::to_string(catalogue_items.size()) +
          ",\"package_version_count\":" + std::to_string(package_version_count) +
          ",\"generated_at\":\"" + json_escape(generated_at) + "\"}\n");
    std::cout << "Built " << catalogue_items.size() << " applications in " << public_dir << '\n';
    return 0;
  }
int main(int argc, char** argv) {
  try {
    if (argc >= 2 && std::string(argv[1]) == "validate-deb") {
      if (argc != 6 && argc != 8) {
        std::cerr << "usage: repository-tool validate-deb FILE RELEASE_TAG PACKAGE_REGEX ARCHITECTURE [ASSET VERSION_REGEX]\n";
        return 2;
      }
      const auto version = argc == 8
        ? package_version_from_identity(argv[3], argv[6], argv[7])
        : release_version(argv[3]);
      check_deb_expected(fs::path(argv[2]), version, argv[4], argv[5]);
      return 0;
    }
    if (argc != 2) { std::cerr << "usage: repository-tool <materialize|sync-intune|publish|validate-deb>\n"; return 2; }
    fs::path root;
    if (const char* configured = std::getenv("REPOSITORY_ROOT"); configured && *configured) {
      root = fs::absolute(configured);
    } else {
      root = fs::current_path();
      if (!fs::exists(root / "catalogue"))
        root = fs::absolute(fs::path(argv[0])).parent_path().parent_path();
    }
    const std::string command = argv[1];
    if (command == "materialize") return materialize(root);
    if (command == "sync-intune") return sync_intune(root);
    if (command == "publish") return publish(root);
    throw std::runtime_error("unknown command: " + command);
  } catch (const std::exception& error) {
    std::cerr << "repository-tool: " << error.what() << '\n';
    return 1;
  }
}
