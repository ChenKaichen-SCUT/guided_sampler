#pragma once
#include <string>
namespace a2 { namespace r4 {
// Shared by the actual native adapter and host adapter; manager-local ids never
// cross the sidecar. The native adapter supplies Z3's real is_skolem() flag.
inline std::string declaration_identity(char sort,bool numerical,std::string const& name,bool skolem){return std::string(skolem?"SKOLEM:":"")+std::string(1,sort)+(numerical?"#":"$")+std::to_string(name.size())+":"+name;}
}}
