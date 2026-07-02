// Winter AI - C++ formatting engine
// Real C++, compiled ahead-of-time with g++ in the Docker build stage,
// not simulated. Formats a final answer into an engine-ready payload
// (originally designed for Unreal Engine blueprint/UE_INSTR consumption).
//
// Usage: ./formatter "<text>"
// Prints JSON: {"payload": "UE_INSTR(\"...\")", "length": N, "engine": "cpp"}

#include <iostream>
#include <string>
#include <cctype>

static std::string sanitize(const std::string& in, size_t max_len) {
    std::string out;
    out.reserve(in.size());
    for (unsigned char c : in) {
        // Keep printable ASCII, common punctuation, and UTF-8 continuation/lead bytes
        // (>=0x80) so accented EN/FR/RW text passes through untouched.
        bool keep = std::isalnum(c) || c == ' ' || c == '-' || c == '.' ||
                    c == ',' || c == '!' || c == '?' || c == '\'' || c >= 0x80;
        if (keep) out += static_cast<char>(c);
        if (out.size() >= max_len) break;
    }
    return out;
}

static std::string json_escape(const std::string& in) {
    std::string out;
    for (char c : in) {
        if (c == '"' ) out += "\\\"";
        else if (c == '\\') out += "\\\\";
        else out += c;
    }
    return out;
}

int main(int argc, char** argv) {
    std::string text = (argc > 1) ? argv[1] : "";
    std::string safe = sanitize(text, 240);
    std::string payload = "UE_INSTR(\"" + safe + "\")";
    std::cout << "{\"payload\": \"" << json_escape(payload)
               << "\", \"length\": " << payload.size()
               << ", \"engine\": \"cpp\"}" << std::endl;
    return 0;
}
