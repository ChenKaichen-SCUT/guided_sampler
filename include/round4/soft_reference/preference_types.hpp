#pragma once
// Included inside a2. Owned typed values only; no solver/AST objects.
namespace r4 {
enum class Policy { Legacy, Reference, Coverage };
struct QueryPreferences {
 Policy policy=Policy::Legacy;
 std::map<std::string,Big> reference;
 std::string hard_hash,reference_hash;
 unsigned hard_count=0,reference_count=0,source_query=0;
};
}
