# -*- coding: utf-8 -*-
"""
mcp_resolver.py — 通过 UE Editor MCP 在线解析 BP 的 GetModuleName 返回值

适用场景：BP 自身重载了 `GetModuleName` 函数图、Return Node 接的是字符串字面量
（不是 BP graph 拼接），但这个字面量没落到 .uasset 的 FName 表（罕见但存在）。

工作模式：
    1. 通过 IPC 写一个 JSON 请求文件（包含 BP path 列表）
    2. 让主脚本通过命令行 / 调用者用 Cursor MCP 工具 (CallMcpTool) 调用：
         action_id: graph.describe  (or graph.describe_enhanced)
         params:    blueprint_name, graph_name="GetModuleName"
    3. 解析 Return Node (`K2Node_FunctionResult`) 的 ModuleName 输入 pin 的 default_value
    4. 写一个回填 JSON 文件给主脚本读

由于这个 Python 脚本本身不能直接调用 Cursor 的 MCP，我们采用：
    - 提供一个独立 CLI 子命令 `mcp-batch-prompt`，让用户/AI 介入用 MCP 跑完一批
    - 主脚本的 --use-mcp 模式：先离线扫，输出一份 `pending_mcp_resolution.json`
      列出所有需要 MCP 验证的 BP；用户/AI 用 MCP 跑完后，再传 `--apply-mcp-result <json>`
      把真实数据合并回 CSV

这种"半离线 + 半在线"模式适合 Cursor agent 工作流：
    - 静态分析永远跑得通
    - MCP 介入由调用者（agent 或人）按需触发
    - 不强制依赖在线编辑器
"""

import json
import os
import re
from pathlib import Path


def parse_describe_response(response, function_name="GetModuleName"):
    """Given a graph.describe (or graph.describe_enhanced) JSON response,
    extract the FString literal returned by `function_name`'s Return Node.

    Strategy:
      Find the K2Node_FunctionResult node. It has an input pin
      `FullModuleName` (or whatever the BP author named the output).
      The pin's `default_value` is the literal returned (if any).
      OR the pin is connected to a string-constant node — walk back one hop.

    Returns the literal string, or None if not statically resolvable.
    """
    if not response or not isinstance(response, dict):
        return None
    if not response.get("success"):
        return None
    nodes = response.get("nodes") or []
    if not nodes and "graph" in response:
        nodes = response["graph"].get("nodes", [])

    # Build node lookup
    by_id = {n.get("node_id"): n for n in nodes if n.get("node_id")}

    # Find the Return node
    for node in nodes:
        if node.get("node_class") == "K2Node_FunctionResult":
            for pin in node.get("pins", []):
                if pin.get("direction") != "input":
                    continue
                # Check default_value first
                dv = pin.get("default_value", "")
                if dv and dv.strip() and "." in dv:
                    return dv.strip()
                # Walk back through linked_to
                linked = pin.get("linked_to", [])
                for link in linked:
                    src_node = by_id.get(link.get("node_id"))
                    if not src_node:
                        continue
                    cls = src_node.get("node_class", "")
                    if cls in ("K2Node_MakeLiteralString", "K2Node_VariableGet"):
                        for p in src_node.get("pins", []):
                            if p.get("direction") == "output":
                                v = p.get("default_value", "")
                                if v and "." in v:
                                    return v.strip()
            return None
    return None


def write_pending_request(pending_bps, out_path):
    """Write a JSON file describing which BPs still need MCP resolution.

    pending_bps: list[dict] with keys:
        - asset_short_name (e.g. 'BP_FootprintComponent')
        - asset_pkg_path   (e.g. '/Game/LetsGo3C/.../BP_FootprintComponent')
    """
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "instructions": (
            "For each pending BP, call user-ue-editor-mcp action 'graph.describe' "
            "with blueprint_name=<asset_pkg_path> and graph_name='GetModuleName'. "
            "Pipe the response into parse_describe_response() and assemble "
            "resolved_module_paths.json with shape: "
            "[ { 'asset_short_name': '...', 'resolved_module': '...' or None } ]. "
            "Then pass --apply-mcp-result <path> to scan_3c_lua_bindings.py."
        ),
        "pending": pending_bps,
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return out_path


def load_mcp_result(path):
    """Load a JSON of MCP resolution results.

    Expected shape:
        [ {"asset_short_name": "BP_Foo", "resolved_module": "LetsGo.Script..."}, ... ]
    or
        {"resolved": { "BP_Foo": "LetsGo.Script..." }, ... }
    Returns dict: {asset_short_name -> resolved_module}
    """
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return {}
    out = {}
    if isinstance(data, list):
        for row in data:
            if isinstance(row, dict):
                name = row.get("asset_short_name")
                mod = row.get("resolved_module")
                if name and mod:
                    out[name] = mod
    elif isinstance(data, dict):
        # Nested form
        resolved = data.get("resolved") or data
        if isinstance(resolved, dict):
            for k, v in resolved.items():
                if isinstance(v, str) and v:
                    out[k] = v
    return out
