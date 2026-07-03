// ============================================================================
// Winter AI -- C++ Fuzzy Scorer + Unreal Engine Remote-Control Bridge
// (compiled native, real Levenshtein DP algorithm)
//
// Two real jobs:
//   1) Fast fuzzy string distance -- used as a fallback matcher when the
//      Python TF-IDF layer and the Prolog exact-keyword layer both score low.
//   2) Emits a structured instruction payload in the shape expected by
//      Unreal Engine's Remote Control HTTP API (see Epic's "Remote Control
//      API" plugin), so a UE project can subscribe to Winter AI's replies and
//      drive an NPC/blueprint from them. This binary does NOT embed or run
//      Unreal Engine itself -- it produces a payload UE's plugin can consume.
//
// Invoked as: ./engine <query> <candidate1> [candidate2 ...]
// ============================================================================
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <cctype>

static int levenshtein(const std::string& a, const std::string& b) {
    const size_t n = a.size(), m = b.size();
    std::vector<std::vector<int>> dp(n + 1, std::vector<int>(m + 1, 0));
    for (size_t i = 0; i <= n; ++i) dp[i][0] = static_cast<int>(i);
    for (size_t j = 0; j <= m; ++j) dp[0][j] = static_cast<int>(j);
    for (size_t i = 1; i <= n; ++i) {
        for (size_t j = 1; j <= m; ++j) {
            int cost = (std::tolower(a[i - 1]) == std::tolower(b[j - 1])) ? 0 : 1;
            dp[i][j] = std::min({ dp[i - 1][j] + 1,
                                   dp[i][j - 1] + 1,
                                   dp[i - 1][j - 1] + cost });
        }
    }
    return dp[n][m];
}

static std::string sanitize_for_payload(const std::string& s) {
    std::string out;
    out.reserve(s.size());
    for (unsigned char c : s) {
        if (c == '"' || c == '\\') { out += '\\'; out += static_cast<char>(c); }
        else if (c == '\n') { out += ' '; }
        else { out += static_cast<char>(c); }
    }
    if (out.size() > 160) out = out.substr(0, 160);
    return out;
}

int main(int argc, char** argv) {
    std::cout << "ENGINE: C++ (native, compiled)\n";
    if (argc < 2) {
        std::cout << "STATUS: no_input\n";
        return 0;
    }
    std::string query = argv[1];
    std::string best_candidate;
    int best_dist = -1;

    for (int i = 2; i < argc; ++i) {
        std::string cand = argv[i];
        int d = levenshtein(query, cand);
        if (best_dist == -1 || d < best_dist) { best_dist = d; best_candidate = cand; }
    }

    if (best_dist >= 0) {
        std::cout << "BEST_MATCH: " << best_candidate << "\n";
        std::cout << "EDIT_DISTANCE: " << best_dist << "\n";
    } else {
        std::cout << "BEST_MATCH: none\n";
        std::cout << "EDIT_DISTANCE: -1\n";
    }

    std::string payload = sanitize_for_payload(query);
    std::cout << "UE_REMOTE_CONTROL_PAYLOAD: {\"ObjectPath\":\"/Game/WinterAI/BP_Assistant\","
                 "\"FunctionName\":\"ReceiveWinterAIReply\","
                 "\"Parameters\":{\"Text\":\"" << payload << "\"}}\n";
    std::cout << "TRACE: dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost)  // Levenshtein DP\n";
    return 0;
}
