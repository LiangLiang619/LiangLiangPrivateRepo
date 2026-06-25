"""
lua_scanner.py — Scan Lua files for external dependencies (8 categories):
  1. require cross-repo references
  1b. UE4.Class external inheritance
  2. Hardcoded /Game/ asset paths
  3. Implicit global variable coupling (_MOE.*, _G.LetsGo*, etc.)
  3a. MOE_3C metatable fallback fields (resolve to _MOE at runtime)
  4. Config/Tables audit (MOE_3C.Config.X / MOE_3C.Tables.X)
  5. Event key origin audit (EventEnum.X)
  6. UI/WindowName coupling
  7. Business keyword presence in function names
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Set

# ---------------------------------------------------------------------------
# Whitelist definitions
# ---------------------------------------------------------------------------

REQUIRE_WHITELIST_PREFIXES = (
    "LetsGo3C.",
    "LetsGoSDK.",
    "UE4.",
    "UnLua.",
)

LUA_STDLIB_MODULES: Set[str] = {
    "string", "table", "math", "io", "os", "coroutine",
    "package", "debug", "utf8", "bit", "bit32", "ffi", "jit",
}

ASSET_PATH_WHITELIST_PREFIXES = (
    "/Game/LetsGo3C/",
    "/Game/LetsGoSDK/",
    "/Game/Engine/",
)

ASSET_PATH_IGNORE_PREFIXES = (
    "/Script/",
    "/Engine/",
)

GLOBAL_WHITELIST_PREFIXES = (
    "MOE_3C.",
    "MOE_3C",
    "_G.LetsGoSDK",
)

# MOE_3C fields that fallback to _MOE at runtime via __index or direct assignment
MOE_3C_EXTERNAL_FIELDS: Set[str] = {
    "DsInstance", "LobbyUtils", "ItemEffectUtil", "HomeGame", "UGC",
    "WindowName", "SocketNameEnum", "UGCGameStatic", "GasAbilityManager",
}

# Business keywords from 3C migration skill (case-insensitive matching)
BUSINESS_KEYWORDS: List[str] = [
    "Farm", "Arena", "UGC", "Chase", "Chest", "Home",
    "StarP", "Community", "Lobby", "Commercial",
]

# Regex for extracting event key definitions from SDK event files
RE_EVENT_DEF_TABLE = re.compile(r"""(\w+)\s*=\s*['"]([^'"]+)['"]""")
RE_EVENT_DEF_ASSIGN = re.compile(r"""(\w+)\.(\w+)\s*=\s*['"]([^'"]+)['"]""")


def load_sdk_event_keys(content_root: Path) -> Set[str]:
    """Load all event keys defined in SDK event files (whitelist for event audit)."""
    sdk_event_files = [
        content_root / "LetsGoSDK" / "Script" / "Core" / "Event" / "CommonEventEnum.lua",
        content_root / "LetsGoSDK" / "Script" / "StartUp" / "Event" / "StartUpEventEnum.lua",
    ]
    known_keys: Set[str] = set()

    for fpath in sdk_event_files:
        if not fpath.is_file():
            continue
        try:
            raw = fpath.read_bytes()
            if raw.startswith(b'\xef\xbb\xbf'):
                raw = raw[3:]
            source = raw.decode("utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue

        for line in source.split("\n"):
            stripped = line.strip()
            if stripped.startswith("--"):
                continue

            # Match: CommonEventEnum.KEY = "value" or StartUpEventEnum.KEY = "value"
            m = RE_EVENT_DEF_ASSIGN.match(stripped)
            if m:
                known_keys.add(m.group(2))
                continue

            # Match table keys: KEY = "value"
            m = RE_EVENT_DEF_TABLE.match(stripped)
            if m:
                known_keys.add(m.group(1))

        # Also match nested table keys like EventNetState.OnXxx, DSA.OnXxx
        # by extracting all string assignments inside the file
        for m in re.finditer(r"""(\w+)\s*=\s*['"]([^'"]+)['"]""", source):
            known_keys.add(m.group(1))

    return known_keys


def load_sdk_commondefine_keys(content_root: Path) -> Set[str]:
    """Load top-level field names defined in SDK CommonDefine files (whitelist for audit)."""
    sdk_define_files = [
        content_root / "LetsGoSDK" / "Script" / "Common" / "Define" / "LetsGoSDKCommonDefine.lua",
        content_root / "LetsGoSDK" / "Script" / "StartUp" / "Common" / "CommonDefine.lua",
    ]
    known_fields: Set[str] = set()

    # Match top-level table field assignments: E_ITEM_TYPE = { or FieldName = value
    re_field = re.compile(r"""^\s*(\w+)\s*=""")
    # Match Module.Field = assignments
    re_module_field = re.compile(r"""^\s*\w+\.(\w+)\s*=""")

    for fpath in sdk_define_files:
        if not fpath.is_file():
            continue
        try:
            raw = fpath.read_bytes()
            if raw.startswith(b'\xef\xbb\xbf'):
                raw = raw[3:]
            source = raw.decode("utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue

        for line in source.split("\n"):
            stripped = line.strip()
            if stripped.startswith("--"):
                continue
            m = re_module_field.match(stripped)
            if m:
                known_fields.add(m.group(1))
                continue
            m = re_field.match(stripped)
            if m:
                known_fields.add(m.group(1))

    return known_fields

# ---------------------------------------------------------------------------
# Category classification
# ---------------------------------------------------------------------------


def classify_require(module: str) -> str:
    if module.startswith("LetsGo."):
        return "LetsGo"
    if module.startswith("Feature."):
        return "Feature"
    if module.startswith("ProjectT."):
        return "ProjectT"
    return "Other"


def classify_asset_path(path: str) -> str:
    if path.startswith("/Game/Feature/ProjectT/") or path.startswith("/Game/ProjectT/"):
        return "ProjectT"
    if path.startswith("/Game/LetsGo/"):
        return "LetsGo"
    if path.startswith("/Game/Feature/"):
        return "Feature"
    return "Other"


def suggest_action_require(module: str, category: str) -> str:
    if category == "LetsGo":
        return "搬迁到 LetsGo3C 或替换为 3C 内部路径"
    if category == "Feature":
        return "解耦或搬迁相关模块到 3C"
    if category == "ProjectT":
        return "移除 ProjectT 依赖或抽象接口"
    return "检查是否需要内化"


def suggest_action_global(expr: str) -> str:
    return "替换为 MOE_3C 本地实现或通过接口注入"


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

RE_REQUIRE_STATIC = re.compile(
    r"""require\s*\(\s*['"]([^'"\s]+)['"]\s*\)""",
)

RE_REQUIRE_DYNAMIC = re.compile(
    r"""require\s*\(\s*(?!['"])(.+?)\s*\)""",
)

RE_ASSET_PATH = re.compile(
    r"""['"](/Game/[\w/._+-]+)['"]""",
)

RE_GLOBAL_MOE = re.compile(
    r"""(?<!\w)_MOE\.([A-Za-z_]\w*)""",
)

RE_GLOBAL_G = re.compile(
    r"""(?<!\w)_G\.((?:LetsGo|Feature|ProjectT)\w*)""",
)

# UE4.Class("parent_path") inheritance
RE_UE4_CLASS = re.compile(
    r"""UE4\.Class\s*\(\s*['"]([^'"]+)['"]\s*\)""",
)

# MOE_3C.<field> access (for fallback detection)
RE_MOE3C_FIELD = re.compile(
    r"""(?<!\w)MOE_3C\.([A-Za-z_]\w*)""",
)

# MOE_3C.Config.<table> or MOE_3C.Tables.<table>
RE_MOE3C_CONFIG = re.compile(
    r"""(?<!\w)MOE_3C\.Config\.([A-Za-z_]\w*)""",
)
RE_MOE3C_TABLES = re.compile(
    r"""(?<!\w)MOE_3C\.Tables\.([A-Za-z_]\w*)""",
)

# MOE_3C.CommonDefine.<EnumOrField> access
RE_MOE3C_COMMONDEFINE = re.compile(
    r"""(?<!\w)MOE_3C\.CommonDefine\.([A-Za-z_]\w*)""",
)

# Event key: (MOE_3C|_MOE).EventEnum.XXX or nested (MOE_3C|_MOE).EventEnum.Namespace.XXX
RE_EVENT_KEY = re.compile(
    r"""(?<!\w)(?:MOE_3C|_MOE)\.EventEnum\.([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)""",
)

# Event usage type detection
RE_EVENT_REGISTER = re.compile(
    r"""(?:MOE_3C|_MOE)\.EventManager:RegisterEvent""",
)
RE_EVENT_DISPATCH = re.compile(
    r"""(?:MOE_3C|_MOE)\.EventManager:DispatchEvent""",
)
RE_EVENT_UNREGISTER = re.compile(
    r"""(?:MOE_3C|_MOE)\.EventManager:UnRegisterEvent""",
)

# UI coupling: UIManager calls and WindowName access
RE_UI_MANAGER = re.compile(
    r"""(?<!\w)(?:MOE_3C|_MOE)\.UIManager:(\w+)""",
)
RE_WINDOW_NAME = re.compile(
    r"""(?<!\w)(?:MOE_3C|_MOE)\.WindowName\.(\w+)""",
)
RE_WINDOW_NAME_BRACKET = re.compile(
    r"""(?<!\w)(?:MOE_3C|_MOE)\.WindowName\[""",
)

# Function definition (for business keyword scanning)
RE_FUNC_DEF = re.compile(
    r"""function\s+(?:\w+[.:])?\s*(\w+)\s*\(""",
)

# Block comment stripping: --[[ ... ]] (greedy minimal)
RE_BLOCK_COMMENT = re.compile(r"--\[\[.*?\]\]", re.DOTALL)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RequireHit:
    file: str
    line: int
    require_module: str
    category: str
    suggested_action: str


@dataclass
class HardpathHit:
    file: str
    line: int
    hardcoded_path: str
    category: str
    suggested_action: str


@dataclass
class GlobalHit:
    global_expr: str
    usage_count: int = 0
    locations: List[str] = field(default_factory=list)
    suggested_action: str = ""


@dataclass
class DynamicRequireWarning:
    file: str
    line: int
    expression: str


@dataclass
class ConfigTableHit:
    table_name: str
    access_type: str  # "Config" or "Tables"
    usage_count: int = 0
    files: List[str] = field(default_factory=list)


@dataclass
class CommonDefineHit:
    define_name: str
    usage_count: int = 0
    files: List[str] = field(default_factory=list)


@dataclass
class EventKeyHit:
    event_key: str
    usage_type: str  # "Register" / "Dispatch" / "UnRegister" / "Access"
    usage_count: int = 0
    files: List[str] = field(default_factory=list)


@dataclass
class UICouplingHit:
    file: str
    line: int
    call_type: str  # "OpenWindow" / "IsWindowOpened" / "CloseWindow" / "WindowName.X"
    window_name: str
    suggested_action: str = "3C 基类不应包含 UI 调用，下沉到业务子类 override"


@dataclass
class BizKeywordHit:
    file: str
    line: int
    keyword: str
    context: str  # function_name / require_path / module_path
    suggested_action: str = "业务逻辑（命中关键词），应下沉到业务子类或不应存在于 3C 仓库"


@dataclass
class LuaScanResult:
    require_hits: List[RequireHit] = field(default_factory=list)
    hardpath_hits: List[HardpathHit] = field(default_factory=list)
    global_hits: Dict[str, GlobalHit] = field(default_factory=dict)
    dynamic_warnings: List[DynamicRequireWarning] = field(default_factory=list)
    config_table_hits: Dict[str, ConfigTableHit] = field(default_factory=dict)
    event_key_hits: Dict[str, EventKeyHit] = field(default_factory=dict)
    common_define_hits: Dict[str, CommonDefineHit] = field(default_factory=dict)
    ui_coupling_hits: List[UICouplingHit] = field(default_factory=list)
    biz_keyword_hits: List[BizKeywordHit] = field(default_factory=list)
    files_scanned: int = 0


# ---------------------------------------------------------------------------
# Core scanning logic
# ---------------------------------------------------------------------------


def _strip_comments(source: str) -> List[Tuple[int, str]]:
    """Strip block comments, return list of (original_line_number, line_content)."""
    stripped = RE_BLOCK_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), source)
    lines = stripped.split("\n")
    result = []
    for i, line in enumerate(lines, start=1):
        comment_pos = -1
        in_string = None
        j = 0
        while j < len(line):
            ch = line[j]
            if in_string is None:
                if ch in ('"', "'"):
                    in_string = ch
                elif ch == '-' and j + 1 < len(line) and line[j + 1] == '-':
                    comment_pos = j
                    break
            else:
                if ch == '\\':
                    j += 1
                elif ch == in_string:
                    in_string = None
            j += 1
        if comment_pos >= 0:
            result.append((i, line[:comment_pos]))
        else:
            result.append((i, line))
    return result


def _is_require_whitelisted(module: str, extra_prefixes: Tuple[str, ...] = ()) -> bool:
    if module in LUA_STDLIB_MODULES:
        return True
    if "." not in module:
        return True
    all_prefixes = REQUIRE_WHITELIST_PREFIXES + extra_prefixes
    for prefix in all_prefixes:
        if module.startswith(prefix):
            return True
    return False


def _is_asset_path_whitelisted(path: str, extra_prefixes: Tuple[str, ...] = ()) -> bool:
    for prefix in ASSET_PATH_IGNORE_PREFIXES:
        if path.startswith(prefix):
            return True
    all_prefixes = ASSET_PATH_WHITELIST_PREFIXES + extra_prefixes
    for prefix in all_prefixes:
        if path.startswith(prefix):
            return True
    return False


def _is_global_whitelisted(expr: str) -> bool:
    for prefix in GLOBAL_WHITELIST_PREFIXES:
        if expr.startswith(prefix):
            return True
    return False


@dataclass
class _FileScanResult:
    """Internal per-file scan result aggregator."""
    require_hits: List[RequireHit] = field(default_factory=list)
    hardpath_hits: List[HardpathHit] = field(default_factory=list)
    global_locs: Dict[str, List[str]] = field(default_factory=dict)
    dynamic_warnings: List[DynamicRequireWarning] = field(default_factory=list)
    config_locs: Dict[str, List[str]] = field(default_factory=dict)
    event_locs: Dict[str, List[str]] = field(default_factory=dict)
    commondefine_locs: Dict[str, List[str]] = field(default_factory=dict)
    ui_hits: List[UICouplingHit] = field(default_factory=list)
    biz_hits: List[BizKeywordHit] = field(default_factory=list)


def _match_business_keyword(text: str) -> str:
    """Return the first business keyword found in text (case-insensitive), or empty string."""
    text_lower = text.lower()
    for kw in BUSINESS_KEYWORDS:
        if kw.lower() in text_lower:
            return kw
    return ""


def scan_lua_file(
    filepath: Path,
    repo_root: Path,
    extra_require_prefixes: Tuple[str, ...] = (),
    extra_asset_prefixes: Tuple[str, ...] = (),
    moe3c_fallback_fields: Set[str] = None,
) -> _FileScanResult:
    """Scan a single Lua file, return hits for all categories."""
    result = _FileScanResult()
    fallback_fields = moe3c_fallback_fields if moe3c_fallback_fields is not None else MOE_3C_EXTERNAL_FIELDS

    try:
        raw = filepath.read_bytes()
        if raw.startswith(b'\xef\xbb\xbf'):
            raw = raw[3:]
        source = raw.decode("utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return result

    rel_path = str(filepath.relative_to(repo_root)).replace("\\", "/")
    lines = _strip_comments(source)

    # Check if file path contains business keyword
    path_kw = _match_business_keyword(rel_path)
    if path_kw:
        result.biz_hits.append(BizKeywordHit(
            file=rel_path, line=0, keyword=path_kw,
            context=f"file_path:{rel_path}",
            suggested_action="文件路径命中业务关键词，整文件可能不应存在于 3C 仓库",
        ))

    for line_no, line_content in lines:
        if not line_content.strip():
            continue

        # Category 1: require
        for m in RE_REQUIRE_STATIC.finditer(line_content):
            module = m.group(1)
            if not _is_require_whitelisted(module, extra_require_prefixes):
                cat = classify_require(module)
                result.require_hits.append(RequireHit(
                    file=rel_path,
                    line=line_no,
                    require_module=module,
                    category=cat,
                    suggested_action=suggest_action_require(module, cat),
                ))
                # Also check require target for business keyword
                req_kw = _match_business_keyword(module)
                if req_kw:
                    result.biz_hits.append(BizKeywordHit(
                        file=rel_path, line=line_no, keyword=req_kw,
                        context=f"require_path:{module}",
                    ))

        # Dynamic require detection
        for m in RE_REQUIRE_DYNAMIC.finditer(line_content):
            if RE_REQUIRE_STATIC.search(line_content):
                continue
            result.dynamic_warnings.append(DynamicRequireWarning(
                file=rel_path,
                line=line_no,
                expression=m.group(1).strip(),
            ))

        # Category 1b: UE4.Class inheritance
        for m in RE_UE4_CLASS.finditer(line_content):
            parent = m.group(1)
            if not _is_require_whitelisted(parent, extra_require_prefixes):
                cat = classify_require(parent)
                result.require_hits.append(RequireHit(
                    file=rel_path,
                    line=line_no,
                    require_module=parent,
                    category=cat,
                    suggested_action="搬迁父类到 3C 或解耦继承关系（UE4.Class 继承）",
                ))

        # Category 2: hardcoded asset path
        for m in RE_ASSET_PATH.finditer(line_content):
            path = m.group(1)
            if not _is_asset_path_whitelisted(path, extra_asset_prefixes):
                cat = classify_asset_path(path)
                result.hardpath_hits.append(HardpathHit(
                    file=rel_path,
                    line=line_no,
                    hardcoded_path=path,
                    category=cat,
                    suggested_action="替换为 3C/SDK 内部路径或参数化",
                ))

        # Category 3: global coupling (_MOE.*)
        for m in RE_GLOBAL_MOE.finditer(line_content):
            expr = f"_MOE.{m.group(1)}"
            if not _is_global_whitelisted(expr):
                loc = f"{rel_path}:{line_no}"
                result.global_locs.setdefault(expr, []).append(loc)

        for m in RE_GLOBAL_G.finditer(line_content):
            expr = f"_G.{m.group(1)}"
            if not _is_global_whitelisted(expr):
                loc = f"{rel_path}:{line_no}"
                result.global_locs.setdefault(expr, []).append(loc)

        # Category 3a: MOE_3C metatable fallback fields
        for m in RE_MOE3C_FIELD.finditer(line_content):
            field_name = m.group(1)
            if field_name in fallback_fields:
                expr = f"MOE_3C.{field_name}"
                loc = f"{rel_path}:{line_no}"
                result.global_locs.setdefault(expr, []).append(loc)

        # Category 4: Config/Tables audit
        for m in RE_MOE3C_CONFIG.finditer(line_content):
            table_name = m.group(1)
            loc = f"{rel_path}:{line_no}"
            result.config_locs.setdefault(f"Config.{table_name}", []).append(loc)

        for m in RE_MOE3C_TABLES.finditer(line_content):
            table_name = m.group(1)
            loc = f"{rel_path}:{line_no}"
            result.config_locs.setdefault(f"Tables.{table_name}", []).append(loc)

        # Category 4b: CommonDefine access
        for m in RE_MOE3C_COMMONDEFINE.finditer(line_content):
            define_name = m.group(1)
            loc = f"{rel_path}:{line_no}"
            result.commondefine_locs.setdefault(define_name, []).append(loc)

        # Category 5: Event key origin
        for m in RE_EVENT_KEY.finditer(line_content):
            key = m.group(1)
            loc = f"{rel_path}:{line_no}"
            result.event_locs.setdefault(key, []).append(loc)

        # Category 6: UI/WindowName coupling
        for m in RE_UI_MANAGER.finditer(line_content):
            call_type = m.group(1)
            result.ui_hits.append(UICouplingHit(
                file=rel_path, line=line_no,
                call_type=call_type, window_name="",
            ))

        for m in RE_WINDOW_NAME.finditer(line_content):
            wnd_name = m.group(1)
            result.ui_hits.append(UICouplingHit(
                file=rel_path, line=line_no,
                call_type=f"WindowName.{wnd_name}", window_name=wnd_name,
            ))

        if RE_WINDOW_NAME_BRACKET.search(line_content):
            result.ui_hits.append(UICouplingHit(
                file=rel_path, line=line_no,
                call_type="WindowName[dynamic]", window_name="(dynamic)",
            ))

        # Category 7: Business keyword in function names
        for m in RE_FUNC_DEF.finditer(line_content):
            func_name = m.group(1)
            kw = _match_business_keyword(func_name)
            if kw:
                result.biz_hits.append(BizKeywordHit(
                    file=rel_path, line=line_no, keyword=kw,
                    context=f"function:{func_name}",
                ))

    return result


def scan_lua_directory(
    repo_root: Path,
    lua_globs: List[str],
    extra_require_prefixes: Tuple[str, ...] = (),
    extra_asset_prefixes: Tuple[str, ...] = (),
    moe3c_fallback_fields: Set[str] = None,
    sdk_event_keys: Set[str] = None,
    sdk_commondefine_keys: Set[str] = None,
) -> LuaScanResult:
    """Scan all Lua files under repo_root matching lua_globs."""
    result = LuaScanResult()
    all_global_locs: Dict[str, List[str]] = {}
    all_config_locs: Dict[str, List[str]] = {}
    all_event_locs: Dict[str, List[str]] = {}
    all_commondefine_locs: Dict[str, List[str]] = {}

    seen_files: Set[Path] = set()
    for pattern in lua_globs:
        for lua_file in repo_root.glob(pattern):
            if lua_file in seen_files:
                continue
            seen_files.add(lua_file)
            if not lua_file.is_file():
                continue

            file_result = scan_lua_file(
                lua_file, repo_root, extra_require_prefixes, extra_asset_prefixes,
                moe3c_fallback_fields,
            )
            result.require_hits.extend(file_result.require_hits)
            result.hardpath_hits.extend(file_result.hardpath_hits)
            result.dynamic_warnings.extend(file_result.dynamic_warnings)
            result.ui_coupling_hits.extend(file_result.ui_hits)
            result.biz_keyword_hits.extend(file_result.biz_hits)

            for expr, locs in file_result.global_locs.items():
                all_global_locs.setdefault(expr, []).extend(locs)

            for key, locs in file_result.config_locs.items():
                all_config_locs.setdefault(key, []).extend(locs)

            for key, locs in file_result.event_locs.items():
                all_event_locs.setdefault(key, []).extend(locs)

            for key, locs in file_result.commondefine_locs.items():
                all_commondefine_locs.setdefault(key, []).extend(locs)

    result.files_scanned = len(seen_files)

    # Aggregate globals (including MOE_3C fallback fields)
    for expr, locs in sorted(all_global_locs.items(), key=lambda x: -len(x[1])):
        if expr.startswith("MOE_3C."):
            action = "运行时回退到 _MOE，需替换为 SDK 来源或本地实现"
        else:
            action = suggest_action_global(expr)
        result.global_hits[expr] = GlobalHit(
            global_expr=expr,
            usage_count=len(locs),
            locations=locs,
            suggested_action=action,
        )

    # Aggregate Config/Tables
    for key, locs in sorted(all_config_locs.items(), key=lambda x: -len(x[1])):
        parts = key.split(".", 1)
        access_type = parts[0]
        table_name = parts[1] if len(parts) > 1 else key
        unique_files = sorted(set(loc.rsplit(":", 1)[0] for loc in locs))
        result.config_table_hits[key] = ConfigTableHit(
            table_name=table_name,
            access_type=access_type,
            usage_count=len(locs),
            files=unique_files,
        )

    # Aggregate Event keys (filter out SDK-defined keys)
    for key, locs in sorted(all_event_locs.items(), key=lambda x: -len(x[1])):
        # Check if key (or its leaf part for nested keys like MoeCharacterEvents.OnXxx)
        # is defined in SDK event files
        leaf_key = key.rsplit(".", 1)[-1] if "." in key else key
        if sdk_event_keys and (key in sdk_event_keys or leaf_key in sdk_event_keys):
            continue
        unique_files = sorted(set(loc.rsplit(":", 1)[0] for loc in locs))
        result.event_key_hits[key] = EventKeyHit(
            event_key=key,
            usage_type="Access",
            usage_count=len(locs),
            files=unique_files,
        )

    # Aggregate CommonDefine (filter out SDK-defined fields)
    for key, locs in sorted(all_commondefine_locs.items(), key=lambda x: -len(x[1])):
        if sdk_commondefine_keys and key in sdk_commondefine_keys:
            continue
        unique_files = sorted(set(loc.rsplit(":", 1)[0] for loc in locs))
        result.common_define_hits[key] = CommonDefineHit(
            define_name=key,
            usage_count=len(locs),
            files=unique_files,
        )

    return result
