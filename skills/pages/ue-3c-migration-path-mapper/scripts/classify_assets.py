#!/usr/bin/env python3
"""
Classify 3C migration assets and generate target paths.

Reads a CSV with '外部资产完整路径' column, classifies each asset into
Character/Controller/Camera, determines subdirectory by asset_class,
and outputs a new CSV with '3C仓库目标路径' column appended.

Assets that cannot be classified by path keywords are printed as
[PENDING] lines for the agent to supplement via uasset-analyzer.
"""

import csv
import os
import re
import sys
from datetime import datetime


# ---------------------------------------------------------------------------
# 3C classification rules (path keyword matching, case-insensitive)
# Order: Camera > Controller > Character (first match wins)
# ---------------------------------------------------------------------------

CAMERA_PATTERNS = [
    re.compile(r'/Camera/', re.IGNORECASE),
    re.compile(r'/CineCamera', re.IGNORECASE),
    re.compile(r'_Camera(?![A-Za-z])', re.IGNORECASE),
    re.compile(r'Camera_', re.IGNORECASE),
    re.compile(r'/CCM_', re.IGNORECASE),
    re.compile(r'(?:^|/)BP_Camera', re.IGNORECASE),
    re.compile(r'(?:^|/)Camera[A-Z]', re.IGNORECASE),  # filename starts with Camera (e.g. CameraHighAdjustCurve)
]

CONTROLLER_PATTERNS = [
    re.compile(r'/Controller/', re.IGNORECASE),
    re.compile(r'/PlayerController/', re.IGNORECASE),
    re.compile(r'/AIController/', re.IGNORECASE),
    re.compile(r'(?:^|/)PC_', re.IGNORECASE),
    re.compile(r'(?:^|/)AIC_', re.IGNORECASE),
    re.compile(r'BP_Controller', re.IGNORECASE),
    re.compile(r'BP_PlayerController', re.IGNORECASE),
    re.compile(r'BP_AIController', re.IGNORECASE),
]

CHARACTER_PATTERNS = [
    re.compile(r'/Characters?/', re.IGNORECASE),
    re.compile(r'/Anim', re.IGNORECASE),
    re.compile(r'/Skeleton/', re.IGNORECASE),
    re.compile(r'/Mesh/SK_', re.IGNORECASE),
    re.compile(r'(?:^|/)BP_CH_', re.IGNORECASE),
    re.compile(r'(?:^|/)ABP_CH_', re.IGNORECASE),
    re.compile(r'(?:^|/)AS_CH_', re.IGNORECASE),
    re.compile(r'(?:^|/)AM_CH_', re.IGNORECASE),
    re.compile(r'(?:^|/)SK_', re.IGNORECASE),
    re.compile(r'(?:^|/)BU_', re.IGNORECASE),
    re.compile(r'(?:^|/)OG_', re.IGNORECASE),
    re.compile(r'(?:^|/)PL_', re.IGNORECASE),
    re.compile(r'/AnimCompressSettings/', re.IGNORECASE),
    re.compile(r'AnimNotif', re.IGNORECASE),
    re.compile(r'/FootPrint/', re.IGNORECASE),
    re.compile(r'/BlendSpace', re.IGNORECASE),
    re.compile(r'(?:^|/)BS_CH_', re.IGNORECASE),
    re.compile(r'(?:^|/)ALI_CH_', re.IGNORECASE),
    re.compile(r'(?:^|/)BP_\w*Char\w*Component', re.IGNORECASE),  # BP_*Char*Component → Character
    re.compile(r'(?:^|/)BP_MoeChar', re.IGNORECASE),  # BP_MoeChar* → Character
    re.compile(r'(?:^|/)BP_MainChar', re.IGNORECASE),  # BP_MainChar* → Character
]


def classify_3c(path):
    """Return 'Camera', 'Controller', 'Character', or None."""
    for pat in CAMERA_PATTERNS:
        if pat.search(path):
            return 'Camera'
    for pat in CONTROLLER_PATTERNS:
        if pat.search(path):
            return 'Controller'
    for pat in CHARACTER_PATTERNS:
        if pat.search(path):
            return 'Character'
    return None


# ---------------------------------------------------------------------------
# asset_class inference from path/filename (no MCP needed)
# ---------------------------------------------------------------------------

ASSET_CLASS_RULES = [
    (re.compile(r'(?:^|/)ABP_', re.IGNORECASE), 'AnimBlueprint'),
    (re.compile(r'(?:^|/)ALI_', re.IGNORECASE), 'AnimBlueprint'),
    (re.compile(r'(?:^|/)AS_', re.IGNORECASE), 'AnimSequence'),
    (re.compile(r'(?:^|/)AM_', re.IGNORECASE), 'AnimMontage'),
    (re.compile(r'(?:^|/)BS_', re.IGNORECASE), 'BlendSpace'),
    (re.compile(r'/AnimCompressSettings/', re.IGNORECASE), 'AnimCompressionSettings'),
    (re.compile(r'AnimNotify', re.IGNORECASE), 'AnimNotify'),
    (re.compile(r'(?:^|/)BP_', re.IGNORECASE), 'Blueprint'),
    (re.compile(r'(?:^|/)SK_.*?/Mesh/', re.IGNORECASE), 'SkeletalMesh'),
    (re.compile(r'/Mesh/SK_', re.IGNORECASE), 'SkeletalMesh'),
    (re.compile(r'(?:^|/)SM_.*?/Mesh/', re.IGNORECASE), 'StaticMesh'),
    (re.compile(r'/Mesh/SM_', re.IGNORECASE), 'StaticMesh'),
    (re.compile(r'(?:^|/)MI_', re.IGNORECASE), 'MaterialInstance'),
    (re.compile(r'(?:^|/)MF_', re.IGNORECASE), 'MaterialFunction'),
    (re.compile(r'(?:^|/)M_', re.IGNORECASE), 'Material'),
    (re.compile(r'(?:^|/)T_', re.IGNORECASE), 'Texture'),
    (re.compile(r'(?:^|/)FX_', re.IGNORECASE), 'Effect'),
    (re.compile(r'/Curves?/', re.IGNORECASE), 'CurveFloat'),
]


def infer_asset_class(path):
    """Infer asset_class from path patterns. Returns class string or None."""
    filename = path.rsplit('/', 1)[-1] if '/' in path else path
    for pat, cls in ASSET_CLASS_RULES:
        if pat.search(filename) or pat.search(path):
            return cls
    return None


# ---------------------------------------------------------------------------
# Subdirectory rules
# ---------------------------------------------------------------------------

ANIMATION_CLASSES = {
    'AnimSequence', 'AnimMontage', 'AnimComposite', 'AnimBlueprint',
    'BlendSpace', 'BlendSpace1D', 'AimOffsetBlendSpace',
    'Skeleton', 'PhysicsAsset', 'AnimationAsset',
    'AnimBoneCompressionSettings', 'AnimCurveCompressionSettings',
    'AnimCompressionSettings',
    'AnimNotify', 'AnimNotifyState', 'AnimLinkedInstance',
}

# 按精确 asset_class 映射到 Animation/<二级目录>
ANIMATION_SUBDIR_MAP = {
    'AnimBlueprint': 'AnimBlueprint',
    'AnimBlueprintGeneratedClass': 'AnimBlueprint',
    'AnimLinkedInstance': 'AnimBlueprint',
    'AnimNotify': 'AnimNotify',
    'AnimNotifyState': 'AnimNotify',
    'AnimSequence': 'AnimSequence',
    'AnimMontage': 'AnimMontage',
    'AnimComposite': 'AnimComposite',
    'BlendSpace': 'BlendSpace',
    'BlendSpace1D': 'BlendSpace',
    'AimOffsetBlendSpace': 'BlendSpace',
    'Skeleton': 'Skeleton',
    'PhysicsAsset': 'PhysicsAsset',
    'AnimBoneCompressionSettings': 'CompressionSettings',
    'AnimCurveCompressionSettings': 'CompressionSettings',
    'AnimCompressionSettings': 'CompressionSettings',
    'AnimationAsset': 'Misc',
}

# 文件名前缀回退（当 asset_class 不可知时）
ANIMATION_NAME_PREFIX_MAP = [
    ('ABP_', 'AnimBlueprint'),
    ('ALI_', 'AnimBlueprint'),
    ('AS_', 'AnimSequence'),
    ('AM_', 'AnimMontage'),
    ('BS_', 'BlendSpace'),
    ('AnimNotify', 'AnimNotify'),
]

CONFIG_CLASSES = {
    'DataTable', 'DataAsset', 'CurveTable', 'CurveFloat', 'CurveVector',
    'CurveLinearColor', 'PrimaryDataAsset', 'CompositeDataTable',
}

COMPONENT_KEYWORDS = [
    'Component', 'ActorComponent', 'SceneComponent', 'PrimitiveComponent',
]

ASSET_CLASS_DISPLAY_MAP = {
    'MaterialInstanceConstant': 'MaterialInstance',
    'Texture2D': 'Texture',
    'TextureCube': 'Texture',
    'TextureRenderTarget2D': 'Texture',
    'NiagaraSystem': 'Effect',
    'NiagaraEmitter': 'Effect',
    'ParticleSystem': 'Effect',
    'SoundWave': 'Sound',
    'SoundCue': 'Sound',
    'BlueprintGeneratedClass': 'Blueprint',
}


def determine_subdir(asset_class, c_class, path):
    """Determine subdirectory given asset_class and 3C classification.

    Animation/<二级>: 按精确 class 细分二级目录（AnimBlueprint/AnimNotify/...）
    Config/:          统一配置子目录（取代旧的 ConfigData/）
    Components/:      组件类
    其他:              按 asset_class 命名
    """
    filename = path.rsplit('/', 1)[-1] if '/' in path else path

    if not asset_class:
        # 文件名前缀回退：仅对 Character 类的动画资产生效
        if c_class == 'Character':
            for prefix, anim_subdir in ANIMATION_NAME_PREFIX_MAP:
                if filename.startswith(prefix):
                    return f'Animation/{anim_subdir}'
        last_dir = path.rsplit('/', 2)[-2] if path.count('/') >= 2 else 'Unknown'
        return last_dir

    if any(kw.lower() in filename.lower() or kw.lower() in asset_class.lower()
           for kw in COMPONENT_KEYWORDS):
        return 'Components'

    if asset_class in ANIMATION_CLASSES and c_class == 'Character':
        anim_subdir = ANIMATION_SUBDIR_MAP.get(asset_class, 'Misc')
        return f'Animation/{anim_subdir}'

    if asset_class in CONFIG_CLASSES:
        return 'Config'

    return ASSET_CLASS_DISPLAY_MAP.get(asset_class, asset_class)


# ---------------------------------------------------------------------------
# Path construction
# ---------------------------------------------------------------------------

TARGET_PREFIX = '/Game/LetsGo3C/Assets/Base'


def build_target_path(c_class, subdir, asset_name):
    """Build the full target path."""
    return f'{TARGET_PREFIX}/{c_class}/{subdir}/{asset_name}'


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process_csv(input_path):
    if not os.path.isfile(input_path):
        print(f"ERROR: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_dir = os.path.join(os.path.dirname(input_path), f'{base_name}_3C_mapped_{timestamp}')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, os.path.basename(input_path))

    with open(input_path, 'r', encoding='utf-8-sig', newline='') as fin:
        reader = csv.reader(fin)
        header = next(reader)
        rows = list(reader)

    try:
        path_col_idx = header.index('外部资产完整路径')
    except ValueError:
        print("ERROR: Column '外部资产完整路径' not found in CSV header.", file=sys.stderr)
        print(f"  Available columns: {header}", file=sys.stderr)
        sys.exit(1)

    insert_idx = path_col_idx + 1
    new_header = header[:insert_idx] + ['3C仓库目标路径'] + header[insert_idx:]

    def insert_target(row, value):
        padded = row + [''] * (insert_idx - len(row)) if len(row) < insert_idx else row
        return padded[:insert_idx] + [value] + padded[insert_idx:]

    pending_rows = []
    results = []
    classified_count = 0
    pending_count = 0

    for row_idx, row in enumerate(rows):
        if len(row) <= path_col_idx:
            results.append(insert_target(row, ''))
            continue

        ue_path = row[path_col_idx].strip()
        if not ue_path:
            results.append(insert_target(row, ''))
            continue

        asset_name = ue_path.rsplit('/', 1)[-1] if '/' in ue_path else ue_path

        c_class = classify_3c(ue_path)
        asset_class = infer_asset_class(ue_path)

        if c_class:
            subdir = determine_subdir(asset_class, c_class, ue_path)
            target = build_target_path(c_class, subdir, asset_name)
            results.append(insert_target(row, target))
            classified_count += 1
        else:
            results.append(insert_target(row, '[PENDING]'))
            pending_rows.append((row_idx + 2, asset_name, ue_path))
            pending_count += 1

    with open(out_path, 'w', encoding='utf-8-sig', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(new_header)
        writer.writerows(results)

    print(f'\n=== 3C Migration Path Mapping Results ===')
    print(f'Input:      {input_path}')
    print(f'Output:     {out_path}')
    print(f'Total rows: {len(rows)}')
    print(f'Classified: {classified_count}')
    print(f'Pending:    {pending_count}')

    if pending_rows:
        print(f'\n--- [PENDING] rows (need uasset-analyzer) ---')
        for csv_row, name, path in pending_rows:
            print(f'  Row {csv_row}: {name}  ({path})')

    print(f'\nDone.')
    return out_path, pending_rows


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python classify_assets.py <input.csv>', file=sys.stderr)
        sys.exit(1)
    process_csv(sys.argv[1])
